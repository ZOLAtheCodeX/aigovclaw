# Workflow: risk-register

**Status**: active. Phase 3 plugin integration complete.

**Primary frameworks**: ISO/IEC 42001:2023 Clauses 6.1.2, 6.1.3, 8.2; NIST AI RMF 1.0 MAP 4.1, MANAGE 1.2, 1.3, 1.4.

**Output artifact**: AI risk register (JSON dict + Markdown + CSV renderings).

**Plugin consumer**: [plugins/risk-register-builder](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/risk-register-builder) from the AIGovOps catalogue. Agent signature: `risk-register-builder/0.1.0`.

## Objective

Produce and maintain a structured AI risk register with framework-mapped controls. Each register entry identifies a risk, its likelihood and impact, the affected AI system, the applicable controls, and the assigned owner. The register is the canonical risk-state artifact feeding SoA generation, AISIA, nonconformity triage, and management review.

## Required inputs

The plugin's `generate_risk_register(inputs)` function requires at minimum:

| Field | Type | Required | Description |
|---|---|---|---|
| `ai_system_inventory` | list | yes | AI systems in AIMS scope with `system_ref` and `system_name`. |
| `risks` | list | no but recommended | Identified risks with `system_ref`, `category`, `description`, and optional fields for scoring and treatment. |
| `framework` | string | no | `iso42001` (default), `nist`, or `dual`. |
| `risk_taxonomy` | list | no | Defaults per framework. |
| `risk_scoring_rubric` | dict | no | Defaults to 5-level qualitative. |
| `soa_rows` | list | no | Cross-link existing controls to the SoA. |
| `role_matrix_lookup` | dict | no | Category-to-default-owner mapping. |
| `scaffold` | bool | no | Emit coverage-gap placeholders. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs** against the schema. Structural issues abort the workflow; content gaps route to the review queue as warnings.
2. **Load** the `iso42001` skill (and `nist-ai-rmf` when framework is `nist` or `dual`). Refuse to run against skills at `-stub` version.
3. **Pull most recent SoA emission** from `~/.hermes/memory/aigovclaw/soa/` to provide `soa_rows` for existing-control cross-linking.
4. **Pull role matrix emission** from `~/.hermes/memory/aigovclaw/role-matrix/` to provide `role_matrix_lookup` when risks do not carry explicit `owner_role`.
5. **Invoke the plugin**: `risk_register_builder.plugin.generate_risk_register(inputs)`.
6. **Render all three forms**: `generate`, `render_markdown`, `render_csv`.
7. **Persist** to `~/.hermes/memory/aigovclaw/risk-register/<timestamp>.{json,md,csv}`.
8. **Surface flagged issues** for rows where residual_score is at or above the organizational high-risk threshold, rows where `treatment_option == "retain"` without a `negative_residual_disclosure_ref` (NIST mode), and rows missing required owner assignments.
9. **Emit an audit-log entry** for the register generation event via the audit-log workflow, citing Clauses 6.1.2 and 7.5.2.
10. **Trigger downstream workflows**: the SoA workflow should re-run when risk-register rows change materially so that existing-control inclusion is re-inferred.

## Quality gates

- Every risk has at least one control mapping with a valid citation.
- Every risk has an assigned owner (from explicit input or role_matrix_lookup).
- Every risk has inherent and residual scores computed from the supplied rubric.
- Register carries a re-assessment trigger definition (schedule-based, event-based, or both).
- Output contains no em-dashes, no emojis, no hedging phrases.
- `agent_signature` matches the installed plugin version.
- All citations match the STYLE.md format per framework.

## Re-assessment triggers

Per Clause 8.2, the risk register must be re-assessed at planned intervals or when significant changes occur. The workflow registers the following triggers by default:

- **Schedule-based**: quarterly (configurable per organizational policy).
- **Event-based**: on AI system scope change, on incident logged in the incident-log, on new AISIA emission, on framework update detected by the framework-monitor workflow.

Triggered re-runs load the prior register version as the baseline and surface deltas in the review queue for owner approval.

## Output artifact specification

Three files per invocation at `~/.hermes/memory/aigovclaw/risk-register/<timestamp>/`:

- `register.json`: the structured dict.
- `register.md`: sorted rows table, top-level citations, summary, coverage-gap list when scaffolded, warnings.
- `register.csv`: spreadsheet-ingestible form.

Files are immutable once written. Updates produce new timestamp directories; prior versions remain for audit trail.

## Integration points

- **Upstream.** `ai-system-inventory` workflow (when introduced) supplies the inventory. `aisia-runner` outputs feed candidate risks via `additional_controls_recommended` to be added to the register as treatments. `framework-monitor` issues trigger review of affected rows.
- **Downstream.** `soa-generator` consumes the register to infer included-implemented controls. `management-review-packager` consumes summary statistics and trend indicators as Clause 9.3.2 category input. `nonconformity-tracker` consumes risk rows when a nonconformity surfaces a previously-unregistered risk.

## Tests

The underlying plugin carries 27 tests at [plugins/risk-register-builder/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/risk-register-builder/tests/test_plugin.py).
