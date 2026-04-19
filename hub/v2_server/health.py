"""Composite system health for the Hub v2 command center.

Computed on demand (cheap filesystem reads) each time GET /api/health fires.
The UI polls this endpoint every 10 seconds. Cold compute cost is
dominated by the plugin-count glob and the warnings walk, both bounded.

Fields:
  plugin_count            Number of plugin directories in the sibling aigovops repo.
  last_run_at             ISO timestamp of the most recent terminal task (any status).
  warning_count           Total `warnings` entries across the most recent artifact
                          per plugin key under the evidence store.
  bundle_signed           True iff the latest bundle has signatures.json with an
                          algorithm other than "none".
  bundle_signed_at        ISO timestamp of the signed bundle directory.
  evidence_artifact_count Count of JSON files under the evidence store.
  evidence_path           Absolute path of the evidence store.
  jurisdictions           Per-jurisdiction readiness indicators when data is present.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import task_runner as _tr


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iso_from_mtime(path: Path) -> str | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def count_plugins(aigovops_root: Path | None) -> int:
    if aigovops_root is None or not aigovops_root.exists():
        return 0
    plugins_dir = aigovops_root / "plugins"
    if not plugins_dir.is_dir():
        return 0
    count = 0
    for child in plugins_dir.iterdir():
        if not child.is_dir():
            continue
        if (child / "plugin.py").exists():
            count += 1
    return count


def latest_task(runner: _tr.TaskRunner) -> dict[str, Any] | None:
    tasks = runner.list_tasks(limit=200)
    terminal = [t for t in tasks if t.get("status") in _tr.TERMINAL_STATES]
    if not terminal:
        return None
    terminal.sort(
        key=lambda r: r.get("ended_at") or r.get("started_at") or r.get("queued_at") or "",
        reverse=True,
    )
    return terminal[0]


def count_warnings(evidence_path: Path) -> int:
    if not evidence_path.exists() or not evidence_path.is_dir():
        return 0
    total = 0
    for sub in evidence_path.iterdir():
        if not sub.is_dir():
            continue
        # Most recent JSON artifact only.
        latest: Path | None = None
        latest_mtime = -1.0
        for f in sub.rglob("*.json"):
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if m > latest_mtime:
                latest_mtime = m
                latest = f
        if latest is None:
            continue
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            continue
        warnings = data.get("warnings") if isinstance(data, dict) else None
        if isinstance(warnings, list):
            total += len(warnings)
    return total


def bundle_signed_status(bundles_root: Path) -> tuple[bool, str | None]:
    """Return (signed, signed_at_iso) for the latest bundle under bundles_root."""
    if not bundles_root.exists() or not bundles_root.is_dir():
        return False, None
    bundle_dirs = [p for p in bundles_root.iterdir() if p.is_dir()]
    if not bundle_dirs:
        return False, None
    bundle_dirs.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    latest = bundle_dirs[0]
    sig_path = latest / "signatures.json"
    if not sig_path.exists():
        return False, _iso_from_mtime(latest)
    try:
        data = json.loads(sig_path.read_text(encoding="utf-8"))
    except Exception:
        return False, _iso_from_mtime(latest)
    algorithm = None
    if isinstance(data, dict):
        algorithm = data.get("algorithm") or (
            (data.get("signatures") or [{}])[0].get("algorithm")
            if isinstance(data.get("signatures"), list)
            else None
        )
    signed = bool(algorithm) and algorithm != "none"
    return signed, _iso_from_mtime(latest)


def count_evidence_artifacts(evidence_path: Path) -> int:
    if not evidence_path.exists() or not evidence_path.is_dir():
        return 0
    return sum(1 for _ in evidence_path.rglob("*.json"))


def jurisdictional_readiness(evidence_path: Path) -> dict[str, dict[str, Any]]:
    """Return a map jurisdiction_id -> {status, source}.

    Status values: ready | ready-with-conditions | partially-ready | not-ready | unknown.
    The heuristic reads certification-readiness artifacts when present.
    """
    out: dict[str, dict[str, Any]] = {}
    cr_dir = evidence_path / "certification-readiness"
    if cr_dir.is_dir():
        latest: Path | None = None
        latest_mtime = -1.0
        for f in cr_dir.glob("*.json"):
            m = f.stat().st_mtime
            if m > latest_mtime:
                latest_mtime = m
                latest = f
        if latest is not None:
            try:
                data = json.loads(latest.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            verdict = None
            if isinstance(data, dict):
                verdict = data.get("readiness_verdict") or data.get("verdict") or (
                    (data.get("summary") or {}).get("verdict")
                    if isinstance(data.get("summary"), dict)
                    else None
                )
            if verdict:
                out["iso-42001"] = {"status": verdict, "source": str(latest.name)}
    return out


def compute_health(
    *,
    runner: _tr.TaskRunner,
    evidence_path: Path,
    aigovops_root: Path | None,
    bundles_root: Path | None = None,
) -> dict[str, Any]:
    bundles = bundles_root if bundles_root is not None else (evidence_path / "bundles")
    signed, signed_at = bundle_signed_status(bundles)
    last = latest_task(runner)
    last_run_at = None
    if last is not None:
        last_run_at = last.get("ended_at") or last.get("started_at")
    return {
        "plugin_count": count_plugins(aigovops_root),
        "last_run_at": last_run_at,
        "warning_count": count_warnings(evidence_path),
        "bundle_signed": signed,
        "bundle_signed_at": signed_at,
        "evidence_artifact_count": count_evidence_artifacts(evidence_path),
        "evidence_path": str(evidence_path),
        "jurisdictions": jurisdictional_readiness(evidence_path),
        "computed_at": _utc_now(),
    }
