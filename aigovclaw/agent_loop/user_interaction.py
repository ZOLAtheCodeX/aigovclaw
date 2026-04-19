"""User-interaction mechanism for PDCA loops.

When a loop needs a human decision (approval, input, or resolution of an
ambiguous situation), it emits a user-input-required entry on the Command
Centre approval queue. The loop pauses; the orchestrator state records the
pending interaction id. When the user answers via
/api/approvals/{id}/approve with a response payload, the loop resumes with
the supplied input.

This module is a thin, stdlib-only broker. It does not depend on the
running Hub v2 server; it writes directly to the approval-queue directory
and reads back when resolved. This keeps the orchestrator runnable in
standalone mode (CI, tests, offline PDCA runs) while still interoperating
with the server when the server is live.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INTERACTION_TYPE = "user-input-required"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_interactions_dir() -> Path:
    return Path.home() / ".hermes" / "memory" / "aigovclaw" / "hub-v2-approvals"


@dataclass
class UserInteractionRequest:
    """A structured prompt emitted to the approval queue.

    Fields:
        interaction_id: unique id; used as the approval-queue task_id.
        prompt: human-readable question.
        context: structured context (gap_key, loop_id, etc).
        required_response_shape: schema hint for the expected response.
        emitted_by: originating loop or orchestrator identifier.
        emitted_at: ISO 8601 UTC timestamp.
        response: populated once resolved.
        resolved_at: ISO 8601 UTC timestamp when the user answered.
        decision: approve or reject.
    """

    interaction_id: str
    prompt: str
    context: dict[str, Any]
    required_response_shape: dict[str, Any]
    emitted_by: str
    emitted_at: str = field(default_factory=_utc_now_iso)
    response: dict[str, Any] | None = None
    resolved_at: str | None = None
    decision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UserInteractionBroker:
    """Queues user-input requests on the approval queue directory.

    The directory layout mirrors hub.v2_server.approval_queue: one
    <interaction_id>.json file per pending prompt. The broker adds a
    discriminator field type=user-input-required so the Command Centre UI
    can render these differently from ordinary task-approval entries.
    """

    def __init__(self, *, interactions_dir: Path | None = None) -> None:
        self.dir = Path(interactions_dir) if interactions_dir else _default_interactions_dir()
        self.dir.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        *,
        prompt: str,
        context: dict[str, Any],
        required_response_shape: dict[str, Any],
        emitted_by: str,
    ) -> UserInteractionRequest:
        """Create a new user-input prompt and persist it to the queue."""
        iid = "ui-" + uuid.uuid4().hex[:16]
        req = UserInteractionRequest(
            interaction_id=iid,
            prompt=prompt,
            context=context,
            required_response_shape=required_response_shape,
            emitted_by=emitted_by,
        )
        path = self.dir / f"{iid}.json"
        payload = {
            "task_id": iid,
            "type": INTERACTION_TYPE,
            "command": "user-input",
            "args": context,
            "argv": [],
            "queued_at": req.emitted_at,
            "decision": None,
            "decided_at": None,
            "decided_by": None,
            "reason": None,
            "prompt": prompt,
            "required_response_shape": required_response_shape,
            "emitted_by": emitted_by,
            "response": None,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return req

    def poll(self, interaction_id: str) -> UserInteractionRequest | None:
        """Check if a prompt has been answered. Returns None if still pending."""
        path = self.dir / f"{interaction_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        if data.get("decision") is None:
            return None
        return UserInteractionRequest(
            interaction_id=data.get("task_id", interaction_id),
            prompt=data.get("prompt", ""),
            context=data.get("args") or {},
            required_response_shape=data.get("required_response_shape") or {},
            emitted_by=data.get("emitted_by", ""),
            emitted_at=data.get("queued_at", _utc_now_iso()),
            response=data.get("response"),
            resolved_at=data.get("decided_at"),
            decision=data.get("decision"),
        )

    def resolve(
        self,
        interaction_id: str,
        *,
        decision: str,
        response: dict[str, Any] | None = None,
        decided_by: str = "operator",
    ) -> UserInteractionRequest:
        """Record a user's response to a prompt. Used by tests and by the
        extended /api/approvals/{id}/approve handler when it accepts a
        response payload.
        """
        if decision not in ("approve", "reject"):
            raise ValueError("decision must be 'approve' or 'reject'")
        path = self.dir / f"{interaction_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"interaction not found: {interaction_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decision"] = decision
        data["decided_at"] = _utc_now_iso()
        data["decided_by"] = decided_by
        data["response"] = response
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return UserInteractionRequest(
            interaction_id=interaction_id,
            prompt=data.get("prompt", ""),
            context=data.get("args") or {},
            required_response_shape=data.get("required_response_shape") or {},
            emitted_by=data.get("emitted_by", ""),
            emitted_at=data.get("queued_at", _utc_now_iso()),
            response=response,
            resolved_at=data["decided_at"],
            decision=decision,
        )
