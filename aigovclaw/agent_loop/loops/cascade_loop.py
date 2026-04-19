"""Cascade propagation loop.

Given a triggering event, invokes the cascade-impact-analyzer to derive a
flat list of downstream ActionRequests, executes each via the action
executor, and recurses when an action's completion emits a new cascade
trigger. Depth-limited (default 5) to prevent runaway propagation, and
budget-limited on total action count.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from .base_loop import Loop


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class CascadeLoop(Loop):
    """Depth-limited cascade propagation over a triggering event tree.

    Args:
        trigger_event: dict {event, source_plugin, [payload]}; passed to the
                       analyzer on the first iteration.
        cascade_analyzer: object exposing analyze_cascade(inputs) that
                          returns {flat_action_list, cascade_tree, ...}.
        action_executor: ActionExecutor (or test double).
        max_depth: maximum recursion depth. Default 5.
        action_budget: maximum total actions executed across all depths.
                       Default 50.
        trigger_derivation: callable(ActionResult) -> trigger_event dict or
                            None, used to detect further cascade triggers
                            after each action. Defaults to a no-op builder
                            that yields no further triggers.
    """

    def __init__(
        self,
        *,
        trigger_event: dict[str, Any],
        cascade_analyzer: Any,
        action_executor: Any,
        max_depth: int = 5,
        action_budget: int = 50,
        trigger_derivation: Callable[[Any], dict[str, Any] | None] | None = None,
        loop_id: str | None = None,
    ) -> None:
        super().__init__(max_iterations=action_budget + 1, loop_id=loop_id or "cascade")
        self.trigger_event = trigger_event
        self.analyzer = cascade_analyzer
        self.executor = action_executor
        self.max_depth = max_depth
        self.action_budget = action_budget
        self.trigger_derivation = trigger_derivation or (lambda _r: None)
        # Queue of (depth, action_dict) pairs.
        self._pending: list[tuple[int, dict[str, Any]]] = []
        self._analyzed_triggers: list[dict[str, Any]] = []
        self._actions_executed: int = 0
        self._initialized: bool = False
        self._terminated_reason: str | None = None

    # ------------------------------------------------------------------
    # Loop contract.
    # ------------------------------------------------------------------

    def should_terminate(self) -> bool:
        if self._terminated_reason is not None:
            return True
        if not self._initialized:
            return False
        if not self._pending:
            return True
        if self._actions_executed >= self.action_budget:
            self._terminated_reason = "budget-exhausted"
            return True
        return False

    def step(self) -> dict[str, Any]:
        if not self._initialized:
            return self._initial_analysis()

        depth, action = self._pending.pop(0)
        if depth > self.max_depth:
            return {
                "thought": f"action at depth {depth} exceeds max_depth={self.max_depth}; skipping",
                "action": self._summarize_action(action),
                "observation": {"skipped": True, "reason": "depth-limit"},
                "outcome": "skipped-depth",
                "depth": depth,
            }

        if self._actions_executed >= self.action_budget:
            self._terminated_reason = "budget-exhausted"
            return {
                "thought": "action budget exhausted",
                "action": self._summarize_action(action),
                "observation": {"skipped": True, "reason": "budget-exhausted"},
                "outcome": "skipped-budget",
                "depth": depth,
            }

        try:
            result = self._invoke_executor(action)
            self._actions_executed += 1
            error = None
        except Exception as exc:
            result = None
            error = f"{type(exc).__name__}: {exc}"
            self._actions_executed += 1

        # Check whether the completion triggers a further cascade.
        derived = None
        if result is not None and error is None:
            try:
                derived = self.trigger_derivation(result)
            except Exception as exc:
                error = f"trigger-derivation-failed: {type(exc).__name__}: {exc}"
                derived = None

        if derived and depth < self.max_depth:
            self._expand(derived, depth + 1)
            derived_action_count = len(self._pending) - (len(self._pending) - 0)  # populated by _expand
        else:
            derived_action_count = 0

        return {
            "thought": (
                f"executed cascade action at depth {depth}; "
                f"budget_used={self._actions_executed}/{self.action_budget}"
            ),
            "action": self._summarize_action(action),
            "observation": {
                "result_status": self._extract_status(result),
                "error": error,
                "further_trigger": derived is not None,
                "derived_actions_enqueued": derived_action_count,
            },
            "outcome": "executed" if error is None else "failed",
            "depth": depth,
        }

    # ------------------------------------------------------------------
    # Internals.
    # ------------------------------------------------------------------

    def _initial_analysis(self) -> dict[str, Any]:
        self._initialized = True
        self._expand(self.trigger_event, depth=1)
        return {
            "thought": "initial cascade analysis complete",
            "action": None,
            "observation": {
                "trigger_event": self.trigger_event,
                "actions_enqueued": len(self._pending),
            },
            "outcome": "analyzed",
            "depth": 0,
        }

    def _expand(self, trigger_event: dict[str, Any], depth: int) -> None:
        """Invoke the analyzer for this trigger and enqueue its actions."""
        self._analyzed_triggers.append({"depth": depth, "event": trigger_event})
        analyze = getattr(self.analyzer, "analyze_cascade", None)
        if analyze is None:
            return
        try:
            output = analyze({"trigger_event": trigger_event})
        except Exception as exc:
            self.record({
                "error": f"analyzer-failed: {type(exc).__name__}: {exc}",
                "depth": depth,
            })
            return
        if not isinstance(output, dict):
            return
        actions = output.get("flat_action_list") or []
        if not isinstance(actions, list):
            return
        for action in actions:
            if not isinstance(action, dict):
                continue
            action = dict(action)
            action.setdefault("request_id", "act-" + uuid.uuid4().hex[:20])
            action.setdefault("requested_at", _utc_now_iso())
            self._pending.append((depth, action))

    def _invoke_executor(self, action: dict[str, Any]) -> Any:
        execute = getattr(self.executor, "execute", None)
        if execute is None:
            raise RuntimeError("action_executor does not expose execute()")
        try:
            from aigovclaw.action_executor import ActionRequest  # type: ignore
            request = ActionRequest(**{k: v for k, v in action.items() if k in ActionRequest.__dataclass_fields__})
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

    @staticmethod
    def _summarize_action(action: dict[str, Any]) -> dict[str, Any]:
        return {
            "action_id": action.get("action_id"),
            "target": action.get("target"),
            "request_id": action.get("request_id"),
        }

    @property
    def actions_executed(self) -> int:
        return self._actions_executed

    @property
    def terminated_reason(self) -> str | None:
        return self._terminated_reason
