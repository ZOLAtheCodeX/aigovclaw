"""End-to-end demo runner for the audit-log workflow.

Flow:
    1. Load input fixture (demos/audit-log/input.json).
    2. Build a TaskEnvelope at the ingress boundary.
    3. Resolve the aigovops audit-log-generator plugin (sibling repo).
    4. Invoke the plugin to produce the structured audit log dict.
    5. Render it to Markdown via the plugin's render_markdown function.
    6. Persist both renderings to demos/audit-log/output/.
    7. Write an audit event describing the workflow run.
    8. Print a summary and exit non-zero on any validation or write failure.

This is a local demo, not a production runner. It does not route through
the action-executor approval queue (the workflow is non-destructive and
the persistence target is inside the demo directory). It does exercise
TaskEnvelope, the aigovops plugin contract, and the AuditEvent schema.

Invocation:
    cd /path/to/aigovclaw
    python demos/audit-log/run.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parent.parent
OUTPUT_DIR = DEMO_DIR / "output"

AIGOVOPS_CANDIDATES = (
    REPO_ROOT.parent / "aigovops",
    Path.home() / "Documents" / "CODING" / "aigovops",
)

PLUGIN_RELATIVE = Path("plugins") / "audit-log-generator" / "plugin.py"


def _locate_plugin() -> Path:
    for root in AIGOVOPS_CANDIDATES:
        candidate = root / PLUGIN_RELATIVE
        if candidate.exists():
            return candidate
    raise SystemExit(
        f"Could not locate audit-log-generator plugin. Searched: "
        f"{[str(r / PLUGIN_RELATIVE) for r in AIGOVOPS_CANDIDATES]}"
    )


def _import_plugin(plugin_path: Path):
    spec = importlib.util.spec_from_file_location("_demo_audit_log_plugin", plugin_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from aigovclaw.task_envelope import TaskEnvelope
    from aigovclaw.action_executor.audit_event import (
        AuditEvent,
        EVENT_WORKFLOW_COMPLETED,
        EVENT_WORKFLOW_FAILED,
        EVENT_WORKFLOW_STARTED,
    )
    from aigovclaw.action_executor.safety import new_request_id

    input_path = DEMO_DIR / "input.json"
    if not input_path.exists():
        raise SystemExit(f"Missing input fixture: {input_path}")
    system_description = json.loads(input_path.read_text(encoding="utf-8"))

    envelope_id = new_request_id()
    envelope = TaskEnvelope(
        envelope_id=envelope_id,
        command="audit-log",
        args=system_description,
        source_type="cli",
        source_id=f"demos/audit-log/run.py@{os.getpid()}",
        actor="demo-runner",
        rationale="Canonical end-to-end demo for the audit-log workflow.",
        requested_at=_utc_now_iso(),
        dry_run=False,
        metadata={"demo_fixture": "demos/audit-log/input.json"},
    )
    envelope.validate()

    workflow_start = AuditEvent(
        event=EVENT_WORKFLOW_STARTED,
        timestamp=_utc_now_iso(),
        audit_entry_id=new_request_id(),
        request_id=envelope_id,
        plugin="audit-log-generator",
        action="re-run-plugin",
        target=envelope.args.get("system_name", ""),
        payload={
            "envelope_source": envelope.source_type,
            "workflow": "audit-log",
        },
    )
    workflow_start.validate()

    plugin_path = _locate_plugin()
    plugin = _import_plugin(plugin_path)

    try:
        entry = plugin.generate_audit_log(envelope.args)
        markdown = plugin.render_markdown(entry)
    except Exception as exc:
        failure = AuditEvent(
            event=EVENT_WORKFLOW_FAILED,
            timestamp=_utc_now_iso(),
            audit_entry_id=new_request_id(),
            request_id=envelope_id,
            plugin="audit-log-generator",
            action="re-run-plugin",
            target=envelope.args.get("system_name", ""),
            payload={"error": f"{type(exc).__name__}: {exc}"},
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "audit-events.jsonl").open("a", encoding="utf-8").write(
            json.dumps(workflow_start.to_dict()) + "\n"
            + json.dumps(failure.to_dict()) + "\n"
        )
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    system_name = entry.get("system_name", "unknown-system")
    timestamp = entry.get("timestamp", _utc_now_iso()).replace(":", "-")
    out_json = OUTPUT_DIR / f"{system_name}-{timestamp}.json"
    out_md = OUTPUT_DIR / f"{system_name}-{timestamp}.md"
    out_json.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(markdown, encoding="utf-8")

    completed = AuditEvent(
        event=EVENT_WORKFLOW_COMPLETED,
        timestamp=_utc_now_iso(),
        audit_entry_id=new_request_id(),
        request_id=envelope_id,
        plugin="audit-log-generator",
        action="re-run-plugin",
        target=system_name,
        payload={
            "output_json": str(out_json.relative_to(REPO_ROOT)),
            "output_markdown": str(out_md.relative_to(REPO_ROOT)),
            "annex_a_controls": [m["control_id"] for m in entry.get("annex_a_mappings", [])],
            "agent_signature": entry.get("agent_signature"),
        },
    )
    completed.validate()

    with (OUTPUT_DIR / "audit-events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(workflow_start.to_dict()) + "\n")
        fh.write(json.dumps(completed.to_dict()) + "\n")

    print(f"system_name:     {system_name}")
    print(f"agent_signature: {entry.get('agent_signature')}")
    print(f"annex_a:         {[m['control_id'] for m in entry.get('annex_a_mappings', [])]}")
    print(f"json:            {out_json.relative_to(REPO_ROOT)}")
    print(f"markdown:        {out_md.relative_to(REPO_ROOT)}")
    print(f"audit events:    {(OUTPUT_DIR / 'audit-events.jsonl').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
