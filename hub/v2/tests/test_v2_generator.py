"""Tests for the AIGovClaw Hub v2 generator.

Standalone runnable: python3 hub/v2/tests/test_v2_generator.py

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

from hub.v2 import generator as v2gen  # noqa: E402


# Placeholder UMDs large enough to pass the >1000-byte sanity floor.
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
        base / "action-required" / "review.json",
        {
            "title": "HIPAA edge classification needs counsel",
            "reason": "action-required-human",
            "AGENT_SIGNATURE": "aigovclaw.mcp-router@0.1.0",
        },
    )


class V2GeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="hub-v2-tests-"))
        self.base = self.tmp / "evidence"
        self.out = self.tmp / "out.html"
        self._orig_react = v2gen.REACT_UMD_PATH
        self._orig_rdom = v2gen.REACT_DOM_UMD_PATH
        vendor = self.tmp / "vendor"
        vendor.mkdir()
        (vendor / "react.js").write_text(_PLACEHOLDER_REACT, encoding="utf-8")
        (vendor / "react-dom.js").write_text(_PLACEHOLDER_REACT_DOM, encoding="utf-8")
        v2gen.REACT_UMD_PATH = vendor / "react.js"
        v2gen.REACT_DOM_UMD_PATH = vendor / "react-dom.js"

    def tearDown(self) -> None:
        v2gen.REACT_UMD_PATH = self._orig_react
        v2gen.REACT_DOM_UMD_PATH = self._orig_rdom

    def _read(self) -> str:
        return self.out.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Smoke / structure
    # ------------------------------------------------------------------

    def test_generator_emits_html(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn('<div id="root"></div>', out)
        self.assertIn('<meta name="viewport"', out)
        self.assertIn("aigovclaw-hub/v2", out)
        self.assertIn("AIGovClaw Hub v2", out)
        parser = _StrictParser()
        parser.feed(out)
        self.assertEqual(parser.errors, [])

    def test_sidebar_has_four_groups(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        for label in ("CASCADE", "DISCOVERY", "ASSURANCE", "GOVERNANCE"):
            self.assertIn(label, out, f"Missing sidebar group label: {label}")

    def test_no_em_dashes_in_output(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        self.assertNotIn("\u2014", self._read())

    def test_no_inter_roboto_system_ui_in_css(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        # Extract the CSS between the first <style>...</style> (head) to scope
        # the assertion to rendered CSS only, since the fallback font stack
        # legitimately contains "system-ui".
        m = re.search(r"<style>(.*?)</style>", out, flags=re.DOTALL)
        self.assertIsNotNone(m)
        css = m.group(1)
        # Banned web fonts: Inter and Roboto are not approved for v2.
        for bad in ("'Inter'", '"Inter"', "'Roboto'", '"Roboto"'):
            self.assertNotIn(bad, css, f"Banned web font token in CSS: {bad}")

    def test_no_purple_gradient_in_css(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read().lower()
        for bad in ("#a855f7", "#9333ea", "#8b5cf6", "#7c3aed"):
            self.assertNotIn(bad, out, f"Banned purple color in output: {bad}")
        self.assertNotIn("purple", out)

    # ------------------------------------------------------------------
    # Maintainer UX
    # ------------------------------------------------------------------

    def test_vendor_files_absent_produces_maintainer_error(self) -> None:
        v2gen.REACT_UMD_PATH = self.tmp / "nonexistent-react.js"
        _seed_evidence(self.base)
        with self.assertRaises(v2gen.VendorMissingError) as ctx:
            v2gen.generate(self.out, evidence_path=self.base)
        msg = str(ctx.exception)
        self.assertIn("hub/v2/vendor", msg)
        self.assertIn("react.production.min.js", msg)

    # ------------------------------------------------------------------
    # UX patterns
    # ------------------------------------------------------------------

    def test_empty_evidence_store_shows_welcome_page(self) -> None:
        self.base.mkdir(parents=True, exist_ok=True)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        # Welcome path references cascade intake call-to-action.
        self.assertIn("cascade-intake", out)
        self.assertIn("No evidence yet", out)

    def test_cascade_intake_wizard_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("CascadeIntakePanel", out)
        self.assertIn("cascade-intake", out)
        self.assertIn("aigovclaw.hub.v2.profile", out)

    def test_jurisdiction_filter_bar_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        for label in ("Global", "USA", "EU", "UK", "Singapore", "Canada"):
            self.assertIn(label, out, f"Missing jurisdiction tab: {label}")

    def test_crosswalk_data_inlined(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(
            self.out,
            evidence_path=self.base,
            aigovops_root=str(_REPO_ROOT.parent / "aigovops"),
        )
        out = self._read()
        m = re.search(
            r'<script type="application/json" id="__AIGOVCLAW_HUB_V2_DATA__">\s*(.*?)\s*</script>',
            out, flags=re.DOTALL,
        )
        self.assertIsNotNone(m, "Data payload <script> not found")
        payload_text = m.group(1).replace("<\\/", "</")
        payload = json.loads(payload_text)
        crosswalk = payload.get("crosswalk", {})
        mappings = crosswalk.get("mappings", [])
        # Crosswalk should contain ISO 42001 mappings at minimum when the
        # aigovops sibling checkout is present. Skip gracefully when it is not.
        if not mappings:
            self.skipTest("aigovops sibling checkout not available for crosswalk test")
        fw_pairs = {(m.get("source_fw"), m.get("target_fw")) for m in mappings}
        self.assertTrue(
            any("iso42001" in (a or "") or "iso42001" in (b or "") for a, b in fw_pairs),
            "No ISO 42001 mapping found in inlined crosswalk",
        )

    def test_all_32_plugin_panels_referenced(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        expected_plugin_panels = [
            "ai-system-inventory-maintainer",
            "aisia-runner",
            "applicability-checker",
            "audit-log-generator",
            "bias-evaluator",
            "certification-readiness",
            "colorado-ai-act-compliance",
            "crosswalk-matrix-builder",
            "data-register-builder",
            "eu-conformity-assessor",
            "evidence-bundle-packager",
            "explainability-documenter",
            "gap-assessment",
            "genai-risk-register",
            "gpai-obligations-tracker",
            "high-risk-classifier",
            "human-oversight-designer",
            "incident-reporting",
            "internal-audit-planner",
            "management-review-packager",
            "metrics-collector",
            "nonconformity-tracker",
            "nyc-ll144-audit-packager",
            "post-market-monitoring",
            "risk-register-builder",
            "robustness-evaluator",
            "role-matrix-generator",
            "singapore-magf-assessor",
            "soa-generator",
            "supplier-vendor-assessor",
            "system-event-logger",
            "uk-atrs-recorder",
        ]
        self.assertEqual(len(expected_plugin_panels), 32)
        for panel_id in expected_plugin_panels:
            self.assertIn(panel_id, out, f"Panel id not referenced in output: {panel_id}")

    def test_reduced_motion_css_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("prefers-reduced-motion", out)

    def test_sessionstorage_for_jurisdiction_filter(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("sessionStorage.setItem", out)
        self.assertIn("aigovclaw.hub.v2.jurisdiction", out)

    def test_action_required_banner_markup(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("action-banner", out)
        self.assertIn("ActionBanner", out)

    def test_three_tab_workspace_pattern(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        # Spot-check: the three tab labels appear in the source.
        self.assertIn("Guidance", out)
        self.assertIn("Artifacts", out)
        self.assertIn("Validation", out)
        # The three-tab workspace factory function is present.
        self.assertIn("ThreeTabWorkspace", out)

    def test_data_payload_valid_json(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        m = re.search(
            r'<script type="application/json" id="__AIGOVCLAW_HUB_V2_DATA__">\s*(.*?)\s*</script>',
            out, flags=re.DOTALL,
        )
        self.assertIsNotNone(m)
        payload = json.loads(m.group(1).replace("<\\/", "</"))
        self.assertTrue(payload.get("has_any_artifacts"))
        self.assertEqual(payload["risk"]["total"], 2)
        self.assertEqual(payload["risk"]["by_tier"]["high"], 1)
        self.assertIn("catalog", payload)
        self.assertEqual(len(payload["catalog"]["groups"]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
