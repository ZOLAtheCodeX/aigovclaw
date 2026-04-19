"""Abstract base class for inner loops.

A Loop is a bounded iterative process with a termination predicate. The
base class owns the iteration counter, the audit trace, pause/resume/abort
hooks, and the max-iterations cap. Concrete subclasses implement step() and
should_terminate().

Design: loops are driven by step(). One call to step() performs one atomic
unit of work and returns a record describing what happened. The outer
orchestrator calls run() which calls step() until should_terminate()
returns True or max_iterations is reached.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


class LoopStatus:
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"
    AWAITING_USER = "awaiting-user"
    MAX_ITERATIONS_HIT = "max-iterations-hit"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Loop(ABC):
    """Base class for all inner loops.

    Subclasses must implement should_terminate() and step(). The base class
    provides audit-trace bookkeeping, status transitions, and run().
    """

    def __init__(self, *, max_iterations: int = 10, loop_id: str | None = None) -> None:
        self.max_iterations = max_iterations
        self.loop_id = loop_id or self.__class__.__name__
        self.audit_trace: list[dict[str, Any]] = []
        self.iteration: int = 0
        self._status: str = LoopStatus.RUNNING
        self._abort_reason: str | None = None

    # ------------------------------------------------------------------
    # Status accessors.
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        return self._status

    @property
    def abort_reason(self) -> str | None:
        return self._abort_reason

    # ------------------------------------------------------------------
    # Abstract contract.
    # ------------------------------------------------------------------

    @abstractmethod
    def should_terminate(self) -> bool:
        """Return True when the loop has reached its natural terminus."""

    @abstractmethod
    def step(self) -> dict[str, Any]:
        """Execute one iteration and return a structured record of what happened.

        The record will be appended to audit_trace automatically by run().
        Subclasses should not append to audit_trace themselves from step().
        """

    # ------------------------------------------------------------------
    # Control hooks.
    # ------------------------------------------------------------------

    def pause(self) -> None:
        if self._status == LoopStatus.RUNNING:
            self._status = LoopStatus.PAUSED

    def resume(self) -> None:
        if self._status in (LoopStatus.PAUSED, LoopStatus.AWAITING_USER):
            self._status = LoopStatus.RUNNING

    def abort(self, reason: str) -> None:
        self._status = LoopStatus.ABORTED
        self._abort_reason = reason

    def await_user(self) -> None:
        self._status = LoopStatus.AWAITING_USER

    def complete(self) -> None:
        self._status = LoopStatus.COMPLETED

    # ------------------------------------------------------------------
    # Driver.
    # ------------------------------------------------------------------

    def run(self) -> list[dict[str, Any]]:
        """Drive the loop to termination, pause, or max-iterations.

        Returns the audit_trace. Callers that need finer control should use
        step() directly.
        """
        while self._status == LoopStatus.RUNNING:
            if self.should_terminate():
                self.complete()
                break
            if self.iteration >= self.max_iterations:
                self._status = LoopStatus.MAX_ITERATIONS_HIT
                break
            self.iteration += 1
            record = self.step()
            if not isinstance(record, dict):
                raise TypeError(
                    f"Loop.step() must return a dict; got {type(record).__name__}"
                )
            record.setdefault("iteration", self.iteration)
            record.setdefault("timestamp", _utc_now_iso())
            record.setdefault("loop_id", self.loop_id)
            self.audit_trace.append(record)
        return list(self.audit_trace)

    # ------------------------------------------------------------------
    # Helpers.
    # ------------------------------------------------------------------

    def record(self, entry: dict[str, Any]) -> None:
        """Append an out-of-band record to the audit trace."""
        entry.setdefault("timestamp", _utc_now_iso())
        entry.setdefault("loop_id", self.loop_id)
        self.audit_trace.append(entry)
