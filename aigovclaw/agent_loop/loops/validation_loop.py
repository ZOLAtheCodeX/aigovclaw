"""Validation / refine-until-clean loop.

Given a proposed change (a file update, an artifact generation call), apply
it in dry-run mode, invoke a validator, and if the validator returns
warnings, refine the proposal using those warnings and re-run. Terminate
when the validator returns clean, when max refinements (default 5) is hit,
or when the caller aborts.
"""

from __future__ import annotations

from typing import Any, Callable

from .base_loop import Loop


class ValidationLoop(Loop):
    """Refine-until-clean loop over a single proposed change.

    Args:
        proposal: the initial change (dict; shape is validator-specific).
        validator: callable(proposal) -> {clean: bool, warnings: list[str]}.
        refiner: callable(proposal, warnings) -> refined proposal.
        executor: optional object with execute() used for non-dry-run
                  application on success; not invoked inside the loop.
        dry_run_only: when True, never calls executor. Default True.
        max_iterations: refinement cap. Default 5.
    """

    def __init__(
        self,
        *,
        proposal: dict[str, Any],
        validator: Callable[[dict[str, Any]], dict[str, Any]],
        refiner: Callable[[dict[str, Any], list[str]], dict[str, Any]],
        executor: Any = None,
        dry_run_only: bool = True,
        max_iterations: int = 5,
        loop_id: str | None = None,
    ) -> None:
        super().__init__(max_iterations=max_iterations, loop_id=loop_id or "validation")
        self.proposal = dict(proposal)
        self.validator = validator
        self.refiner = refiner
        self.executor = executor
        self.dry_run_only = dry_run_only
        self._clean: bool = False
        self._last_warnings: list[str] = []

    # ------------------------------------------------------------------
    # Loop contract.
    # ------------------------------------------------------------------

    def should_terminate(self) -> bool:
        return self._clean

    def step(self) -> dict[str, Any]:
        try:
            verdict = self.validator(self.proposal)
        except Exception as exc:
            self.abort(f"validator-raised: {type(exc).__name__}: {exc}")
            return {
                "thought": "validator raised; aborting",
                "action": None,
                "observation": {"error": str(exc)},
                "outcome": "aborted",
            }
        if not isinstance(verdict, dict):
            self.abort("validator returned non-dict verdict")
            return {
                "thought": "validator returned non-dict verdict; aborting",
                "action": None,
                "observation": {"verdict": verdict},
                "outcome": "aborted",
            }
        warnings = verdict.get("warnings") or []
        if not isinstance(warnings, list):
            warnings = [str(warnings)]
        self._last_warnings = [str(w) for w in warnings]
        clean = bool(verdict.get("clean")) and not warnings
        if clean:
            self._clean = True
            return {
                "thought": "validator clean; terminating",
                "action": None,
                "observation": {"clean": True, "warnings": []},
                "outcome": "clean",
            }
        # Refine and continue.
        previous = self.proposal
        try:
            self.proposal = self.refiner(self.proposal, list(self._last_warnings))
        except Exception as exc:
            self.abort(f"refiner-raised: {type(exc).__name__}: {exc}")
            return {
                "thought": "refiner raised; aborting",
                "action": None,
                "observation": {"error": str(exc)},
                "outcome": "aborted",
            }
        return {
            "thought": (
                f"validator returned {len(self._last_warnings)} warning(s); "
                "invoking refiner and re-validating"
            ),
            "action": {"op": "refine", "previous_len": len(str(previous))},
            "observation": {
                "clean": False,
                "warnings": list(self._last_warnings),
                "refined_len": len(str(self.proposal)),
            },
            "outcome": "refined",
        }

    # ------------------------------------------------------------------
    # Public accessors.
    # ------------------------------------------------------------------

    @property
    def is_clean(self) -> bool:
        return self._clean

    @property
    def last_warnings(self) -> list[str]:
        return list(self._last_warnings)
