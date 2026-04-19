"""trigger-downstream handler.

Writes a cascade-queue entry that the PDCA orchestrator (built by a parallel
subagent) will consume. This handler does NOT execute the downstream
action itself; it only enqueues.

Cascade queue layout:
    ~/.hermes/memory/aigovclaw/cascade-queue/<request_id>.json
"""

from __future__ import annotations

import json
from typing import Any

from ..action_registry import ActionRequest
from ..safety import DEFAULT_MEMORY_ROOT, utc_now_iso


def handle(request: ActionRequest, dry_run: bool) -> dict[str, Any]:
    args = request.args or {}
    cascade_node_id = args.get("cascade_node_id")
    if not cascade_node_id:
        raise ValueError("trigger-downstream requires args['cascade_node_id']")

    queue_dir = DEFAULT_MEMORY_ROOT / "cascade-queue"

    if dry_run:
        return {
            "cascade_node_id": cascade_node_id,
            "would_enqueue_under": str(queue_dir),
        }

    queue_dir.mkdir(parents=True, exist_ok=True)
    path = queue_dir / f"{request.request_id}.json"
    entry = {
        "request_id": request.request_id,
        "cascade_node_id": cascade_node_id,
        "source_plugin": request.plugin,
        "source_rationale": request.rationale,
        "enqueued_at": utc_now_iso(),
        "downstream_args": args.get("downstream_args") or {},
    }
    path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return {"cascade_node_id": cascade_node_id, "queue_path": str(path)}
