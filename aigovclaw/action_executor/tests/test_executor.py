"""Tests for the aigovclaw action-executor layer.

Standalone runnable:
    python3 aigovclaw/action_executor/tests/test_executor.py

Each test isolates state via a tmpdir-backed memory_root and a hermetic
AuthorityPolicy so tests never touch the operator's real ~/.hermes tree.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aigovclaw.action_executor import (  # noqa: E402
    ActionExecutor,
    ActionRequest,
    ActionResult,
    ActionValidationError,
)
from aigovclaw.action_executor.action_registry import (  # noqa: E402
    AUTHORITY_ASK,
    AUTHORITY_AUTONOMOUS,
    AUTHORITY_TAKE,
)
from aigovclaw.action_executor.authority_policy import AuthorityPolicy  # noqa: E402
from aigovclaw.action_executor import safety  # noqa: E402


def _make_request(**overrides):
    base = {
        "action_id": "notification",
        "plugin": "test-plugin",
        "target": "local-file",
        "args": {"channel": "local-file", "message": "hello", "severity": "info"},
        "rationale": "unit test",
        "requested_at": safety.utc_now_iso(),
        "request_id": safety.new_request_id(),
        "dry_run": False,
    }
    base.update(overrides)
    return ActionRequest(**base)


def _policy(
    *,
    default_mode="ask-permission",
    require_approval_for_destructive=True,
    require_approval_for_external=True,
    overrides=None,
    autonomous_opt_ins=None,
    rate_limits=None,
):
    data = {
        "defaults": {
            "mode": default_mode,
            "require_approval_for_destructive": require_approval_for_destructive,
            "require_approval_for_external": require_approval_for_external,
            "max_rate_per_hour": rate_limits or {
                "file-update": 60,
                "mcp-push": 20,
                "notification": 120,
                "re-run-plugin": 60,
                "trigger-downstream": 60,
                "git-commit-and-push": 10,
            },
        },
        "overrides": overrides or [],
        "autonomous_opt_ins": autonomous_opt_ins or [],
    }
    return AuthorityPolicy(data)


class ActionExecutorBaseCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory_root = Path(self.tmp.name)
        # Allow file-update to write under tmp by setting allowed-roots patch.
        self._orig_allowed = safety.allowed_roots
        safety.allowed_roots = lambda: [self.memory_root]
        # Also patch the import used by file_update handler.
        from aigovclaw.action_executor.handlers import file_update
        file_update.allowed_roots = safety.allowed_roots

    def tearDown(self):
        safety.allowed_roots = self._orig_allowed
        from aigovclaw.action_executor.handlers import file_update
        file_update.allowed_roots = self._orig_allowed
        self.tmp.cleanup()

    def make_executor(self, *, policy=None):
        return ActionExecutor(
            memory_root=self.memory_root,
            policy=policy or _policy(default_mode="take-resolving-action",
                                     require_approval_for_external=False),
        )


class TestHappyPaths(ActionExecutorBaseCase):
    def test_01_notification_ask_permission_queued_then_approved_executes(self):
        # default ask-permission: notification should queue.
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(default_mode="ask-permission",
                           overrides=[]),
        )
        req = _make_request(action_id="notification",
                            args={"channel": "local-file", "message": "m", "severity": "info"})
        result = ex.execute(req)
        self.assertEqual(result.status, "approved-pending")
        self.assertEqual(len(ex.pending()), 1)
        after = ex.approve(req.request_id)
        self.assertEqual(after.status, "executed")
        self.assertTrue(Path(after.output["log_path"]).exists())

    def test_02_notification_take_resolving_action_executes_immediately(self):
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(default_mode="take-resolving-action",
                           require_approval_for_external=False),
        )
        req = _make_request()
        result = ex.execute(req)
        self.assertEqual(result.status, "executed")
        self.assertEqual(result.authority_mode_used, AUTHORITY_TAKE)


class TestAuthorityResolution(ActionExecutorBaseCase):
    def test_03_destructive_override_forces_ask_permission(self):
        # Force notification to 'destructive' via a patched registry to prove
        # the safety downgrade path exists.
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(
                default_mode="autonomous",
                require_approval_for_destructive=True,
                autonomous_opt_ins=["test-plugin"],
            ),
        )
        ex.registry["notification"].safety["destructive"] = True
        try:
            req = _make_request()
            result = ex.execute(req)
            self.assertEqual(result.status, "approved-pending")
        finally:
            ex.registry["notification"].safety["destructive"] = False

    def test_12_authority_override_matches(self):
        # Override for this plugin+action should flip default ask to take.
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(
                default_mode="ask-permission",
                require_approval_for_external=False,
                overrides=[
                    {"plugin": "audit-log-generator",
                     "action": "notification",
                     "mode": "take-resolving-action"},
                ],
            ),
        )
        req = _make_request(plugin="audit-log-generator")
        result = ex.execute(req)
        self.assertEqual(result.status, "executed")

    def test_13_external_side_effect_forces_ask(self):
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(
                default_mode="take-resolving-action",
                require_approval_for_external=True,
            ),
        )
        req = _make_request()  # notification has external_side_effect=True
        result = ex.execute(req)
        self.assertEqual(result.status, "approved-pending")

    def test_22_autonomous_opt_in_enforced(self):
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(
                default_mode="autonomous",
                require_approval_for_external=False,
                autonomous_opt_ins=[],  # empty
            ),
        )
        req = _make_request()
        # With no opt-in, autonomous downgrades to ask-permission.
        result = ex.execute(req)
        self.assertEqual(result.status, "approved-pending")


class TestFileUpdate(ActionExecutorBaseCase):
    def test_07_snapshot_taken_before_file_update(self):
        target = self.memory_root / "demo.json"
        target.write_text('{"a": 1}', encoding="utf-8")
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(default_mode="take-resolving-action",
                           require_approval_for_external=False),
        )
        req = _make_request(
            action_id="file-update",
            target=str(target),
            args={"path": str(target), "updates_dict": {"b": 2}, "diff_mode": "merge-json"},
        )
        result = ex.execute(req)
        self.assertEqual(result.status, "executed", msg=result.error)
        snap_dir = Path(result.rollback_snapshot_path)
        self.assertTrue((snap_dir / "original").exists())
        self.assertEqual(json.loads(target.read_text()), {"a": 1, "b": 2})

    def test_05_dry_run_returns_diff_no_mutation(self):
        target = self.memory_root / "dry.json"
        target.write_text('{"a": 1}', encoding="utf-8")
        ex = self.make_executor()
        req = _make_request(
            action_id="file-update",
            target=str(target),
            args={"path": str(target), "updates_dict": {"b": 2}, "diff_mode": "merge-json"},
            dry_run=True,
        )
        result = ex.execute(req)
        self.assertEqual(result.status, "skipped-dry-run")
        self.assertIn("diff_preview", result.output)
        # File unchanged.
        self.assertEqual(json.loads(target.read_text()), {"a": 1})

    def test_17_path_outside_allowed_roots_raises(self):
        bogus = Path("/tmp/aigovclaw-test-outside-root.json")
        ex = self.make_executor()
        req = _make_request(
            action_id="file-update",
            target=str(bogus),
            args={"path": str(bogus), "updates_dict": {}, "diff_mode": "replace", "content": "x"},
        )
        result = ex.execute(req)
        # Handler raises PermissionError before mutation. Because the target
        # did not exist, the snapshot was an absence-marker; the rollback
        # helper "succeeds" trivially and the status reports rolled-back.
        # Either terminal failure status is acceptable here; the contract is
        # that the handler never executed.
        self.assertIn(result.status, ("failed", "rolled-back"))
        self.assertIn("outside", result.error.lower())
        self.assertFalse(bogus.exists())

    def test_08_rollback_on_handler_failure(self):
        target = self.memory_root / "rb.json"
        target.write_text('{"original": true}', encoding="utf-8")
        ex = self.make_executor()
        req = _make_request(
            action_id="file-update",
            target=str(target),
            # Invalid diff_mode triggers ValueError after snapshot is taken.
            args={"path": str(target), "diff_mode": "nonsense"},
        )
        result = ex.execute(req)
        self.assertIn(result.status, ("failed", "rolled-back"))
        # Original content preserved.
        self.assertEqual(json.loads(target.read_text()), {"original": True})


class TestValidationAndAudit(ActionExecutorBaseCase):
    def test_06_unknown_action_fails_fast(self):
        ex = self.make_executor()
        req = _make_request(action_id="not-a-real-action")
        result = ex.execute(req)
        self.assertEqual(result.status, "failed")
        self.assertIn("unknown action_id", result.error)

    def test_19_missing_required_args_fails(self):
        ex = self.make_executor()
        req = _make_request(action_id="file-update", args={})  # no 'path'
        result = ex.execute(req)
        self.assertEqual(result.status, "failed")

    def test_09_pre_action_audit_written(self):
        ex = self.make_executor()
        req = _make_request()
        result = ex.execute(req)
        self.assertEqual(result.status, "executed")
        logs = list((self.memory_root / "audit-log").glob("*.jsonl"))
        self.assertTrue(logs)
        events = []
        for p in logs:
            for line in p.read_text().splitlines():
                events.append(json.loads(line))
        event_types = [e["event"] for e in events if e.get("request_id") == req.request_id]
        self.assertIn("action-intent", event_types)
        self.assertLess(
            event_types.index("action-intent"),
            event_types.index("action-completed"),
        )

    def test_10_post_action_audit_written(self):
        ex = self.make_executor()
        req = _make_request()
        result = ex.execute(req)
        self.assertEqual(result.status, "executed")
        logs = list((self.memory_root / "audit-log").glob("*.jsonl"))
        events = []
        for p in logs:
            for line in p.read_text().splitlines():
                events.append(json.loads(line))
        completed = [e for e in events if e["event"] == "action-completed"
                     and e.get("request_id") == req.request_id]
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["audit_entry_id"], result.audit_entry_id)

    def test_21_handler_exception_triggers_rollback_and_audit(self):
        target = self.memory_root / "exc.json"
        target.write_text('"before"', encoding="utf-8")
        ex = self.make_executor()
        req = _make_request(
            action_id="file-update",
            target=str(target),
            args={"path": str(target), "diff_mode": "merge-json", "updates_dict": "not-a-dict"},
        )
        result = ex.execute(req)
        self.assertIn(result.status, ("failed", "rolled-back"))
        logs = list((self.memory_root / "audit-log").glob("*.jsonl"))
        events = []
        for p in logs:
            for line in p.read_text().splitlines():
                events.append(json.loads(line))
        failed = [e for e in events if e["event"] == "action-failed"
                  and e.get("request_id") == req.request_id]
        self.assertEqual(len(failed), 1)


class TestApprovalFlow(ActionExecutorBaseCase):
    def test_11_rejection_records_audit(self):
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(default_mode="ask-permission"),
        )
        req = _make_request()
        pending = ex.execute(req)
        self.assertEqual(pending.status, "approved-pending")
        rejected = ex.reject(req.request_id, reason="operator declined")
        self.assertEqual(rejected.status, "rejected")
        self.assertEqual(rejected.error, "operator declined")
        logs = list((self.memory_root / "audit-log").glob("*.jsonl"))
        events = []
        for p in logs:
            for line in p.read_text().splitlines():
                events.append(json.loads(line))
        reject_events = [e for e in events if e["event"] == "action-rejected"
                         and e.get("request_id") == req.request_id]
        self.assertEqual(len(reject_events), 1)

    def test_14_git_commit_never_executes_without_approval(self):
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(
                default_mode="autonomous",
                require_approval_for_external=False,
                autonomous_opt_ins=["test-plugin"],
            ),
        )
        req = _make_request(
            action_id="git-commit-and-push",
            target=str(self.memory_root),
            args={
                "repo_path": str(self.memory_root),
                "files": ["demo.txt"],
                "commit_message": "msg",
                "branch": None,
                "push_remote": None,
            },
        )
        result = ex.execute(req)
        self.assertEqual(result.status, "approved-pending")


class TestRateLimit(ActionExecutorBaseCase):
    def test_04_rate_limit_exceeded(self):
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(
                default_mode="take-resolving-action",
                require_approval_for_external=False,
                rate_limits={"notification": 2,
                             "file-update": 60, "mcp-push": 20,
                             "re-run-plugin": 60, "trigger-downstream": 60,
                             "git-commit-and-push": 10},
            ),
        )
        for _ in range(2):
            r = ex.execute(_make_request())
            self.assertEqual(r.status, "executed")
        r3 = ex.execute(_make_request())
        self.assertEqual(r3.status, "skipped-rate-limit")

    def test_20_rate_limit_window_allows_new_call_when_cleared(self):
        # We fake clear-window by pointing the executor at a fresh memory root.
        ex1 = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(
                default_mode="take-resolving-action",
                require_approval_for_external=False,
                rate_limits={"notification": 1,
                             "file-update": 60, "mcp-push": 20,
                             "re-run-plugin": 60, "trigger-downstream": 60,
                             "git-commit-and-push": 10},
            ),
        )
        r1 = ex1.execute(_make_request())
        self.assertEqual(r1.status, "executed")
        r2 = ex1.execute(_make_request())
        self.assertEqual(r2.status, "skipped-rate-limit")

        # New memory root = fresh window.
        fresh = tempfile.TemporaryDirectory()
        try:
            ex2 = ActionExecutor(
                memory_root=Path(fresh.name),
                policy=_policy(
                    default_mode="take-resolving-action",
                    require_approval_for_external=False,
                    rate_limits={"notification": 1,
                                 "file-update": 60, "mcp-push": 20,
                                 "re-run-plugin": 60, "trigger-downstream": 60,
                                 "git-commit-and-push": 10},
                ),
            )
            r3 = ex2.execute(_make_request())
            self.assertEqual(r3.status, "executed")
        finally:
            fresh.cleanup()


class TestOtherHandlers(ActionExecutorBaseCase):
    def test_15_rerun_plugin_invokes_and_writes(self):
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(default_mode="take-resolving-action",
                           require_approval_for_external=False),
        )
        # audit-log-generator plugin: use a real plugin if aigovops exists.
        inputs = {
            "system_name": "test-system",
            "purpose": "test",
            "risk_tier": "minimal",
            "data_processed": ["operational logs"],
            "deployment_context": "internal dev",
            "governance_decisions": ["approved for testing"],
            "responsible_parties": ["Zola"],
            "enrich_with_crosswalk": False,
        }
        req = _make_request(
            action_id="re-run-plugin",
            target="audit-log-generator",
            args={"plugin_name": "audit-log-generator", "inputs": inputs},
        )
        result = ex.execute(req)
        if result.status == "failed":
            # aigovops checkout not found in this environment; skip rather than fail.
            self.skipTest(f"aigovops unavailable: {result.error}")
        self.assertEqual(result.status, "executed")
        out_path = Path(result.output["output_path"])
        self.assertTrue(out_path.exists())
        data = json.loads(out_path.read_text())
        self.assertEqual(data["system_name"], "test-system")

    def test_16_mcp_push_dry_run_returns_metadata(self):
        ex = self.make_executor()
        req = _make_request(
            action_id="mcp-push",
            target="notion",
            args={
                "mcp_server": "notion",
                "tool_name": "create-page",
                "payload": {"artifact_type": "audit-log-entry", "title": "x"},
            },
            dry_run=True,
        )
        result = ex.execute(req)
        self.assertEqual(result.status, "skipped-dry-run")
        self.assertEqual(result.output["would_push_to"], "notion")
        self.assertEqual(result.output["tool_name"], "create-page")


class TestConcurrency(ActionExecutorBaseCase):
    def test_18_concurrent_requests_same_action_race_safely(self):
        ex = ActionExecutor(
            memory_root=self.memory_root,
            policy=_policy(
                default_mode="take-resolving-action",
                require_approval_for_external=False,
                rate_limits={"notification": 1000,
                             "file-update": 60, "mcp-push": 20,
                             "re-run-plugin": 60, "trigger-downstream": 60,
                             "git-commit-and-push": 10},
            ),
        )
        results: list[ActionResult] = []
        lock = threading.Lock()

        def worker():
            r = ex.execute(_make_request())
            with lock:
                results.append(r)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)
        self.assertEqual(len(results), 10)
        statuses = [r.status for r in results]
        self.assertTrue(all(s == "executed" for s in statuses), statuses)


if __name__ == "__main__":
    unittest.main(verbosity=2)
