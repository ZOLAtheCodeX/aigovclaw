# Workflow: role-matrix

**Status**: active. Phase 3 plugin integration complete.

**Primary frameworks**: ISO/IEC 42001:2023 Clause 5.3, Annex A Control A.3.2; NIST AI RMF 1.0 GOVERN 2.1.

**Output artifact**: Role and responsibility matrix (JSON dict + Markdown + CSV).

**Plugin consumer**: [plugins/role-matrix-generator](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/role-matrix-generator). Agent signature: `role-matrix-generator/0.1.0`.

## Objective

Produce and maintain the role and responsibility matrix for AI governance decisions. The matrix is a referenced input to SoA approval, AISIA sign-off, risk acceptance, nonconformity response, and every other workflow that requires a named authority per Clause 5.3. It is not an operational runbook; it is the authority register.

## Required inputs

Plugin signature: `generate_role_matrix(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `org_chart` | list of dicts | yes | Roles with reporting lines. |
| `role_assignments` | dict | yes | Explicit RACI mapping. |
| `authority_register` | dict | yes | Role to authority-basis reference. |
| `decision_categories` | list | no | Defaults to the standard 8. |
| `activities` | list | no | Defaults to propose / review / approve / consulted / informed. |
| `backup_assignments` | dict | no | Role to backup-role. |
| `reviewed_by` | string | no | |

See the plugin's [README](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/role-matrix-generator/README.md) for full schema.

## Steps

1. **Validate inputs** against schema. Structural problems abort; content gaps warn.
2. **Load the `iso42001` skill**; refuse `-stub` versions.
3. **Invoke the plugin**: `role_matrix_generator.plugin.generate_role_matrix(inputs)`.
4. **Render all three forms**: dict, Markdown, CSV.
5. **Persist** to `~/.hermes/memory/aigovclaw/role-matrix/<timestamp>/matrix.{json,md,csv}`.
6. **Surface flagged issues** for any row with `role_name == "REQUIRES HUMAN ASSIGNMENT"`, any warning about missing authority basis on an approve-activity row, or any warning about missing backup for an approval role. Each flagged item cites Clause 5.3 and names the unassigned slot.
7. **Emit an audit-log entry** via the audit-log workflow, citing Clause 5.3 and Annex A Control A.3.2.

## Quality gates

- Every decision category has exactly one approve-activity role.
- Every role with approval authority has an authority_basis reference.
- Every role with approval authority has a named backup.
- Matrix header cites both Clause 5.3 and A.3.2 (plus GOVERN 2.1 for NIST mode).
- Output contains no em-dashes, no emojis, no hedging.
- `agent_signature` matches the installed plugin version.

## Cadence and triggers

- **Schedule-based**: annual review at minimum; quarterly configurable.
- **Event-based**: significant organizational change (restructuring, executive succession, new AIMS scope boundary), new decision category introduced by an upstream workflow, framework update that adds or changes role-specific requirements.

Triggered re-runs compare against the prior matrix and surface deltas for authority-level approval per Clause 5.3.

## Integration points

- **Upstream**: organizational HRIS or directory system for `org_chart`; policy register for `authority_register`.
- **Downstream**: `risk-register-builder` (owner lookup), `soa-generator` (approver identification), `aisia-runner` (sign-off authority), `management-review-packager` (attendees and distribution list), `nonconformity-tracker` (corrective-action owners).

## Tests

Plugin carries 19 tests at [plugins/role-matrix-generator/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/role-matrix-generator/tests/test_plugin.py).
