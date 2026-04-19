"""AIGovClaw Hub v2 generator.

Builds the practitioner-facing single-file dashboard by inlining:
  - The AIGovOS-derived sidebar IA (CASCADE / DISCOVERY / ASSURANCE / GOVERNANCE)
  - A panel catalogue covering the 32 AIGovOps plugins + four derived panels
    (dashboard, certification, tasks, cascade-intake)
  - The crosswalk mapping catalogue condensed to {id, source_fw, target_fw,
    source_ref, target_ref, relationship, confidence} per row. The graph view
    and the mappings table read directly from this inlined JSON.
  - Risk register, SoA, nonconformity, KPI, gap-assessment, action-required,
    and framework counts derived from the local evidence store (same Store
    API as v0 and v1).

Stdlib Python only. Vendored React UMD bundles loaded from hub/v2/vendor/.
No network at generate time. No CDN at runtime.
"""

from __future__ import annotations

import json
import os
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..generator import (
    ARTIFACT_DIRS,
    SOA_STATUSES,
    EU_TIERS,
    US_STATE_ROWS,
    Store,
    resolve_evidence_path,
    _age_days,
    _count_by,
    _rel_from_base,
    _walk_json,
)
from .templates import (
    APP_JS,
    HTML_TEMPLATE,
    TAILWIND_SUBSET_CSS,
    VENDOR_MISSING_MESSAGE,
)


VENDOR_DIR = Path(__file__).parent / "vendor"
REACT_UMD_PATH = VENDOR_DIR / "react.production.min.js"
REACT_DOM_UMD_PATH = VENDOR_DIR / "react-dom.production.min.js"

# AIGovOps plugin catalogue. Path resolved relative to this file when the
# aigovops repo is a sibling of aigovclaw. Optional: the generator works
# without it; crosswalk mappings are omitted when the path is unreachable.
DEFAULT_AIGOVOPS_ROOT = (
    Path(__file__).resolve().parents[3] / "aigovops"
)


class VendorMissingError(RuntimeError):
    """Raised when required vendor files are not present."""


# --------------------------------------------------------------------------
# Panel catalogue
# --------------------------------------------------------------------------

# Every panel id is the AIGovOps plugin slug, except the four derived panels:
# dashboard, certification, tasks, cascade-intake, crosswalk.
#
# Grouping adopts the AIGovOS IA verbatim:
#   CASCADE    = applicability and intake
#   DISCOVERY  = knowledge and cross-framework analysis
#   ASSURANCE  = evidence and validation
#   GOVERNANCE = decision-making and attestation (including jurisdictions)

PANEL_CATALOGUE = {
    "groups": [
        {
            "id": "command-center",
            "label": "COMMAND CENTRE",
            "items": [
                {"id": "command-center", "label": "Command Centre"},
            ],
        },
        {
            "id": "cascade",
            "label": "CASCADE",
            "items": [
                {"id": "framework-monitor", "label": "Regulatory feed"},
                {"id": "applicability-checker", "label": "Applicability assessment"},
                {"id": "cascade-intake", "label": "Cascade intake"},
            ],
        },
        {
            "id": "discovery",
            "label": "DISCOVERY",
            "items": [
                {"id": "crosswalk", "label": "Crosswalk browser"},
                {"id": "crosswalk-matrix-builder", "label": "Crosswalk matrix"},
                {"id": "gap-explorer", "label": "Gap explorer"},
                {"id": "citation-search", "label": "Citation search"},
            ],
        },
        {
            "id": "assurance",
            "label": "ASSURANCE",
            "items": [
                {"id": "ai-system-inventory-maintainer", "label": "AI systems registry"},
                {"id": "risk-register-builder", "label": "Risk register"},
                {"id": "soa-generator", "label": "Statement of Applicability"},
                {"id": "aisia-runner", "label": "AISIA viewer"},
                {"id": "audit-log-generator", "label": "Audit log"},
                {"id": "metrics-collector", "label": "Metrics dashboard"},
                {"id": "post-market-monitoring", "label": "Post-market monitoring"},
                {"id": "robustness-evaluator", "label": "Robustness evaluation"},
                {"id": "bias-evaluator", "label": "Bias evaluation"},
                {"id": "evidence-bundle-packager", "label": "Evidence bundle inspector"},
                {"id": "certification-readiness", "label": "Certification readiness"},
                {"id": "gap-assessment", "label": "Gap assessment"},
            ],
        },
        {
            "id": "governance",
            "label": "GOVERNANCE",
            "items": [
                {"id": "management-review-packager", "label": "Management review"},
                {"id": "internal-audit-planner", "label": "Internal audit plan"},
                {"id": "role-matrix-generator", "label": "Role matrix"},
                {"id": "nonconformity-tracker", "label": "Nonconformity register"},
                {"id": "incident-reporting", "label": "Incident reporting"},
                {"id": "eu-conformity-assessor", "label": "EU conformity assessment"},
                {"id": "gpai-obligations-tracker", "label": "GPAI obligations"},
                {"id": "human-oversight-designer", "label": "Human oversight design"},
                {"id": "supplier-vendor-assessor", "label": "Supplier and vendor"},
                {"id": "action-required", "label": "Action required queue"},
                {"id": "uk-atrs-recorder", "label": "UK ATRS"},
                {"id": "colorado-ai-act-compliance", "label": "Colorado SB 205"},
                {"id": "nyc-ll144-audit-packager", "label": "NYC LL 144"},
                {"id": "singapore-magf-assessor", "label": "Singapore MAGF"},
                {"id": "explainability-documenter", "label": "Explainability docs"},
                {"id": "system-event-logger", "label": "System event log"},
                {"id": "genai-risk-register", "label": "GenAI risk register"},
                {"id": "high-risk-classifier", "label": "EU AI Act classifier"},
                {"id": "data-register-builder", "label": "Data register"},
            ],
        },
    ],
    # Per-panel metadata. Keep descriptions concise and certification-grade.
    "panels": {
        "command-center": {
            "title": "Command Centre",
            "group": "COMMAND CENTRE",
            "description": "Live task queue, health strip, approvals, and quick actions. Requires the Command Centre v2 server.",
            "plugin": "hub.v2_server",
        },
        "dashboard": {
            "title": "Dashboard",
            "group": "Home",
            "description": "Composite AIMS posture snapshot.",
            "plugin": "hub.v2",
        },
        "certification": {
            "title": "Certification",
            "group": "Home",
            "description": "ISO 42001 clause-by-clause readiness.",
            "plugin": "aigovops.certification-readiness",
            "skill": "skills/certification-readiness/SKILL.md",
            "frameworks": ["ISO-42001"],
        },
        "tasks": {
            "title": "Tasks",
            "group": "Home",
            "description": "Action queue across panels.",
            "plugin": "hub.v2",
        },
        "framework-monitor": {
            "title": "Regulatory feed",
            "group": "CASCADE",
            "description": "Detection stream for new or amended obligations.",
            "plugin": "workflows/framework-monitor",
            "frameworks": ["ISO-42001", "NIST-AI-RMF", "EU-AI-Act", "UK-ATRS", "NYC-LL144", "Colorado-SB-205"],
        },
        "applicability-checker": {
            "title": "Applicability assessment",
            "group": "CASCADE",
            "description": "EU AI Act applicability by target date + system classification.",
            "plugin": "aigovops.applicability-checker",
            "skill": "skills/applicability-checker/SKILL.md",
            "frameworks": ["EU-AI-Act"],
        },
        "cascade-intake": {
            "title": "Cascade intake wizard",
            "group": "CASCADE",
            "description": "Capture organization posture once for downstream filtering.",
            "plugin": "hub.v2",
        },
        "crosswalk": {
            "title": "Crosswalk browser",
            "group": "DISCOVERY",
            "description": "Graph view of framework-to-framework mappings.",
            "plugin": "aigovops.crosswalk-matrix-builder",
            "skill": "skills/crosswalk-matrix-builder/SKILL.md",
            "frameworks": ["ISO-42001", "NIST-AI-RMF", "EU-AI-Act", "UK-ATRS", "NYC-LL144", "Colorado-SB-205", "California", "Singapore-MAGF"],
        },
        "crosswalk-matrix-builder": {
            "title": "Crosswalk matrix",
            "group": "DISCOVERY",
            "description": "Cross-framework coverage, gap, or matrix query result.",
            "plugin": "aigovops.crosswalk-matrix-builder",
            "skill": "skills/crosswalk-matrix-builder/SKILL.md",
            "frameworks": ["ISO-42001", "NIST-AI-RMF", "EU-AI-Act"],
        },
        "gap-explorer": {
            "title": "Gap explorer",
            "group": "DISCOVERY",
            "description": "Cross-framework gap visualization layered over gap-assessment output.",
            "plugin": "aigovops.gap-assessment",
            "skill": "skills/gap-assessment/SKILL.md",
        },
        "citation-search": {
            "title": "Citation search",
            "group": "DISCOVERY",
            "description": "Full-text search across citations in every artifact.",
            "plugin": "hub.v2",
        },
        "ai-system-inventory-maintainer": {
            "title": "AI systems registry",
            "group": "ASSURANCE",
            "description": "Validated, versioned AI system inventory with per-system applicability.",
            "plugin": "aigovops.ai-system-inventory-maintainer",
            "skill": "skills/ai-system-inventory-maintainer/SKILL.md",
            "frameworks": ["ISO-42001", "NIST-AI-RMF", "EU-AI-Act"],
        },
        "risk-register-builder": {
            "title": "Risk register",
            "group": "ASSURANCE",
            "description": "ISO 42001 and NIST AI RMF-compliant AI risk register.",
            "plugin": "aigovops.risk-register-builder",
            "skill": "skills/risk-register-builder/SKILL.md",
            "frameworks": ["ISO-42001", "NIST-AI-RMF"],
        },
        "soa-generator": {
            "title": "Statement of Applicability",
            "group": "ASSURANCE",
            "description": "ISO 42001-compliant Statement of Applicability.",
            "plugin": "aigovops.soa-generator",
            "skill": "skills/soa-generator/SKILL.md",
            "frameworks": ["ISO-42001"],
        },
        "aisia-runner": {
            "title": "AISIA viewer",
            "group": "ASSURANCE",
            "description": "ISO 42001 and NIST AI RMF-compliant AI System Impact Assessment. FRIA coverage included.",
            "plugin": "aigovops.aisia-runner",
            "skill": "skills/aisia-runner/SKILL.md",
            "frameworks": ["ISO-42001", "NIST-AI-RMF", "EU-AI-Act"],
        },
        "audit-log-generator": {
            "title": "Audit log",
            "group": "ASSURANCE",
            "description": "ISO 42001-compliant audit log timeline.",
            "plugin": "aigovops.audit-log-generator",
            "skill": "skills/audit-log-generator/SKILL.md",
            "frameworks": ["ISO-42001"],
        },
        "metrics-collector": {
            "title": "Metrics dashboard",
            "group": "ASSURANCE",
            "description": "NIST AI RMF MEASURE 2.x metrics with threshold-breach routing.",
            "plugin": "aigovops.metrics-collector",
            "skill": "skills/metrics-collector/SKILL.md",
            "frameworks": ["NIST-AI-RMF"],
        },
        "post-market-monitoring": {
            "title": "Post-market monitoring",
            "group": "ASSURANCE",
            "description": "EU AI Act Article 72, ISO 42001 Clause 9.1, NIST MANAGE 4.x plan.",
            "plugin": "aigovops.post-market-monitoring",
            "skill": "skills/post-market-monitoring/SKILL.md",
            "frameworks": ["EU-AI-Act", "ISO-42001", "NIST-AI-RMF"],
        },
        "robustness-evaluator": {
            "title": "Robustness evaluation",
            "group": "ASSURANCE",
            "description": "EU AI Act Article 15, ISO 42001 A.6.2.4, NIST MEASURE 2.5-2.7.",
            "plugin": "aigovops.robustness-evaluator",
            "skill": "skills/robustness-evaluator/SKILL.md",
            "frameworks": ["EU-AI-Act", "ISO-42001", "NIST-AI-RMF"],
        },
        "bias-evaluator": {
            "title": "Bias evaluation",
            "group": "ASSURANCE",
            "description": "Fairness metrics with NYC LL144, EU AI Act Article 10(4), Colorado, Singapore application.",
            "plugin": "aigovops.bias-evaluator",
            "skill": "skills/bias-evaluator/SKILL.md",
            "frameworks": ["NYC-LL144", "EU-AI-Act", "Colorado-SB-205", "Singapore-MAGF", "ISO-42001", "NIST-AI-RMF"],
        },
        "evidence-bundle-packager": {
            "title": "Evidence bundle inspector",
            "group": "ASSURANCE",
            "description": "Deterministic, optionally HMAC-SHA256 signed evidence bundles.",
            "plugin": "aigovops.evidence-bundle-packager",
            "skill": "skills/evidence-bundle-packager/SKILL.md",
        },
        "certification-readiness": {
            "title": "Certification readiness",
            "group": "ASSURANCE",
            "description": "Graduated readiness verdict with evidence completeness, gaps, blockers, remediations.",
            "plugin": "aigovops.certification-readiness",
            "skill": "skills/certification-readiness/SKILL.md",
            "frameworks": ["ISO-42001"],
        },
        "gap-assessment": {
            "title": "Gap assessment",
            "group": "ASSURANCE",
            "description": "Framework gap assessment for ISO 42001, NIST AI RMF, or EU AI Act.",
            "plugin": "aigovops.gap-assessment",
            "skill": "skills/gap-assessment/SKILL.md",
            "frameworks": ["ISO-42001", "NIST-AI-RMF", "EU-AI-Act"],
        },
        "management-review-packager": {
            "title": "Management review",
            "group": "GOVERNANCE",
            "description": "ISO 42001 Clause 9.3.2 management review input package.",
            "plugin": "aigovops.management-review-packager",
            "skill": "skills/management-review-packager/SKILL.md",
            "frameworks": ["ISO-42001"],
        },
        "internal-audit-planner": {
            "title": "Internal audit plan",
            "group": "GOVERNANCE",
            "description": "ISO 42001 Clause 9.2 internal audit programme, schedule, criteria, impartiality.",
            "plugin": "aigovops.internal-audit-planner",
            "skill": "skills/internal-audit-planner/SKILL.md",
            "frameworks": ["ISO-42001"],
        },
        "role-matrix-generator": {
            "title": "Role matrix",
            "group": "GOVERNANCE",
            "description": "ISO 42001-compliant role and responsibility matrix.",
            "plugin": "aigovops.role-matrix-generator",
            "skill": "skills/role-matrix-generator/SKILL.md",
            "frameworks": ["ISO-42001"],
        },
        "nonconformity-tracker": {
            "title": "Nonconformity register",
            "group": "GOVERNANCE",
            "description": "ISO 42001 Clause 10.2 and NIST MANAGE 4.2 nonconformity and corrective-action records.",
            "plugin": "aigovops.nonconformity-tracker",
            "skill": "skills/nonconformity-tracker/SKILL.md",
            "frameworks": ["ISO-42001", "NIST-AI-RMF"],
        },
        "incident-reporting": {
            "title": "Incident reporting",
            "group": "GOVERNANCE",
            "description": "Regulatory-deadline-aware external incident reports.",
            "plugin": "aigovops.incident-reporting",
            "skill": "skills/incident-reporting/SKILL.md",
            "frameworks": ["EU-AI-Act", "Colorado-SB-205", "NYC-LL144"],
        },
        "eu-conformity-assessor": {
            "title": "EU conformity assessment",
            "group": "GOVERNANCE",
            "description": "EU AI Act Article 43 procedure selection, Annex IV completeness, Article 17 QMS.",
            "plugin": "aigovops.eu-conformity-assessor",
            "skill": "skills/eu-conformity-assessor/SKILL.md",
            "frameworks": ["EU-AI-Act"],
        },
        "gpai-obligations-tracker": {
            "title": "GPAI obligations",
            "group": "GOVERNANCE",
            "description": "EU AI Act Articles 51 to 55 GPAI obligations and systemic-risk classification.",
            "plugin": "aigovops.gpai-obligations-tracker",
            "skill": "skills/gpai-obligations-tracker/SKILL.md",
            "frameworks": ["EU-AI-Act"],
        },
        "human-oversight-designer": {
            "title": "Human oversight design",
            "group": "GOVERNANCE",
            "description": "EU AI Act Article 14, ISO 42001 A.9.x, NIST MANAGE 2.3 oversight design.",
            "plugin": "aigovops.human-oversight-designer",
            "skill": "skills/human-oversight-designer/SKILL.md",
            "frameworks": ["EU-AI-Act", "ISO-42001", "NIST-AI-RMF"],
        },
        "supplier-vendor-assessor": {
            "title": "Supplier and vendor",
            "group": "GOVERNANCE",
            "description": "ISO 42001 A.10, EU AI Act Article 25, NYC LL144 Section 5-300 vendor assessment.",
            "plugin": "aigovops.supplier-vendor-assessor",
            "skill": "skills/supplier-vendor-assessor/SKILL.md",
            "frameworks": ["ISO-42001", "EU-AI-Act", "NYC-LL144"],
        },
        "action-required": {
            "title": "Action required queue",
            "group": "GOVERNANCE",
            "description": "Artifacts tagged action-required-human by the MCP router.",
            "plugin": "aigovclaw.mcp-router",
        },
        "uk-atrs-recorder": {
            "title": "UK ATRS",
            "group": "GOVERNANCE",
            "description": "UK Algorithmic Transparency Recording Standard record, Tier 1 and Tier 2.",
            "plugin": "aigovops.uk-atrs-recorder",
            "skill": "skills/uk-atrs-recorder/SKILL.md",
            "frameworks": ["UK-ATRS"],
        },
        "colorado-ai-act-compliance": {
            "title": "Colorado SB 205",
            "group": "GOVERNANCE",
            "description": "Colorado SB 205 developer and deployer compliance record.",
            "plugin": "aigovops.colorado-ai-act-compliance",
            "skill": "skills/colorado-ai-act-compliance/SKILL.md",
            "frameworks": ["Colorado-SB-205"],
        },
        "nyc-ll144-audit-packager": {
            "title": "NYC LL 144",
            "group": "GOVERNANCE",
            "description": "NYC Local Law 144 bias audit public-disclosure bundle.",
            "plugin": "aigovops.nyc-ll144-audit-packager",
            "skill": "skills/nyc-ll144-audit-packager/SKILL.md",
            "frameworks": ["NYC-LL144"],
        },
        "singapore-magf-assessor": {
            "title": "Singapore MAGF",
            "group": "GOVERNANCE",
            "description": "Singapore MAGF 2e pillar assessment with MAS FEAT layering.",
            "plugin": "aigovops.singapore-magf-assessor",
            "skill": "skills/singapore-magf-assessor/SKILL.md",
            "frameworks": ["Singapore-MAGF"],
        },
        "explainability-documenter": {
            "title": "Explainability docs",
            "group": "GOVERNANCE",
            "description": "NIST MEASURE 2.9, EU AI Act Article 86, ISO 42001 A.8.2, UK ATRS explainability.",
            "plugin": "aigovops.explainability-documenter",
            "skill": "skills/explainability-documenter/SKILL.md",
            "frameworks": ["NIST-AI-RMF", "EU-AI-Act", "ISO-42001", "UK-ATRS"],
        },
        "system-event-logger": {
            "title": "System event log",
            "group": "GOVERNANCE",
            "description": "EU AI Act Article 12 / 19 / 26(6), ISO 42001 A.6.2.8, NIST MEASURE 2.8 logging.",
            "plugin": "aigovops.system-event-logger",
            "skill": "skills/system-event-logger/SKILL.md",
            "frameworks": ["EU-AI-Act", "ISO-42001", "NIST-AI-RMF"],
        },
        "genai-risk-register": {
            "title": "GenAI risk register",
            "group": "GOVERNANCE",
            "description": "NIST AI 600-1 GenAI Profile 12-risk register with cross-references.",
            "plugin": "aigovops.genai-risk-register",
            "skill": "skills/genai-risk-register/SKILL.md",
            "frameworks": ["NIST-AI-RMF", "EU-AI-Act", "California"],
        },
        "high-risk-classifier": {
            "title": "EU AI Act classifier",
            "group": "GOVERNANCE",
            "description": "EU AI Act Article 5, 6, Annex I, Annex III risk-tier classification.",
            "plugin": "aigovops.high-risk-classifier",
            "skill": "skills/high-risk-classifier/SKILL.md",
            "frameworks": ["EU-AI-Act"],
        },
        "data-register-builder": {
            "title": "Data register",
            "group": "GOVERNANCE",
            "description": "ISO 42001 A.7 and EU AI Act Article 10 data register.",
            "plugin": "aigovops.data-register-builder",
            "skill": "skills/data-register-builder/SKILL.md",
            "frameworks": ["ISO-42001", "EU-AI-Act"],
        },
    },
}


# --------------------------------------------------------------------------
# Crosswalk extraction
# --------------------------------------------------------------------------

# The crosswalk YAML files live under aigovops/plugins/crosswalk-matrix-builder/data/.
# Rather than take a YAML dependency or inline the full YAML (8500+ lines),
# we parse out just the mapping primitives with a tiny block-aware scanner.

_CROSSWALK_FILES = (
    "iso42001-eu-ai-act.yaml",
    "iso42001-nist-ai-rmf.yaml",
    "iso42001-uk-atrs.yaml",
    "uk-atrs-nist-ai-rmf.yaml",
    "california-crosswalk.yaml",
    "colorado-sb205-crosswalk.yaml",
    "nyc-ll144-crosswalk.yaml",
    "singapore-magf-crosswalk.yaml",
)


_FIELD_RE = re.compile(r"^\s{2,}([a-z_]+):\s*(.*)$")


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def _parse_crosswalk_yaml(path: Path) -> list[dict]:
    """Minimal scanner for the aigovops crosswalk YAML schema.

    The schema is strictly: top-level `mappings:` list, each item begins with
    `  - id:` and contains `source_framework`, `source_ref`, `target_framework`,
    `target_ref`, `relationship`, `confidence`. No nested structures are read.
    Unknown fields are ignored. This is not a general YAML parser.
    """
    if not path.exists() or not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[dict] = []
    cur: dict | None = None
    in_mappings = False
    for raw_line in text.splitlines():
        if not in_mappings:
            if raw_line.strip() == "mappings:":
                in_mappings = True
            continue
        stripped = raw_line.strip()
        if stripped.startswith("- id:"):
            if cur and cur.get("id"):
                out.append(cur)
            cur = {"id": _strip_quotes(stripped.split(":", 1)[1])}
            continue
        if cur is None:
            continue
        m = _FIELD_RE.match(raw_line)
        if not m:
            continue
        key = m.group(1)
        val = m.group(2)
        if key in (
            "source_framework",
            "source_ref",
            "source_title",
            "target_framework",
            "target_ref",
            "target_title",
            "relationship",
            "confidence",
        ):
            cur[key] = _strip_quotes(val)
    if cur and cur.get("id"):
        out.append(cur)
    return out


def _extract_crosswalk(aigovops_root: Path | None) -> dict:
    """Extract condensed mappings + graph from the aigovops crosswalk data."""
    mappings: list[dict] = []
    if aigovops_root is None or not aigovops_root.exists():
        return {"nodes": [], "edges": [], "mappings": []}
    data_dir = aigovops_root / "plugins" / "crosswalk-matrix-builder" / "data"
    if not data_dir.is_dir():
        return {"nodes": [], "edges": [], "mappings": []}
    for name in _CROSSWALK_FILES:
        for row in _parse_crosswalk_yaml(data_dir / name):
            mappings.append({
                "id": row.get("id"),
                "source_fw": row.get("source_framework"),
                "source_ref": row.get("source_ref"),
                "target_fw": row.get("target_framework"),
                "target_ref": row.get("target_ref"),
                "relationship": row.get("relationship"),
                "confidence": row.get("confidence"),
            })
    # Build graph.
    fw_counts: dict[str, int] = {}
    edge_counts: dict[tuple[str, str], int] = {}
    for m in mappings:
        sf = m.get("source_fw") or ""
        tf = m.get("target_fw") or ""
        if sf:
            fw_counts[sf] = fw_counts.get(sf, 0) + 1
        if tf and tf != sf:
            fw_counts[tf] = fw_counts.get(tf, 0) + 1
        if sf and tf and sf != tf:
            key = tuple(sorted((sf, tf)))
            edge_counts[key] = edge_counts.get(key, 0) + 1
    nodes = [
        {"id": fw, "label": _fw_label(fw), "count": count}
        for fw, count in sorted(fw_counts.items(), key=lambda kv: -kv[1])
    ]
    edges = [{"a": k[0], "b": k[1], "count": c} for k, c in edge_counts.items()]
    return {"nodes": nodes, "edges": edges, "mappings": mappings}


def _fw_label(fw: str) -> str:
    return {
        "iso42001": "ISO 42001",
        "nist-ai-rmf": "NIST AI RMF",
        "eu-ai-act": "EU AI Act",
        "uk-atrs": "UK ATRS",
        "nyc-ll144": "NYC LL 144",
        "colorado-sb205": "Colorado SB 205",
        "singapore-magf": "Singapore MAGF",
        "cppa-admt": "CPPA ADMT",
        "ca-ab-1008": "CA AB 1008",
        "ca-sb-942": "CA SB 942",
        "ca-ab-2013": "CA AB 2013",
        "ca-sb-1001": "CA SB 1001",
        "ca-ab-1836": "CA AB 1836",
    }.get(fw, fw)


# --------------------------------------------------------------------------
# Evidence-store extractors (reuse v1 shapes)
# --------------------------------------------------------------------------


def _extract_risk(store: Store) -> dict:
    arts = store.artifacts.get("risk-register", [])
    rows: list[dict] = []
    for a in arts:
        r = a.data.get("rows") or a.data.get("risks")
        if isinstance(r, list):
            rows.extend([x for x in r if isinstance(x, dict)])
    by_tier = {"high": 0, "medium": 0, "low": 0}
    for r in rows:
        tier = r.get("tier")
        if tier in by_tier:
            by_tier[tier] += 1
        else:
            score = r.get("inherent_score") or r.get("residual_score")
            if isinstance(score, (int, float)):
                if score >= 15:
                    by_tier["high"] += 1
                elif score >= 8:
                    by_tier["medium"] += 1
                else:
                    by_tier["low"] += 1
    return {"total": len(rows), "by_tier": by_tier}


def _extract_soa(store: Store) -> dict:
    arts = store.artifacts.get("soa", [])
    rows: list[dict] = []
    for a in arts:
        r = a.data.get("rows") or a.data.get("controls")
        if isinstance(r, list):
            rows.extend([x for x in r if isinstance(x, dict)])
    by_status = _count_by(rows, "status")
    out = {s: by_status.get(s, 0) for s in SOA_STATUSES}
    return {"by_status": out}


def _extract_nonconformity(store: Store) -> dict:
    arts = store.artifacts.get("nonconformity", [])
    now = datetime.now(tz=timezone.utc)
    open_ages: list[float] = []
    IN_PROGRESS = {
        "investigated", "root-cause-identified", "corrective-action-planned",
        "corrective-action-in-progress", "effectiveness-reviewed",
    }
    CLOSED = {"closed"}
    counts = {"open": 0, "in_progress": 0, "closed": 0}
    for a in arts:
        records = a.data.get("records") or []
        if not isinstance(records, list):
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue
            status = rec.get("status") or rec.get("state") or "detected"
            if status in CLOSED:
                counts["closed"] += 1
            elif status in IN_PROGRESS:
                counts["in_progress"] += 1
            else:
                counts["open"] += 1
                detected = rec.get("detected_at") or rec.get("created_at")
                if isinstance(detected, str):
                    d = _age_days(detected, now)
                    if d is not None:
                        open_ages.append(d)
    median_age = statistics.median(open_ages) if open_ages else 0
    return {
        "open": counts["open"],
        "in_progress": counts["in_progress"],
        "closed": counts["closed"],
        "median_age_days": median_age,
    }


def _extract_kpi(store: Store) -> dict:
    arts = store.artifacts.get("metrics", [])
    breaches = 0
    total = 0
    for a in arts:
        kpi_records = a.data.get("kpi_records") or a.data.get("kpis") or []
        if isinstance(kpi_records, list):
            total += sum(1 for k in kpi_records if isinstance(k, dict))
        tb = a.data.get("threshold_breaches") or []
        if isinstance(tb, list):
            breaches += sum(1 for k in tb if isinstance(k, dict))
    return {"breaches": breaches, "total": total}


def _extract_gap(store: Store) -> dict:
    arts = store.artifacts.get("gap-assessment", [])
    fw_aliases = {
        "iso42001": "ISO-42001", "iso-42001": "ISO-42001", "ISO-42001": "ISO-42001",
        "nist": "NIST-AI-RMF", "nist-ai-rmf": "NIST-AI-RMF", "NIST-AI-RMF": "NIST-AI-RMF",
        "eu-ai-act": "EU-AI-Act", "EU-AI-Act": "EU-AI-Act",
    }
    by_fw: dict[str, list[float]] = {}
    for a in arts:
        fw = a.data.get("target_framework") or a.data.get("framework")
        summary = a.data.get("summary") or {}
        score = summary.get("coverage_score") if isinstance(summary, dict) else None
        if score is None:
            score = a.data.get("coverage_score")
        if isinstance(fw, str) and isinstance(score, (int, float)):
            normalized = fw_aliases.get(fw, fw)
            by_fw.setdefault(normalized, []).append(float(score))
    frameworks = []
    for fw in ("ISO-42001", "NIST-AI-RMF", "EU-AI-Act"):
        scores = by_fw.get(fw, [])
        pct = (sum(scores) / len(scores) * 100.0) if scores else 0.0
        frameworks.append({"label": fw, "pct": pct})
    return {"frameworks": frameworks}


def _extract_action_required(store: Store) -> dict:
    arts = store.artifacts.get("action-required", [])
    rows = []
    for a in arts[:50]:
        d = a.data
        rows.append({
            "title": d.get("title") or d.get("summary") or a.path.stem,
            "reason": d.get("reason") or d.get("tag") or "action-required-human",
        })
    return {"rows": rows}


# --------------------------------------------------------------------------
# Payload
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Extended plugin-keyed artifact loading for v2 bespoke renderers.
# v2 renderers read from store.artifacts[<plugin-key>]. The base Store loads a
# narrower set of ARTIFACT_DIRS for v0/v1 aggregate views. v2 augments the
# store by walking each plugin directory under base/ so bespoke panels can
# surface the latest artifact shape-for-shape. Absent directories remain empty.
# --------------------------------------------------------------------------

EXTENDED_PLUGIN_DIRS = (
    "framework-monitor",
    "applicability-checker",
    "ai-system-inventory-maintainer",
    "audit-log-generator",
    "post-market-monitoring",
    "robustness-evaluator",
    "bias-evaluator",
    "evidence-bundle-packager",
    "certification-readiness",
    "management-review-packager",
    "internal-audit-planner",
    "role-matrix-generator",
    "incident-reporting",
    "eu-conformity-assessor",
    "gpai-obligations-tracker",
    "human-oversight-designer",
    "supplier-vendor-assessor",
    "singapore-magf-assessor",
    "explainability-documenter",
    "system-event-logger",
    "genai-risk-register",
    "data-register-builder",
    "crosswalk-matrix-builder",
)


def _augment_store_for_v2(store: Store) -> None:
    """Load plugin-keyed directories that the base Store does not load."""
    for key in EXTENDED_PLUGIN_DIRS:
        if key in store.artifacts:
            continue
        store.artifacts[key] = list(_walk_json(store.base / key))


def _summarize_artifacts(store: Store) -> dict:
    """Compact per-plugin summary: latest artifact data and warning count."""
    out: dict[str, dict] = {}
    for key, arts in store.artifacts.items():
        if not arts:
            out[key] = {"count": 0, "warnings": 0, "latest": None}
            continue
        latest = arts[-1]
        warn_count = 0
        for a in arts:
            w = a.data.get("warnings")
            if isinstance(w, list):
                warn_count += len(w)
        out[key] = {
            "count": len(arts),
            "warnings": warn_count,
            "latest": latest.data,
        }
    return out


def _collect_citations(store: Store) -> list[dict]:
    """Flatten all citations across every loaded artifact for citation-search."""
    out: list[dict] = []
    seen: set[tuple] = set()
    for key, arts in store.artifacts.items():
        for a in arts:
            cits = a.data.get("citations")
            if not isinstance(cits, list):
                continue
            for c in cits:
                text = c if isinstance(c, str) else (c.get("text") or c.get("ref") if isinstance(c, dict) else None)
                if not isinstance(text, str) or not text:
                    continue
                sig = (key, text)
                if sig in seen:
                    continue
                seen.add(sig)
                out.append({"source": key, "text": text})
                if len(out) >= 2000:
                    return out
    return out


def build_payload(
    store: Store,
    *,
    generated_at: str,
    aigovops_root: Path | None,
) -> dict:
    _augment_store_for_v2(store)
    return {
        "generated_at": generated_at,
        "evidence_path": str(store.base),
        "has_any_artifacts": not store.is_empty(),
        "catalog": PANEL_CATALOGUE,
        "risk": _extract_risk(store),
        "soa": _extract_soa(store),
        "nonconformity": _extract_nonconformity(store),
        "kpi": _extract_kpi(store),
        "gap": _extract_gap(store),
        "action_required": _extract_action_required(store),
        "crosswalk": _extract_crosswalk(aigovops_root),
        "artifacts": _summarize_artifacts(store),
        "citations_index": _collect_citations(store),
    }


# --------------------------------------------------------------------------
# Vendor loading
# --------------------------------------------------------------------------


def _load_vendor(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise VendorMissingError(VENDOR_MISSING_MESSAGE)
    text = path.read_text(encoding="utf-8")
    if len(text) < 1000:
        raise VendorMissingError(
            VENDOR_MISSING_MESSAGE
            + f"\n(File {path} exists but is too small to be a real UMD bundle.)"
        )
    return text


def _sanitize_for_inline(js: str) -> str:
    return js.replace("</script", "<\\/script")


def _sanitize_json_for_inline(s: str) -> str:
    return s.replace("</", "<\\/")


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def render(
    store: Store,
    *,
    generated_at: str | None = None,
    aigovops_root: Path | None = None,
) -> str:
    now = generated_at or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    root = aigovops_root if aigovops_root is not None else DEFAULT_AIGOVOPS_ROOT
    payload = build_payload(store, generated_at=now, aigovops_root=root)
    react_umd = _sanitize_for_inline(_load_vendor(REACT_UMD_PATH))
    react_dom_umd = _sanitize_for_inline(_load_vendor(REACT_DOM_UMD_PATH))
    data_json = _sanitize_json_for_inline(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
    out = HTML_TEMPLATE.format(
        tailwind_css=TAILWIND_SUBSET_CSS,
        react_umd=react_umd,
        react_dom_umd=react_dom_umd,
        data_json=data_json,
        app_js=_sanitize_for_inline(APP_JS),
    )
    # Hard guard: no em-dashes in output.
    if "\u2014" in out:
        out = out.replace("\u2014", "--")
    return out


def generate(
    output_path: str | os.PathLike,
    evidence_path: str | os.PathLike | None = None,
    aigovops_root: str | os.PathLike | None = None,
) -> Path:
    base = resolve_evidence_path(evidence_path)
    store = Store.load(base)
    root = Path(aigovops_root).expanduser().resolve() if aigovops_root else None
    html_out = render(store, aigovops_root=root)
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_out, encoding="utf-8")
    return out
