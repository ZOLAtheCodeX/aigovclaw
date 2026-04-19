"""Safety primitives for the action executor.

Provides:
    AuditLogger           append-only audit log. Uses the aigovops audit-log-
                          generator plugin when available, falls back to a
                          local JSONL writer otherwise.
    RateLimiter           counts recent audit entries per (plugin, action).
    snapshot_target       copies a file to an action-snapshot directory.
    rollback              restores a snapshot back over the live target.
    allowed_roots         returns the set of absolute paths file_update may write to.

Rate limiting, snapshots, and audit writes share a single memory root so
tests can isolate them via the memory_root constructor argument on
ActionExecutor.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import shutil
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_LOCK = threading.RLock()

DEFAULT_MEMORY_ROOT = Path.home() / ".hermes" / "memory" / "aigovclaw"
AIGOVOPS_ROOT_CANDIDATES = (
    Path(__file__).resolve().parents[3] / "aigovops",
    Path.home() / "Documents" / "CODING" / "aigovops",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_request_id() -> str:
    """Generate a deterministic-ish ULID-like identifier.

    ULIDs are time-ordered 26-char base32 strings. We synthesize a compatible
    shape from the wall clock and a random suffix; callers depend only on
    uniqueness and sortability, not on strict ULID-spec conformance.
    """
    ts_ms = int(time.time() * 1000)
    # 48 bits of timestamp, 80 bits of randomness, base32 (Crockford subset).
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    ts_part = ""
    t = ts_ms
    for _ in range(10):
        ts_part = alphabet[t & 0x1F] + ts_part
        t >>= 5
    rand_bits = uuid.uuid4().int & ((1 << 80) - 1)
    rand_part = ""
    for _ in range(16):
        rand_part = alphabet[rand_bits & 0x1F] + rand_part
        rand_bits >>= 5
    return ts_part + rand_part


def allowed_roots() -> list[Path]:
    """Return the absolute paths file_update is allowed to mutate.

    Always includes ~/.hermes/memory/aigovclaw/. Includes the local aigovops
    and aigovclaw source trees when AIGOVCLAW_ALLOW_SOURCE_WRITES=1.
    """
    roots: list[Path] = [DEFAULT_MEMORY_ROOT]
    if os.environ.get("AIGOVCLAW_ALLOW_SOURCE_WRITES") == "1":
        home = Path.home()
        for name in ("aigovops", "aigovclaw"):
            candidate = home / "Documents" / "CODING" / name
            if candidate.exists():
                roots.append(candidate)
    return roots


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def snapshot_target(memory_root: Path, request_id: str, target: Path) -> Path | None:
    """Copy target into the per-request snapshot dir. No-op when target missing."""
    snapshot_dir = memory_root / "action-snapshots" / request_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        # Record absence so rollback can delete what the handler creates.
        (snapshot_dir / "TARGET_DID_NOT_EXIST").write_text(
            str(target), encoding="utf-8"
        )
        return snapshot_dir
    dest = snapshot_dir / "original"
    if target.is_file():
        shutil.copy2(target, dest)
    else:
        shutil.copytree(target, dest, dirs_exist_ok=True)
    return snapshot_dir


def rollback(snapshot_dir: Path, target: Path) -> bool:
    """Restore target from snapshot_dir. Returns True on success."""
    if snapshot_dir is None or not snapshot_dir.exists():
        return False
    missing_marker = snapshot_dir / "TARGET_DID_NOT_EXIST"
    original = snapshot_dir / "original"
    try:
        if missing_marker.exists():
            if target.exists():
                if target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            return True
        if not original.exists():
            return False
        if original.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
        else:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(original, target)
        return True
    except Exception:
        return False


class AuditLogger:
    """Append-only audit log with three event flavours: intent, completed, failed.

    Records land in memory_root/audit-log/YYYY-MM-DD.jsonl. Each line is a
    self-contained JSON object; no compaction, no rewriting.

    When the aigovops audit-log-generator plugin can be imported, every
    'action-completed' entry tied to a governance-grade action also gets
    passed through the plugin for Annex A enrichment; failures there are
    recorded as warnings and never block execution.
    """

    def __init__(self, memory_root: Path):
        self.memory_root = Path(memory_root)
        self.dir = self.memory_root / "audit-log"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._signing_key = os.environ.get("AIGOVCLAW_AUDIT_SIGNING_KEY", "")

    def _path_for_today(self) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.dir / f"{day}.jsonl"

    def write(self, event: dict[str, Any]) -> str:
        """Append an event, return its audit_entry_id."""
        entry_id = new_request_id()
        payload = dict(event)
        payload["audit_entry_id"] = entry_id
        payload.setdefault("timestamp", utc_now_iso())
        if self._signing_key:
            digest = hmac.new(
                self._signing_key.encode("utf-8"),
                json.dumps(payload, sort_keys=True).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            payload["hmac_sha256"] = digest
        with _LOCK:
            with self._path_for_today().open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload) + "\n")
        return entry_id

    def recent_events(self, since: datetime) -> list[dict[str, Any]]:
        """Return events logged on or after `since` across recent day-files."""
        out: list[dict[str, Any]] = []
        if not self.dir.exists():
            return out
        cutoff_iso = since.replace(microsecond=0).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        # Walk the last two day-files to survive UTC-day rollover.
        day_files = sorted(self.dir.glob("*.jsonl"))[-2:]
        for f in day_files:
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = rec.get("timestamp")
                    if isinstance(ts, str) and ts >= cutoff_iso:
                        out.append(rec)
            except OSError:
                continue
        return out


class RateLimiter:
    """Hourly rate limiter backed by the audit log."""

    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger

    def count_recent(self, plugin: str, action_id: str) -> int:
        """Count rate-limit-consuming events in the last hour for (plugin, action).

        One attempt produces exactly one 'action-intent' event regardless of
        outcome (completed, failed, queued for approval). Counting intents
        avoids double-counting the completed/failed follow-up.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        n = 0
        for rec in self.audit.recent_events(since):
            if rec.get("plugin") != plugin or rec.get("action") != action_id:
                continue
            if rec.get("event") == "action-intent":
                n += 1
        return n

    def over_limit(self, plugin: str, action_id: str, limit: int | None) -> bool:
        if limit is None:
            return False
        return self.count_recent(plugin, action_id) >= limit


def try_import_audit_plugin() -> Any | None:
    """Attempt to import the aigovops audit-log-generator plugin.

    Returns the module when the sibling checkout is present, None otherwise.
    Downstream callers must treat absence as a benign degradation.
    """
    for candidate in AIGOVOPS_ROOT_CANDIDATES:
        p = candidate / "plugins" / "audit-log-generator" / "plugin.py"
        if not p.exists():
            continue
        spec = importlib.util.spec_from_file_location(
            "_aigovclaw_audit_log_plugin", p
        )
        if spec is None or spec.loader is None:
            continue
        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None
    return None
