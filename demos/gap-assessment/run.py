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
from dataclasses import dataclass
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


def _build_envelope(envelope_id: str, inputs: dict) -> "TaskEnvelope":
    from aigovclaw.task_envelope import TaskEnvelope
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
    return envelope


def _create_start_event(envelope_id: str, args: dict) -> "AuditEvent":
    from aigovclaw.action_executor.audit_event import AuditEvent, EVENT_WORKFLOW_STARTED
    from aigovclaw.action_executor.safety import new_request_id
    workflow_start = AuditEvent(
        event=EVENT_WORKFLOW_STARTED,
        timestamp=_utc_now_iso(),
        audit_entry_id=new_request_id(),
        request_id=envelope_id,
        plugin="gap-assessment",
        action="re-run-plugin",
        target=args.get("target_framework", ""),
        payload={
            "envelope_source": "cli",
            "workflow": "gap-assessment",
            "scope_boundary": args.get("scope_boundary", ""),
        },
    )
    workflow_start.validate()
    return workflow_start


def _create_failure_event(envelope_id: str, args: dict, exc: Exception) -> "AuditEvent":
    from aigovclaw.action_executor.audit_event import AuditEvent, EVENT_WORKFLOW_FAILED
    from aigovclaw.action_executor.safety import new_request_id
    failure = AuditEvent(
        event=EVENT_WORKFLOW_FAILED,
        timestamp=_utc_now_iso(),
        audit_entry_id=new_request_id(),
        request_id=envelope_id,
        plugin="gap-assessment",
        action="re-run-plugin",
        target=args.get("target_framework", ""),
        payload={"error": f"{type(exc).__name__}: {exc}"},
    )
    return failure


@dataclass
class CompletionStats:
    """Statistics for the completed gap assessment."""
    row_count: int
    classification_counts: dict
    coverage_score: str | None
    agent_signature: str | None


def _create_completed_event(
    envelope_id: str, framework: str, out_paths: tuple[Path, Path, Path], stats: CompletionStats
) -> "AuditEvent":
    from aigovclaw.action_executor.audit_event import AuditEvent, EVENT_WORKFLOW_COMPLETED
    from aigovclaw.action_executor.safety import new_request_id
    out_json, out_md, out_csv = out_paths
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
            "row_count": stats.row_count,
            "classification_counts": stats.classification_counts,
            "coverage_score": stats.coverage_score,
            "agent_signature": stats.agent_signature,
        },
    )
    completed.validate()
    return completed


def _persist_outputs(assessment: dict, markdown: str, csv_text: str) -> tuple[Path, Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = assessment.get("timestamp", _utc_now_iso()).replace(":", "-")
    framework = assessment.get("target_framework", "unknown")
    out_json = OUTPUT_DIR / f"{framework}-{timestamp}.json"
    out_md = OUTPUT_DIR / f"{framework}-{timestamp}.md"
    out_csv = OUTPUT_DIR / f"{framework}-{timestamp}.csv"
    out_json.write_text(json.dumps(assessment, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(markdown, encoding="utf-8")
    out_csv.write_text(csv_text, encoding="utf-8")
    return out_json, out_md, out_csv


def _calculate_stats(assessment: dict) -> CompletionStats:
    classifications = [row.get("classification") for row in assessment.get("rows", [])]
    summary = assessment.get("summary") or {}
    counts = summary.get("classification_counts") or {
        c: classifications.count(c) for c in set(classifications)
    }
    return CompletionStats(
        row_count=len(classifications),
        classification_counts=counts,
        coverage_score=summary.get("coverage_score"),
        agent_signature=assessment.get("agent_signature"),
    )


def _log_workflow_failure(
    workflow_start: "AuditEvent", failure: "AuditEvent", exc: Exception
) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "audit-events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(workflow_start.to_dict()) + "\n")
        fh.write(json.dumps(failure.to_dict()) + "\n")
    print(f"FAILED: {exc}", file=sys.stderr)
    return 1


def _print_summary(
    framework: str, stats: CompletionStats, out_paths: tuple[Path, Path, Path]
) -> None:
    out_json, out_md, out_csv = out_paths
    print(f"framework:            {framework}")
    print(f"agent_signature:      {stats.agent_signature}")
    print(f"rows:                 {stats.row_count}")
    print(f"classification_counts: {stats.classification_counts}")
    print(f"coverage_score:       {stats.coverage_score}")
    print(f"json:                 {out_json.relative_to(REPO_ROOT)}")
    print(f"markdown:             {out_md.relative_to(REPO_ROOT)}")
    print(f"csv:                  {out_csv.relative_to(REPO_ROOT)}")
    print(f"audit events:         {(OUTPUT_DIR / 'audit-events.jsonl').relative_to(REPO_ROOT)}")


def _process_workflow(envelope: "TaskEnvelope") -> tuple[dict, str, str] | Exception:
    plugin_path = _locate_plugin()
    plugin = _import_plugin(plugin_path)

    try:
        assessment = plugin.generate_gap_assessment(envelope.args)
        markdown = plugin.render_markdown(assessment)
        csv_text = plugin.render_csv(assessment)
        return assessment, markdown, csv_text
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return exc


def _log_events(workflow_start: "AuditEvent", completed: "AuditEvent") -> None:
    with (OUTPUT_DIR / "audit-events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(workflow_start.to_dict()) + "\n")
        fh.write(json.dumps(completed.to_dict()) + "\n")


def _run_workflow() -> int:
    from aigovclaw.action_executor.safety import new_request_id

    input_path = DEMO_DIR / "input.json"
    if not input_path.exists():
        raise SystemExit(f"Missing input fixture: {input_path}")
    inputs = json.loads(input_path.read_text(encoding="utf-8"))

    envelope_id = new_request_id()
    envelope = _build_envelope(envelope_id, inputs)
    workflow_start = _create_start_event(envelope_id, envelope.args)

    result = _process_workflow(envelope)
    if isinstance(result, Exception):
        failure = _create_failure_event(envelope_id, envelope.args, result)
        return _log_workflow_failure(workflow_start, failure, result)

    assessment, markdown, csv_text = result

    out_paths = _persist_outputs(assessment, markdown, csv_text)
    stats = _calculate_stats(assessment)
    framework = assessment.get("target_framework", "unknown")

    completed = _create_completed_event(envelope_id, framework, out_paths, stats)

    _log_events(workflow_start, completed)

    _print_summary(framework, stats, out_paths)
    return 0


def main() -> int:
    """Run the gap-assessment end-to-end demo."""
    sys.path.insert(0, str(REPO_ROOT))
    return _run_workflow()


if __name__ == "__main__":
    raise SystemExit(main())
