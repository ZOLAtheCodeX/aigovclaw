# Workflow: metrics-collector

**Status**: active. Phase 3 plugin integration complete.

**Primary frameworks**: NIST AI RMF 1.0 MEASURE 1.1, 2.1, 2.3, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12; MEASURE 3.1, MEASURE 4.1; MANAGE 4.1. NIST AI 600-1 (Generative AI Profile) overlay. ISO/IEC 42001:2023 Clause 9.1.

**Output artifact**: Trustworthy-AI metrics report (KPI records + per-system V&V summaries + threshold-breach routing list). JSON dict + Markdown + CSV.

**Plugin consumer**: [plugins/metrics-collector](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/metrics-collector). Agent signature: `metrics-collector/0.1.0`.

## Objective

Aggregate precomputed trustworthy-AI measurements from the organization's MLOps pipelines, validate them against the MEASURE 2.x metric catalog (plus AI 600-1 overlay when a generative-AI system is in scope), attach subcategory citations, flag threshold breaches, and route breaches to the risk-register and nonconformity-tracker workflows.

This is the runtime loop behind NIST MEASURE 3.1 ongoing monitoring and MANAGE 4.1 post-deployment monitoring. Under ISO 42001 it satisfies Clause 9.1 monitoring and measurement for the metric families the organization has defined.

## Required inputs

Plugin signature: `generate_metrics_report(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `ai_system_inventory` | list | yes | Systems in scope; `system_type: generative-ai` auto-enables AI 600-1 overlay. |
| `measurements` | list | yes | Precomputed measurements from MLOps; see plugin README. |
| `metric_catalog` | dict | no | Overrides or extends the default 9-family catalog. |
| `thresholds` | dict | no | Per-metric threshold specs. Required for breach routing to trigger. |
| `genai_overlay_enabled` | bool | no | Explicit override; auto-detected otherwise. |
| `framework` | string | no | `nist` (default), `iso42001`, `dual`. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs**. Structural problems abort; unknown families, missing method refs, missing test-set refs surface as per-KPI warnings.
2. **Load the `nist-ai-rmf` skill** (plus `iso42001` for iso or dual mode). Refuse `-stub` versions.
3. **Pull organizational threshold policy** from `~/.hermes/memory/aigovclaw/thresholds/current.json` when thresholds are not provided inline. Thresholds are organizational policy, not measurement data; they are approved separately per the role matrix.
4. **Invoke the plugin**: `metrics_collector.plugin.generate_metrics_report(inputs)`.
5. **Render** the JSON dict, Markdown document, and CSV.
6. **Persist** all three to `~/.hermes/memory/aigovclaw/metrics/<window_end>/report.{json,md,csv}` where `<window_end>` is the measurement window end timestamp for stable sorting.
7. **Emit an audit-log entry** for the measurement-cycle completion via the audit-log workflow, citing `MEASURE 3.1` (and Clause 9.1 in iso or dual mode).
8. **Route threshold breaches**:
   1. For every entry in `threshold_breaches`, check the organizational breach-routing policy to determine whether the breach is material.
   2. Material breaches trigger the nonconformity-tracker workflow with a new record citing the breached MEASURE subcategory as `source_citation`.
   3. All breaches (material or not) trigger the risk-register workflow as candidate risk updates for owner review.
9. **Surface flagged issues** for: every threshold breach; every KPI record with `requires_test_set: True` but no `test_set_ref`; measurement-drift indicators surfaced by the per-system summary (the summary emits a drift warning when a family has breach counts trending up across the last three emissions at this window-end cadence).
10. **Meta-measurement cadence**: at the organizational meta-measurement interval (typically quarterly), emit a separate V&V evaluation record citing `MEASURE 4.1` (measurement approaches periodically assessed for efficacy) summarizing whether thresholds remain calibrated and which metrics are producing signal vs. noise.

## Quality gates

- Every measurement has its `metric_family` and `metric_id` in the catalog or surfaces a warning.
- Every test-set-required measurement (validity-reliability, privacy, fairness, most GenAI overlay families) has a `test_set_ref` or surfaces a warning.
- Every measurement has a `measurement_method_ref` per MEASURE 2.1; missing refs surface warnings.
- Every threshold breach either routes to a downstream workflow or is explicitly acknowledged as non-material in the review queue.
- Output contains no em-dashes, emojis, or hedging.
- `agent_signature` matches the installed plugin version.

## Cadence and triggers

- **Schedule-based**: weekly, daily, or hourly depending on metric cadence. Different families measure at different cadences; the workflow runs at the shortest organizational cadence and only emits KPIs for families with fresh measurements.
- **Event-based**: new deployment (triggers a validity-reliability cycle against the current production test set); incident logged (triggers safety and security-resilience measurement); framework-update detected by framework-monitor (triggers catalog and threshold review).

## Threshold-management note

Thresholds are organizational policy. The plugin enforces them but does not set them. Threshold additions, deletions, or value changes require approval per the role matrix under the decision category `Metric catalog approval`. Threshold changes produce an audit-log entry citing Clause 7.5.2 so the threshold history is itself evidence.

## Integration points

- **Upstream**: MLOps pipeline emissions (test-set evaluations, production telemetry, privacy probes, fairness probes, incident logs), organizational threshold policy, role-matrix for threshold-change approvers.
- **Downstream**: risk-register for threshold-triggered candidate risks, nonconformity-tracker for material breaches, management-review-packager (KPI summary feeds Clause 9.3.2 AIMS performance input).

## Tests

Plugin carries 33 tests at [plugins/metrics-collector/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/metrics-collector/tests/test_plugin.py).
