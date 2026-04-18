# Workflow: data-register

**Status**: active. Phase 3 plugin integration complete.

**Primary frameworks**: ISO/IEC 42001:2023 Annex A Controls A.7.2 through A.7.6; EU AI Act Article 10.

**Output artifact**: AI data register (JSON + Markdown + CSV).

**Plugin consumer**: [plugins/data-register-builder](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/data-register-builder). Agent signature: `data-register-builder/0.1.0`.

## Objective

Produce and maintain the AI data register covering every dataset used by AI systems in AIMS scope: training, validation, testing, inference, reference, and benchmark datasets. For each dataset, record purpose stage, source, acquisition method, provenance chain, quality checks, representativeness, bias assessment, data preparation steps, protected attributes, retention expiry, and owner.

The data register is the authoritative evidence package for ISO 42001 Annex A A.7 (data controls) and EU AI Act Article 10 (data governance for high-risk AI systems).

## Required inputs

Plugin signature: `generate_data_register(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `data_inventory` | list | yes | Dataset entries with id, name, purpose_stage, source and optional profiling fields. |
| `ai_system_inventory` | list | no | Used for high-risk determination. |
| `retention_policy` | dict | no | Maps data_category to retention_days. |
| `role_matrix_lookup` | dict | no | Data-governance role default. |
| `framework` | string | no | `iso42001`, `eu-ai-act`, `dual`. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs**. Invalid purpose_stage or source raises before processing.
2. **Load skills** (`iso42001`, plus `eu-ai-act` for eu-ai-act or dual mode).
3. **Pull role matrix emission** from `~/.hermes/memory/aigovclaw/role-matrix/` to provide `role_matrix_lookup` when not supplied inline.
4. **Pull AI system inventory** from the organization's system-of-record.
5. **Invoke the plugin**: `data_register_builder.plugin.generate_data_register(inputs)`.
6. **Render all three forms**: JSON, Markdown, CSV.
7. **Persist** to `~/.hermes/memory/aigovclaw/data-register/<timestamp>/register.{json,md,csv}`.
8. **Surface flagged issues**: every row with warnings routes to the review queue with the warning text; high-risk training data without bias_assessment is a high-priority flagged issue.
9. **Emit audit-log entry** citing A.7.2 (iso42001) and Article 10, Paragraph 1 (eu-ai-act).
10. **Downstream routing**: datasets nearing retention_expiry_date route to the nonconformity-tracker if no retention-plan action exists.

## Quality gates

- Every dataset has at least id, name, purpose_stage, source.
- Every training dataset for a high-risk system has bias_assessment (Article 10(5)).
- Every training/validation/testing dataset has quality_checks covering all five dimensions (Article 10(3), A.7.4).
- Every dataset has provenance_chain (A.7.5).
- Every dataset has an owner_role.
- Retention policy applied where configured.
- Output contains no em-dashes, emojis, or hedging.

## Cadence and triggers

- **Schedule-based**: quarterly by default.
- **Event-based**: new AI system onboarding (triggers data-register update for the system's datasets); new data source adoption; data schema change; framework update affecting A.7 or Article 10.

## Integration points

- **Upstream**: data engineering pipelines (dataset profiling), role-matrix-generator (owner defaults), ai-system-inventory workflow.
- **Downstream**: audit-log-generator (data lifecycle events), risk-register-builder (data-quality risks become register entries), aisia-runner (datasets inform AISIA context), nonconformity-tracker (retention breaches become nonconformities).

## Tests

Plugin carries 25 tests at [plugins/data-register-builder/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/data-register-builder/tests/test_plugin.py).
