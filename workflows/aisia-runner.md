# Workflow: aisia-runner

**Status**: active. Phase 3 plugin integration complete.

**Primary frameworks**: ISO/IEC 42001:2023 Clause 6.1.4; NIST AI RMF 1.0 MAP 1.1, 3.1, 3.2, 5.1.

**Output artifact**: AI System Impact Assessment document (JSON dict + Markdown rendering).

**Plugin consumer**: [plugins/aisia-runner](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/aisia-runner) from the AIGovOps catalogue. Agent signature: `aisia-runner/0.1.0`.

## Objective

Execute an AI System Impact Assessment. Document impacts on affected individuals, groups, and society, classify each impact by severity and likelihood, identify existing controls, compute residual impact, and recommend additional controls where residual impact exceeds organizational tolerance. The AISIA is required under Clause 6.1.4 for every AI system in AIMS scope and must be reviewed when significant changes occur.

## Required inputs

The plugin's `run_aisia(inputs)` function requires at minimum:

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | Dict with `system_name`, `purpose`; optional `intended_use`, `decision_context`, `deployment_environment`, `data_categories_processed`, `decision_authority`, `reversibility`, `system_type`. |
| `affected_stakeholders` | list | yes | Non-empty list. Each entry is a string or a dict with `name` and optional `protected_attributes`, `size_estimate`. |
| `impact_assessments` | list | no but recommended | Provided impacts; one entry per (stakeholder, dimension) pair. Empty list produces a register-level warning. |
| `impact_dimensions` | list | no | Dimensions to assess. Default: `fundamental-rights, group-fairness, societal, physical-safety`. |
| `risk_scoring_rubric` | dict | no | With `severity_scale` and `likelihood_scale`. Default: 5-level qualitative. |
| `soa_rows` | list | no | For cross-linking existing controls to the SoA. Pulled from the most recent SoA emission for this scope. |
| `framework` | string | no | `iso42001` (default), `nist`, or `dual`. |
| `scaffold` | bool | no | Default True for first-run AISIAs; False when refreshing. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs** against the schema. If `affected_stakeholders` is empty or `system_description` lacks `system_name` or `purpose`, abort and surface to the review queue.
2. **Load the `iso42001` skill** (and optionally `nist-ai-rmf` when `framework` is `nist` or `dual`) from the catalogue. Refuse to generate against any skill at `-stub` version.
3. **Pull most recent SoA** for the system's scope from `~/.hermes/memory/aigovclaw/soa/`. If present, pass `soa_rows` into the plugin for cross-linking. If absent, proceed without SoA linking and surface a review-queue note that the SoA should be regenerated after the AISIA lands.
4. **Invoke the plugin**: `aisia_runner.plugin.run_aisia(inputs)`. Returns a structured AISIA dict.
5. **Render human-readable form**: `aisia_runner.plugin.render_markdown(aisia)`.
6. **Persist both renderings** to `~/.hermes/memory/aigovclaw/aisia/<system_name>/<timestamp>.{json,md}`.
7. **Surface to the review queue** with the accountable party named (AI system owner or delegated DPO / AI Ethics Officer per Clause 5.3 role matrix). AISIA sign-off is human-required; the agent does not finalize.
8. **Emit an audit-log entry** for the AISIA event via the audit-log workflow, citing `Clause 6.1.4` and the AISIA document reference.
9. **Open flagged-issue records** for every section with severity `catastrophic` or `major` and residual severity at or above `major` after existing controls. These are high-residual-risk items that warrant immediate attention outside the normal review cadence.
10. **Trigger the risk-register workflow** with any `additional_controls_recommended` from the AISIA output, so recommended controls land in the risk register as candidate treatments.

## Quality gates

All of the following must hold before the workflow is declared complete:

- Every stakeholder group identified in `affected_stakeholders` has at least one section covering at least one dimension (zero-coverage stakeholders surface a warning).
- Every section has `severity` and `likelihood` from the supplied rubric; missing values surface as section warnings, not silent.
- Every section lists at least one control (existing or recommended); zero-control sections surface a warning.
- Physical-safety sections have severity at or above `moderate` unless the system_description explicitly documents no physical-harm potential. The plugin enforces the floor as a warning; the workflow treats it as a blocker for sign-off.
- Every section carries the required framework citations per the `framework` setting.
- Output contains no em-dashes (U+2014), no emojis, no hedging phrases.
- `agent_signature` matches the installed plugin version.

## Output artifact specification

Two files per invocation at `~/.hermes/memory/aigovclaw/aisia/<system_name>/`:

- `<timestamp>.json`: the dict returned by `run_aisia`. Machine-readable; referenced by the risk register builder, the SoA generator, and the management-review input package workflow.
- `<timestamp>.md`: the Markdown rendering. Audit-evidence format; distributed to the AISIA sign-off authority and retained per Clause 7.5.3.

Files are immutable once written. Refresh triggers (significant change, scheduled cadence) produce new files with new timestamps; prior versions remain for audit trail.

## Integration points

- **Upstream triggers.** Significant-change events against an AI system; scheduled cadence (typically annual per AIMS policy); new deployment; regulatory change affecting applicability.
- **Downstream consumers.** SoA generator uses the AISIA outputs as input to Annex A A.5 control inclusion rationale. Risk register builder consumes `additional_controls_recommended` as candidate risk treatments. Management review input package references the AISIA as AIMS-performance evidence per Clause 9.3.2.

## Tests

The underlying plugin carries 23 tests at [plugins/aisia-runner/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/aisia-runner/tests/test_plugin.py). Integration tests for the full workflow land when the aigovclaw test harness is added.
