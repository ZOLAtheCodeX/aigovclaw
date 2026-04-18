# Workflow: high-risk-classifier

**Status**: active. Phase 4 plugin integration complete.

**Primary framework**: EU AI Act (Articles 5, 6, 50; Annex I; Annex III).

**Output artifact**: Risk-tier classification record (JSON + Markdown).

**Plugin consumer**: [plugins/high-risk-classifier](https://github.com/ZOLAtheCodeX/aigovops/tree/main/plugins/high-risk-classifier). Agent signature: `high-risk-classifier/0.1.0`.

## Objective

For every AI system in AIMS scope, classify under EU AI Act risk tiers: prohibited (Article 5), high-risk via Annex I product-safety (Article 6(1)), high-risk via Annex III (Article 6(2)), limited-risk (Article 50 transparency), or minimal-risk. The classification drives which Chapter III obligations apply, which Article 27 FRIA is required, and which conformity-assessment path the provider follows.

The workflow does NOT make the final legal call. Article 5 and Article 6(3) matches route to `requires-legal-review` with the evidence legal counsel needs.

## Required inputs

Plugin signature: `classify(inputs)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | system_name, intended_use, sector; optional deployment_context, data_processed, self-declarations (annex_iii, article_5, article_6_3_exception), Annex I product_type, deployer_scope. |
| `reviewed_by` | string | no | |

## Steps

1. **Validate inputs**.
2. **Load the `eu-ai-act` skill**.
3. **Invoke the plugin**: `high_risk_classifier.plugin.classify(inputs)`.
4. **Render Markdown**.
5. **Persist** to `~/.hermes/memory/aigovclaw/high-risk-classifier/<system>/<timestamp>.{json,md}`.
6. **Surface flagged issues** for every `requires-legal-review` result. Include the matched Article 5 or Article 6(3) context so counsel has the evidence.
7. **Trigger downstream** on classification result:
   1. `high-risk-annex-iii` or `high-risk-annex-i` → kick off the `aisia-runner` workflow for Article 27 FRIA (if `deployer_scope: true`) and the `risk-register-builder` workflow for Article 9 risk management.
   2. `requires-legal-review` → route to the review queue with highest priority; do not auto-start Chapter III workflows until legal confirms.
   3. `limited-risk` → record Article 50 transparency obligations in the organizational-actions queue.
   4. `minimal-risk` → record and file; no mandatory downstream workflow.
8. **Emit audit-log entry** citing Article 6 for the classification event.

## Quality gates

- Every system produces a classification (never skipped).
- Every `requires-legal-review` classification names the specific Article 5 or Article 6(3) flag that triggered it.
- Every `high-risk-annex-iii` classification lists the matched Annex III category.
- Every `high-risk-annex-i` classification names the Annex I legislation.
- No em-dashes, emojis, or hedging in output.

## Cadence and triggers

- **Event-based**: new AI system onboarding; AI system intended-use change; Annex III modification (via delegated act detected by framework-monitor).
- **Schedule-based**: annually per system to catch intended-use drift.

## Integration points

- **Upstream**: AI system inventory workflow.
- **Downstream**: applicability-checker (consumes the classification), aisia-runner, risk-register-builder, audit-log-generator.

## Tests

Plugin carries 22 tests at [plugins/high-risk-classifier/tests/test_plugin.py](https://github.com/ZOLAtheCodeX/aigovops/blob/main/plugins/high-risk-classifier/tests/test_plugin.py).
