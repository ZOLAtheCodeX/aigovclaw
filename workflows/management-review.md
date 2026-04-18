# Workflow: management-review

**Status**: active. Phase 3 plugin integration complete.

**Primary framework**: ISO/IEC 42001:2023 Clause 9.3.2 (inputs); Clause 7.5.3 (distribution evidence). Clause 9.3.1 (the meeting itself) and 9.3.3 (outputs) are human-driven and out of scope for this workflow.

**Output artifact**: Management review input package (JSON dict + Markdown) and a Clause 7.5.3 distribution audit-log hook.

**Plugin consumer**: [plugins/management-review-packager](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/management-review-packager). Agent signature: `management-review-packager/0.1.0`.

## Objective

Assemble the Clause 9.3.2 pre-read distributed to top management before each scheduled management review. The agent does not hold the meeting; it composes the inputs from sources of record and emits the distribution audit-log entry. Meeting outputs (Clause 9.3.3) are captured separately via the audit-log workflow at meeting time.

## Required inputs

Plugin signature: `generate_review_package(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `review_window` | dict | yes | `{start, end}` as ISO dates. |
| `attendees` | list | yes | Non-empty list of role names from the role matrix. |
| Nine category keys | string, list, or dict | no but recommended | See [plugin README](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/management-review-packager/README.md) for full list. |
| `meeting_metadata` | dict | no | `{scheduled_date, location, ...}`. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs**.
2. **Load the `iso42001` skill**.
3. **Pull source-of-record references** from aigovclaw memory for each Clause 9.3.2 category:
   1. `previous_review_actions`: prior `~/.hermes/memory/aigovclaw/management-review/` emissions.
   2. `aims_performance`: most recent KPI report reference.
   3. `audit_results`: most recent internal-audit report reference.
   4. `nonconformity_trends`: most recent nonconformity register with trend direction summary.
   5. `objective_fulfillment`: objective-status source ref.
   6. `stakeholder_feedback`: feedback register items for the window.
   7. `ai_risks_and_opportunities`: most recent risk register reference.
   8. `continual_improvement_opportunities`: continual-improvement backlog reference.
   9. `external_internal_issues_changes`: context-change log for the window.
4. **Invoke the plugin**: `management_review_packager.plugin.generate_review_package(inputs)`.
5. **Render Markdown** for distribution to attendees.
6. **Persist** to `~/.hermes/memory/aigovclaw/management-review/<timestamp>/package.{json,md}`.
7. **Route the distribution_hook** to the audit-log workflow so the distribution event is logged per Clause 7.5.3. The hook names every attendee and references the stored package.
8. **Surface flagged issues** for any category marked as not populated, any breach flags in `aims_performance`, and any overdue open actions in `previous_review_actions`.

## Quality gates

- All nine Clause 9.3.2 input categories appear in the package section list.
- Every populated category references a source of record, not a narrative summary.
- Distribution hook cites Clause 7.5.3 and names every attendee.
- Attendees list is non-empty.
- `agent_signature` matches the installed plugin version.
- No em-dashes, emojis, or hedging.

## Cadence and triggers

- **Schedule-based**: tied to organizational management-review cadence (typically quarterly or semi-annually). Workflow fires a configurable number of days before the scheduled meeting to allow review-queue time.
- **Event-based**: ad-hoc assembly when top management calls an unscheduled review (for example in response to a high-severity incident).

## Integration points

- **Upstream**: every other aigovclaw workflow produces inputs. This is the integrator workflow.
- **Downstream**: `audit-log` receives the distribution hook; meeting outputs (Clause 9.3.3 decisions, action items) are captured by the audit-log workflow at meeting time and feed the next cycle's `previous_review_actions` category.

## Tests

Plugin carries 17 tests at [plugins/management-review-packager/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/management-review-packager/tests/test_plugin.py).
