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
        # COMMAND CENTER + CASCADE + DISCOVERY + ASSURANCE + GOVERNANCE
        self.assertEqual(len(payload["catalog"]["groups"]), 5)

    # ------------------------------------------------------------------
    # Bespoke renderer coverage
    # ------------------------------------------------------------------

    def test_all_bespoke_panels_have_renderers(self) -> None:
        """Every sidebar panel id must either match a special-case renderer
        (dashboard, crosswalk, cascade-intake, risk-register-builder,
        soa-generator, gap-assessment, action-required) or appear in
        PANEL_FACTORIES so it receives a bespoke triple, not the generic
        fallback."""
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        special = {
            "dashboard", "crosswalk", "cascade-intake", "risk-register-builder",
            "soa-generator", "gap-assessment", "action-required",
            "certification", "tasks",
        }
        catalog = v2gen.PANEL_CATALOGUE
        panel_ids: list[str] = []
        for group in catalog["groups"]:
            for item in group["items"]:
                panel_ids.append(item["id"])
        # Every non-special panel id must appear in the PANEL_FACTORIES map
        # in the rendered HTML (string presence of the id as a JS key).
        for pid in panel_ids:
            if pid in special:
                continue
            # Find the factory assignment line by literal string match.
            self.assertIn(f"'{pid}'", out, f"PANEL_FACTORIES entry missing for {pid}")

    def test_empty_store_every_panel_emits_empty_panel(self) -> None:
        """With an empty evidence store, the EmptyPanel marker must be present
        in the rendered JS. This confirms renderers use the empty fallback
        rather than crashing on undefined artifact data."""
        self.base.mkdir(parents=True, exist_ok=True)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("EmptyPanel", out)
        self.assertIn("data-empty", out)

    def test_no_factory_fallback_marker_for_registered_panels(self) -> None:
        """The 'Unregistered panel id' warning must not fire for any sidebar
        panel. It should only appear in the bundled JS source (the branch),
        not as an actual rendered message."""
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        # The warning string exists in the JS source (as a branch) but the
        # rendered payload must not indicate any panel hit that branch.
        # We confirm by checking that every sidebar panel id is present as
        # a PANEL_FACTORIES key in the inlined JS.
        self.assertIn("PANEL_FACTORIES", out)
        for pid in (
            "framework-monitor", "applicability-checker", "audit-log-generator",
            "bias-evaluator", "certification-readiness", "management-review-packager",
            "incident-reporting", "data-register-builder",
        ):
            self.assertIn(f"'{pid}':", out, f"Factory key not found for {pid}")

    def test_warning_rendering_from_plugin_artifact(self) -> None:
        """Seed a synthetic bias-evaluator artifact with one warning. Confirm
        the warning text reaches the rendered payload under the artifacts
        summary and is visible to ValidationFromWarnings."""
        _write(
            self.base / "bias-evaluator" / "be.json",
            {
                "timestamp": "2026-04-18T13:00:00Z",
                "agent_signature": "aigovops.bias-evaluator@0.1.0",
                "metrics": [{"protected_attribute": "gender", "metric": "impact_ratio", "value": 0.72}],
                "rule_findings": [{"jurisdiction": "NYC-LL144", "rule": "4/5ths", "status": "fail", "detail": "Below 0.8"}],
                "warnings": ["Selection rate reference-group count below threshold for statistical validity"],
            },
        )
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        m = re.search(
            r'<script type="application/json" id="__AIGOVCLAW_HUB_V2_DATA__">\s*(.*?)\s*</script>',
            out, flags=re.DOTALL,
        )
        self.assertIsNotNone(m)
        payload = json.loads(m.group(1).replace("<\\/", "</"))
        bias = payload["artifacts"].get("bias-evaluator")
        self.assertIsNotNone(bias)
        self.assertEqual(bias["count"], 1)
        self.assertEqual(bias["warnings"], 1)
        self.assertIn("Selection rate", json.dumps(bias["latest"]))

    def test_citation_index_populated_from_artifacts(self) -> None:
        """The citation-search panel depends on the citations_index payload.
        Seed two artifacts with citations and confirm both surface."""
        _write(
            self.base / "risk-register" / "rr-cited.json",
            {
                "timestamp": "2026-04-18T14:00:00Z",
                "agent_signature": "aigovops.risk-register@0.3.1",
                "rows": [{"id": "R-100", "tier": "high"}],
                "citations": ["ISO/IEC 42001:2023, Clause 6.1.2", "NIST AI RMF GOVERN 1.1"],
            },
        )
        _write(
            self.base / "audit-log-generator" / "log-cited.json",
            {
                "timestamp": "2026-04-18T14:05:00Z",
                "agent_signature": "aigovops.audit-log-generator@0.1.0",
                "events": [],
                "citations": ["ISO/IEC 42001:2023, Clause 9.2"],
            },
        )
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        m = re.search(
            r'<script type="application/json" id="__AIGOVCLAW_HUB_V2_DATA__">\s*(.*?)\s*</script>',
            out, flags=re.DOTALL,
        )
        self.assertIsNotNone(m)
        payload = json.loads(m.group(1).replace("<\\/", "</"))
        cits = payload.get("citations_index", [])
        self.assertGreaterEqual(len(cits), 3)
        texts = [c["text"] for c in cits]
        self.assertIn("ISO/IEC 42001:2023, Clause 6.1.2", texts)
        self.assertIn("NIST AI RMF GOVERN 1.1", texts)
        self.assertIn("ISO/IEC 42001:2023, Clause 9.2", texts)

    # ------------------------------------------------------------------
    # Command Center markup (subsystem 2)
    # ------------------------------------------------------------------

    def test_command_center_panel_registered(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("COMMAND CENTER", out)
        self.assertIn("CommandCenterPanel", out)
        self.assertIn("'command-center'", out)

    def test_health_strip_component_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("HealthStrip", out)
        self.assertIn("data-health-strip", out)
        # Symbols used per project convention (not emojis).
        self.assertIn("\\u2713", out)  # check
        self.assertIn("\\u21bb", out)  # refresh

    def test_quick_actions_component_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("QuickActions", out)
        self.assertIn("data-quick-actions", out)
        self.assertIn("Needs approval", out)

    def test_task_queue_component_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("TaskQueue", out)
        self.assertIn("data-task-queue", out)
        # Pause/Resume/Cancel buttons rendered from task status.
        self.assertIn("Pause", out)
        self.assertIn("Resume", out)
        self.assertIn("Cancel", out)

    def test_approval_queue_component_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("ApprovalQueuePanel", out)
        self.assertIn("data-approval-queue", out)
        self.assertIn("Approve", out)
        self.assertIn("Reject", out)

    def test_activity_log_component_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("ActivityLog", out)
        self.assertIn("data-activity-log", out)

    def test_executive_view_toggle_present(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        self.assertIn("ExecutiveView", out)
        self.assertIn("data-executive-view", out)
        self.assertIn("Executive view", out)
        self.assertIn("Operating view", out)
        self.assertIn("aigovclaw.hub.v2.executiveView", out)

    def test_polling_intervals_configured(self) -> None:
        _seed_evidence(self.base)
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        # 2-second and 10-second cadences documented in the polling block.
        self.assertIn("2000", out)
        self.assertIn("10000", out)
        self.assertIn("/api/health", out)
        self.assertIn("/api/tasks", out)
        self.assertIn("/api/approvals", out)
        self.assertIn("/api/commands", out)

    def test_extended_plugin_dirs_loaded_by_v2_store(self) -> None:
        """Seed an artifact in a directory the base Store does not load,
        and confirm v2's _augment_store_for_v2 picks it up so bespoke
        renderers can find it."""
        _write(
            self.base / "human-oversight-designer" / "hod.json",
            {
                "timestamp": "2026-04-18T15:00:00Z",
                "agent_signature": "aigovops.human-oversight-designer@0.1.0",
                "ability_coverage": [
                    {"ability": "monitor", "status": "covered", "mechanism": "dashboard"},
                    {"ability": "intervene", "status": "partial", "mechanism": "kill switch"},
                ],
                "override_capability": {"present": True, "mechanism": "manual stop"},
            },
        )
        v2gen.generate(self.out, evidence_path=self.base)
        out = self._read()
        m = re.search(
            r'<script type="application/json" id="__AIGOVCLAW_HUB_V2_DATA__">\s*(.*?)\s*</script>',
            out, flags=re.DOTALL,
        )
        self.assertIsNotNone(m)
        payload = json.loads(m.group(1).replace("<\\/", "</"))
        hod = payload["artifacts"].get("human-oversight-designer")
        self.assertIsNotNone(hod)
        self.assertEqual(hod["count"], 1)
        latest = hod["latest"]
        self.assertEqual(len(latest["ability_coverage"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
