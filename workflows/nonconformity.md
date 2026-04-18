# Workflow: nonconformity

**Status**: active. Phase 3 plugin integration complete.

**Primary frameworks**: ISO/IEC 42001:2023 Clauses 10.2, 7.5.2; NIST AI RMF 1.0 MANAGE 4.2.

**Output artifact**: Nonconformity and corrective-action register (JSON dict + Markdown) plus audit-log hooks for every state transition.

**Plugin consumer**: [plugins/nonconformity-tracker](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/nonconformity-tracker). Agent signature: `nonconformity-tracker/0.1.0`.

## Objective

Track AI governance nonconformities through the full Clause 10.2 corrective-action lifecycle. Validate that every record's current state has the required fields (root cause, corrective actions, effectiveness review). Emit an audit-log entry for every state transition per Clause 7.5.2 so the corrective-action history is itself auditable.

## Required inputs

Plugin signature: `generate_nonconformity_register(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `records` | list of dicts | yes | Each record has `description`, `source_citation`, `detected_by`, `detection_date`, `status` and optional lifecycle fields. |
| `framework` | string | no | `iso42001` (default), `nist`, `dual`. |
| `reviewed_by` | string | no | |

See [plugin README](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/nonconformity-tracker/README.md) for full record schema.

## Workflow states

`detected` → `investigated` → `root-cause-identified` → `corrective-action-planned` → `corrective-action-in-progress` → `corrective-action-complete` → `effectiveness-reviewed` → `closed`.

Closure with `effectiveness_outcome: ineffective` is a Clause 10.2 violation. The plugin surfaces this as a warning; the workflow treats it as a blocker for closure and surfaces a flagged-issue record requiring reopening at `investigated` or `root-cause-identified`.

## Steps

1. **Validate inputs**. Invalid `status` or missing required fields raise before any state transition is processed.
2. **Load the `iso42001` skill** (plus `nist-ai-rmf` for NIST or dual mode).
3. **Invoke the plugin**: `nonconformity_tracker.plugin.generate_nonconformity_register(inputs)`.
4. **Route inferred audit_log_events** to the audit-log workflow so every state transition lands as a documented-information record citing Clause 7.5.2. This is the most important integration in this workflow: the corrective-action history is itself evidence.
5. **Persist the register** to `~/.hermes/memory/aigovclaw/nonconformity/<timestamp>/register.{json,md}`.
6. **Surface flagged issues** for: open records past their corrective-action target date; closed records with `effectiveness_outcome: ineffective` (requires reopen); records missing Clause 10.2 required fields at their current state.
7. **Trigger the risk-register workflow** when a closed record's `risk_register_updates` references risks that need creation or modification.

## Quality gates

- Every record's current state has its required fields populated per the plugin's per-state invariant rules.
- Every `state_history` entry produces exactly one `audit_log_events` entry (no skipped transitions in the audit trail).
- Every closure has a named `effectiveness_reviewer` and a non-empty `effectiveness_outcome`.
- No closure with `effectiveness_outcome: ineffective`.
- Output contains no em-dashes, emojis, or hedging.

## Cadence and triggers

- **Event-based**: nonconformity detection (from monitoring, audit, stakeholder feedback, incident); corrective-action milestone (transition, completion, effectiveness review).
- **Schedule-based**: weekly rollup surfacing open records and past-due actions to the review queue.

## Integration points

- **Upstream**: `audit-log` workflow surfaces governance events that may indicate nonconformities; `risk-register` workflow surfaces retained-risk thresholds breached; `aisia-runner` flags high-residual sections; operational monitoring detects KPI breaches.
- **Downstream**: `audit-log` receives the inferred state-transition entries; `risk-register` receives risk-register updates at closure; `management-review-packager` consumes the register under Clause 9.3.2 nonconformity-trends category.

## Tests

Plugin carries 21 tests at [plugins/nonconformity-tracker/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/nonconformity-tracker/tests/test_plugin.py).
