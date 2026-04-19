"""End-to-end demo runner for the gap-assessment workflow.

Flow mirrors demos/audit-log/run.py:
    1. Load input fixture (demos/gap-assessment/input.json).
    2. Build a TaskEnvelope.
    3. Resolve the aigovops gap-assessment plugin.
    4. Invoke generate_gap_assessment to produce the structured dict.
    5. Render Markdown and CSV via the plugin's render helpers.
    6. Persist all three renderings to demos/gap-assessment/output/.
    7. Append workflow-started and workflow-completed AuditEvents.

This demo uses target_framework=iso42001 so the plugin falls back to
DEFAULT_ISO_TARGETS (Annex A controls) without requiring a target list
in the fixture. The fixture describes two inventoried AI systems, a
mix of current-state evidence, three manual classifications, and one
exclusion justification. The result exercises covered, partially-covered,
not-covered, and not-applicable classifications in one run.

Invocation:
    cd /path/to/aigovclaw
    python demos/gap-assessment/run.py
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

PLUGIN_RELATIVE = Path("gap-assessment") / "plugin.py"


def _aigovops_plugin_candidates() -> list[Path]:
    """Ordered list of paths where the plugin may live."""
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
        "Could not locate gap-assessment plugin. Searched: "
        f"{[str(c) for c in candidates]}"
    )


def _import_plugin(plugin_path: Path):
    spec = importlib.util.spec_from_file_location("_demo_gap_assessment_plugin", plugin_path)
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
    inputs = json.loads(input_path.read_text(encoding="utf-8"))

    envelope_id = new_request_id()
    envelope = TaskEnvelope(
        envelope_id=envelope_id,
        command="gap-assessment",
        args=inputs,
        source_type="cli",
        source_id=f"demos/gap-assessment/run.py@{os.getpid()}",
        actor="demo-runner",
        rationale="Canonical end-to-end demo for the gap-assessment workflow.",
        requested_at=_utc_now_iso(),
        dry_run=False,
        metadata={"demo_fixture": "demos/gap-assessment/input.json"},
    )
    envelope.validate()

    workflow_start = AuditEvent(
        event=EVENT_WORKFLOW_STARTED,
        timestamp=_utc_now_iso(),
        audit_entry_id=new_request_id(),
        request_id=envelope_id,
        plugin="gap-assessment",
        action="re-run-plugin",
        target=envelope.args.get("target_framework", ""),
        payload={
            "envelope_source": envelope.source_type,
            "workflow": "gap-assessment",
            "scope_boundary": envelope.args.get("scope_boundary", ""),
        },
    )
    workflow_start.validate()

    plugin_path = _locate_plugin()
    plugin = _import_plugin(plugin_path)

    try:
        assessment = plugin.generate_gap_assessment(envelope.args)
        markdown = plugin.render_markdown(assessment)
        csv_text = plugin.render_csv(assessment)
    except Exception as exc:
        failure = AuditEvent(
            event=EVENT_WORKFLOW_FAILED,
            timestamp=_utc_now_iso(),
            audit_entry_id=new_request_id(),
            request_id=envelope_id,
            plugin="gap-assessment",
            action="re-run-plugin",
            target=envelope.args.get("target_framework", ""),
            payload={"error": f"{type(exc).__name__}: {exc}"},
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with (OUTPUT_DIR / "audit-events.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(workflow_start.to_dict()) + "\n")
            fh.write(json.dumps(failure.to_dict()) + "\n")
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = assessment.get("timestamp", _utc_now_iso()).replace(":", "-")
    framework = assessment.get("target_framework", "unknown")
    out_json = OUTPUT_DIR / f"{framework}-{timestamp}.json"
    out_md = OUTPUT_DIR / f"{framework}-{timestamp}.md"
    out_csv = OUTPUT_DIR / f"{framework}-{timestamp}.csv"
    out_json.write_text(json.dumps(assessment, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(markdown, encoding="utf-8")
    out_csv.write_text(csv_text, encoding="utf-8")

    classifications = [row.get("classification") for row in assessment.get("rows", [])]
    summary = assessment.get("summary") or {}
    counts = summary.get("classification_counts") or {
        c: classifications.count(c) for c in set(classifications)
    }
    coverage_score = summary.get("coverage_score")

    completed = AuditEvent(
        event=EVENT_WORKFLOW_COMPLETED,
        timestamp=_utc_now_iso(),
        audit_entry_id=new_request_id(),
        request_id=envelope_id,
        plugin="gap-assessment",
        action="re-run-plugin",
        target=framework,
        payload={
            "output_json": str(out_json.relative_to(REPO_ROOT)),
            "output_markdown": str(out_md.relative_to(REPO_ROOT)),
            "output_csv": str(out_csv.relative_to(REPO_ROOT)),
            "row_count": len(classifications),
            "classification_counts": counts,
            "coverage_score": coverage_score,
            "agent_signature": assessment.get("agent_signature"),
        },
    )
    completed.validate()

    with (OUTPUT_DIR / "audit-events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(workflow_start.to_dict()) + "\n")
        fh.write(json.dumps(completed.to_dict()) + "\n")

    print(f"framework:            {framework}")
    print(f"agent_signature:      {assessment.get('agent_signature')}")
    print(f"rows:                 {len(classifications)}")
    print(f"classification_counts: {counts}")
    print(f"coverage_score:       {coverage_score}")
    print(f"json:                 {out_json.relative_to(REPO_ROOT)}")
    print(f"markdown:             {out_md.relative_to(REPO_ROOT)}")
    print(f"csv:                  {out_csv.relative_to(REPO_ROOT)}")
    print(f"audit events:         {(OUTPUT_DIR / 'audit-events.jsonl').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
