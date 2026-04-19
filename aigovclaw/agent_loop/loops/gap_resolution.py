"""Gap-resolution inner loop.

Implements the ReAct-style remediation loop:

    for each gap:
        thought: "gap X requires action Y"
        action:  ActionRequest submitted to executor
        observation: ActionResult + follow-up gap re-assessment
        if still gap: retry with backoff (up to max_retries attempts)
        if still failing: mark gap as needs-human-intervention and emit a
                          user-input prompt on the approval queue

Terminates when all gaps are either resolved or marked needs-human-intervention.

The loop emits one audit entry per step. Each entry is a ReAct trace
record: {thought, action, observation, outcome}. The full audit_trace is
suitable for inclusion in an audit-log-generator run after the fact.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from .base_loop import Loop, LoopStatus


GAP_STATUS_OPEN = "open"
GAP_STATUS_RESOLVED = "resolved"
GAP_STATUS_NEEDS_HUMAN = "needs-human-intervention"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class GapResolutionLoop(Loop):
    """ReAct-style remediation over a batch of certification-readiness gaps.

    Args:
        gaps: list of gap dicts from certification-readiness (each must
              carry gap_key and description, matching the plugin output).
        action_executor: an ActionExecutor (or test double) exposing execute().
        verifier: optional callable(gap) -> bool that returns True when the
                  gap has been resolved. Defaults to a stub that treats
                  executor-reported success as resolution.
        action_builder: optional callable(gap) -> ActionRequest-like dict
                        used to construct the action. Defaults to a builder
                        derived from the gap's target_plugin field.
        user_broker: optional UserInteractionBroker; used to surface
                     needs-human-intervention prompts to the Command Centre.
        max_retries: per-gap retry budget before escalation. Default 3.
        max_iterations: overall step cap. Default len(gaps) * (max_retries + 1).
    """

    def __init__(
        self,
        *,
        gaps: list[dict[str, Any]],
        action_executor: Any,
        verifier: Callable[[dict[str, Any]], bool] | None = None,
        action_builder: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        user_broker: Any = None,
        max_retries: int = 3,
        max_iterations: int | None = None,
        loop_id: str | None = None,
    ) -> None:
        default_cap = max(1, len(gaps) * (max_retries + 1) + 1)
        super().__init__(
            max_iterations=max_iterations or default_cap,
            loop_id=loop_id or "gap-resolution",
        )
        self.gaps: list[dict[str, Any]] = [
            {
                **g,
                "_status": GAP_STATUS_OPEN,
                "_attempts": 0,
                "_last_error": None,
            }
            for g in gaps
        ]
        self.executor = action_executor
        self.verifier = verifier or self._default_verifier
        self.action_builder = action_builder or self._default_action_builder
        self.user_broker = user_broker
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # Default stubs.
    # ------------------------------------------------------------------

    @staticmethod
    def _default_verifier(gap: dict[str, Any]) -> bool:
        """Treat the most recent action result as the verification signal.

        The default verifier inspects gap['_last_result'] (populated by
        step()) and returns True when status == 'executed'. Callers that
        need re-running the gap-assessment plugin should pass a custom
        verifier.
        """
        last = gap.get("_last_result")
        if last is None:
            return False
        status = getattr(last, "status", None) if not isinstance(last, dict) else last.get("status")
        return status == "executed"

    @staticmethod
    def _default_action_builder(gap: dict[str, Any]) -> dict[str, Any]:
        """Build a re-run-plugin ActionRequest from gap metadata."""
        target_plugin = gap.get("target_plugin") or gap.get("artifact_type") or "practitioner-review"
        rationale = (
            f"gap-resolution loop remediating {gap.get('gap_key', 'unknown-gap')}: "
            f"{gap.get('description', '')}"
        )
        return {
            "action_id": "re-run-plugin",
            "plugin": "orchestrator",
            "target": target_plugin,
            "args": {"gap_key": gap.get("gap_key", "")},
            "rationale": rationale,
            "dry_run": False,
            "requested_at": _utc_now_iso(),
            "request_id": "act-" + uuid.uuid4().hex[:20],
        }

    # ------------------------------------------------------------------
    # Loop contract.
    # ------------------------------------------------------------------

    def should_terminate(self) -> bool:
        return all(
            g["_status"] in (GAP_STATUS_RESOLVED, GAP_STATUS_NEEDS_HUMAN)
            for g in self.gaps
        )

    def _next_open_gap(self) -> dict[str, Any] | None:
        for g in self.gaps:
            if g["_status"] == GAP_STATUS_OPEN:
                return g
        return None

    def step(self) -> dict[str, Any]:
        gap = self._next_open_gap()
        if gap is None:
            # Should be caught by should_terminate; defensive stub.
            return {
                "thought": "no open gaps remain",
                "action": None,
                "observation": None,
                "outcome": "noop",
            }

        thought = (
            f"gap {gap.get('gap_key', 'unknown')} is open after "
            f"{gap['_attempts']} attempt(s); requires remediation via target_plugin="
            f"{gap.get('target_plugin', 'unknown')}."
        )

        action = self.action_builder(gap)
        gap["_attempts"] += 1

        try:
            result = self._invoke_executor(action)
            gap["_last_result"] = result
            error = None
        except Exception as exc:
            result = None
            gap["_last_result"] = None
            gap["_last_error"] = f"{type(exc).__name__}: {exc}"
            error = gap["_last_error"]

        verified = False
        if result is not None and error is None:
            try:
                verified = bool(self.verifier(gap))
            except Exception as exc:
                error = f"verifier-raised: {type(exc).__name__}: {exc}"
                verified = False

        if verified:
            gap["_status"] = GAP_STATUS_RESOLVED
            outcome = "resolved"
        elif gap["_attempts"] >= self.max_retries:
            gap["_status"] = GAP_STATUS_NEEDS_HUMAN
            outcome = "needs-human-intervention"
            self._surface_to_user(gap, error)
        else:
            outcome = "retrying"

        observation = {
            "result_status": self._extract_status(result),
            "verified": verified,
            "error": error,
            "attempt": gap["_attempts"],
            "retries_remaining": max(0, self.max_retries - gap["_attempts"]),
        }

        return {
            "thought": thought,
            "action": self._summarize_action(action),
            "observation": observation,
            "outcome": outcome,
            "gap_key": gap.get("gap_key"),
        }

    # ------------------------------------------------------------------
    # Helpers.
    # ------------------------------------------------------------------

    def _invoke_executor(self, action: dict[str, Any]) -> Any:
        """Call executor.execute, tolerating both the real ActionRequest
        dataclass and plain-dict test doubles.
        """
        execute = getattr(self.executor, "execute", None)
        if execute is None:
            raise RuntimeError("action_executor does not expose execute()")
        # Attempt structured ActionRequest first for real executor.
        try:
            from aigovclaw.action_executor import ActionRequest  # type: ignore
            request = ActionRequest(**{k: v for k, v in action.items() if k in ActionRequest.__dataclass_fields__})
            return execute(request)
        except Exception:
            # Fallback: pass the dict directly (test doubles).
            return execute(action)

    @staticmethod
    def _extract_status(result: Any) -> str | None:
        if result is None:
            return None
        if isinstance(result, dict):
            return result.get("status")
        return getattr(result, "status", None)

    @staticmethod
    def _summarize_action(action: dict[str, Any]) -> dict[str, Any]:
        return {
            "action_id": action.get("action_id"),
            "target": action.get("target"),
            "request_id": action.get("request_id"),
            "rationale": action.get("rationale"),
            "dry_run": action.get("dry_run", False),
        }

    def _surface_to_user(self, gap: dict[str, Any], error: str | None) -> None:
        if self.user_broker is None:
            gap["_escalated"] = True
            return
        try:
            req = self.user_broker.emit(
                prompt=(
                    f"Gap '{gap.get('gap_key')}' could not be resolved after "
                    f"{self.max_retries} attempts. Please review and provide "
                    "direction: retry with modified parameters, defer to next cycle, or mark accepted-with-risk."
                ),
                context={
                    "gap_key": gap.get("gap_key"),
                    "description": gap.get("description"),
                    "artifact_type": gap.get("artifact_type"),
                    "last_error": error,
                    "loop_id": self.loop_id,
                },
                required_response_shape={
                    "decision": "one of: retry | defer | accept-with-risk",
                    "notes": "free text, optional",
                },
                emitted_by=self.loop_id,
            )
            gap["_user_interaction_id"] = req.interaction_id
            gap["_escalated"] = True
        except Exception as exc:
            gap["_escalation_error"] = f"{type(exc).__name__}: {exc}"
            gap["_escalated"] = False

    # ------------------------------------------------------------------
    # Public reporting.
    # ------------------------------------------------------------------

    def resolved_gaps(self) -> list[dict[str, Any]]:
        return [g for g in self.gaps if g["_status"] == GAP_STATUS_RESOLVED]

    def unresolved_gaps(self) -> list[dict[str, Any]]:
        return [g for g in self.gaps if g["_status"] == GAP_STATUS_NEEDS_HUMAN]
