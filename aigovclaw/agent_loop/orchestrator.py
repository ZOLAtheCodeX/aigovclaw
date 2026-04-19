"""PDCA cycle orchestrator.

Drives the AI Management System through Plan-Do-Check-Act cycles:

    Plan   - invoke certification-path-planner with current readiness.
    Do     - execute each milestone's action requests via the executor.
    Check  - re-run certification-readiness.assess_readiness on the bundle.
    Act    - compare verdicts. Improved: increment iteration, go to Plan.
             Unchanged or worsened: surface to approval queue as PDCA-stuck,
             optionally trigger a cascade loop.

Termination: readiness == 'ready-with-high-confidence' OR user abort OR
max_iterations (default 10).

All dependencies are injected. The orchestrator does not import
certification-path-planner or cascade-impact-analyzer directly; callers
pass instances (real or test doubles). This keeps the orchestrator
runnable in environments where the parallel-built plugins are not yet
available and makes testing straightforward.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .loops.cascade_loop import CascadeLoop
from .loops.gap_resolution import GapResolutionLoop
from .state import PDCACycleState, default_state_dir, save_state
from .user_interaction import UserInteractionBroker


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------


class PDCAPhase:
    PLAN = "plan"
    DO = "do"
    CHECK = "check"
    ACT = "act"
    DONE = "done"
    ABORTED = "aborted"


READINESS_TERMINAL = "ready-with-high-confidence"

READINESS_RANK = {
    "not-ready": 0,
    "partially-ready": 1,
    "ready-with-conditions": 2,
    "ready-with-high-confidence": 3,
}


class PDCAError(RuntimeError):
    """Raised for structural orchestrator errors (bad state, missing deps)."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# PDCACycle.
# ---------------------------------------------------------------------------


class PDCACycle:
    """A single Plan-Do-Check-Act cycle instance.

    Constructor args:
        action_executor: ActionExecutor instance (or test double) with execute().
        organization_ref: caller-provided opaque ref to the organization.
        target_certification: target from certification-readiness.VALID_TARGETS.
        target_date: ISO date for the certification deadline.
        planner: object exposing plan_certification_path(inputs); used in Plan.
        readiness_assessor: callable(inputs) -> report; used in Check.
        cascade_analyzer: optional object exposing analyze_cascade(); used
                          in Act when the verdict stalls.
        audit_log_generator: optional callable(event_dict) -> None; receives
                             one call per orchestrator phase transition.
        user_broker: optional UserInteractionBroker. Constructed by default.
        state_dir: optional override for persistence root.
        max_iterations: outer-loop cap. Default 10.
        cycle_id: optional explicit id; a new one is generated otherwise.
    """

    def __init__(
        self,
        *,
        action_executor: Any,
        organization_ref: str,
        target_certification: str,
        target_date: str,
        planner: Any,
        readiness_assessor: Callable[[dict[str, Any]], dict[str, Any]],
        cascade_analyzer: Any = None,
        audit_log_generator: Callable[[dict[str, Any]], Any] | None = None,
        user_broker: UserInteractionBroker | None = None,
        state_dir: Path | None = None,
        max_iterations: int = 10,
        cycle_id: str | None = None,
    ) -> None:
        if not organization_ref:
            raise PDCAError("organization_ref is required")
        if not target_certification:
            raise PDCAError("target_certification is required")
        if not target_date:
            raise PDCAError("target_date is required")
        if planner is None:
            raise PDCAError("planner is required")
        if readiness_assessor is None:
            raise PDCAError("readiness_assessor is required")

        self.executor = action_executor
        self.planner = planner
        self.readiness_assessor = readiness_assessor
        self.cascade_analyzer = cascade_analyzer
        self.audit_log_generator = audit_log_generator
        self.user_broker = user_broker or UserInteractionBroker()
        self.state_dir = Path(state_dir) if state_dir else default_state_dir()
        self.state_dir.mkdir(parents=True, exist_ok=True)

        cid = cycle_id or ("pdca-" + uuid.uuid4().hex[:16])
        self.state = PDCACycleState(
            cycle_id=cid,
            organization_ref=organization_ref,
            target_certification=target_certification,
            target_date=target_date,
            max_iterations=max_iterations,
        )
        self._current_inner_loop: Any = None

    # ------------------------------------------------------------------
    # Lifecycle.
    # ------------------------------------------------------------------

    def start(self) -> dict[str, Any]:
        """Initialize the cycle and record the first audit entry."""
        self.state.phase = PDCAPhase.PLAN
        self.state.iteration = 1
        self.state.started_at = _utc_now_iso()
        self._emit_audit("pdca-cycle-started", {
            "cycle_id": self.state.cycle_id,
            "target_certification": self.state.target_certification,
            "target_date": self.state.target_date,
            "max_iterations": self.state.max_iterations,
        })
        self._persist()
        return self.state.to_dict()

    def pause(self) -> dict[str, Any]:
        """Pause after the current atomic operation."""
        self.state.paused_for_user = True
        self._emit_audit("pdca-cycle-paused", {"cycle_id": self.state.cycle_id})
        self._persist()
        return self.state.to_dict()

    def resume(self) -> dict[str, Any]:
        """Unpause the cycle. Callers should then invoke step()."""
        self.state.paused_for_user = False
        self.state.pending_user_interaction_id = None
        self._emit_audit("pdca-cycle-resumed", {"cycle_id": self.state.cycle_id})
        self._persist()
        return self.state.to_dict()

    def abort(self, reason: str) -> dict[str, Any]:
        self.state.phase = PDCAPhase.ABORTED
        self.state.abort_reason = reason
        self._emit_audit("pdca-cycle-aborted", {
            "cycle_id": self.state.cycle_id,
            "reason": reason,
        })
        self._persist()
        return self.state.to_dict()

    # ------------------------------------------------------------------
    # Step dispatcher.
    # ------------------------------------------------------------------

    def step(self) -> dict[str, Any]:
        """Advance the cycle by one phase, or continue the current loop.

        Returns the post-step state dict.
        """
        if self.state.phase in (PDCAPhase.DONE, PDCAPhase.ABORTED):
            return self.state.to_dict()
        if self.state.paused_for_user:
            return self.state.to_dict()

        phase = self.state.phase
        if phase == PDCAPhase.PLAN:
            self._run_plan()
        elif phase == PDCAPhase.DO:
            self._run_do()
        elif phase == PDCAPhase.CHECK:
            self._run_check()
        elif phase == PDCAPhase.ACT:
            self._run_act()
        else:
            raise PDCAError(f"unknown phase {phase!r}")

        self._persist()
        return self.state.to_dict()

    # ------------------------------------------------------------------
    # Phase implementations.
    # ------------------------------------------------------------------

    def _run_plan(self) -> None:
        inputs = {
            "current_readiness_ref": self.state.last_readiness_ref or "",
            "target_certification": self.state.target_certification,
            "target_date": self.state.target_date,
        }
        try:
            plan_output = self.planner.plan_certification_path(inputs)
        except Exception as exc:
            self._emit_audit("pdca-plan-failed", {
                "cycle_id": self.state.cycle_id,
                "error": f"{type(exc).__name__}: {exc}",
            })
            self.abort(f"plan-failed: {exc}")
            return

        if not isinstance(plan_output, dict):
            self.abort("planner returned non-dict output")
            return

        milestones = plan_output.get("milestones") or []
        self.state.plan_cache = plan_output

        self._emit_audit("pdca-plan-complete", {
            "cycle_id": self.state.cycle_id,
            "iteration": self.state.iteration,
            "milestone_count": len(milestones),
        })

        if not milestones:
            # Nothing to do; short-circuit to Check so the terminal verdict is
            # captured.
            self.state.phase = PDCAPhase.CHECK
            return

        self.state.phase = PDCAPhase.DO

    def _run_do(self) -> None:
        plan = self.state.plan_cache or {}
        milestones = plan.get("milestones") or []
        pending_approval = False

        for milestone in milestones:
            actions = milestone.get("remediation_action_requests") or []
            for action in actions:
                if not isinstance(action, dict):
                    continue
                action = dict(action)
                action.setdefault("request_id", "act-" + uuid.uuid4().hex[:20])
                action.setdefault("requested_at", _utc_now_iso())
                action.setdefault("rationale", (
                    f"PDCA Do phase iteration {self.state.iteration} "
                    f"for milestone {milestone.get('id', 'unknown')}"
                ))
                try:
                    result = self._invoke_executor(action)
                except Exception as exc:
                    self._emit_audit("pdca-do-action-error", {
                        "cycle_id": self.state.cycle_id,
                        "milestone": milestone.get("id"),
                        "request_id": action.get("request_id"),
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                    continue
                status = self._extract_status(result)
                self._emit_audit("pdca-do-action", {
                    "cycle_id": self.state.cycle_id,
                    "milestone": milestone.get("id"),
                    "request_id": action.get("request_id"),
                    "result_status": status,
                })
                if status == "approved-pending":
                    pending_approval = True
                    # Emit a user-input prompt so the approval cannot be
                    # silently lost.
                    req = self.user_broker.emit(
                        prompt=(
                            f"Approval required for action {action.get('action_id')} "
                            f"on target {action.get('target')} (milestone "
                            f"{milestone.get('id')})."
                        ),
                        context={
                            "cycle_id": self.state.cycle_id,
                            "request_id": action.get("request_id"),
                            "milestone_id": milestone.get("id"),
                        },
                        required_response_shape={"decision": "approve | reject"},
                        emitted_by=f"pdca-cycle/{self.state.cycle_id}",
                    )
                    self.state.paused_for_user = True
                    self.state.pending_user_interaction_id = req.interaction_id
                    return  # Halt Do phase; resume() will un-pause.

        if pending_approval:
            # Should not reach here; handled above.
            return

        self.state.phase = PDCAPhase.CHECK

    def _run_check(self) -> None:
        try:
            report = self.readiness_assessor({
                "target_certification": self.state.target_certification,
                "organization_ref": self.state.organization_ref,
            })
        except Exception as exc:
            self._emit_audit("pdca-check-failed", {
                "cycle_id": self.state.cycle_id,
                "error": f"{type(exc).__name__}: {exc}",
            })
            self.abort(f"check-failed: {exc}")
            return

        if not isinstance(report, dict):
            self.abort("readiness_assessor returned non-dict output")
            return

        verdict = report.get("readiness_level", "not-ready")
        previous = self.state.readiness_history[-1]["readiness_level"] if self.state.readiness_history else None
        delta = self._verdict_delta(previous, verdict)

        self.state.readiness_history.append({
            "iteration": self.state.iteration,
            "readiness_level": verdict,
            "verdict_delta": delta,
            "gap_count": report.get("summary", {}).get("gap_count", 0) if isinstance(report.get("summary"), dict) else 0,
            "blocker_count": report.get("summary", {}).get("blocker_count", 0) if isinstance(report.get("summary"), dict) else 0,
        })

        self._emit_audit("pdca-check-complete", {
            "cycle_id": self.state.cycle_id,
            "iteration": self.state.iteration,
            "readiness_level": verdict,
            "verdict_delta": delta,
        })

        self.state.phase = PDCAPhase.ACT

    def _run_act(self) -> None:
        history = self.state.readiness_history
        if not history:
            self.abort("act-phase reached with no readiness history")
            return

        latest = history[-1]
        verdict = latest["readiness_level"]
        delta = latest["verdict_delta"]

        if verdict == READINESS_TERMINAL:
            self.state.phase = PDCAPhase.DONE
            self._emit_audit("pdca-cycle-complete", {
                "cycle_id": self.state.cycle_id,
                "iteration": self.state.iteration,
                "readiness_level": verdict,
            })
            return

        if delta in ("improved", "first-measurement"):
            if self.state.iteration >= self.state.max_iterations:
                self.state.phase = PDCAPhase.DONE
                self._emit_audit("pdca-max-iterations-hit", {
                    "cycle_id": self.state.cycle_id,
                    "iteration": self.state.iteration,
                })
                return
            self.state.iteration += 1
            self.state.phase = PDCAPhase.PLAN
            self._emit_audit("pdca-iteration-increment", {
                "cycle_id": self.state.cycle_id,
                "new_iteration": self.state.iteration,
            })
            return

        # Unchanged or worsened: surface PDCA-stuck and optionally trigger
        # cascade analysis.
        req = self.user_broker.emit(
            prompt=(
                f"PDCA cycle {self.state.cycle_id} is stuck at readiness_level="
                f"{verdict} (delta={delta}) after iteration {self.state.iteration}. "
                "Human intervention required."
            ),
            context={
                "cycle_id": self.state.cycle_id,
                "iteration": self.state.iteration,
                "verdict": verdict,
                "delta": delta,
            },
            required_response_shape={
                "decision": "one of: retry | abort | trigger-cascade | accept-with-conditions",
                "notes": "free text, optional",
            },
            emitted_by=f"pdca-cycle/{self.state.cycle_id}",
        )
        self.state.paused_for_user = True
        self.state.pending_user_interaction_id = req.interaction_id
        self._emit_audit("pdca-stuck", {
            "cycle_id": self.state.cycle_id,
            "iteration": self.state.iteration,
            "verdict": verdict,
            "delta": delta,
            "interaction_id": req.interaction_id,
        })

    # ------------------------------------------------------------------
    # Inner-loop dispatcher.
    # ------------------------------------------------------------------

    def run_gap_resolution(
        self,
        gaps: list[dict[str, Any]],
        *,
        verifier: Callable[[dict[str, Any]], bool] | None = None,
        max_retries: int = 3,
    ) -> GapResolutionLoop:
        """Delegate to a GapResolutionLoop. Used by Do phase or callers
        wanting direct gap remediation outside the full PDCA cycle.
        """
        loop = GapResolutionLoop(
            gaps=gaps,
            action_executor=self.executor,
            verifier=verifier,
            user_broker=self.user_broker,
            max_retries=max_retries,
        )
        self.state.current_loop = loop.loop_id
        self._persist()
        loop.run()
        self.state.current_loop = None
        self._persist()
        return loop

    def run_cascade(
        self,
        trigger_event: dict[str, Any],
        *,
        max_depth: int = 5,
        action_budget: int = 50,
    ) -> CascadeLoop:
        if self.cascade_analyzer is None:
            raise PDCAError("cascade_analyzer was not provided to this PDCACycle")
        loop = CascadeLoop(
            trigger_event=trigger_event,
            cascade_analyzer=self.cascade_analyzer,
            action_executor=self.executor,
            max_depth=max_depth,
            action_budget=action_budget,
        )
        self.state.current_loop = loop.loop_id
        self._persist()
        loop.run()
        self.state.current_loop = None
        self._persist()
        return loop

    # ------------------------------------------------------------------
    # Helpers.
    # ------------------------------------------------------------------

    @staticmethod
    def _verdict_delta(previous: str | None, current: str) -> str:
        if previous is None:
            return "first-measurement"
        prev_rank = READINESS_RANK.get(previous, -1)
        curr_rank = READINESS_RANK.get(current, -1)
        if curr_rank > prev_rank:
            return "improved"
        if curr_rank < prev_rank:
            return "worsened"
        return "unchanged"

    def _invoke_executor(self, action: dict[str, Any]) -> Any:
        execute = getattr(self.executor, "execute", None)
        if execute is None:
            raise PDCAError("action_executor does not expose execute()")
        try:
            from aigovclaw.action_executor import ActionRequest  # type: ignore
            request = ActionRequest(**{
                k: v for k, v in action.items() if k in ActionRequest.__dataclass_fields__
            })
            return execute(request)
        except Exception:
            return execute(action)

    @staticmethod
    def _extract_status(result: Any) -> str | None:
        if result is None:
            return None
        if isinstance(result, dict):
            return result.get("status")
        return getattr(result, "status", None)

    def _emit_audit(self, event_kind: str, payload: dict[str, Any]) -> None:
        if self.audit_log_generator is None:
            return
        try:
            self.audit_log_generator({
                "kind": event_kind,
                "timestamp": _utc_now_iso(),
                "payload": payload,
            })
        except Exception:
            # Audit-log errors must not propagate and break the loop.
            pass

    def _persist(self) -> None:
        save_state(self.state, state_dir=self.state_dir)
