"""Replay test for the gap-assessment end-to-end demo.

Runs demos/gap-assessment/run.py in place and asserts output shape
against the aigovops gap-assessment plugin contract. Skips when the
aigovops plugins path is not available; see run.py for the candidate
search order.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "demos" / "gap-assessment"


def _aigovops_available() -> bool:
    """Mirror the candidate list used by run.py to stay consistent."""
    candidates: list[Path] = []
    env_path = os.environ.get("AIGOVOPS_PLUGINS_PATH")
    if env_path:
        candidates.append(Path(env_path) / "gap-assessment" / "plugin.py")
    candidates.append(REPO_ROOT.parent / "aigovops" / "plugins" / "gap-assessment" / "plugin.py")
    candidates.append(
        Path.home() / "Documents" / "CODING" / "aigovops" / "plugins"
        / "gap-assessment" / "plugin.py"
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
    json_files = sorted(real_out.glob("iso42001-*.json"))
    md_files = sorted(real_out.glob("iso42001-*.md"))
    csv_files = sorted(real_out.glob("iso42001-*.csv"))
    events_file = real_out / "audit-events.jsonl"

    assert json_files, "No JSON output was produced."
    assert md_files, "No Markdown output was produced."
    assert csv_files, "No CSV output was produced."
    assert events_file.exists(), "No audit-events.jsonl was produced."

    assessment = json.loads(json_files[-1].read_text(encoding="utf-8"))
    assert assessment["target_framework"] == "iso42001"
    assert assessment["agent_signature"].startswith("gap-assessment/")
    assert isinstance(assessment["rows"], list) and assessment["rows"]

    valid_classifications = {"covered", "partially-covered", "not-covered", "not-applicable"}
    for row in assessment["rows"]:
        assert set(row).issuperset({"target_id", "citation", "classification", "justification", "next_step"})
        assert row["classification"] in valid_classifications
        assert row["citation"].startswith("ISO/IEC 42001:2023, Annex A, Control ")

    summary = assessment["summary"]
    assert summary["total_targets"] == len(assessment["rows"])
    assert 0.0 <= summary["coverage_score"] <= 1.0
    assert set(summary["classification_counts"]).issubset(valid_classifications)

    md_text = md_files[-1].read_text(encoding="utf-8")
    assert "Gap Assessment" in md_text
    assert "iso42001" in md_text
    assert "\u2014" not in md_text, "Markdown contains forbidden em-dash."

    csv_text = csv_files[-1].read_text(encoding="utf-8")
    assert csv_text.splitlines()[0].startswith("target_id,")

    event_lines = [
        json.loads(line)
        for line in events_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    kinds = {evt["event"] for evt in event_lines}
    assert "workflow-started" in kinds
    assert "workflow-completed" in kinds
    for evt in event_lines:
        assert "timestamp" in evt
        assert evt.get("plugin") == "gap-assessment"
