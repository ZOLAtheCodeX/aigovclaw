"""
AIGovClaw: Local Filesystem Adapter

The null / baseline adapter. Writes artifact dicts to the existing
local source-of-record path at ~/.hermes/memory/aigovclaw/<artifact-type>/.
Implements the adapter contract defined in the adapters README so that
the adapter layer has a reference implementation against which concrete
external adapters (notion, archer, drata, and others) can be compared
during Phase 4.

Status: functional baseline. Not a stub. Runs as the default destination
when no external adapter is configured.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ADAPTER_NAME = "local-filesystem"
ADAPTER_VERSION = "0.1.0"

SUPPORTED_ARTIFACT_TYPES = frozenset((
    "audit-log-entry",
    "risk-register-row",
    "SoA-row",
    "AISIA-section",
    "role-matrix",
    "review-minutes",
    "nonconformity-record",
    "KPI",
    "gap-assessment",
    "review-package",
    "metrics-report",
    "soa",
    "aisia",
))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _classify_action(artifact: dict[str, Any]) -> str:
    """Derive the action-item classification tag from artifact warnings."""
    warnings = artifact.get("warnings") or []
    if isinstance(warnings, list) and len(warnings) > 0:
        return "action-required-human"
    # Per-row warnings aggregated.
    row_warnings = 0
    for key in ("rows", "records", "sections", "kpi_records"):
        items = artifact.get(key) or []
        for item in items:
            if isinstance(item, dict) and item.get("warnings"):
                row_warnings += len(item["warnings"])
    if row_warnings > 0:
        return "action-required-human"
    # Low-confidence signals: draft agent_signature, small summary numbers, scaffold_rows present.
    if artifact.get("scaffold_rows") or artifact.get("scaffold_sections"):
        return "completed-autonomously-low-confidence"
    return "completed-autonomously-high-confidence"


class LocalFilesystemAdapter:
    """Adapter that writes artifacts to the local Hermes memory filesystem."""

    name = ADAPTER_NAME
    version = ADAPTER_VERSION

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        base = config.get("base_path") or os.path.expanduser("~/.hermes/memory/aigovclaw")
        self.base_path = Path(base)

    def health_check(self) -> dict[str, Any]:
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            probe = self.base_path / ".health-probe"
            probe.write_text(_utc_now_iso(), encoding="utf-8")
            probe.unlink()
        except Exception as exc:
            return {"status": "error", "detail": f"local path not writable: {exc}"}
        return {"status": "ok", "detail": f"writing to {self.base_path}"}

    def supported_artifact_types(self) -> list[str]:
        return sorted(SUPPORTED_ARTIFACT_TYPES)

    def push_artifact(self, artifact: dict[str, Any], artifact_type: str) -> dict[str, Any]:
        if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
            return {
                "status": "error",
                "destination_ref": None,
                "error": f"unsupported artifact_type {artifact_type!r}; adapter supports {sorted(SUPPORTED_ARTIFACT_TYPES)}",
                "pushed_at": _utc_now_iso(),
            }
        if not isinstance(artifact, dict):
            return {
                "status": "error",
                "destination_ref": None,
                "error": "artifact must be a dict",
                "pushed_at": _utc_now_iso(),
            }

        timestamp = artifact.get("timestamp") or _utc_now_iso()
        safe_timestamp = timestamp.replace(":", "-")
        target_dir = self.base_path / artifact_type
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{safe_timestamp}.json"

        try:
            target_file.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
        except Exception as exc:
            return {
                "status": "error",
                "destination_ref": None,
                "error": f"write failed: {exc}",
                "pushed_at": _utc_now_iso(),
            }

        action_tag = _classify_action(artifact)
        return {
            "status": "ok",
            "destination_ref": str(target_file),
            "error": None,
            "pushed_at": _utc_now_iso(),
            "action_tag": action_tag,
            "adapter_name": ADAPTER_NAME,
            "adapter_version": ADAPTER_VERSION,
        }

    def batch_push(self, artifacts: list[tuple[dict[str, Any], str]]) -> list[dict[str, Any]]:
        return [self.push_artifact(a, t) for a, t in artifacts]

    def pull_feedback(self, since: str) -> list[dict[str, Any]]:
        # Local filesystem does not support round-trip feedback; this is the
        # source of record, not a destination users edit back.
        raise NotImplementedError(
            "local-filesystem adapter is the source of record, not a destination for user feedback"
        )
