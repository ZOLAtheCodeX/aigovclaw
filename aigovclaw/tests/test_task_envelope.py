"""Tests for the TaskEnvelope ingress schema."""

from __future__ import annotations

import json

import pytest

from aigovclaw.task_envelope import TaskEnvelope, TaskEnvelopeError, VALID_SOURCE_TYPES


def _valid_payload() -> dict:
    return {
        "envelope_id": "01H000000000000000000AUDIT",
        "command": "audit-log",
        "args": {"system_name": "test-system", "risk_tier": "minimal"},
        "source_type": "hub-api",
        "source_id": "hub-v2-server",
        "actor": "operator@example.test",
        "rationale": "Generate audit entry for unit test fixture.",
        "requested_at": "2026-04-19T00:00:00Z",
        "dry_run": False,
        "metadata": {"priority": "normal"},
    }


def test_from_dict_round_trips_to_dict():
    env = TaskEnvelope.from_dict(_valid_payload())
    assert env.to_dict()["command"] == "audit-log"
    assert env.to_dict()["source_type"] == "hub-api"


def test_from_dict_sets_defaults_for_optional_fields():
    payload = _valid_payload()
    del payload["dry_run"]
    del payload["metadata"]
    del payload["rationale"]
    env = TaskEnvelope.from_dict(payload)
    assert env.dry_run is False
    assert env.metadata == {}
    assert env.rationale == ""


def test_missing_required_field_raises():
    payload = _valid_payload()
    del payload["command"]
    with pytest.raises(TaskEnvelopeError, match="command"):
        TaskEnvelope.from_dict(payload)


def test_invalid_source_type_raises():
    payload = _valid_payload()
    payload["source_type"] = "not-a-real-source"
    with pytest.raises(TaskEnvelopeError, match="source_type"):
        TaskEnvelope.from_dict(payload)


def test_empty_command_raises():
    payload = _valid_payload()
    payload["command"] = ""
    with pytest.raises(TaskEnvelopeError, match="command"):
        TaskEnvelope.from_dict(payload)


def test_args_must_be_dict():
    payload = _valid_payload()
    payload["args"] = ["not", "a", "dict"]
    with pytest.raises(TaskEnvelopeError, match="args"):
        TaskEnvelope.from_dict(payload)


def test_non_dict_input_raises():
    with pytest.raises(TaskEnvelopeError, match="dict"):
        TaskEnvelope.from_dict("not a dict")  # type: ignore[arg-type]


def test_every_valid_source_type_accepted():
    payload = _valid_payload()
    for source in VALID_SOURCE_TYPES:
        payload["source_type"] = source
        env = TaskEnvelope.from_dict(payload)
        assert env.source_type == source


def test_dict_round_trips_through_json():
    env = TaskEnvelope.from_dict(_valid_payload())
    serialized = json.dumps(env.to_dict())
    reloaded = TaskEnvelope.from_dict(json.loads(serialized))
    assert reloaded == env
