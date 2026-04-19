"""Persisted state for PDCA cycles.

Each cycle records its phase, iteration, timestamps, verdict history, and
(when applicable) the identifier of the currently-running inner loop. State
is persisted under:

    ~/.hermes/memory/aigovclaw/agent-loop-state/<cycle_id>.json

The persistence format is intentionally JSON for forward compatibility with
external inspection tools and for symmetry with the Hub v2 task runner.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state_dir() -> Path:
    return Path.home() / ".hermes" / "memory" / "aigovclaw" / "agent-loop-state"


@dataclass
class PDCACycleState:
    """State for a single PDCA cycle, persisted across runs.

    Fields:
        cycle_id: unique identifier for this cycle.
        organization_ref: caller-provided reference to the subject organization.
        target_certification: one of the VALID_TARGETS from certification-readiness.
        target_date: ISO date for the certification deadline.
        phase: current phase (plan, do, check, act, done, aborted).
        iteration: 1-based iteration counter across the outer loop.
        started_at: ISO 8601 UTC timestamp when the cycle was created.
        last_checkpoint: ISO 8601 UTC timestamp of the last state write.
        current_loop: identifier of the currently-running inner loop, or None.
        paused_for_user: True if the cycle is halted awaiting user input.
        pending_user_interaction_id: approval-queue id of an unresolved prompt.
        readiness_history: list of dicts {iteration, readiness_level, verdict_delta}.
        max_iterations: outer-loop termination cap.
        plan_cache: most recent certification-path-planner output for Do phase.
        last_readiness_ref: path to the most recent readiness-assessment artifact.
        abort_reason: set when phase == aborted.
    """

    cycle_id: str
    organization_ref: str
    target_certification: str
    target_date: str
    phase: str = "plan"
    iteration: int = 1
    started_at: str = field(default_factory=_utc_now_iso)
    last_checkpoint: str = field(default_factory=_utc_now_iso)
    current_loop: str | None = None
    paused_for_user: bool = False
    pending_user_interaction_id: str | None = None
    readiness_history: list[dict[str, Any]] = field(default_factory=list)
    max_iterations: int = 10
    plan_cache: dict[str, Any] | None = None
    last_readiness_ref: str | None = None
    abort_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PDCACycleState":
        allowed = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)


def save_state(state: PDCACycleState, state_dir: Path | None = None) -> Path:
    """Persist a cycle state to disk. Returns the file path."""
    base = Path(state_dir) if state_dir else default_state_dir()
    base.mkdir(parents=True, exist_ok=True)
    state.last_checkpoint = _utc_now_iso()
    path = base / f"{state.cycle_id}.json"
    path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    return path


def load_state(cycle_id: str, state_dir: Path | None = None) -> PDCACycleState:
    """Load a cycle state from disk. Raises FileNotFoundError if absent."""
    base = Path(state_dir) if state_dir else default_state_dir()
    path = base / f"{cycle_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"PDCA cycle state not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return PDCACycleState.from_dict(data)
