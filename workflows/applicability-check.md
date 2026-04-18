# Workflow: applicability-check

**Status**: active. Phase 3 plugin integration complete.

**Primary framework**: EU AI Act (Regulation (EU) 2024/1689), Articles 5, 6, 9-15, 16-29, 50, 51-55, 72-73, and 113 (entry into force).

**Output artifact**: EU AI Act applicability report (JSON + Markdown).

**Plugin consumer**: [plugins/applicability-checker](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/applicability-checker). Agent signature: `applicability-checker/0.1.0`.

## Objective

Given a system description and a target date, produce a report naming which EU AI Act provisions apply to the system on that date, which are pending with dates, which delegated acts and codes of practice are relevant, and which organizational actions are due.

The workflow serves two audiences:

1. **Compliance officers planning forward**: "What do we need to prepare for by 2 August 2026 for this high-risk system?"
2. **Operations teams checking current state**: "What obligations does this GPAI model face today?"

## Required inputs

Plugin signature: `check_applicability(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | Includes `is_high_risk`, `is_gpai`, optional `is_systemic_risk_gpai`, `is_annex_i_product`, `placed_on_market_before`, `system_name`. |
| `target_date` | string | yes | ISO 8601 date. |
| `enforcement_timeline` | dict | yes | Loaded YAML from `skills/eu-ai-act/enforcement-timeline.yaml`. |
| `delegated_acts` | dict | no | Loaded YAML from `skills/eu-ai-act/delegated-acts.yaml`. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs**. Invalid target_date or missing enforcement_timeline raises.
2. **Load the `eu-ai-act` skill** from the catalogue; refuse `-stub` versions.
3. **Load timeline and delegated-acts data** by reading
   `~/.hermes/skills/aigovops/eu-ai-act/enforcement-timeline.yaml` and
   `~/.hermes/skills/aigovops/eu-ai-act/delegated-acts.yaml` respectively.
4. **Pull system classification** either from the caller or from the high-risk-classifier workflow (when it exists; Phase 4).
5. **Invoke the plugin**: `applicability_checker.plugin.check_applicability(inputs)`.
6. **Render Markdown** for human review.
7. **Persist** to `~/.hermes/memory/aigovclaw/applicability/<target-date>/<system>/report.{json,md}`.
8. **Surface organizational actions** to the review queue. Actions from the most-recently-active enforcement events are prioritized.
9. **Emit audit-log entry** citing Article 113 for the evaluation event.

## Quality gates

- Every output carries a target_date, system_description_echo, and applicable_events list.
- Every organizational_action is traceable to an enforcement event and a citation.
- Delegated-act filtering is based on explicit system classification, not narrative inference.
- Output contains no em-dashes, emojis, or hedging.

## Cadence and triggers

- **Schedule-based**: re-run quarterly at minimum for every high-risk system to catch pending-but-soon events.
- **Event-based**: system risk classification changes; framework-monitor detects a delegated-act publication; management review preparation.
- **Ad-hoc**: any operations team asking "does X apply to me?"

## Integration points

- **Upstream**: `high-risk-classifier` workflow (when exists) produces `is_high_risk` and `is_annex_i_product` inputs; framework-monitor surfaces timeline changes.
- **Downstream**: `management-review-packager` references the report in the Clause 9.3.2 AIMS performance section; compliance backlog populated from organizational_actions; risk-register-builder flags pending-but-imminent events as risks.

## Tests

Plugin carries 26 tests at [plugins/applicability-checker/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/applicability-checker/tests/test_plugin.py).
