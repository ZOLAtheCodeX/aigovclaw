"""Tests for the AIGovClaw Hub generator.

Standalone runnable: python3 hub/tests/test_generator.py
"""

from __future__ import annotations

import html.parser
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


# Allow running the file directly from inside the hub/tests/ directory.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hub.generator import generate, resolve_evidence_path  # noqa: E402


class _StrictParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def error(self, message: str) -> None:  # pragma: no cover
        self.errors.append(message)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _seed(base: Path) -> None:
    _write(
        base / "risk-register" / "2026-04-18.json",
        {
            "generated_at": "2026-04-18T12:00:00Z",
            "AGENT_SIGNATURE": "aigovops.risk-register@0.3.1",
            "risks": [
                {"id": "R-001", "tier": "high", "status": "open"},
                {"id": "R-002", "tier": "medium", "status": "mitigated"},
                {"id": "R-003", "tier": "low", "status": "open"},
                {"id": "R-004", "tier": "high", "status": "mitigated"},
            ],
        },
    )
    _write(
        base / "soa" / "soa-2026-04-18.json",
        {
            "generated_at": "2026-04-18T12:01:00Z",
            "AGENT_SIGNATURE": "aigovops.soa-maintenance@0.2.0",
            "controls": [
                {"id": "A.6.2.4", "status": "included-implemented"},
                {"id": "A.6.2.5", "status": "included-planned"},
                {"id": "A.7.1.1", "status": "included-partial"},
                {"id": "A.8.1.1", "status": "excluded-not-applicable"},
                {"id": "A.8.2.1", "status": "excluded-risk-accepted"},
                {"id": "A.9.1.1", "status": "included-implemented"},
            ],
        },
    )
    for i, (sid, state) in enumerate(
        [("sys-a", "complete"), ("sys-b", "gaps"), ("sys-c", "missing")]
    ):
        _write(
            base / "aisia" / f"{sid}.json",
            {
                "system_id": sid,
                "state": state,
                "generated_at": f"2026-04-1{i}T12:00:00Z",
                "AGENT_SIGNATURE": "aigovops.aisia@0.1.0",
            },
        )
    _write(
        base / "nonconformity" / "nc-001.json",
        {"id": "NC-001", "state": "open", "created_at": "2026-04-01T00:00:00Z",
         "AGENT_SIGNATURE": "aigovops.nc@0.1.0"},
    )
    _write(
        base / "nonconformity" / "nc-002.json",
        {"id": "NC-002", "state": "in-progress", "created_at": "2026-04-10T00:00:00Z",
         "AGENT_SIGNATURE": "aigovops.nc@0.1.0"},
    )
    _write(
        base / "nonconformity" / "nc-003.json",
        {"id": "NC-003", "state": "closed", "created_at": "2026-03-01T00:00:00Z",
         "AGENT_SIGNATURE": "aigovops.nc@0.1.0"},
    )
    _write(
        base / "metrics" / "2026-04-18.json",
        {
            "generated_at": "2026-04-18T12:02:00Z",
            "AGENT_SIGNATURE": "aigovops.metrics-collector@0.4.0",
            "kpis": [
                {"name": "drift-rate", "breach": True},
                {"name": "latency", "breach": False},
                {"name": "bias-delta", "status": "breach"},
            ],
        },
    )
    _write(
        base / "gap-assessment" / "iso.json",
        {"framework": "ISO-42001", "coverage_score": 72.0,
         "AGENT_SIGNATURE": "aigovops.gap@0.1.0"},
    )
    _write(
        base / "gap-assessment" / "nist.json",
        {"framework": "NIST-AI-RMF", "coverage_score": 64.0,
         "AGENT_SIGNATURE": "aigovops.gap@0.1.0"},
    )
    _write(
        base / "gap-assessment" / "eu.json",
        {"framework": "EU-AI-Act", "coverage_score": 58.0,
         "AGENT_SIGNATURE": "aigovops.gap@0.1.0"},
    )
    for sid, tier in [
        ("clinical-triage", "high-risk-annex-iii"),
        ("social-score", "prohibited"),
        ("biometric-id", "high-risk-annex-i"),
        ("chatbot-faq", "limited-risk"),
        ("recsys-content", "minimal-risk"),
        ("hipaa-edge", "requires-legal-review"),
    ]:
        _write(
            base / "classification" / f"{sid}.json",
            {"system_id": sid, "risk_tier": tier,
             "AGENT_SIGNATURE": "aigovops.eu-classifier@0.2.0"},
        )
    _write(
        base / "action-required" / "review-hipaa.json",
        {
            "title": "HIPAA edge classification needs counsel",
            "reason": "action-required-human",
            "AGENT_SIGNATURE": "aigovclaw.mcp-router@0.1.0",
        },
    )


class HubGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="hub-tests-"))
        self.base = self.tmp / "evidence"
        self.out = self.tmp / "out.html"

    def _read(self) -> str:
        return self.out.read_text(encoding="utf-8")

    def test_full_render(self) -> None:
        _seed(self.base)
        generate(self.out, evidence_path=self.base)
        html_out = self._read()

        # Structural sections.
        for heading in (
            "Risk register",
            "Statement of Applicability",
            "AISIA coverage",
            "Nonconformity",
            "KPI posture",
            "Gap assessment",
            "EU AI Act classification",
            "Action required",
            "Provenance",
        ):
            self.assertIn(heading, html_out, f"Missing section: {heading}")

        # Exact counts from seed.
        # Risk register: 4 total, 2 high, 1 medium, 1 low, 2 open, 2 mitigated.
        self.assertRegex(html_out, r'class="count accent">4<')  # total rows
        # SoA: 2 included-implemented, 1 each for the other four.
        self.assertIn("included implemented", html_out)
        # AISIA: 1 complete, 1 gaps, 1 missing, 3 total.
        # KPI: 2 breaches.
        self.assertRegex(html_out, r'class="count danger">2<')
        # Gap assessment coverage bars.
        self.assertIn("ISO-42001", html_out)
        self.assertIn("NIST-AI-RMF", html_out)
        self.assertIn("EU-AI-Act", html_out)
        # EU tiers all present.
        for tier in ("prohibited", "high risk annex i", "limited risk", "minimal risk"):
            self.assertIn(tier, html_out)
        # Action required item title.
        self.assertIn("HIPAA edge classification", html_out)

        # Provenance footer shows AGENT_SIGNATURE strings.
        for sig in (
            "aigovops.risk-register@0.3.1",
            "aigovops.soa-maintenance@0.2.0",
            "aigovops.metrics-collector@0.4.0",
            "aigovops.eu-classifier@0.2.0",
            "aigovclaw.mcp-router@0.1.0",
        ):
            self.assertIn(sig, html_out, f"Missing signature: {sig}")

        # No em-dash in output.
        self.assertNotIn("\u2014", html_out)

        # Viewport + reduced motion.
        self.assertIn('<meta name="viewport"', html_out)
        self.assertIn("prefers-reduced-motion", html_out)

        # No external URLs for CSS or JS. Hub is fully self-contained.
        ext = re.findall(r'(?:src|href)="(https?://[^"]+)"', html_out)
        self.assertEqual(ext, [], f"Unexpected external URLs: {ext}")
        # No CDN font / css / js references.
        for bad in (
            "fonts.googleapis",
            "cdn.jsdelivr",
            "unpkg.com",
            "cdnjs.cloudflare",
            "rel=\"stylesheet\"",  # no external stylesheet links at all
        ):
            self.assertNotIn(bad, html_out, f"Unexpected reference: {bad}")

        # No banned fonts or generic stacks in the CSS.
        for bad_font in ("Inter", "Roboto", "ui-sans-serif", "system-ui"):
            self.assertNotIn(bad_font, html_out, f"Banned font: {bad_font}")
        # No purple gradient defaults.
        for bad_color in ("#a855f7", "#9333ea", "#8b5cf6", "#7c3aed"):
            self.assertNotIn(bad_color, html_out.lower(), f"Banned color: {bad_color}")

        # Parses without errors.
        parser = _StrictParser()
        parser.feed(html_out)
        self.assertEqual(parser.errors, [])

    def test_empty_state(self) -> None:
        self.base.mkdir(parents=True, exist_ok=True)
        generate(self.out, evidence_path=self.base)
        html_out = self._read()
        self.assertIn("No evidence yet.", html_out)
        self.assertIn("hermes run", html_out)
        self.assertNotIn("\u2014", html_out)
        self.assertIn('<meta name="viewport"', html_out)
        self.assertIn("prefers-reduced-motion", html_out)

    def test_missing_dir(self) -> None:
        # Evidence path does not exist at all. Must still render empty state
        # without raising.
        ghost = self.tmp / "does-not-exist"
        generate(self.out, evidence_path=ghost)
        self.assertIn("No evidence yet.", self._read())

    def test_env_override(self) -> None:
        _seed(self.base)
        os.environ["AIGOVCLAW_EVIDENCE_PATH"] = str(self.base)
        try:
            resolved = resolve_evidence_path()
            self.assertEqual(resolved, self.base.resolve())
        finally:
            del os.environ["AIGOVCLAW_EVIDENCE_PATH"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
