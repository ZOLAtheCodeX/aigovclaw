"""notification handler.

Supports channels:
    local-file      append JSONL record to ~/.hermes/memory/aigovclaw/notifications/<date>.log
    stdout          print the record to process stdout

Future-sprint placeholders raise NotImplementedError so callers get a clear
signal instead of a silent drop.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..action_registry import ActionRequest
from ..safety import DEFAULT_MEMORY_ROOT, utc_now_iso


FUTURE_CHANNELS = {"slack", "telegram", "discord", "email", "desktop"}


def handle(request: ActionRequest, dry_run: bool) -> dict[str, Any]:
    args = request.args or {}
    channel = args.get("channel")
    message = args.get("message")
    severity = args.get("severity", "info")

    if not channel:
        raise ValueError("notification requires args['channel']")
    if message is None:
        raise ValueError("notification requires args['message']")

    if channel in FUTURE_CHANNELS:
        raise NotImplementedError(
            f"channel {channel!r} lands in a follow-up sprint; supported now: local-file, stdout."
        )

    record = {
        "timestamp": utc_now_iso(),
        "plugin": request.plugin,
        "request_id": request.request_id,
        "channel": channel,
        "severity": severity,
        "message": message,
    }

    if dry_run:
        return {
            "would_deliver_to": channel,
            "severity": severity,
            "message_preview": str(message)[:200],
        }

    if channel == "local-file":
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_dir = DEFAULT_MEMORY_ROOT / "notifications"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{day}.log"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        return {"channel": channel, "delivered": True, "log_path": str(log_path)}

    if channel == "stdout":
        sys.stdout.write(json.dumps(record) + "\n")
        sys.stdout.flush()
        return {"channel": channel, "delivered": True}

    raise ValueError(f"unknown notification channel {channel!r}")
