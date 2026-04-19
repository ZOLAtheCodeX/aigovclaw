"""Task envelope: canonical input contract at the ingress boundary.

A TaskEnvelope is the form that external callers (Hub v2 HTTP API, CLI,
channel adapters, scheduled triggers) use to submit work to AIGovClaw.
The envelope is distinct from an ActionRequest: one envelope can resolve
to zero, one, or many ActionRequests once a workflow runs.

The envelope carries everything the downstream policy, workflow, and
audit layers need to make decisions without re-reading upstream state:
who asked, through what channel, with what rationale, at what time, and
under which request-id.

This file is stdlib-only by design. The runtime-config package does not
take a pydantic dependency. Validation is explicit via validate() which
raises TaskEnvelopeError on the first failure. Callers deserialize JSON
into dicts then call from_dict() which validates before returning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


VALID_SOURCE_TYPES = (
    "hub-api",
    "hub-ui",
    "cli",
    "channel-slack",
    "channel-discord",
    "channel-telegram",
    "channel-email",
    "scheduled",
    "cascade",
    "test",
)


class TaskEnvelopeError(ValueError):
    """Raised when a TaskEnvelope fails validation."""


@dataclass
class TaskEnvelope:
    """Canonical task submission envelope.

    Fields:
        envelope_id: deterministic unique id. Callers generate via
            aigovclaw.action_executor.safety.new_request_id() or an
            equivalent time-ordered identifier.
        command: stable command name from the Hub command registry
            (for example audit-log, gap-assessment, risk-register).
        args: command-specific arguments. Structure is owned by the
            workflow the command resolves to; the envelope does not
            validate inner shape beyond requiring a dict.
        source_type: categorical ingress type. See VALID_SOURCE_TYPES.
        source_id: free-form identifier of the originating surface
            (channel id, user id, scheduled-task id, cascade-node id).
        actor: the human or system principal that initiated the task.
            Use "system:<name>" for non-human initiators.
        rationale: free-text justification. Recorded on every audit
            entry that descends from this envelope.
        requested_at: ISO 8601 UTC timestamp of ingress.
        dry_run: when True, downstream action handlers return a preview
            and do not mutate state. Propagates to every ActionRequest
            derived from this envelope.
        metadata: additional context the workflow may consume but the
            envelope does not interpret (locale, priority, thread id).
    """

    envelope_id: str
    command: str
    args: dict[str, Any]
    source_type: str
    source_id: str
    actor: str
    rationale: str
    requested_at: str
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Raise TaskEnvelopeError on the first structural problem."""
        if not isinstance(self.envelope_id, str) or not self.envelope_id:
            raise TaskEnvelopeError("envelope_id must be a non-empty string")
        if not isinstance(self.command, str) or not self.command:
            raise TaskEnvelopeError("command must be a non-empty string")
        if not isinstance(self.args, dict):
            raise TaskEnvelopeError("args must be a dict")
        if self.source_type not in VALID_SOURCE_TYPES:
            raise TaskEnvelopeError(
                f"source_type {self.source_type!r} not in {VALID_SOURCE_TYPES}"
            )
        if not isinstance(self.source_id, str) or not self.source_id:
            raise TaskEnvelopeError("source_id must be a non-empty string")
        if not isinstance(self.actor, str) or not self.actor:
            raise TaskEnvelopeError("actor must be a non-empty string")
        if not isinstance(self.rationale, str):
            raise TaskEnvelopeError("rationale must be a string (may be empty)")
        if not isinstance(self.requested_at, str) or not self.requested_at:
            raise TaskEnvelopeError("requested_at must be a non-empty ISO 8601 string")
        if not isinstance(self.dry_run, bool):
            raise TaskEnvelopeError("dry_run must be a bool")
        if not isinstance(self.metadata, dict):
            raise TaskEnvelopeError("metadata must be a dict")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON encoding."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskEnvelope":
        """Deserialize from a dict and validate. Raises TaskEnvelopeError on failure."""
        if not isinstance(data, dict):
            raise TaskEnvelopeError("envelope payload must be a dict")
        try:
            envelope = cls(
                envelope_id=data["envelope_id"],
                command=data["command"],
                args=data.get("args") or {},
                source_type=data["source_type"],
                source_id=data["source_id"],
                actor=data["actor"],
                rationale=data.get("rationale", ""),
                requested_at=data["requested_at"],
                dry_run=bool(data.get("dry_run", False)),
                metadata=data.get("metadata") or {},
            )
        except KeyError as exc:
            raise TaskEnvelopeError(f"missing required field: {exc.args[0]}") from exc
        envelope.validate()
        return envelope
