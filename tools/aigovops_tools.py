"""
AIGovOps Plugin Tool Definitions

Every AIGovOps plugin registered with the AIGovClaw harness. Each
definition declares:

- The tool name the harness exposes to the model.
- The plugin directory and function to invoke.
- The input schema the harness validates against.
- Safety properties per the harness paradigm (all AIGovOps plugins are
  read-only, concurrency-safe, non-destructive; see module-level
  rationale below).
- The source SKILL.md the tool derives from.
- The artifact_type the tool produces, enabling adapter routing.

Persistence of plugin outputs to the aigovclaw memory filesystem is the
responsibility of the workflow layer (aigovclaw/workflows/*.md), not of
the plugin itself. Adapters push to external destinations. Plugins stay
pure: in, out, no side effects. This separation is the reason all tools
here are classified is_read_only=True.

Loading: the register_aigovops_tools(plugins_path) function is the
import-time hook the Hermes harness (or install.sh post-install) calls to
populate the REGISTRY singleton from registry.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .registry import REGISTRY, Tool


def _load_plugin_module(plugin_name: str, plugins_path: Path):
    """Load plugin.py from plugins/<plugin_name>/plugin.py by path.

    Loads via importlib.util to avoid sys.path manipulation and to handle
    the hyphenated directory names correctly."""
    plugin_file = plugins_path / plugin_name / "plugin.py"
    if not plugin_file.is_file():
        raise FileNotFoundError(f"plugin file not found: {plugin_file}")
    spec = importlib.util.spec_from_file_location(
        f"aigovops_plugin_{plugin_name.replace('-', '_')}",
        plugin_file,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {plugin_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Every AIGovOps plugin exposed as a Hermes tool. The harness reads this
# list at startup and registers each entry.
PLUGIN_TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "generate_audit_log",
        "plugin": "audit-log-generator",
        "function": "generate_audit_log",
        "description": (
            "Generate an ISO 42001 audit log entry for an AI governance event. "
            "Cites Clause 7.5.2 documented information and Clause 9.1 monitoring."
        ),
        "input_schema": {
            "system_name": {"type": "string", "required": True, "description": "AI system identifier."},
            "purpose": {"type": "string", "required": True, "description": "Intended use and decision context."},
            "risk_tier": {
                "type": "string", "required": True,
                "enum": ["minimal", "limited", "high", "unacceptable"],
                "description": "Risk tier classification.",
            },
            "data_processed": {"type": "list", "required": True, "description": "Categories of data processed."},
            "deployment_context": {"type": "string", "required": True, "description": "Where and how deployed."},
            "governance_decisions": {"type": "list", "required": True, "description": "Decisions made in this event."},
            "responsible_parties": {"type": "list", "required": True, "description": "Accountable parties."},
        },
        "source_skill": "iso42001",
        "artifact_type": "audit-log-entry",
    },
    {
        "name": "generate_role_matrix",
        "plugin": "role-matrix-generator",
        "function": "generate_role_matrix",
        "description": (
            "Generate an ISO 42001 Clause 5.3 role and responsibility matrix. "
            "Validates an explicit RACI; refuses to invent role assignments."
        ),
        "input_schema": {
            "org_chart": {"type": "list", "required": True, "description": "Roles with reporting lines."},
            "role_assignments": {"type": "dict", "required": True, "description": "Explicit RACI mapping."},
            "authority_register": {"type": "dict", "required": True, "description": "Role to authority-basis."},
            "decision_categories": {"type": "list", "required": False},
            "activities": {"type": "list", "required": False},
            "backup_assignments": {"type": "dict", "required": False},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "iso42001",
        "artifact_type": "role-matrix",
    },
    {
        "name": "generate_risk_register",
        "plugin": "risk-register-builder",
        "function": "generate_risk_register",
        "description": (
            "Generate an ISO 42001 Clause 6.1.2 or NIST AI RMF risk register. "
            "Validates provided risks; does not invent them. Supports dual-framework citations."
        ),
        "input_schema": {
            "ai_system_inventory": {"type": "list", "required": True, "description": "AI systems in scope."},
            "risks": {"type": "list", "required": False, "description": "Identified risks; plugin warns if empty."},
            "framework": {
                "type": "string", "required": False,
                "enum": ["iso42001", "nist", "dual"],
                "description": "Citation rendering mode.",
            },
            "risk_taxonomy": {"type": "list", "required": False},
            "risk_scoring_rubric": {"type": "dict", "required": False},
            "soa_rows": {"type": "list", "required": False},
            "role_matrix_lookup": {"type": "dict", "required": False},
            "scaffold": {"type": "bool", "required": False},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "iso42001",
        "artifact_type": "risk-register",
    },
    {
        "name": "generate_soa",
        "plugin": "soa-generator",
        "function": "generate_soa",
        "description": (
            "Generate an ISO 42001 Clause 6.1.3 Statement of Applicability. "
            "Infers coverage from the risk register; accepts exclusion justifications."
        ),
        "input_schema": {
            "ai_system_inventory": {"type": "list", "required": True},
            "risk_register": {"type": "list", "required": False, "description": "Rows from risk-register-builder."},
            "annex_a_controls": {"type": "list", "required": False},
            "implementation_plans": {"type": "dict", "required": False},
            "exclusion_justifications": {"type": "dict", "required": False},
            "scope_notes": {"type": "dict", "required": False},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "iso42001",
        "artifact_type": "soa",
    },
    {
        "name": "run_aisia",
        "plugin": "aisia-runner",
        "function": "run_aisia",
        "description": (
            "Execute an ISO 42001 Clause 6.1.4 AISIA or an EU AI Act Article 27 FRIA. "
            "Validates impact assessments; enforces physical-safety severity floor."
        ),
        "input_schema": {
            "system_description": {"type": "dict", "required": True, "description": "System info including system_name and purpose."},
            "affected_stakeholders": {"type": "list", "required": True},
            "impact_assessments": {"type": "list", "required": False},
            "impact_dimensions": {"type": "list", "required": False},
            "risk_scoring_rubric": {"type": "dict", "required": False},
            "soa_rows": {"type": "list", "required": False},
            "framework": {
                "type": "string", "required": False,
                "enum": ["iso42001", "nist", "dual", "eu-ai-act"],
            },
            "scaffold": {"type": "bool", "required": False},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "iso42001",
        "artifact_type": "aisia",
    },
    {
        "name": "generate_nonconformity_register",
        "plugin": "nonconformity-tracker",
        "function": "generate_nonconformity_register",
        "description": (
            "Validate and enrich ISO 42001 Clause 10.2 nonconformity records. "
            "Enforces per-state invariants; emits audit-log hooks for state transitions."
        ),
        "input_schema": {
            "records": {"type": "list", "required": True, "description": "Nonconformity records with required lifecycle fields."},
            "framework": {"type": "string", "required": False, "enum": ["iso42001", "nist", "dual"]},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "iso42001",
        "artifact_type": "nonconformity-register",
    },
    {
        "name": "generate_review_package",
        "plugin": "management-review-packager",
        "function": "generate_review_package",
        "description": (
            "Assemble the ISO 42001 Clause 9.3.2 management review input package. "
            "Aggregates source-of-record references across all nine required categories."
        ),
        "input_schema": {
            "review_window": {"type": "dict", "required": True, "description": "Dict with 'start' and 'end' ISO dates."},
            "attendees": {"type": "list", "required": True},
            "previous_review_actions": {"type": "any", "required": False},
            "external_internal_issues_changes": {"type": "any", "required": False},
            "aims_performance": {"type": "any", "required": False},
            "audit_results": {"type": "any", "required": False},
            "nonconformity_trends": {"type": "any", "required": False},
            "objective_fulfillment": {"type": "any", "required": False},
            "stakeholder_feedback": {"type": "any", "required": False},
            "ai_risks_and_opportunities": {"type": "any", "required": False},
            "continual_improvement_opportunities": {"type": "any", "required": False},
            "meeting_metadata": {"type": "dict", "required": False},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "iso42001",
        "artifact_type": "review-package",
    },
    {
        "name": "generate_metrics_report",
        "plugin": "metrics-collector",
        "function": "generate_metrics_report",
        "description": (
            "Aggregate and validate NIST AI RMF MEASURE 2.x trustworthy-AI metrics. "
            "Supports AI 600-1 overlay and threshold-breach routing. Does not compute metrics."
        ),
        "input_schema": {
            "ai_system_inventory": {"type": "list", "required": True},
            "measurements": {"type": "list", "required": True, "description": "Precomputed measurements from MLOps telemetry."},
            "metric_catalog": {"type": "dict", "required": False},
            "thresholds": {"type": "dict", "required": False},
            "genai_overlay_enabled": {"type": "bool", "required": False},
            "framework": {"type": "string", "required": False, "enum": ["iso42001", "nist", "dual"]},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "nist-ai-rmf",
        "artifact_type": "metrics-report",
    },
    {
        "name": "generate_data_register",
        "plugin": "data-register-builder",
        "function": "generate_data_register",
        "description": (
            "Generate an ISO 42001 Annex A A.7 / EU AI Act Article 10 AI data register. "
            "Validates provided dataset entries; does not discover or profile data."
        ),
        "input_schema": {
            "data_inventory": {"type": "list", "required": True, "description": "Dataset entries with required id, name, purpose_stage, source."},
            "ai_system_inventory": {"type": "list", "required": False},
            "retention_policy": {"type": "dict", "required": False},
            "role_matrix_lookup": {"type": "dict", "required": False},
            "framework": {"type": "string", "required": False, "enum": ["iso42001", "eu-ai-act", "dual"]},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "iso42001",
        "artifact_type": "data-register",
    },
    {
        "name": "check_applicability",
        "plugin": "applicability-checker",
        "function": "check_applicability",
        "description": (
            "Report EU AI Act provision applicability for a system at a target date. "
            "Uses skills/eu-ai-act/enforcement-timeline.yaml and delegated-acts.yaml as data."
        ),
        "input_schema": {
            "system_description": {"type": "dict", "required": True, "description": "Includes is_high_risk, is_gpai, optional is_annex_i_product."},
            "target_date": {"type": "string", "required": True, "description": "ISO 8601 date."},
            "enforcement_timeline": {"type": "dict", "required": True, "description": "Loaded YAML from skills/eu-ai-act/enforcement-timeline.yaml."},
            "delegated_acts": {"type": "dict", "required": False, "description": "Loaded YAML from skills/eu-ai-act/delegated-acts.yaml."},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "eu-ai-act",
        "artifact_type": "applicability-report",
    },
    {
        "name": "classify_risk_tier",
        "plugin": "high-risk-classifier",
        "function": "classify",
        "description": (
            "Classify an AI system under EU AI Act risk tiers. "
            "Screens for Article 5 prohibited practices and Annex III high-risk categories. "
            "Flags legal-review cases rather than auto-deciding."
        ),
        "input_schema": {
            "system_description": {"type": "dict", "required": True, "description": "Required: system_name, intended_use, sector."},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "eu-ai-act",
        "artifact_type": "risk-tier-classification",
    },
    {
        "name": "generate_gap_assessment",
        "plugin": "gap-assessment",
        "function": "generate_gap_assessment",
        "description": (
            "Produce a gap assessment against a target framework (iso42001, nist, eu-ai-act). "
            "Classifies every control as covered, partially-covered, not-covered, or not-applicable."
        ),
        "input_schema": {
            "ai_system_inventory": {"type": "list", "required": True},
            "target_framework": {
                "type": "string", "required": True,
                "enum": ["iso42001", "nist", "eu-ai-act"],
            },
            "targets": {"type": "list", "required": False, "description": "Required for nist and eu-ai-act; optional for iso42001."},
            "soa_rows": {"type": "list", "required": False},
            "current_state_evidence": {"type": "dict", "required": False},
            "manual_classifications": {"type": "dict", "required": False},
            "exclusion_justifications": {"type": "dict", "required": False},
            "scope_boundary": {"type": "string", "required": False},
            "reviewed_by": {"type": "string", "required": False},
        },
        "source_skill": "iso42001",
        "artifact_type": "gap-assessment",
    },
]


def register_aigovops_tools(plugins_path: Path | str) -> list[str]:
    """Register every AIGovOps plugin as a Tool in the global REGISTRY.

    Args:
        plugins_path: filesystem path to the aigovops plugins/ directory.
                      In a Hermes-installed workspace, this is typically
                      ~/.hermes/skills/aigovops/plugins or a symlink.

    Returns:
        List of registered tool names.

    Raises:
        FileNotFoundError: if the plugins directory does not exist.
        ImportError: if a plugin module fails to load.
    """
    plugins_path = Path(plugins_path)
    if not plugins_path.is_dir():
        raise FileNotFoundError(f"plugins directory not found: {plugins_path}")

    registered: list[str] = []
    for definition in PLUGIN_TOOL_DEFS:
        module = _load_plugin_module(definition["plugin"], plugins_path)
        handler_name = definition["function"]
        if not hasattr(module, handler_name):
            raise ImportError(
                f"plugin {definition['plugin']!r} module does not expose "
                f"function {handler_name!r}; check the plugin's public API"
            )
        handler = getattr(module, handler_name)
        tool = Tool(
            name=definition["name"],
            description=definition["description"],
            handler=handler,
            input_schema=definition["input_schema"],
            is_read_only=True,
            is_concurrency_safe=True,
            is_destructive=False,
            source_skill=definition.get("source_skill"),
            artifact_type=definition.get("artifact_type"),
        )
        REGISTRY.register(tool)
        registered.append(tool.name)

    return registered


def unregister_all() -> None:
    """Clear the global registry. Test-only."""
    REGISTRY.clear()
