# Workflow: gap-assessment

**Status**: active. Phase 3 plugin integration complete.

**Primary frameworks**: ISO/IEC 42001:2023 Clauses 6.1.2 and 6.1.3; NIST AI RMF 1.0 MAP 4.1 and MANAGE 1.2; EU AI Act Article 9 (risk management for high-risk systems).

**Output artifact**: Structured gap assessment (JSON dict + Markdown + CSV) with per-target classification, justification, and next-step recommendation. Coverage score included as a dashboard indicator.

**Plugin consumer**: [plugins/gap-assessment](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/gap-assessment). Agent signature: `gap-assessment/0.1.0`.

## Objective

Assess the organization's current AIMS state against a target framework and produce a structured gap report. Each control or subcategory is classified as covered, partially-covered, not-covered, or not-applicable, with a supporting justification and a recommended next step grounded in the organization's evidence.

Unlike the SoA (which records inclusion decisions and implementation status for the purpose of audit submission), the gap assessment is a management-facing artifact for planning. It surfaces the implementation backlog; the SoA records what has been implemented.

## Required inputs

Plugin signature: `generate_gap_assessment(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `ai_system_inventory` | list | yes | AI systems in AIMS scope. |
| `target_framework` | string | yes | `iso42001`, `nist`, or `eu-ai-act`. |
| `targets` | list | required for nist and eu-ai-act; optional for iso42001 | Subcategory or article list. |
| `soa_rows` | list | no | From `soa-generator`; used for iso42001 coverage inference. |
| `current_state_evidence` | dict | no | Evidence references per target. |
| `manual_classifications` | dict | no | Organizational overrides. |
| `exclusion_justifications` | dict | no | Justifications for not-applicable classifications. |
| `scope_boundary` | string | no | AIMS scope description. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs**. Invalid framework, invalid classification, or missing `targets` for nist/eu-ai-act raises before processing.
2. **Load the skill** matching `target_framework`. Refuse `-stub` versions.
3. **Pull most recent SoA emission** from `~/.hermes/memory/aigovclaw/soa/` when `target_framework=='iso42001'` and `soa_rows` is not supplied inline.
4. **Pull skill-default target list** when the caller did not supply `targets` and the framework has no embedded default. For NIST, read the subcategory list from the loaded `nist-ai-rmf` skill; for EU AI Act, read from the `eu-ai-act` skill's operationalization map.
5. **Invoke the plugin**: `gap_assessment.plugin.generate_gap_assessment(inputs)`.
6. **Render all three forms**: JSON dict, Markdown, CSV.
7. **Persist** to `~/.hermes/memory/aigovclaw/gap-assessment/<timestamp>/assessment.{json,md,csv}`.
8. **Surface flagged issues** for every row with `REQUIRES REVIEWER DECISION` (both `classification=not-covered` with the decision marker); unknown-target register warnings; blank manual-classification or exclusion justifications.
9. **Emit an audit-log entry** citing `ISO/IEC 42001:2023, Clause 6.1.2` (for iso42001) or the relevant framework clause.
10. **Trigger downstream workflows**:
    1. Rows with `classification=not-covered` and no existing implementation plan route to the `risk-register` workflow as candidate risks with category `compliance-gap`.
    2. The coverage score feeds the `management-review-packager` workflow as a Clause 9.3.2 `aims_performance` category input with `trend_direction` derived by comparing against the prior assessment.

## Quality gates

- Every target has a classification from one of the four valid values.
- Every `not-applicable` row has a non-blank justification.
- Every `covered` or `partially-covered` row has either an SoA row reference, an evidence reference, or a manual classification with justification.
- Output contains no em-dashes, emojis, or hedging.
- `agent_signature` matches the installed plugin version.

## Cadence and triggers

- **Schedule-based**: quarterly by default. Management review cycles typically request a fresh gap assessment as an input.
- **Event-based**: SoA emission (triggers iso42001 gap re-assessment against the updated SoA); framework update detected by `framework-monitor`; significant scope change.

## Integration points

- **Upstream**: `soa-generator` (iso42001 coverage), skill registry (target enumeration), organizational evidence registers (current state).
- **Downstream**: `risk-register` (compliance-gap candidate risks), `management-review-packager` (coverage score and trend as AIMS performance signal), implementation planning (not-covered rows become backlog items).

## Tests

Plugin carries 23 tests at [plugins/gap-assessment/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/gap-assessment/tests/test_plugin.py).
