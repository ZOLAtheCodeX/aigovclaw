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

PLUGIN_RELATIVE = Path("audit-log-generator") / "plugin.py"

sys.path.insert(0, str(REPO_ROOT))
from aigovclaw.task_envelope import TaskEnvelope
from aigovclaw.action_executor.audit_event import (
    AuditEvent,
    EVENT_WORKFLOW_COMPLETED,
    EVENT_WORKFLOW_FAILED,
    EVENT_WORKFLOW_STARTED,
)
from aigovclaw.action_executor.safety import new_request_id


def _aigovops_plugin_candidates() -> list[Path]:
    """Return the ordered list of paths where the plugin may live.

    Precedence:
      1. AIGOVOPS_PLUGINS_PATH env var (matches the convention used by
         tools/tests/test_registry.py and the CI workflow).
      2. Sibling checkout relative to the repo root.
      3. User's canonical CODING dir layout.
    """
    candidates: list[Path] = []
    env_path = os.environ.get("AIGOVOPS_PLUGINS_PATH")
    if env_path:
        candidates.append(Path(env_path) / PLUGIN_RELATIVE)
    candidates.append(REPO_ROOT.parent / "aigovops" / "plugins" / PLUGIN_RELATIVE)
    candidates.append(
        Path.home() / "Documents" / "CODING" / "aigovops" / "plugins" / PLUGIN_RELATIVE
    )
    return candidates


def _locate_plugin() -> Path:
    candidates = _aigovops_plugin_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(
        "Could not locate audit-log-generator plugin. Searched: "
        f"{[str(c) for c in candidates]}"
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


def _load_input_fixture() -> dict:
    input_path = DEMO_DIR / "input.json"
    if not input_path.exists():
        raise SystemExit(f"Missing input fixture: {input_path}")
    return json.loads(input_path.read_text(encoding="utf-8"))


def _build_task_envelope(system_description: dict, envelope_id: str) -> TaskEnvelope:
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
    return envelope


def _build_workflow_start_event(envelope: TaskEnvelope) -> AuditEvent:
    workflow_start = AuditEvent(
        event=EVENT_WORKFLOW_STARTED,
        timestamp=_utc_now_iso(),
        audit_entry_id=new_request_id(),
        request_id=envelope.envelope_id,
        plugin="audit-log-generator",
        action="re-run-plugin",
        target=envelope.args.get("system_name", ""),
        payload={
            "envelope_source": envelope.source_type,
            "workflow": "audit-log",
        },
    )
    workflow_start.validate()
    return workflow_start


def _handle_failure(exc: Exception, envelope_id: str, system_name: str, workflow_start: AuditEvent) -> int:
    failure = AuditEvent(
        event=EVENT_WORKFLOW_FAILED,
        timestamp=_utc_now_iso(),
        audit_entry_id=new_request_id(),
        request_id=envelope_id,
        plugin="audit-log-generator",
        action="re-run-plugin",
        target=system_name,
        payload={"error": f"{type(exc).__name__}: {exc}"},
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "audit-events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(workflow_start.to_dict()) + "\n")
        fh.write(json.dumps(failure.to_dict()) + "\n")
    print(f"FAILED: {exc}", file=sys.stderr)
    return 1


def _write_outputs_and_complete(entry: dict, markdown: str, envelope_id: str, workflow_start: AuditEvent) -> int:
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


def main() -> int:
    system_description = _load_input_fixture()
    envelope_id = new_request_id()

    envelope = _build_task_envelope(system_description, envelope_id)
    workflow_start = _build_workflow_start_event(envelope)

    plugin_path = _locate_plugin()
    plugin = _import_plugin(plugin_path)

    try:
        entry = plugin.generate_audit_log(envelope.args)
        markdown = plugin.render_markdown(entry)
    except Exception as exc:
        system_name = envelope.args.get("system_name", "")
        return _handle_failure(exc, envelope_id, system_name, workflow_start)

    return _write_outputs_and_complete(entry, markdown, envelope_id, workflow_start)


if __name__ == "__main__":
    raise SystemExit(main())
