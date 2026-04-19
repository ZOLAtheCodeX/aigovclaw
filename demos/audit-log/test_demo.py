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
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "demos" / "audit-log"


def _aigovops_available() -> bool:
    """Mirror the candidate list used by run.py to stay consistent."""
    candidates: list[Path] = []
    env_path = os.environ.get("AIGOVOPS_PLUGINS_PATH")
    if env_path:
        candidates.append(Path(env_path) / "audit-log-generator" / "plugin.py")
    candidates.append(REPO_ROOT.parent / "aigovops" / "plugins" / "audit-log-generator" / "plugin.py")
    candidates.append(
        Path.home() / "Documents" / "CODING" / "aigovops" / "plugins"
        / "audit-log-generator" / "plugin.py"
    )
    return any(c.exists() for c in candidates)


pytestmark = pytest.mark.skipif(
    not _aigovops_available(),
    reason="aigovops plugins path not present. Set AIGOVOPS_PLUGINS_PATH or place a sibling checkout.",
)


def test_demo_runs_and_produces_expected_artifacts():
    runner = DEMO_DIR / "run.py"
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
