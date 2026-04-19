"""Tests for the AIGovClaw Hub v1 generator.

Standalone runnable: python3 hub/v1/tests/test_v1_generator.py

Vendor files (React UMD) may not be present in a fresh clone. Tests that
render the full artifact seed tiny placeholder files into a temporary
VENDOR_DIR override so the generator has something to inline. This keeps
the suite independent of maintainer-drop state.
"""

from __future__ import annotations

import html.parser
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hub.v1 import generator as v1gen  # noqa: E402


# A payload large enough to pass the >1000-byte sanity floor.
_PLACEHOLDER_REACT = (
    "/* placeholder react UMD for tests */\n"
    "window.React = { createElement: function(){ return {}; }, "
    "useState: function(v){ return [v, function(){}]; }, "
    "useEffect: function(){}, useMemo: function(fn){ return fn(); }, "
    "useRef: function(v){ return { current: v }; } };\n"
    + "// pad " * 300
)
_PLACEHOLDER_REACT_DOM = (
    "/* placeholder react-dom UMD for tests */\n"
    "window.ReactDOM = { createRoot: function(el){ "
    "return { render: function(){ el.innerHTML = '<div>rendered</div>'; } }; "
    "} };\n"
    + "// pad " * 300
)


class _StrictParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def error(self, message: str) -> None:  # pragma: no cover
        self.errors.append(message)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _seed_evidence(base: Path) -> None:
    _write(
        base / "risk-register" / "rr.json",
        {
            "generated_at": "2026-04-18T12:00:00Z",
            "AGENT_SIGNATURE": "aigovops.risk-register@0.3.1",
            "rows": [
                {"id": "R-001", "tier": "high", "treatment_option": "reduce"},
                {"id": "R-002", "tier": "medium", "treatment_option": "accept"},
            ],
        },
    )
    _write(
        base / "soa" / "soa.json",
        {
            "generated_at": "2026-04-18T12:01:00Z",
            "AGENT_SIGNATURE": "aigovops.soa@0.2.0",
            "rows": [
                {"id": "A.6.2.4", "status": "included-implemented"},
                {"id": "A.7.1.1", "status": "included-partial"},
            ],
        },
    )
    _write(
        base / "aisia" / "sys-a.json",
        {
            "system_id": "sys-a",
            "AGENT_SIGNATURE": "aigovops.aisia@0.1.0",
        },
    )
    _write(
        base / "metrics" / "m.json",
        {
            "AGENT_SIGNATURE": "aigovops.metrics@0.4.0",
            "kpis": [{"name": "drift"}, {"name": "latency"}],
            "threshold_breaches": [{"name": "drift"}],
        },
    )
    _write(
        base / "gap-assessment" / "iso.json",
        {
            "target_framework": "ISO-42001",
            "summary": {"coverage_score": 0.72},
            "AGENT_SIGNATURE": "aigovops.gap@0.1.0",
        },
    )
    _write(
        base / "classification" / "clinical.json",
        {
            "system_id": "clinical-triage",
            "risk_tier": "high-risk-annex-iii",
            "AGENT_SIGNATURE": "aigovops.eu-classifier@0.2.0",
        },
    )
    _write(
        base / "action-required" / "review.json",
        {
            "title": "HIPAA edge classification needs counsel",
            "reason": "action-required-human",
            "AGENT_SIGNATURE": "aigovclaw.mcp-router@0.1.0",
        },
    )


class V1GeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="hub-v1-tests-"))
        self.base = self.tmp / "evidence"
        self.out = self.tmp / "out.html"
        # Point the generator at placeholder vendor files so tests do not
        # require the maintainer-drop artifacts.
        self._orig_react = v1gen.REACT_UMD_PATH
        self._orig_rdom = v1gen.REACT_DOM_UMD_PATH
        vendor = self.tmp / "vendor"
        vendor.mkdir()
        (vendor / "react.js").write_text(_PLACEHOLDER_REACT, encoding="utf-8")
        (vendor / "react-dom.js").write_text(_PLACEHOLDER_REACT_DOM, encoding="utf-8")
        v1gen.REACT_UMD_PATH = vendor / "react.js"
        v1gen.REACT_DOM_UMD_PATH = vendor / "react-dom.js"

    def tearDown(self) -> None:
        v1gen.REACT_UMD_PATH = self._orig_react
        v1gen.REACT_DOM_UMD_PATH = self._orig_rdom

    def _read(self) -> str:
        return self.out.read_text(encoding="utf-8")

    def test_renders_structural_html(self) -> None:
        _seed_evidence(self.base)
        v1gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        # Mount point for React.
        self.assertIn('<div id="root"></div>', out)
        # Viewport and generator meta.
        self.assertIn('<meta name="viewport"', out)
        self.assertIn('aigovclaw-hub/v1', out)
        # Title references v1.
        self.assertIn("AIGovClaw Command Centre v1", out)
        # Aesthetic bar present.
        self.assertIn("#d97757", out)
        self.assertIn("#0f1419", out)
        self.assertIn("JetBrains Mono", out)
        self.assertIn("Crimson Pro", out)
        # No banned fonts or colors.
        for bad_font in ("Inter", "Roboto", "ui-sans-serif", "system-ui"):
            self.assertNotIn(bad_font, out, f"Banned font: {bad_font}")
        for bad_color in ("#a855f7", "#9333ea", "#8b5cf6", "#7c3aed"):
            self.assertNotIn(bad_color, out.lower(), f"Banned color: {bad_color}")

    def test_at_least_two_scripts_present(self) -> None:
        _seed_evidence(self.base)
        v1gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        # React, ReactDOM, data, parse-helper, app-js => at least 5. Require >= 2.
        self.assertGreaterEqual(out.count("<script"), 2)

    def test_no_em_dash(self) -> None:
        _seed_evidence(self.base)
        v1gen.generate(self.out, evidence_path=self.base)
        self.assertNotIn("\u2014", self._read())

    def test_data_payload_valid_json(self) -> None:
        _seed_evidence(self.base)
        v1gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        m = re.search(
            r'<script type="application/json" id="__AIGOVCLAW_HUB_DATA__">\s*(.*?)\s*</script>',
            out, flags=re.DOTALL,
        )
        self.assertIsNotNone(m, "Data payload <script> not found")
        payload_text = m.group(1)
        # Undo the inline-safety escape that generator applies before parsing.
        payload_text = payload_text.replace("<\\/", "</")
        payload = json.loads(payload_text)
        self.assertTrue(payload.get("has_any_artifacts"))
        self.assertIn("risk", payload)
        self.assertIn("soa", payload)
        self.assertIn("provenance", payload)
        self.assertEqual(payload["risk"]["total"], 2)
        self.assertEqual(payload["risk"]["by_tier"]["high"], 1)
        self.assertEqual(payload["kpi"]["breaches"], 1)
        # Provenance lists the seeded artifact types.
        types = {r["type"] for r in payload["provenance"]["rows"]}
        self.assertIn("risk-register", types)
        self.assertIn("soa", types)

    def test_parses_with_html_parser(self) -> None:
        _seed_evidence(self.base)
        v1gen.generate(self.out, evidence_path=self.base)
        parser = _StrictParser()
        parser.feed(self._read())
        self.assertEqual(parser.errors, [])

    def test_empty_state_renders(self) -> None:
        # Evidence path empty: payload has_any_artifacts is false.
        self.base.mkdir(parents=True, exist_ok=True)
        v1gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn('<div id="root"></div>', out)
        m = re.search(
            r'<script type="application/json" id="__AIGOVCLAW_HUB_DATA__">\s*(.*?)\s*</script>',
            out, flags=re.DOTALL,
        )
        self.assertIsNotNone(m)
        payload = json.loads(m.group(1).replace("<\\/", "</"))
        self.assertFalse(payload["has_any_artifacts"])
        # Still no em-dash.
        self.assertNotIn("\u2014", out)

    def test_vendor_missing_raises(self) -> None:
        # Point at a nonexistent path.
        v1gen.REACT_UMD_PATH = self.tmp / "does-not-exist-react.js"
        _seed_evidence(self.base)
        with self.assertRaises(v1gen.VendorMissingError):
            v1gen.generate(self.out, evidence_path=self.base)

    def test_no_external_urls_except_github(self) -> None:
        _seed_evidence(self.base)
        v1gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        # Collect every src/href referencing http(s).
        refs = re.findall(r'(?:src|href)="(https?://[^"]+)"', out)
        for r in refs:
            self.assertIn("github.com", r, f"Non-github external URL in output: {r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
