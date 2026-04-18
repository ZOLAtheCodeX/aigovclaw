# Workflow: soa

**Status**: active. Phase 3 plugin integration complete.

**Primary framework**: ISO/IEC 42001:2023 Clause 6.1.3.

**Output artifact**: Statement of Applicability (JSON dict + Markdown + CSV).

**Plugin consumer**: [plugins/soa-generator](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/soa-generator). Agent signature: `soa-generator/0.1.0`.

## Objective

Produce the Statement of Applicability: the certification-audit centerpiece that records, for every Annex A control, whether the control is included or excluded from the AIMS with justification grounded in organizational context, the risk register, and the implementation posture. The SoA is the single most-scrutinized artifact at ISO 42001 certification audit.

## Required inputs

Plugin signature: `generate_soa(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `ai_system_inventory` | list | yes | AI systems in AIMS scope. |
| `risk_register` | list | no | From `risk-register-builder`. Rows' `existing_controls` references infer control inclusion. |
| `annex_a_controls` | list | no | Defaults to embedded 38-control list. |
| `implementation_plans` | dict | no | Maps control_id to plan metadata. |
| `exclusion_justifications` | dict | no | Maps control_id to exclusion text. |
| `scope_notes` | dict | no | Maps control_id to subset-of-systems scope. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs**.
2. **Load the `iso42001` skill**.
3. **Pull most recent risk register emission** from `~/.hermes/memory/aigovclaw/risk-register/` so that existing-control inclusion is inferred from current risk state.
4. **Invoke the plugin**: `soa_generator.plugin.generate_soa(inputs)`.
5. **Render all three forms**.
6. **Persist** to `~/.hermes/memory/aigovclaw/soa/<timestamp>/soa.{json,md,csv}`.
7. **Surface flagged issues** for every row with a `REQUIRES REVIEWER DECISION` justification, every excluded row with a blank justification, every planned or partial row without a `target_date`, and every unknown-control cross-check warning.
8. **Emit an audit-log entry** citing Clause 6.1.3 and Clause 7.5.2.

## Quality gates

- Every Annex A control appears in the SoA; no silent omissions.
- Every included control has implementation status recorded (`included-implemented`, `included-partial`, or `included-planned`).
- Every excluded control has justification grounded in organizational or scope evidence, not placeholder text.
- Every partial or planned status references an implementation plan with a target date.
- SoA is dated and references the approving authority per the role matrix (see the role-matrix workflow; SoA approval requires a named approver).
- `agent_signature` matches the installed plugin version.
- No em-dashes, emojis, or hedging.

## Re-run triggers

The SoA is re-generated on:

- **Risk register emission**: any material change in the risk register triggers a fresh SoA so existing-control inclusion stays consistent with current risk state.
- **Annex A update**: if the `framework-monitor` workflow detects an ISO 42001 revision affecting Annex A, the SoA re-runs and surfaces new or changed controls to the review queue.
- **Scope change**: when the AIMS scope (Clause 4.3) changes.
- **Scheduled cadence**: at minimum annually.

## Human approval gate

The SoA is a documented organizational decision. The plugin produces a draft with every row's status populated; the reviewer named in the role matrix approves it explicitly. The agent does not finalize the SoA. Approval events are logged as audit-log entries citing Clause 6.1.3.

## Integration points

- **Upstream**: `risk-register` workflow supplies existing-control inferences; organizational context provides exclusion justifications and implementation plans.
- **Downstream**: `aisia-runner` uses SoA row references to cross-link existing controls to impact mitigations; `management-review-packager` references the SoA under Clause 9.3.2 AIMS-performance inputs.

## Tests

Plugin carries 22 tests at [plugins/soa-generator/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/soa-generator/tests/test_plugin.py).
