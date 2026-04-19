"""Tests for the AIGovClaw Hub v2 command-center server.

Standalone runnable: python3 hub/v2_server/tests/test_server.py

The tests exercise:
  - Command registry enumeration
  - Task lifecycle (enqueue, run to completion, list, detail)
  - Pause and resume via SIGSTOP and SIGCONT
  - Graceful cancel (SIGTERM) with escalation
  - Approval flow (awaiting-approval, approve -> start, reject -> cancel)
  - Health endpoint
  - Artifacts endpoint
  - Error responses (unknown command, unknown task, unknown action)
  - Concurrent tasks (two running at once)
  - Orphan reaping on restart
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# The v2 generator import requires vendor files. Seed placeholders before
# importing server.py so the html cache can render on the first GET /.
from hub.v2 import generator as _v2gen  # noqa: E402

_PLACEHOLDER_REACT = (
    "/* placeholder react UMD */\n"
    "window.React = { createElement: function(){ return {}; }, "
    "useState: function(v){ return [v, function(){}]; }, "
    "useEffect: function(){}, useMemo: function(fn){ return fn(); }, "
    "useRef: function(v){ return { current: v }; } };\n"
    + "// pad " * 300
)
_PLACEHOLDER_REACT_DOM = (
    "/* placeholder react-dom UMD */\n"
    "window.ReactDOM = { createRoot: function(el){ "
    "return { render: function(){ el.innerHTML = '<div>rendered</div>'; } }; "
    "} };\n"
    + "// pad " * 300
)


def _seed_vendor(tmp: Path) -> None:
    vendor = tmp / "vendor"
    vendor.mkdir(exist_ok=True)
    (vendor / "react.js").write_text(_PLACEHOLDER_REACT, encoding="utf-8")
    (vendor / "react-dom.js").write_text(_PLACEHOLDER_REACT_DOM, encoding="utf-8")
    _v2gen.REACT_UMD_PATH = vendor / "react.js"
    _v2gen.REACT_DOM_UMD_PATH = vendor / "react-dom.js"


from hub.v2_server import server as cc_server  # noqa: E402
from hub.v2_server import task_runner as tr  # noqa: E402
from hub.v2_server.command_registry import build_registry, public_registry  # noqa: E402
from hub.v2_server.health import compute_health  # noqa: E402


def _http_get(url: str, timeout: float = 3.0) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body and body.strip().startswith(("{", "[")) else body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, body


def _http_post(url: str, data: dict | None = None, timeout: float = 3.0) -> tuple[int, dict]:
    payload = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, body


class _ServerFixture:
    """Helper: stands up a real ThreadedHTTPServer on an ephemeral port."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.evidence = tmp / "evidence"
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.tasks_dir = tmp / "tasks"
        self.approvals_dir = tmp / "approvals"
        self.server, self.state = cc_server.build_server(
            host="127.0.0.1",
            port=0,
            evidence_path=self.evidence,
            aigovops_root=None,
            tasks_dir=self.tasks_dir,
            approvals_dir=self.approvals_dir,
        )
        self.host, self.port = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def url(self, path: str) -> str:
        return f"http://{self.host}:{self.port}{path}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class CommandCenterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="hub-v2-cc-tests-"))
        _seed_vendor(self.tmp)
        self.fix = _ServerFixture(self.tmp)
        # Inject a test-safe command that we control.
        def _sleep_argv(args: dict) -> list[str]:
            secs = str(args.get("seconds", "0.3"))
            return [sys.executable, "-c", f"import time, sys; print('start'); sys.stdout.flush(); time.sleep({secs}); print('done')"]

        def _bad_argv(_args: dict) -> list[str]:
            return [sys.executable, "-c", "import sys; sys.exit(2)"]

        def _sleep_long_argv(args: dict) -> list[str]:
            return [sys.executable, "-c", "import time; [time.sleep(0.1) for _ in range(200)]"]

        self.fix.state.registry["test-sleep"] = {
            "id": "test-sleep", "display_name": "Test sleep", "description": "",
            "category": "diagnostic", "args_schema": [], "requires_approval": False,
            "build_argv": _sleep_argv,
        }
        self.fix.state.registry["test-fail"] = {
            "id": "test-fail", "display_name": "Test fail", "description": "",
            "category": "diagnostic", "args_schema": [], "requires_approval": False,
            "build_argv": _bad_argv,
        }
        self.fix.state.registry["test-long"] = {
            "id": "test-long", "display_name": "Test long", "description": "",
            "category": "diagnostic", "args_schema": [], "requires_approval": False,
            "build_argv": _sleep_long_argv,
        }
        self.fix.state.registry["test-approved"] = {
            "id": "test-approved", "display_name": "Test approved", "description": "",
            "category": "bundle", "args_schema": [], "requires_approval": True,
            "build_argv": _sleep_argv,
        }

    def tearDown(self) -> None:
        self.fix.close()

    # ------------------------------------------------------------------
    # Registry + commands
    # ------------------------------------------------------------------

    def test_commands_endpoint_returns_registry(self) -> None:
        status, data = _http_get(self.fix.url("/api/commands"))
        self.assertEqual(status, 200)
        self.assertIn("commands", data)
        ids = [c["id"] for c in data["commands"]]
        for expected in ("run-full-pipeline", "pack-bundle", "verify-bundle", "check-readiness", "doctor", "regenerate-hub"):
            self.assertIn(expected, ids, f"expected registry entry missing: {expected}")

    def test_registry_public_view_omits_build_argv(self) -> None:
        reg = build_registry(aigovops_root=None)
        pub = public_registry(reg)
        self.assertTrue(all("build_argv" not in spec for spec in pub))

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def test_enqueue_runs_and_succeeds(self) -> None:
        status, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-sleep", "args": {"seconds": "0.1"}})
        self.assertEqual(status, 200)
        task_id = data["task_id"]
        self.assertEqual(data["status"], tr.STATUS_RUNNING)
        rec = self.fix.state.runner.wait(task_id, timeout=5.0)
        self.assertEqual(rec["status"], tr.STATUS_SUCCEEDED)
        self.assertEqual(rec["exit_code"], 0)
        self.assertIn("done", "\n".join(rec["stdout_tail"]))

    def test_enqueue_failing_command_marked_failed(self) -> None:
        status, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-fail"})
        self.assertEqual(status, 200)
        rec = self.fix.state.runner.wait(data["task_id"], timeout=5.0)
        self.assertEqual(rec["status"], tr.STATUS_FAILED)
        self.assertEqual(rec["exit_code"], 2)

    def test_unknown_command_returns_400(self) -> None:
        status, data = _http_post(self.fix.url("/api/tasks"), {"command": "does-not-exist"})
        self.assertEqual(status, 400)
        self.assertEqual(data["error"], "unknown_command")

    def test_list_tasks_filtered_by_status(self) -> None:
        _http_post(self.fix.url("/api/tasks"), {"command": "test-sleep", "args": {"seconds": "0.05"}})
        _http_post(self.fix.url("/api/tasks"), {"command": "test-sleep", "args": {"seconds": "0.05"}})
        # Wait for completion.
        time.sleep(0.6)
        status, data = _http_get(self.fix.url(f"/api/tasks?status={tr.STATUS_SUCCEEDED}"))
        self.assertEqual(status, 200)
        tasks = data["tasks"]
        self.assertTrue(all(t["status"] == tr.STATUS_SUCCEEDED for t in tasks))
        self.assertGreaterEqual(len(tasks), 2)

    def test_task_detail_returns_stdout_tail(self) -> None:
        _, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-sleep", "args": {"seconds": "0.1"}})
        self.fix.state.runner.wait(data["task_id"], timeout=5.0)
        status, rec = _http_get(self.fix.url(f"/api/tasks/{data['task_id']}"))
        self.assertEqual(status, 200)
        self.assertIn("stdout_tail", rec)
        self.assertIsInstance(rec["stdout_tail"], list)

    def test_task_not_found_returns_404(self) -> None:
        status, data = _http_get(self.fix.url("/api/tasks/00000000deadbeef"))
        self.assertEqual(status, 404)
        self.assertEqual(data["error"], "not_found")

    # ------------------------------------------------------------------
    # Pause / resume
    # ------------------------------------------------------------------

    def test_pause_and_resume(self) -> None:
        _, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-long"})
        task_id = data["task_id"]
        # Give it a moment to enter RUNNING.
        time.sleep(0.15)
        status, rec = _http_post(self.fix.url(f"/api/tasks/{task_id}/pause"))
        self.assertEqual(status, 200)
        self.assertEqual(rec["status"], tr.STATUS_PAUSED)
        status, rec = _http_post(self.fix.url(f"/api/tasks/{task_id}/resume"))
        self.assertEqual(status, 200)
        self.assertEqual(rec["status"], tr.STATUS_RUNNING)
        # Clean up.
        _http_post(self.fix.url(f"/api/tasks/{task_id}/cancel"))
        self.fix.state.runner.wait(task_id, timeout=6.0)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def test_cancel_terminates_running_task(self) -> None:
        _, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-long"})
        task_id = data["task_id"]
        time.sleep(0.15)
        status, rec = _http_post(self.fix.url(f"/api/tasks/{task_id}/cancel"))
        self.assertEqual(status, 200)
        self.assertEqual(rec["status"], tr.STATUS_CANCELLED)
        final = self.fix.state.runner.wait(task_id, timeout=8.0)
        self.assertEqual(final["status"], tr.STATUS_CANCELLED)

    def test_unknown_task_action_returns_400(self) -> None:
        _, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-sleep", "args": {"seconds": "0.05"}})
        status, body = _http_post(self.fix.url(f"/api/tasks/{data['task_id']}/frobnicate"))
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "unknown_action")

    # ------------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------------

    def test_approval_flow_approve_then_run(self) -> None:
        _, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-approved", "args": {"seconds": "0.1"}})
        task_id = data["task_id"]
        self.assertEqual(data["status"], tr.STATUS_AWAITING_APPROVAL)
        # Pending approvals surfaced.
        status, pending = _http_get(self.fix.url("/api/approvals"))
        self.assertEqual(status, 200)
        pending_ids = [p["task_id"] for p in pending["approvals"]]
        self.assertIn(task_id, pending_ids)
        # Approve.
        status, rec = _http_post(self.fix.url(f"/api/approvals/{task_id}/approve"))
        self.assertEqual(status, 200)
        # Task now running or completed.
        final = self.fix.state.runner.wait(task_id, timeout=6.0)
        self.assertEqual(final["status"], tr.STATUS_SUCCEEDED)

    def test_approval_flow_reject_cancels(self) -> None:
        _, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-approved"})
        task_id = data["task_id"]
        status, rec = _http_post(
            self.fix.url(f"/api/approvals/{task_id}/reject"),
            {"reason": "not this time"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(rec["status"], tr.STATUS_CANCELLED)

    # ------------------------------------------------------------------
    # Health and artifacts
    # ------------------------------------------------------------------

    def test_health_returns_expected_shape(self) -> None:
        status, data = _http_get(self.fix.url("/api/health"))
        self.assertEqual(status, 200)
        for key in (
            "plugin_count", "last_run_at", "warning_count",
            "bundle_signed", "evidence_artifact_count", "evidence_path",
            "jurisdictions", "computed_at",
        ):
            self.assertIn(key, data, f"missing health key: {key}")

    def test_health_reflects_recent_task(self) -> None:
        _, data = _http_post(self.fix.url("/api/tasks"), {"command": "test-sleep", "args": {"seconds": "0.05"}})
        self.fix.state.runner.wait(data["task_id"], timeout=5.0)
        _, health = _http_get(self.fix.url("/api/health"))
        self.assertIsNotNone(health["last_run_at"])

    def test_artifacts_endpoint(self) -> None:
        # Seed a synthetic artifact.
        art = self.fix.evidence / "bias-evaluator" / "out.json"
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text(json.dumps({"warnings": ["w1"]}), encoding="utf-8")
        status, data = _http_get(self.fix.url("/api/artifacts"))
        self.assertEqual(status, 200)
        paths = [a["path"] for a in data["artifacts"]]
        self.assertIn("bias-evaluator/out.json", paths)

    # ------------------------------------------------------------------
    # Concurrency + orphan reap
    # ------------------------------------------------------------------

    def test_concurrent_tasks_both_run(self) -> None:
        _, a = _http_post(self.fix.url("/api/tasks"), {"command": "test-sleep", "args": {"seconds": "0.2"}})
        _, b = _http_post(self.fix.url("/api/tasks"), {"command": "test-sleep", "args": {"seconds": "0.2"}})
        self.assertNotEqual(a["task_id"], b["task_id"])
        ra = self.fix.state.runner.wait(a["task_id"], timeout=6.0)
        rb = self.fix.state.runner.wait(b["task_id"], timeout=6.0)
        self.assertEqual(ra["status"], tr.STATUS_SUCCEEDED)
        self.assertEqual(rb["status"], tr.STATUS_SUCCEEDED)

    def test_orphan_reap_marks_interrupted(self) -> None:
        # Write a fake state.json with a dead pid.
        dead_pid = 9999999  # extremely unlikely to be alive
        tid = "cafebabecafebabe"
        sub = self.fix.state.runner.tasks_dir / tid
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "state.json").write_text(
            json.dumps({
                "task_id": tid, "command": "test-sleep", "args": {},
                "argv": ["/bin/true"], "status": tr.STATUS_RUNNING,
                "queued_at": "2020-01-01T00:00:00Z", "started_at": "2020-01-01T00:00:00Z",
                "pid": dead_pid, "exit_code": None, "summary": None,
                "stdout_tail": [],
            }),
            encoding="utf-8",
        )
        # Rebuild runner to force a reap.
        new_runner = tr.TaskRunner(tasks_dir=self.fix.state.runner.tasks_dir)
        rec = new_runner.get(tid)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["status"], tr.STATUS_INTERRUPTED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
