"""Approval queue for the Hub v2 command center.

Tasks flagged `requires_approval=True` land in the AWAITING_APPROVAL state.
The approver can approve (which calls task_runner.approve and starts the
subprocess) or reject (which cancels the task with a reason).

Approval records persist to disk under:
  ~/.hermes/memory/aigovclaw/hub-v2-approvals/<task_id>.json

Each record carries the original command, args, approver decision, and
decision timestamp. The record is written when the task enters the queue
and updated when a decision is made.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import task_runner


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_dir() -> Path:
    return Path.home() / ".hermes" / "memory" / "aigovclaw" / "hub-v2-approvals"


class ApprovalQueue:
    def __init__(
        self,
        runner: task_runner.TaskRunner,
        *,
        approvals_dir: Path | None = None,
    ) -> None:
        self.runner = runner
        self.dir = Path(approvals_dir) if approvals_dir else _default_dir()
        self.dir.mkdir(parents=True, exist_ok=True)

    def register(self, rec: dict[str, Any]) -> None:
        """Record an awaiting-approval task."""
        if rec.get("status") != task_runner.STATUS_AWAITING_APPROVAL:
            return
        path = self.dir / f"{rec['task_id']}.json"
        payload = {
            "task_id": rec["task_id"],
            "command": rec["command"],
            "args": rec["args"],
            "argv": rec["argv"],
            "queued_at": rec["queued_at"],
            "decision": None,
            "decided_at": None,
            "decided_by": None,
            "reason": None,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def pending(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for child in sorted(self.dir.iterdir()) if self.dir.exists() else []:
            if not child.suffix == ".json":
                continue
            try:
                data = json.loads(child.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict) and data.get("decision") is None:
                out.append(data)
        return out

    def approve(self, task_id: str, *, approver: str = "operator") -> dict[str, Any]:
        rec = self.runner.approve(task_id)
        self._record_decision(task_id, "approve", approver=approver)
        return rec

    def reject(
        self,
        task_id: str,
        *,
        approver: str = "operator",
        reason: str | None = None,
    ) -> dict[str, Any]:
        rec = self.runner.reject(task_id, reason=reason)
        self._record_decision(task_id, "reject", approver=approver, reason=reason)
        return rec

    def _record_decision(
        self,
        task_id: str,
        decision: str,
        *,
        approver: str,
        reason: str | None = None,
    ) -> None:
        path = self.dir / f"{task_id}.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {"task_id": task_id}
        data["decision"] = decision
        data["decided_at"] = _utc_now()
        data["decided_by"] = approver
        if reason:
            data["reason"] = reason
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
