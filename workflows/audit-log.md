# Workflow: audit-log

**Status**: active. Phase 3 plugin integration complete.

**Primary framework**: ISO/IEC 42001:2023

**Output artifact**: ISO 42001-compliant audit log entry (dict for JSON serialization plus Markdown rendering).

**Plugin consumer**: [plugins/audit-log-generator](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/audit-log-generator) from the AIGovOps catalogue. Agent signature embedded in every entry is `audit-log-generator/0.1.0`.

## Objective

Generate an audit log entry that documents an AI governance event in a form acceptable as audit evidence under ISO/IEC 42001:2023. The entry carries canonical clause and Annex A control citations, is timestamped in ISO 8601 UTC, names responsible parties, and lists the governance decisions made in the event with their citation anchors.

## Required inputs

The plugin's `generate_audit_log(system_description)` function requires a dict with:

| Field | Type | Required | Description |
|---|---|---|---|
| `system_name` | string | yes | Identifier of the AI system. |
| `purpose` | string | yes | Intended use and decision context. |
| `risk_tier` | string | yes | One of `minimal`, `limited`, `high`, `unacceptable`. |
| `data_processed` | list of strings | yes | Categories of data the system processes. |
| `deployment_context` | string | yes | Where and how the system is deployed. |
| `governance_decisions` | list of strings | yes | Decisions made in the governance event being logged. May be empty. |
| `responsible_parties` | list of strings | yes | Parties accountable for the decisions. May be empty. |

Missing or malformed inputs raise `ValueError`; the workflow surfaces the error to the review queue and does not emit a partial log.

## Steps

1. **Validate the input** against the schema above. If any required field is missing or malformed, abort the workflow and surface the validation error to the human review queue as a flagged-issue record.
2. **Load the `iso42001` skill** from the catalogue at `~/.hermes/skills/aigovops/iso42001/` (populated by the AIGovClaw installer). Validate the skill's version suffix is at `-draft` or a released version; refuse to generate against a `-stub` skill.
3. **Invoke the plugin** by calling `audit_log_generator.plugin.generate_audit_log(system_description)`. The plugin returns a structured dict with `timestamp`, `system_name`, `clause_mappings`, `annex_a_mappings`, `evidence_items`, `human_readable_summary`, and `agent_signature`.
4. **Render human-readable form** by calling `audit_log_generator.plugin.render_markdown(entry)`. The result is a Markdown document suitable for inclusion in an audit evidence package.
5. **Persist both renderings**:
   1. Write the dict to the audit log store as a JSON document at `~/.hermes/memory/aigovclaw/audit-log/<system_name>/<timestamp>.json`.
   2. Write the Markdown to the same directory at `<timestamp>.md`.
6. **Run the quality gate** defined in the next section. Do not declare the workflow done until the gate passes.
7. **Present the output to the user** with a summary of the clause mappings and Annex A control mappings, plus links to the JSON and Markdown files.
8. **Surface a flagged-issue record** if the entry references a risk-tier `high` AI system and the most recent AISIA for that system is older than the organizational re-assessment cadence. The flagged issue cites `ISO/IEC 42001:2023, Clause 6.1.4` and proposes the AISIA refresh workflow as the resolution step.

## Quality gates

All of the following must hold before the workflow is declared complete. Failures are surfaced to the review queue with the specific gate named.

- Every framework citation in the output uses the exact STYLE.md format: `ISO/IEC 42001:2023, Clause X.X.X` for main-body clauses and `ISO/IEC 42001:2023, Annex A, Control A.X.Y` for Annex A controls. The plugin's test suite enforces this at emission; the workflow re-verifies at persistence time.
- The output contains no em-dashes (U+2014), no emojis, and no hedging phrases. The plugin's test suite enforces this on generated strings; the workflow re-verifies on the full rendered Markdown.
- Every responsible party named in the input appears in the rendered output.
- The `timestamp` is within the last 60 seconds of workflow invocation (no stale emission).
- The JSON and Markdown files are byte-identical to each other in the structured fields they share (system_name, timestamp, clause and control citations).
- The `agent_signature` matches the installed plugin version. Version mismatches between the expected signature and the emitted signature are logged as a nonconformity against Clause 7.5.2 documented-information control.

## Output artifact specification

Two files per invocation, co-located under `~/.hermes/memory/aigovclaw/audit-log/<system_name>/`:

- `<timestamp>.json`: the dict returned by `generate_audit_log`. Suitable for ingestion into GRC tooling, long-term archival, and machine-readable cross-referencing from other workflows (for example, the management-review input package workflow pulls this file).
- `<timestamp>.md`: the Markdown rendering produced by `render_markdown`. Suitable for inclusion in audit evidence packages, email distribution, and human review.

Files are immutable once written. Corrections are new files referencing the prior timestamp; the correction relationship is logged as its own audit-log-entry citing `ISO/IEC 42001:2023, Clause 7.5.2`.

## Integration points

- **Upstream triggers.** The workflow is invoked by: the operational monitoring loop when it detects a governance-relevant event against an AI system; the management-review preparation workflow when assembling the Clause 9.3.2 input package; the framework-monitor workflow when an applicable framework update lands; direct human invocation via the Hermes agent interface.
- **Downstream consumers.** Emitted entries are read by: the management-review input package workflow (Clause 9.3.2); the nonconformity tracker when an entry references a triggering event; the risk register builder when an entry references a newly-identified risk. Consumers access entries by `system_name` and `timestamp` range.

## Tests

The underlying plugin carries 18 tests at [plugins/audit-log-generator/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/audit-log-generator/tests/test_plugin.py). The workflow itself will receive integration tests when the aigovclaw test harness is added in a later Phase 3 commit.
