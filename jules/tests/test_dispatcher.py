"""
Tests for the Jules dispatcher.

Runs under pytest, but also runs standalone via
`python3 jules/tests/test_dispatcher.py`. No real network calls are made.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from jules.dispatcher import (
    AGENT_SIGNATURE,
    ConfigurationError,
    Dispatcher,
    FlaggedIssue,
    FlaggedIssueStore,
    JulesApiError,
    JulesClient,
    PLAYBOOK_NAMES,
    StateTransitionError,
    VALID_STATES,
    VALID_TRANSITIONS,
    _render_prompt,
    classify_failure,
    is_retriable,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_issue(**overrides) -> FlaggedIssue:
    base = dict(
        id="fi_test0000000001",
        type="framework-drift",
        source="human",
        playbook="framework-drift",
        target_repo="ZOLAtheCodeX/aigovops",
        target_branch="main",
        priority="normal",
        state="flagged",
        retry_count=0,
        payload={"note": "test"},
    )
    base.update(overrides)
    return FlaggedIssue(**base)


def _make_playbook_dir(tmp: Path) -> Path:
    pb = tmp / "playbook"
    pb.mkdir(parents=True, exist_ok=True)
    for name in PLAYBOOK_NAMES:
        (pb / f"{name}.md").write_text(
            f"Test playbook body for {name}. "
            f"Issue: {{{{ISSUE_ID}}}} Repo: {{{{TARGET_REPO}}}} "
            f"Branch: {{{{BRANCH_NAME}}}} PR: {{{{PR_TITLE}}}} "
            f"Payload: {{{{PAYLOAD_JSON}}}}",
            encoding="utf-8",
        )
    return pb


# ---------------------------------------------------------------------------
# FlaggedIssue dataclass round-trip
# ---------------------------------------------------------------------------


class TestFlaggedIssue(unittest.TestCase):
    def test_roundtrip_to_dict_from_dict(self):
        issue = _make_issue(session_id="s1", pr_url="https://example.com/pr/1")
        d = issue.to_dict()
        self.assertEqual(d["id"], issue.id)
        self.assertEqual(d["session_id"], "s1")
        restored = FlaggedIssue.from_dict(d)
        self.assertEqual(restored.to_dict(), d)

    def test_from_dict_ignores_unknown_keys(self):
        d = _make_issue().to_dict()
        d["unknown_field"] = "should-be-dropped"
        restored = FlaggedIssue.from_dict(d)
        self.assertFalse(hasattr(restored, "unknown_field"))

    def test_transition_valid(self):
        issue = _make_issue(state="flagged")
        issue.transition("queued")
        self.assertEqual(issue.state, "queued")

    def test_transition_invalid_raises(self):
        issue = _make_issue(state="flagged")
        with self.assertRaises(StateTransitionError):
            issue.transition("merged")

    def test_transition_unknown_state_raises(self):
        issue = _make_issue(state="flagged")
        with self.assertRaises(StateTransitionError):
            issue.transition("not-a-state")

    def test_terminal_state_sets_final_state(self):
        issue = _make_issue(state="reviewed")
        issue.transition("merged")
        self.assertEqual(issue.final_state, "merged")


# ---------------------------------------------------------------------------
# FlaggedIssueStore
# ---------------------------------------------------------------------------


class TestFlaggedIssueStore(unittest.TestCase):
    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            issue = _make_issue()
            store.save(issue)
            loaded = store.load(issue.id)
            self.assertEqual(loaded.id, issue.id)
            self.assertEqual(loaded.playbook, issue.playbook)

    def test_list_by_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            a = _make_issue(id="fi_a", state="flagged")
            b = _make_issue(id="fi_b", state="queued")
            c = _make_issue(id="fi_c", state="queued")
            store.save(a)
            store.save(b)
            store.save(c)
            queued = store.list_by_state("queued")
            self.assertEqual({i.id for i in queued}, {"fi_b", "fi_c"})

    def test_list_by_state_rejects_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            with self.assertRaises(ValueError):
                store.list_by_state("not-a-state")

    def test_archive_moves_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            issue = _make_issue(id="fi_arch", state="reviewed")
            issue.transition("merged")
            store.save(issue)
            dst = store.archive("fi_arch")
            self.assertTrue(dst.is_file())
            self.assertFalse((store.flagged_dir / "fi_arch.json").is_file())

    def test_archive_rejects_non_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            issue = _make_issue(id="fi_live", state="flagged")
            store.save(issue)
            with self.assertRaises(ValueError):
                store.archive("fi_live")


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class TestStateMachine(unittest.TestCase):
    def test_all_states_declared_in_transitions(self):
        for state in VALID_STATES:
            self.assertIn(state, VALID_TRANSITIONS)

    def test_valid_path_flagged_to_merged(self):
        issue = _make_issue(state="flagged")
        for target in ("queued", "dispatched", "in-progress", "draft-pr", "reviewed", "merged"):
            issue.transition(target)
        self.assertEqual(issue.state, "merged")
        self.assertEqual(issue.final_state, "merged")

    def test_terminal_states_have_no_transitions(self):
        for state in ("merged", "rejected", "escalated"):
            self.assertEqual(VALID_TRANSITIONS[state], ())


# ---------------------------------------------------------------------------
# Failure decision tree
# ---------------------------------------------------------------------------


class TestFailureDecisionTree(unittest.TestCase):
    def _make_dispatcher(self, tmp: Path) -> Dispatcher:
        store = FlaggedIssueStore(tmp)
        pb = _make_playbook_dir(tmp)
        return Dispatcher(store=store, client=None, playbook_dir=pb)

    def test_retriable_under_cap_requeues(self):
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = self._make_dispatcher(Path(tmp))
            issue = _make_issue(state="in-progress", retry_count=0)
            issue.transition("failed")
            dispatcher.store.save(issue)
            dispatcher.handle_terminal_failure(issue, "install-failure")
            self.assertEqual(issue.state, "queued")
            self.assertEqual(issue.retry_count, 1)

    def test_retriable_at_cap_escalates(self):
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = self._make_dispatcher(Path(tmp))
            issue = _make_issue(state="in-progress", retry_count=2)
            issue.transition("failed")
            dispatcher.store.save(issue)
            dispatcher.handle_terminal_failure(issue, "install-failure")
            self.assertEqual(issue.state, "escalated")

    def test_terminal_class_always_escalates(self):
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = self._make_dispatcher(Path(tmp))
            issue = _make_issue(state="in-progress", retry_count=0)
            issue.transition("failed")
            dispatcher.store.save(issue)
            dispatcher.handle_terminal_failure(issue, "plan-out-of-scope")
            self.assertEqual(issue.state, "escalated")

    def test_classify_failure_maps_keywords(self):
        self.assertEqual(classify_failure("npm install exploded"), "install-failure")
        self.assertEqual(classify_failure("VM timeout after 30m"), "vm-timeout")
        self.assertEqual(classify_failure("network dns error"), "network-error")
        self.assertEqual(classify_failure("plan out-of-scope"), "plan-out-of-scope")
        self.assertEqual(classify_failure("unknown reason blob"), "model-refused")

    def test_is_retriable(self):
        self.assertTrue(is_retriable("install-failure"))
        self.assertTrue(is_retriable("vm-timeout"))
        self.assertFalse(is_retriable("plan-out-of-scope"))
        self.assertFalse(is_retriable("model-refused"))


# ---------------------------------------------------------------------------
# JulesClient header/URL construction
# ---------------------------------------------------------------------------


class TestJulesClient(unittest.TestCase):
    def test_requires_api_key(self):
        os.environ.pop("JULES_API_KEY", None)
        with self.assertRaises(ConfigurationError):
            JulesClient()

    def test_uses_env_api_key(self):
        os.environ["JULES_API_KEY"] = "fake-key-env"
        try:
            client = JulesClient(session=MagicMock())
            headers = client._headers()
            self.assertEqual(headers["X-Goog-Api-Key"], "fake-key-env")
            self.assertEqual(headers["Content-Type"], "application/json")
            self.assertIn("jules-dispatcher", headers["User-Agent"])
        finally:
            os.environ.pop("JULES_API_KEY", None)

    def test_create_session_builds_correct_request(self):
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "sess-123"}'
        mock_resp.json.return_value = {"id": "sess-123"}
        mock_session.request.return_value = mock_resp

        client = JulesClient(api_key="k", session=mock_session)
        resp = client.create_session(
            repo="ZOLAtheCodeX/aigovops",
            prompt="do the thing",
            branch="main",
            parallel=1,
        )
        self.assertEqual(resp["id"], "sess-123")
        call = mock_session.request.call_args
        self.assertEqual(call.kwargs["method"], "POST")
        self.assertTrue(call.kwargs["url"].endswith("/v1alpha/sessions"))
        self.assertEqual(call.kwargs["headers"]["X-Goog-Api-Key"], "k")
        body = json.loads(call.kwargs["data"])
        self.assertEqual(body["prompt"], "do the thing")
        self.assertEqual(body["sources"][0]["githubRepo"]["repo"], "ZOLAtheCodeX/aigovops")
        self.assertEqual(body["requirePlanApproval"], True)

    def test_create_session_defaults_include_automation_mode_and_plan_approval(self):
        """Default call: body has automationMode=AUTO_CREATE_PR and requirePlanApproval=true."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"{}"
        mock_resp.json.return_value = {}
        mock_session.request.return_value = mock_resp
        client = JulesClient(api_key="k", session=mock_session)
        client.create_session(repo="a/b", prompt="p")
        body = json.loads(mock_session.request.call_args.kwargs["data"])
        self.assertEqual(body["automationMode"], "AUTO_CREATE_PR")
        self.assertEqual(body["requirePlanApproval"], True)

    def test_create_session_require_plan_approval_false_is_passed_through(self):
        """require_plan_approval=False sets requirePlanApproval to false in the body.

        Documented behaviour: the field is always present; a false value is
        sent verbatim. This is a deliberate choice over omission so Jules
        cannot silently fall back to its own default.
        """
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"{}"
        mock_resp.json.return_value = {}
        mock_session.request.return_value = mock_resp
        client = JulesClient(api_key="k", session=mock_session)
        client.create_session(repo="a/b", prompt="p", require_plan_approval=False)
        body = json.loads(mock_session.request.call_args.kwargs["data"])
        self.assertIn("requirePlanApproval", body)
        self.assertEqual(body["requirePlanApproval"], False)

    def test_create_session_automation_mode_none_omits_field(self):
        """automation_mode=None omits the automationMode field from the body."""
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"{}"
        mock_resp.json.return_value = {}
        mock_session.request.return_value = mock_resp
        client = JulesClient(api_key="k", session=mock_session)
        client.create_session(repo="a/b", prompt="p", automation_mode=None)
        body = json.loads(mock_session.request.call_args.kwargs["data"])
        self.assertNotIn("automationMode", body)

    def test_non_2xx_raises_api_error(self):
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.content = b'{"error": "rate limit"}'
        mock_resp.json.return_value = {"error": "rate limit"}
        mock_session.request.return_value = mock_resp
        client = JulesClient(api_key="k", session=mock_session)
        with self.assertRaises(JulesApiError) as ctx:
            client.get_session("sess")
        self.assertEqual(ctx.exception.status_code, 429)

    def test_send_message_endpoint_shape(self):
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"{}"
        mock_resp.json.return_value = {}
        mock_session.request.return_value = mock_resp
        client = JulesClient(api_key="k", session=mock_session)
        client.send_message("sess-1", "hello")
        call = mock_session.request.call_args
        self.assertIn("sessions/sess-1:sendMessage", call.kwargs["url"])

    def test_invalid_repo_rejected(self):
        client = JulesClient(api_key="k", session=MagicMock())
        with self.assertRaises(ValueError):
            client.create_session(repo="", prompt="x")

    def test_invalid_parallel_rejected(self):
        client = JulesClient(api_key="k", session=MagicMock())
        with self.assertRaises(ValueError):
            client.create_session(repo="a/b", prompt="x", parallel=0)


# ---------------------------------------------------------------------------
# Dispatcher + audit
# ---------------------------------------------------------------------------


class TestDispatcherAudit(unittest.TestCase):
    def test_emit_audit_log_invokes_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            pb = _make_playbook_dir(Path(tmp))
            mock_registry = MagicMock()
            mock_registry.invoke.return_value = {"audit_event_id": "audit-42"}
            dispatcher = Dispatcher(
                store=store, client=None, playbook_dir=pb, tool_registry=mock_registry
            )
            issue = _make_issue(state="flagged")
            dispatcher.enqueue(issue)
            audit_id = dispatcher.emit_audit_log(issue, outcome="merged")
            self.assertEqual(audit_id, "audit-42")
            self.assertEqual(issue.audit_event_id, "audit-42")
            mock_registry.invoke.assert_called_once()
            call = mock_registry.invoke.call_args
            self.assertEqual(call.args[0], "generate_audit_log")

    def test_emit_audit_log_without_registry_uses_synthetic_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            pb = _make_playbook_dir(Path(tmp))
            dispatcher = Dispatcher(store=store, client=None, playbook_dir=pb, tool_registry=None)
            issue = _make_issue()
            dispatcher.enqueue(issue)
            audit_id = dispatcher.emit_audit_log(issue)
            self.assertIsNotNone(audit_id)
            self.assertTrue(audit_id.startswith("audit-synth-"))


class TestDispatcherEnqueue(unittest.TestCase):
    def test_enqueue_rejects_unknown_playbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            pb = _make_playbook_dir(Path(tmp))
            dispatcher = Dispatcher(store=store, client=None, playbook_dir=pb)
            issue = _make_issue(playbook="not-a-playbook")
            with self.assertRaises(ValueError):
                dispatcher.enqueue(issue)

    def test_enqueue_advances_to_queued(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            pb = _make_playbook_dir(Path(tmp))
            dispatcher = Dispatcher(store=store, client=None, playbook_dir=pb)
            issue = _make_issue()
            dispatcher.enqueue(issue)
            self.assertEqual(issue.state, "queued")

    def test_dispatch_queued_dry_run_makes_no_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            pb = _make_playbook_dir(Path(tmp))
            dispatcher = Dispatcher(store=store, client=None, playbook_dir=pb)
            issue = _make_issue()
            dispatcher.enqueue(issue)
            changed = dispatcher.dispatch_queued(max_parallel=3, dry_run=True)
            self.assertEqual(changed, [])
            self.assertEqual(issue.state, "queued")

    def test_dispatch_queued_reads_playbook_metadata_overrides(self):
        """Dispatcher honours per-playbook overrides in payload.playbook_metadata.

        Sets automation_mode=None and require_plan_approval=False on the
        issue payload; expects those values on the JulesClient.create_session
        call rather than the dispatcher-level defaults.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            pb = _make_playbook_dir(Path(tmp))
            mock_client = MagicMock()
            mock_client.create_session.return_value = {"id": "sess-ovr", "url": "https://x"}
            dispatcher = Dispatcher(store=store, client=mock_client, playbook_dir=pb)
            issue = _make_issue(
                id="fi_ovr",
                payload={
                    "note": "override-test",
                    "playbook_metadata": {
                        "automation_mode": None,
                        "require_plan_approval": False,
                    },
                },
            )
            dispatcher.enqueue(issue)
            changed = dispatcher.dispatch_queued(max_parallel=3, dry_run=False)
            self.assertEqual(len(changed), 1)
            kwargs = mock_client.create_session.call_args.kwargs
            self.assertIsNone(kwargs["automation_mode"])
            self.assertEqual(kwargs["require_plan_approval"], False)

    def test_dispatch_queued_uses_dispatcher_defaults_when_no_override(self):
        """Without per-playbook overrides, dispatcher defaults reach create_session."""
        with tempfile.TemporaryDirectory() as tmp:
            store = FlaggedIssueStore(Path(tmp))
            pb = _make_playbook_dir(Path(tmp))
            mock_client = MagicMock()
            mock_client.create_session.return_value = {"id": "sess-def", "url": "https://x"}
            dispatcher = Dispatcher(store=store, client=mock_client, playbook_dir=pb)
            issue = _make_issue(id="fi_def")
            dispatcher.enqueue(issue)
            dispatcher.dispatch_queued(max_parallel=3, dry_run=False)
            kwargs = mock_client.create_session.call_args.kwargs
            self.assertEqual(kwargs["automation_mode"], "AUTO_CREATE_PR")
            self.assertEqual(kwargs["require_plan_approval"], True)


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


class TestPromptRender(unittest.TestCase):
    def test_render_substitutes_placeholders(self):
        template = "repo={{TARGET_REPO}} branch={{BRANCH_NAME}} title={{PR_TITLE}}"
        issue = _make_issue(id="fi_abc", playbook="markdown-lint")
        rendered = _render_prompt(template, issue)
        self.assertIn("ZOLAtheCodeX/aigovops", rendered)
        self.assertIn("jules/markdown-lint-fi_abc", rendered)
        self.assertIn("[jules:markdown-lint]", rendered)


# ---------------------------------------------------------------------------
# JSON Schemas validate happy-path instances
# ---------------------------------------------------------------------------


class TestSchemas(unittest.TestCase):
    SCHEMAS_DIR = REPO_ROOT / "jules" / "schemas"

    def _load(self, name: str) -> dict:
        return json.loads((self.SCHEMAS_DIR / name).read_text(encoding="utf-8"))

    def test_flagged_issue_schema_loads(self):
        schema = self._load("flagged-issue.schema.json")
        self.assertEqual(schema["title"], "FlaggedIssue")
        self.assertIn("properties", schema)
        self.assertIn("playbook", schema["properties"])

    def test_flagged_issue_instance_conforms(self):
        """Validate a happy-path instance against the schema via a hand-rolled
        check. Full JSON Schema validation is not a stdlib capability; this
        performs required-fields + enum-values check, which is the material
        part."""
        schema = self._load("flagged-issue.schema.json")
        instance = _make_issue().to_dict()
        for req in schema["required"]:
            self.assertIn(req, instance, f"missing required field {req}")
        self.assertIn(instance["playbook"], schema["properties"]["playbook"]["enum"])
        self.assertIn(instance["state"], schema["properties"]["state"]["enum"])
        self.assertIn(instance["priority"], schema["properties"]["priority"]["enum"])

    def test_playbook_metadata_schema_loads(self):
        schema = self._load("playbook-metadata.schema.json")
        self.assertEqual(schema["title"], "PlaybookMetadata")

    def test_playbook_metadata_instance_conforms(self):
        schema = self._load("playbook-metadata.schema.json")
        instance = {
            "playbook_name": "markdown-lint",
            "description": "Fix markdown lint regressions without prose edits.",
            "auto_merge_allowed": True,
            "requires_human_review": False,
            "max_retries": 2,
            "timeout_seconds": 1800,
        }
        for req in schema["required"]:
            self.assertIn(req, instance)
        self.assertIn(
            instance["playbook_name"],
            schema["properties"]["playbook_name"]["enum"],
        )


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


class TestCliSmoke(unittest.TestCase):
    def _run_cli(self, argv):
        from jules.cli import main
        return main(argv)

    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as ctx:
            self._run_cli(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_enqueue_dispatch_list_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "jules"
            root.mkdir()
            _make_playbook_dir(root)
            (root / "flagged").mkdir(exist_ok=True)
            (root / "archive").mkdir(exist_ok=True)

            payload_file = Path(tmp) / "payload.json"
            payload_file.write_text(json.dumps({"note": "ok"}), encoding="utf-8")

            # enqueue
            rc = self._run_cli([
                "--root", str(root),
                "enqueue",
                "--type", "test-type",
                "--playbook", "markdown-lint",
                "--target-repo", "ZOLAtheCodeX/aigovops",
                "--payload-json", str(payload_file),
                "--id", "fi_cli_smoke",
            ])
            self.assertEqual(rc, 0)

            # dispatch dry-run
            rc = self._run_cli([
                "--root", str(root),
                "dispatch", "--dry-run",
            ])
            self.assertEqual(rc, 0)

            # list
            rc = self._run_cli(["--root", str(root), "list"])
            self.assertEqual(rc, 0)

            # list by state
            rc = self._run_cli(["--root", str(root), "list", "--state", "queued"])
            self.assertEqual(rc, 0)

            # show
            rc = self._run_cli(["--root", str(root), "show", "fi_cli_smoke"])
            self.assertEqual(rc, 0)

            # audit (no registry; synthetic id)
            rc = self._run_cli(["--root", str(root), "audit", "fi_cli_smoke"])
            self.assertEqual(rc, 0)


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def _run_all() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(_run_all())
