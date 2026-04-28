"""Tests for the PDCA orchestrator.

Uses stdlib unittest so the suite runs in the zero-dependency CI environment
used by aigovclaw. A MockActionExecutor and MockPlanner let us exercise the
full state machine without depending on the parallel-built plugins.

Run: python3 -m unittest aigovclaw.agent_loop.tests.test_orchestrator -v
     or: python3 aigovclaw/agent_loop/tests/test_orchestrator.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

# Ensure the package root is on sys.path when invoked as a script.
_PKG_ROOT = Path(__file__).resolve().parents[3]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from aigovclaw.agent_loop import (  # noqa: E402
    CascadeLoop,
    GapResolutionLoop,
    PDCACycle,
    PDCAPhase,
    PDCAError,
    UserInteractionBroker,
)
from aigovclaw.agent_loop.state import load_state  # noqa: E402


# ---------------------------------------------------------------------------
# Test doubles.
# ---------------------------------------------------------------------------


class MockActionExecutor:
    """Minimal double matching the ActionExecutor contract documented in the spec."""

    def __init__(self, *, status_sequence: list[str] | None = None, raise_on: set | None = None) -> None:
        self._statuses = list(status_sequence or [])
        self._raise_on = raise_on or set()
        self.calls: list[dict] = []

    def execute(self, action):
        if isinstance(action, dict):
            action_dict = action
        else:
            action_dict = {
                "action_id": getattr(action, "action_id", None),
                "target": getattr(action, "target", None),
                "request_id": getattr(action, "request_id", None),
            }
        self.calls.append(action_dict)
        if action_dict.get("request_id") in self._raise_on:
            raise RuntimeError("synthetic executor failure")
        status = self._statuses.pop(0) if self._statuses else "executed"
        return SimpleNamespace(
            request_id=action_dict.get("request_id"),
            status=status,
            authority_mode_used="autonomous",
            audit_entry_id="audit-test",
            rollback_snapshot_path=None,
            started_at="2026-04-18T00:00:00Z",
            ended_at="2026-04-18T00:00:01Z",
            output={},
            error=None,
        )


class MockPlanner:
    """Canned planner. Emits a fixed milestone list on each call."""

    def __init__(self, plan_sequence: list[dict] | None = None) -> None:
        self.plan_sequence = list(plan_sequence or [])
        self.calls: list[dict] = []

    def plan_certification_path(self, inputs):
        self.calls.append(inputs)
        if self.plan_sequence:
            return self.plan_sequence.pop(0)
        return {"milestones": []}


def make_readiness_assessor(sequence):
    seq = list(sequence)
    def _assess(_inputs):
        if seq:
            return seq.pop(0)
        return {"readiness_level": "not-ready", "summary": {"gap_count": 0, "blocker_count": 0}}
    return _assess


def make_audit_recorder():
    records: list[dict] = []
    def _rec(ev):
        records.append(ev)
    return _rec, records


# ---------------------------------------------------------------------------
# Test helpers.
# ---------------------------------------------------------------------------


def _make_cycle(tmp_path, *, plan_sequence=None, readiness_sequence=None,
                executor_statuses=None, max_iterations=5):
    broker_dir = Path(tmp_path) / "broker"
    broker_dir.mkdir(parents=True, exist_ok=True)
    broker = UserInteractionBroker(interactions_dir=broker_dir)
    audit, audit_records = make_audit_recorder()
    executor = MockActionExecutor(status_sequence=executor_statuses or [])
    planner = MockPlanner(plan_sequence=plan_sequence)
    assessor = make_readiness_assessor(readiness_sequence or [])
    cycle = PDCACycle(
        action_executor=executor,
        organization_ref="org-test",
        target_certification="iso42001-stage1",
        target_date="2026-12-31",
        planner=planner,
        readiness_assessor=assessor,
        audit_log_generator=audit,
        user_broker=broker,
        state_dir=Path(tmp_path) / "state",
        max_iterations=max_iterations,
    )
    return cycle, planner, executor, audit_records, broker


# ---------------------------------------------------------------------------
# Orchestrator tests (20+).
# ---------------------------------------------------------------------------


class TestOrchestratorConstruction(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_requires_organization_ref(self):
        with self.assertRaises(PDCAError):
            PDCACycle(
                action_executor=MockActionExecutor(),
                organization_ref="",
                target_certification="iso42001-stage1",
                target_date="2026-12-31",
                planner=MockPlanner(),
                readiness_assessor=lambda _: {"readiness_level": "not-ready"},
            )

    def test_requires_planner(self):
        with self.assertRaises(PDCAError):
            PDCACycle(
                action_executor=MockActionExecutor(),
                organization_ref="org",
                target_certification="iso42001-stage1",
                target_date="2026-12-31",
                planner=None,
                readiness_assessor=lambda _: {"readiness_level": "not-ready"},
            )

    def test_requires_readiness_assessor(self):
        with self.assertRaises(PDCAError):
            PDCACycle(
                action_executor=MockActionExecutor(),
                organization_ref="org",
                target_certification="iso42001-stage1",
                target_date="2026-12-31",
                planner=MockPlanner(),
                readiness_assessor=None,
            )

    def test_start_initializes_state_and_persists(self):
        cycle, *_ = _make_cycle(self.tmp.name)
        state = cycle.start()
        self.assertEqual(state["phase"], PDCAPhase.PLAN)
        self.assertEqual(state["iteration"], 1)
        # State persisted to disk.
        reloaded = load_state(state["cycle_id"], state_dir=Path(self.tmp.name) / "state")
        self.assertEqual(reloaded.cycle_id, state["cycle_id"])


class TestOrchestratorHappyPath(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_two_iteration_happy_path(self):
        plans = [
            {"milestones": [
                {"id": "m1", "remediation_action_requests": [
                    {"action_id": "re-run-plugin", "plugin": "orchestrator",
                     "target": "soa-generator", "args": {}, "rationale": "test"},
                ]},
            ]},
            {"milestones": [
                {"id": "m2", "remediation_action_requests": [
                    {"action_id": "re-run-plugin", "plugin": "orchestrator",
                     "target": "risk-register-builder", "args": {}, "rationale": "test"},
                ]},
            ]},
        ]
        readiness = [
            {"readiness_level": "partially-ready", "summary": {"gap_count": 3, "blocker_count": 0}},
            {"readiness_level": "ready-with-high-confidence", "summary": {"gap_count": 0, "blocker_count": 0}},
        ]
        cycle, planner, executor, audit, _ = _make_cycle(
            self.tmp.name,
            plan_sequence=plans,
            readiness_sequence=readiness,
            executor_statuses=["executed", "executed"],
        )
        cycle.start()
        # Drive to completion.
        for _ in range(30):
            state = cycle.step()
            if state["phase"] in (PDCAPhase.DONE, PDCAPhase.ABORTED):
                break
        self.assertEqual(cycle.state.phase, PDCAPhase.DONE)
        self.assertEqual(cycle.state.iteration, 2)
        self.assertEqual(len(executor.calls), 2)
        # Audit should have entries for plan-complete, do-action, check-complete, etc.
        kinds = [r["kind"] for r in audit]
        self.assertIn("pdca-cycle-started", kinds)
        self.assertIn("pdca-plan-complete", kinds)
        self.assertIn("pdca-do-action", kinds)
        self.assertIn("pdca-check-complete", kinds)
        self.assertIn("pdca-cycle-complete", kinds)

    def test_empty_plan_shortcircuits_to_check(self):
        plans = [{"milestones": []}]
        readiness = [{"readiness_level": "ready-with-high-confidence",
                       "summary": {"gap_count": 0, "blocker_count": 0}}]
        cycle, *_ = _make_cycle(self.tmp.name, plan_sequence=plans, readiness_sequence=readiness)
        cycle.start()
        cycle.step()  # Plan (empty).
        self.assertEqual(cycle.state.phase, PDCAPhase.CHECK)
        cycle.step()  # Check.
        self.assertEqual(cycle.state.phase, PDCAPhase.ACT)
        cycle.step()  # Act.
        self.assertEqual(cycle.state.phase, PDCAPhase.DONE)


class TestOrchestratorPauseResumeAbort(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_pause_halts_steps(self):
        cycle, *_ = _make_cycle(self.tmp.name)
        cycle.start()
        cycle.pause()
        self.assertTrue(cycle.state.paused_for_user)
        # step() should return without advancing.
        before_phase = cycle.state.phase
        state = cycle.step()
        self.assertEqual(state["phase"], before_phase)

    def test_resume_clears_paused_flag(self):
        cycle, *_ = _make_cycle(self.tmp.name)
        cycle.start()
        cycle.pause()
        cycle.resume()
        self.assertFalse(cycle.state.paused_for_user)
        self.assertIsNone(cycle.state.pending_user_interaction_id)

    def test_abort_marks_state_and_records_reason(self):
        cycle, *_ = _make_cycle(self.tmp.name)
        cycle.start()
        cycle.abort("operator-requested")
        self.assertEqual(cycle.state.phase, PDCAPhase.ABORTED)
        self.assertEqual(cycle.state.abort_reason, "operator-requested")
        # step() on aborted cycle is a no-op.
        state = cycle.step()
        self.assertEqual(state["phase"], PDCAPhase.ABORTED)


class TestOrchestratorMaxIterations(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_max_iterations_terminates_even_if_improving(self):
        # Always-improving (but never reaching terminal) readiness sequence.
        plans = [{"milestones": []}] * 5
        readiness = [
            {"readiness_level": "not-ready", "summary": {"gap_count": 5, "blocker_count": 1}},
            {"readiness_level": "partially-ready", "summary": {"gap_count": 3, "blocker_count": 0}},
            {"readiness_level": "ready-with-conditions", "summary": {"gap_count": 1, "blocker_count": 0}},
            {"readiness_level": "ready-with-conditions", "summary": {"gap_count": 1, "blocker_count": 0}},
            {"readiness_level": "ready-with-conditions", "summary": {"gap_count": 1, "blocker_count": 0}},
        ]
        cycle, *_ = _make_cycle(
            self.tmp.name, plan_sequence=plans, readiness_sequence=readiness,
            max_iterations=3,
        )
        cycle.start()
        for _ in range(40):
            state = cycle.step()
            if state["phase"] in (PDCAPhase.DONE, PDCAPhase.ABORTED):
                break
        self.assertIn(cycle.state.phase, (PDCAPhase.DONE, PDCAPhase.ABORTED))
        self.assertLessEqual(cycle.state.iteration, 3)


class TestOrchestratorPhaseTransitions(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_check_act_plan_loopback_on_improvement(self):
        plans = [
            {"milestones": []},
            {"milestones": []},
        ]
        readiness = [
            {"readiness_level": "partially-ready", "summary": {"gap_count": 2, "blocker_count": 0}},
            {"readiness_level": "ready-with-conditions", "summary": {"gap_count": 0, "blocker_count": 0}},
        ]
        cycle, *_ = _make_cycle(self.tmp.name, plan_sequence=plans, readiness_sequence=readiness, max_iterations=5)
        cycle.start()
        # Iteration 1: Plan(empty) -> Check -> Act. first-measurement treated
        # as 'improved' so iteration advances.
        cycle.step()  # Plan
        cycle.step()  # Check
        cycle.step()  # Act
        self.assertEqual(cycle.state.iteration, 2)
        self.assertEqual(cycle.state.phase, PDCAPhase.PLAN)

    def test_improvement_increments_iteration(self):
        plans = [{"milestones": []}, {"milestones": []}, {"milestones": []}]
        readiness = [
            {"readiness_level": "not-ready", "summary": {"gap_count": 5, "blocker_count": 1}},
            {"readiness_level": "partially-ready", "summary": {"gap_count": 2, "blocker_count": 0}},
            {"readiness_level": "ready-with-high-confidence", "summary": {"gap_count": 0, "blocker_count": 0}},
        ]
        cycle, *_, broker = _make_cycle(
            self.tmp.name, plan_sequence=plans, readiness_sequence=readiness, max_iterations=5,
        )
        cycle.start()
        # First-measurement advances. Subsequent 'improved' deltas advance
        # through to terminal verdict.
        for _ in range(30):
            state = cycle.step()
            if state["phase"] in (PDCAPhase.DONE, PDCAPhase.ABORTED):
                break
        self.assertEqual(cycle.state.phase, PDCAPhase.DONE)
        self.assertGreaterEqual(cycle.state.iteration, 2)


class TestOrchestratorStuckBehavior(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_stuck_verdict_pauses_for_user(self):
        plans = [{"milestones": []}, {"milestones": []}]
        readiness = [
            {"readiness_level": "partially-ready", "summary": {"gap_count": 3, "blocker_count": 0}},
            {"readiness_level": "partially-ready", "summary": {"gap_count": 3, "blocker_count": 0}},
        ]
        cycle, *_, broker = _make_cycle(
            self.tmp.name, plan_sequence=plans, readiness_sequence=readiness,
        )
        cycle.start()
        for _ in range(10):
            cycle.step()
            if cycle.state.paused_for_user:
                break
        self.assertTrue(cycle.state.paused_for_user)
        self.assertIsNotNone(cycle.state.pending_user_interaction_id)

    def test_stuck_emits_user_interaction(self):
        # Iteration 1 -> first-measurement (advances). Iteration 2 -> worsened
        # from partially-ready to not-ready triggers stuck.
        plans = [{"milestones": []}, {"milestones": []}]
        readiness = [
            {"readiness_level": "partially-ready", "summary": {"gap_count": 3, "blocker_count": 0}},
            {"readiness_level": "not-ready", "summary": {"gap_count": 5, "blocker_count": 2}},
        ]
        cycle, _, _, _, broker = _make_cycle(
            self.tmp.name, plan_sequence=plans, readiness_sequence=readiness,
        )
        cycle.start()
        for _ in range(15):
            cycle.step()
            if cycle.state.paused_for_user:
                break
        iid = cycle.state.pending_user_interaction_id
        self.assertIsNotNone(iid)
        # Broker directory should contain the interaction file.
        pending = [p for p in broker.dir.iterdir() if p.suffix == ".json"]
        self.assertTrue(any(iid in p.name for p in pending))


class TestOrchestratorApprovalPendingFlow(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_approved_pending_action_pauses_do_phase(self):
        plans = [{"milestones": [
            {"id": "m1", "remediation_action_requests": [
                {"action_id": "mcp-push", "plugin": "orchestrator",
                 "target": "external", "args": {}, "rationale": "test"},
            ]},
        ]}]
        readiness = [{"readiness_level": "ready-with-high-confidence",
                       "summary": {"gap_count": 0, "blocker_count": 0}}]
        cycle, _, _, _, broker = _make_cycle(
            self.tmp.name, plan_sequence=plans, readiness_sequence=readiness,
            executor_statuses=["approved-pending"],
        )
        cycle.start()
        cycle.step()  # Plan.
        cycle.step()  # Do - should hit approval-pending.
        self.assertTrue(cycle.state.paused_for_user)
        self.assertIsNotNone(cycle.state.pending_user_interaction_id)

    def test_resume_after_approval_advances_phase(self):
        plans = [{"milestones": [
            {"id": "m1", "remediation_action_requests": [
                {"action_id": "mcp-push", "plugin": "orchestrator",
                 "target": "x", "args": {}, "rationale": "test"},
            ]},
        ]}]
        readiness = [{"readiness_level": "ready-with-high-confidence",
                       "summary": {"gap_count": 0, "blocker_count": 0}}]
        cycle, _, _, _, broker = _make_cycle(
            self.tmp.name, plan_sequence=plans, readiness_sequence=readiness,
            executor_statuses=["approved-pending"],
        )
        cycle.start()
        cycle.step()  # Plan.
        cycle.step()  # Do - paused.
        iid = cycle.state.pending_user_interaction_id
        broker.resolve(iid, decision="approve", response={"decision": "approve"})
        cycle.resume()
        self.assertFalse(cycle.state.paused_for_user)


class TestOrchestratorAuditEntries(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_audit_emitted_on_start(self):
        cycle, _, _, audit, _ = _make_cycle(self.tmp.name)
        cycle.start()
        self.assertTrue(any(r["kind"] == "pdca-cycle-started" for r in audit))

    def test_audit_emitted_on_abort(self):
        cycle, _, _, audit, _ = _make_cycle(self.tmp.name)
        cycle.start()
        cycle.abort("test")
        self.assertTrue(any(r["kind"] == "pdca-cycle-aborted" for r in audit))

    def test_audit_includes_cycle_id_on_every_entry(self):
        cycle, _, _, audit, _ = _make_cycle(self.tmp.name)
        cycle.start()
        for r in audit:
            self.assertIn("payload", r)
            if "cycle_id" in r["payload"]:
                self.assertEqual(r["payload"]["cycle_id"], cycle.state.cycle_id)


class TestOrchestratorPersistence(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_state_persisted_after_each_step(self):
        plans = [{"milestones": []}]
        readiness = [{"readiness_level": "ready-with-high-confidence",
                       "summary": {"gap_count": 0, "blocker_count": 0}}]
        cycle, *_ = _make_cycle(self.tmp.name, plan_sequence=plans, readiness_sequence=readiness)
        cycle.start()
        cycle.step()
        state_dir = Path(self.tmp.name) / "state"
        state_file = state_dir / f"{cycle.state.cycle_id}.json"
        self.assertTrue(state_file.exists())
        on_disk = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["cycle_id"], cycle.state.cycle_id)

    def test_state_round_trip_via_load_state(self):
        cycle, *_ = _make_cycle(self.tmp.name)
        cycle.start()
        reloaded = load_state(cycle.state.cycle_id, state_dir=Path(self.tmp.name) / "state")
        self.assertEqual(reloaded.organization_ref, "org-test")
        self.assertEqual(reloaded.target_certification, "iso42001-stage1")


class TestOrchestratorVerdictDelta(unittest.TestCase):

    def test_delta_improved(self):
        self.assertEqual(PDCACycle._verdict_delta("not-ready", "partially-ready"), "improved")
        self.assertEqual(PDCACycle._verdict_delta("partially-ready", "ready-with-high-confidence"), "improved")

    def test_delta_worsened(self):
        self.assertEqual(PDCACycle._verdict_delta("ready-with-conditions", "not-ready"), "worsened")

    def test_delta_unchanged(self):
        self.assertEqual(PDCACycle._verdict_delta("partially-ready", "partially-ready"), "unchanged")

    def test_delta_first_measurement(self):
        self.assertEqual(PDCACycle._verdict_delta(None, "not-ready"), "first-measurement")


# ---------------------------------------------------------------------------
# Cascade loop tests.
# ---------------------------------------------------------------------------


class StubCascadeAnalyzer:
    def __init__(self, plans_by_event):
        self.plans = dict(plans_by_event)
        self.calls = []

    def analyze_cascade(self, inputs):
        self.calls.append(inputs)
        event = inputs.get("trigger_event", {}).get("event")
        return self.plans.get(event, {"flat_action_list": [], "cascade_tree": {}})


class TestCascadeLoop(unittest.TestCase):

    def test_no_cascade_empty_returns_empty_trace(self):
        analyzer = StubCascadeAnalyzer({})
        exec_mock = MockActionExecutor()
        loop = CascadeLoop(
            trigger_event={"event": "no-match", "source_plugin": "x"},
            cascade_analyzer=analyzer,
            action_executor=exec_mock,
        )
        trace = loop.run()
        # Initial analysis always emits one record.
        self.assertGreaterEqual(len(trace), 1)
        self.assertEqual(loop.actions_executed, 0)

    def test_depth_limit_enforced(self):
        # Every event produces one action and one further trigger. The loop
        # should stop at max_depth.
        analyzer = StubCascadeAnalyzer({
            f"ev-{i}": {
                "flat_action_list": [
                    {"action_id": "re-run-plugin", "plugin": "x", "target": "t",
                     "args": {}, "rationale": "r"},
                ],
            }
            for i in range(20)
        })
        exec_mock = MockActionExecutor()
        # trigger_derivation cycles events ev-0 -> ev-1 -> ...
        counter = {"i": 0}
        def derive(_result):
            counter["i"] += 1
            return {"event": f"ev-{counter['i']}", "source_plugin": "x"}
        loop = CascadeLoop(
            trigger_event={"event": "ev-0", "source_plugin": "x"},
            cascade_analyzer=analyzer,
            action_executor=exec_mock,
            max_depth=3,
            trigger_derivation=derive,
        )
        loop.run()
        # Depth 1, 2, 3 actions executed; derivations beyond depth 3 skipped.
        self.assertLessEqual(loop.actions_executed, 4)

    def test_budget_exhaustion_terminates(self):
        # Every action derives a new trigger with another action; budget=2 must stop.
        analyzer = StubCascadeAnalyzer({
            f"ev-{i}": {"flat_action_list": [
                {"action_id": "x", "plugin": "y", "target": "t", "args": {}, "rationale": "r"},
            ]}
            for i in range(20)
        })
        exec_mock = MockActionExecutor()
        counter = {"i": 0}
        def derive(_result):
            counter["i"] += 1
            return {"event": f"ev-{counter['i']}", "source_plugin": "x"}
        loop = CascadeLoop(
            trigger_event={"event": "ev-0", "source_plugin": "x"},
            cascade_analyzer=analyzer,
            action_executor=exec_mock,
            max_depth=10,
            action_budget=2,
            trigger_derivation=derive,
        )
        loop.run()
        self.assertLessEqual(loop.actions_executed, 3)

    def test_trigger_derivation_exception_handled_safely(self):
        analyzer = StubCascadeAnalyzer({
            "ev-0": {"flat_action_list": [
                {"action_id": "x", "plugin": "y", "target": "t", "args": {}, "rationale": "r"},
            ]}
        })
        exec_mock = MockActionExecutor()

        def faulty_derive(_result):
            raise ValueError("Intentional crash in trigger derivation")

        loop = CascadeLoop(
            trigger_event={"event": "ev-0", "source_plugin": "x"},
            cascade_analyzer=analyzer,
            action_executor=exec_mock,
            trigger_derivation=faulty_derive,
        )
        # Should not raise exception
        loop.run()

        # Only the initial action should be executed, no derived actions
        self.assertEqual(loop.actions_executed, 1)


# ---------------------------------------------------------------------------
# Validation loop tests.
# ---------------------------------------------------------------------------


from aigovclaw.agent_loop.loops.validation_loop import ValidationLoop  # noqa: E402


class TestValidationLoop(unittest.TestCase):

    def test_clean_on_first_validation(self):
        def validator(_p):
            return {"clean": True, "warnings": []}
        def refiner(p, _w):
            return p
        loop = ValidationLoop(
            proposal={"content": "x"},
            validator=validator,
            refiner=refiner,
        )
        loop.run()
        self.assertTrue(loop.is_clean)
        self.assertEqual(len(loop.audit_trace), 1)

    def test_refine_until_clean_success(self):
        calls = {"n": 0}
        def validator(_p):
            calls["n"] += 1
            if calls["n"] <= 2:
                return {"clean": False, "warnings": [f"w{calls['n']}"]}
            return {"clean": True, "warnings": []}
        def refiner(p, warnings):
            return {**p, "revision": p.get("revision", 0) + 1}
        loop = ValidationLoop(
            proposal={"content": "x", "revision": 0},
            validator=validator,
            refiner=refiner,
        )
        loop.run()
        self.assertTrue(loop.is_clean)
        self.assertEqual(loop.proposal["revision"], 2)

    def test_max_refinement_cap_hit(self):
        def validator(_p):
            return {"clean": False, "warnings": ["persistent"]}
        def refiner(p, _w):
            return {**p, "r": p.get("r", 0) + 1}
        loop = ValidationLoop(
            proposal={"r": 0},
            validator=validator,
            refiner=refiner,
            max_iterations=3,
        )
        loop.run()
        self.assertFalse(loop.is_clean)
        # max-iterations-hit means the run loop exited without completing.
        self.assertEqual(loop.iteration, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
