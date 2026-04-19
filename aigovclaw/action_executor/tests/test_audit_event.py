"""Tests for AuditEvent schema."""

from __future__ import annotations

import pytest

from aigovclaw.action_executor.audit_event import (
    AuditEvent,
    AuditEventError,
    EVENT_ACTION_COMPLETED,
    EVENT_ACTION_INTENT,
    EVENT_QUALITY_GATE_FAILED,
    VALID_EVENT_TYPES,
)


def test_minimal_valid_event_validates():
    evt = AuditEvent(
        event=EVENT_ACTION_INTENT,
        timestamp="2026-04-19T00:00:00Z",
    )
    evt.validate()


def test_unknown_event_type_rejected():
    evt = AuditEvent(event="not-a-real-event", timestamp="2026-04-19T00:00:00Z")
    with pytest.raises(AuditEventError, match="event"):
        evt.validate()


def test_missing_timestamp_rejected():
    evt = AuditEvent(event=EVENT_ACTION_INTENT, timestamp="")
    with pytest.raises(AuditEventError, match="timestamp"):
        evt.validate()


def test_to_dict_flattens_payload_for_on_disk_shape():
    evt = AuditEvent(
        event=EVENT_ACTION_COMPLETED,
        timestamp="2026-04-19T00:00:00Z",
        audit_entry_id="01H00ENTRY",
        request_id="01H00REQUEST",
        plugin="audit-log-generator",
        action="re-run-plugin",
        target="audit-log-generator",
        payload={"output": {"system_name": "x"}, "rollback_snapshot_path": None},
    )
    flat = evt.to_dict()
    assert flat["event"] == EVENT_ACTION_COMPLETED
    assert flat["plugin"] == "audit-log-generator"
    assert flat["output"] == {"system_name": "x"}
    assert flat["rollback_snapshot_path"] is None


def test_from_dict_preserves_unknown_fields_in_payload():
    flat = {
        "event": EVENT_ACTION_INTENT,
        "timestamp": "2026-04-19T00:00:00Z",
        "plugin": "p",
        "authority_mode": "ask-permission",
        "risk_tier": "high",
        "dry_run": False,
    }
    evt = AuditEvent.from_dict(flat)
    assert evt.event == EVENT_ACTION_INTENT
    assert evt.plugin == "p"
    assert evt.payload["authority_mode"] == "ask-permission"
    assert evt.payload["risk_tier"] == "high"
    assert evt.payload["dry_run"] is False


def test_round_trip_is_lossless():
    flat_in = {
        "event": EVENT_QUALITY_GATE_FAILED,
        "timestamp": "2026-04-19T00:00:00Z",
        "audit_entry_id": "A",
        "request_id": "R",
        "plugin": "p",
        "action": "a",
        "target": "t",
        "gate_name": "citation-format",
        "detail": "Annex A.5.2 missing",
    }
    evt = AuditEvent.from_dict(flat_in)
    flat_out = evt.to_dict()
    assert flat_out == flat_in


def test_every_declared_event_type_is_valid():
    for event_type in VALID_EVENT_TYPES:
        AuditEvent(event=event_type, timestamp="2026-04-19T00:00:00Z").validate()
