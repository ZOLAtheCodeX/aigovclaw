"""Audit event schema.

Formalizes the shape of entries written by AuditLogger. The logger
continues to accept free-form dicts for backward compatibility, but
every callsite should populate fields from this module's constants
and the AuditEvent.validate() helper to catch schema drift early.

Event types land in the audit log at memory_root/audit-log/YYYY-MM-DD.jsonl
and feed:
    - the rate limiter (counts action-intent)
    - the Hub v2 approval queue view
    - the ISO 42001 Clause 9.1 audit trail
    - the PDCA orchestrator's re-run replay logic

This module is stdlib-only. Validation is a no-op helper that raises
on obvious shape errors; it does not enforce a JSON Schema.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


EVENT_ACTION_INTENT = "action-intent"
EVENT_ACTION_COMPLETED = "action-completed"
EVENT_ACTION_FAILED = "action-failed"
EVENT_ACTION_REJECTED = "action-rejected"
EVENT_ACTION_APPROVED = "action-approved"
EVENT_ACTION_DRY_RUN = "action-dry-run"
EVENT_ACTION_RATE_LIMITED = "action-rate-limited"
EVENT_ENVELOPE_ACCEPTED = "envelope-accepted"
EVENT_ENVELOPE_REJECTED = "envelope-rejected"
EVENT_WORKFLOW_STARTED = "workflow-started"
EVENT_WORKFLOW_COMPLETED = "workflow-completed"
EVENT_WORKFLOW_FAILED = "workflow-failed"
EVENT_QUALITY_GATE_FAILED = "quality-gate-failed"

VALID_EVENT_TYPES = (
    EVENT_ACTION_INTENT,
    EVENT_ACTION_COMPLETED,
    EVENT_ACTION_FAILED,
    EVENT_ACTION_REJECTED,
    EVENT_ACTION_APPROVED,
    EVENT_ACTION_DRY_RUN,
    EVENT_ACTION_RATE_LIMITED,
    EVENT_ENVELOPE_ACCEPTED,
    EVENT_ENVELOPE_REJECTED,
    EVENT_WORKFLOW_STARTED,
    EVENT_WORKFLOW_COMPLETED,
    EVENT_WORKFLOW_FAILED,
    EVENT_QUALITY_GATE_FAILED,
)


class AuditEventError(ValueError):
    """Raised when an AuditEvent payload fails validation."""


@dataclass
class AuditEvent:
    """Canonical audit log entry shape.

    Fields:
        event: categorical event type. See VALID_EVENT_TYPES.
        timestamp: ISO 8601 UTC timestamp when the event occurred.
        audit_entry_id: deterministic unique id for this entry.
            AuditLogger.write populates this on append; callers may
            leave it empty at construction time.
        request_id: correlates to the ActionRequest or TaskEnvelope
            that this event describes. Empty for system-originated
            events with no upstream correlation.
        plugin: originating plugin name, or "aigovclaw" for executor-
            internal events.
        action: action_id from the action registry, if applicable.
        target: primary target string (filepath, plugin name, etc).
        payload: event-specific structured data. Callers stay within
            documented per-event shapes; this dict is not further
            validated at the schema boundary.
        hmac_sha256: optional HMAC signature, written only when
            AIGOVCLAW_AUDIT_SIGNING_KEY is set in the environment.
    """

    event: str
    timestamp: str
    audit_entry_id: str = ""
    request_id: str = ""
    plugin: str = ""
    action: str = ""
    target: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    hmac_sha256: str = ""

    def validate(self) -> None:
        """Raise AuditEventError on the first structural problem."""
        if self.event not in VALID_EVENT_TYPES:
            raise AuditEventError(
                f"event {self.event!r} not in {VALID_EVENT_TYPES}"
            )
        if not isinstance(self.timestamp, str) or not self.timestamp:
            raise AuditEventError("timestamp must be a non-empty ISO 8601 string")
        if not isinstance(self.payload, dict):
            raise AuditEventError("payload must be a dict")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the on-disk JSONL shape.

        The logger historically wrote flat dicts with event-specific
        fields at the top level. For backward compatibility, this
        method flattens the payload onto the root object. New callsites
        should prefer the explicit payload={} form.
        """
        out = {
            "event": self.event,
            "timestamp": self.timestamp,
        }
        if self.audit_entry_id:
            out["audit_entry_id"] = self.audit_entry_id
        if self.request_id:
            out["request_id"] = self.request_id
        if self.plugin:
            out["plugin"] = self.plugin
        if self.action:
            out["action"] = self.action
        if self.target:
            out["target"] = self.target
        out.update(self.payload)
        if self.hmac_sha256:
            out["hmac_sha256"] = self.hmac_sha256
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEvent":
        """Parse a flat on-disk dict back into an AuditEvent.

        Fields not in the canonical set are preserved under payload to
        keep round-tripping lossless against the legacy flat writer.
        """
        if not isinstance(data, dict):
            raise AuditEventError("audit event data must be a dict")
        known = {
            "event", "timestamp", "audit_entry_id", "request_id",
            "plugin", "action", "target", "hmac_sha256",
        }
        payload = {k: v for k, v in data.items() if k not in known}
        event = cls(
            event=data.get("event", ""),
            timestamp=data.get("timestamp", ""),
            audit_entry_id=data.get("audit_entry_id", ""),
            request_id=data.get("request_id", ""),
            plugin=data.get("plugin", ""),
            action=data.get("action", ""),
            target=data.get("target", ""),
            payload=payload,
            hmac_sha256=data.get("hmac_sha256", ""),
        )
        event.validate()
        return event
