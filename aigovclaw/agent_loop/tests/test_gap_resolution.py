"""Tests for the gap-resolution inner loop.

Run: python3 -m unittest aigovclaw.agent_loop.tests.test_gap_resolution -v
     or: python3 aigovclaw/agent_loop/tests/test_gap_resolution.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

_PKG_ROOT = Path(__file__).resolve().parents[3]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from aigovclaw.agent_loop import GapResolutionLoop, UserInteractionBroker  # noqa: E402
from aigovclaw.agent_loop.loops.gap_resolution import (  # noqa: E402
    GAP_STATUS_NEEDS_HUMAN,
    GAP_STATUS_RESOLVED,
)


# ---------------------------------------------------------------------------
# Test doubles.
# ---------------------------------------------------------------------------


class ScriptedExecutor:
    """Returns status values per request in order of call."""

    def __init__(self, statuses):
        self._statuses = list(statuses)
        self.calls: list[dict] = []

    def execute(self, action):
        if isinstance(action, dict):
            rec = action
        else:
            rec = {"action_id": getattr(action, "action_id", None)}
        self.calls.append(rec)
        status = self._statuses.pop(0) if self._statuses else "executed"
        return SimpleNamespace(
            request_id=rec.get("request_id"),
            status=status,
            authority_mode_used="autonomous",
            audit_entry_id="a",
            rollback_snapshot_path=None,
            started_at="2026-04-18T00:00:00Z",
            ended_at="2026-04-18T00:00:01Z",
            output={},
            error=None,
        )


def _gap(gap_key, target_plugin="soa-generator"):
    return {
        "gap_key": gap_key,
        "description": f"Gap {gap_key}",
        "artifact_type": "soa",
        "target_plugin": target_plugin,
    }


# ---------------------------------------------------------------------------
# Tests (10+).
# ---------------------------------------------------------------------------


class TestGapResolutionHappyPath(unittest.TestCase):

    def test_all_gaps_resolved_in_one_iteration(self):
        exec_ = ScriptedExecutor(["executed", "executed", "executed"])
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa"), _gap("missing-risk-register"), _gap("missing-role-matrix")],
            action_executor=exec_,
        )
        loop.run()
        self.assertEqual(len(loop.resolved_gaps()), 3)
        self.assertEqual(len(loop.unresolved_gaps()), 0)
        self.assertEqual(len(exec_.calls), 3)

    def test_gap_with_empty_list_terminates_immediately(self):
        loop = GapResolutionLoop(gaps=[], action_executor=ScriptedExecutor([]))
        loop.run()
        self.assertEqual(len(loop.audit_trace), 0)


class TestGapResolutionRetryLogic(unittest.TestCase):

    def test_gap_requires_retry_then_succeeds(self):
        # Custom verifier: requires 2 attempts before returning True.
        attempts = {"n": 0}
        def verifier(_g):
            attempts["n"] += 1
            return attempts["n"] >= 2
        exec_ = ScriptedExecutor(["executed", "executed", "executed"])
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa")],
            action_executor=exec_,
            verifier=verifier,
            max_retries=3,
        )
        loop.run()
        self.assertEqual(len(loop.resolved_gaps()), 1)
        # Should have taken 2 attempts.
        self.assertEqual(len(exec_.calls), 2)

    def test_gap_exceeds_retry_budget_marks_needs_human(self):
        # Verifier never returns True.
        def verifier(_g):
            return False
        exec_ = ScriptedExecutor(["executed", "executed", "executed"])
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa")],
            action_executor=exec_,
            verifier=verifier,
            max_retries=3,
        )
        loop.run()
        self.assertEqual(len(loop.unresolved_gaps()), 1)
        self.assertEqual(loop.unresolved_gaps()[0]["_status"], GAP_STATUS_NEEDS_HUMAN)
        # Should have tried max_retries times.
        self.assertEqual(len(exec_.calls), 3)

    def test_executor_raises_then_succeeds(self):
        calls = {"n": 0}
        class RaisingThenExec:
            def execute(self, _action):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise RuntimeError("transient failure")
                return SimpleNamespace(
                    request_id="x", status="executed", authority_mode_used="autonomous",
                    audit_entry_id="a", rollback_snapshot_path=None,
                    started_at="", ended_at="", output={}, error=None,
                )
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa")],
            action_executor=RaisingThenExec(),
            max_retries=3,
        )
        loop.run()
        self.assertEqual(len(loop.resolved_gaps()), 1)


class TestGapResolutionReActTrace(unittest.TestCase):

    def test_react_trace_contains_thought_action_observation(self):
        exec_ = ScriptedExecutor(["executed"])
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa")],
            action_executor=exec_,
        )
        loop.run()
        self.assertEqual(len(loop.audit_trace), 1)
        entry = loop.audit_trace[0]
        self.assertIn("thought", entry)
        self.assertIn("action", entry)
        self.assertIn("observation", entry)
        self.assertIn("outcome", entry)
        self.assertEqual(entry["outcome"], "resolved")
        self.assertEqual(entry["gap_key"], "missing-soa")

    def test_react_trace_records_each_attempt(self):
        def verifier(_g):
            return False
        exec_ = ScriptedExecutor(["executed"] * 10)
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa")],
            action_executor=exec_,
            verifier=verifier,
            max_retries=3,
        )
        loop.run()
        # 3 attempts should be recorded.
        outcomes = [e["outcome"] for e in loop.audit_trace]
        self.assertEqual(outcomes.count("retrying"), 2)
        self.assertEqual(outcomes.count("needs-human-intervention"), 1)

    def test_react_trace_includes_iteration_and_timestamp(self):
        exec_ = ScriptedExecutor(["executed"])
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa")],
            action_executor=exec_,
        )
        loop.run()
        entry = loop.audit_trace[0]
        self.assertIn("iteration", entry)
        self.assertIn("timestamp", entry)
        self.assertIn("loop_id", entry)


class TestGapResolutionEscalation(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_needs_human_emits_user_interaction(self):
        broker = UserInteractionBroker(interactions_dir=Path(self.tmp.name))
        def verifier(_g):
            return False
        exec_ = ScriptedExecutor(["executed"] * 5)
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa")],
            action_executor=exec_,
            verifier=verifier,
            max_retries=2,
            user_broker=broker,
        )
        loop.run()
        # Broker directory should have an interaction file.
        files = [p for p in Path(self.tmp.name).iterdir() if p.suffix == ".json"]
        self.assertEqual(len(files), 1)
        # Gap carries the interaction id.
        unresolved = loop.unresolved_gaps()[0]
        self.assertIn("_user_interaction_id", unresolved)

    def test_no_broker_still_escalates_gap(self):
        def verifier(_g):
            return False
        exec_ = ScriptedExecutor(["executed"] * 5)
        loop = GapResolutionLoop(
            gaps=[_gap("missing-soa")],
            action_executor=exec_,
            verifier=verifier,
            max_retries=2,
        )
        loop.run()
        unresolved = loop.unresolved_gaps()
        self.assertEqual(len(unresolved), 1)
        self.assertTrue(unresolved[0].get("_escalated"))


class TestGapResolutionAuditEntriesPerIteration(unittest.TestCase):

    def test_one_audit_entry_per_iteration(self):
        exec_ = ScriptedExecutor(["executed", "executed", "executed"])
        loop = GapResolutionLoop(
            gaps=[_gap("g1"), _gap("g2"), _gap("g3")],
            action_executor=exec_,
        )
        loop.run()
        self.assertEqual(len(loop.audit_trace), 3)
        for entry in loop.audit_trace:
            self.assertIn("iteration", entry)
            self.assertEqual(entry["outcome"], "resolved")


class TestGapResolutionMixedOutcomes(unittest.TestCase):

    def test_mix_of_resolved_and_needs_human(self):
        # First gap resolves immediately; second gap never verifies.
        verifier_gaps = {}
        def verifier(gap):
            # Resolve g1 immediately, never resolve g2.
            return gap.get("gap_key") == "g1"
        exec_ = ScriptedExecutor(["executed"] * 10)
        loop = GapResolutionLoop(
            gaps=[_gap("g1"), _gap("g2")],
            action_executor=exec_,
            verifier=verifier,
            max_retries=2,
        )
        loop.run()
        self.assertEqual(len(loop.resolved_gaps()), 1)
        self.assertEqual(loop.resolved_gaps()[0]["gap_key"], "g1")
        self.assertEqual(len(loop.unresolved_gaps()), 1)
        self.assertEqual(loop.unresolved_gaps()[0]["gap_key"], "g2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
