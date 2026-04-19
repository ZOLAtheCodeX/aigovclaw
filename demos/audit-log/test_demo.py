"""Replay test for the audit-log end-to-end demo.

Runs the demo as a subprocess in a fresh scratch directory, verifies the
process exits cleanly, and asserts the output artifacts match the shape
the plugin contract promises. If the plugin changes contract, or the
TaskEnvelope schema drifts, or the AuditEvent schema drifts, this test
fails loudly.

The test is slow relative to unit tests (spawns a subprocess, imports the
sibling aigovops plugin). That is intentional: it is the only test that
covers the whole path end-to-end.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "demos" / "audit-log"
AIGOVOPS_CANDIDATES = (
    REPO_ROOT.parent / "aigovops",
    Path.home() / "Documents" / "CODING" / "aigovops",
)


def _aigovops_available() -> bool:
    for root in AIGOVOPS_CANDIDATES:
        if (root / "plugins" / "audit-log-generator" / "plugin.py").exists():
            return True
    return False


pytestmark = pytest.mark.skipif(
    not _aigovops_available(),
    reason="Sibling aigovops repo with audit-log-generator plugin not present.",
)


def test_demo_runs_and_produces_expected_artifacts(tmp_path):
    scratch_demo = tmp_path / "audit-log"
    shutil.copytree(DEMO_DIR, scratch_demo)
    # Wipe any pre-existing output inside the scratch copy.
    out_dir = scratch_demo / "output"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    runner = scratch_demo / "run.py"
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}" + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"demo exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    real_out = DEMO_DIR / "output"
    json_files = sorted(real_out.glob("ClaimsTriageAI-v1-*.json"))
    md_files = sorted(real_out.glob("ClaimsTriageAI-v1-*.md"))
    events_file = real_out / "audit-events.jsonl"

    assert json_files, "No JSON output was produced."
    assert md_files, "No Markdown output was produced."
    assert events_file.exists(), "No audit-events.jsonl was produced."

    entry = json.loads(json_files[-1].read_text(encoding="utf-8"))
    assert entry["system_name"] == "ClaimsTriageAI-v1"
    assert entry["agent_signature"].startswith("audit-log-generator/")
    assert isinstance(entry["clause_mappings"], list) and entry["clause_mappings"]
    assert isinstance(entry["annex_a_mappings"], list) and entry["annex_a_mappings"]
    for mapping in entry["annex_a_mappings"]:
        assert set(mapping) == {"control_id", "citation", "rationale"}
        assert mapping["citation"].startswith("ISO/IEC 42001:2023, Annex A, Control ")

    md_text = md_files[-1].read_text(encoding="utf-8")
    assert "ClaimsTriageAI-v1" in md_text
    assert "Annex A" in md_text
    assert "\u2014" not in md_text, "Markdown output contains forbidden em-dash."

    event_lines = [
        json.loads(line)
        for line in events_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert event_lines, "audit-events.jsonl was empty."
    kinds = {evt["event"] for evt in event_lines}
    assert "workflow-started" in kinds
    assert "workflow-completed" in kinds
    for evt in event_lines:
        assert "timestamp" in evt
        assert evt.get("plugin") == "audit-log-generator"
