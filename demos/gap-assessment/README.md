# Demo: gap-assessment workflow

End-to-end demonstration of the gap-assessment workflow against the ISO/IEC 42001 Annex A control set. Produces JSON, Markdown, and CSV renderings, plus audit-event trail. Exercises covered, partially-covered, not-covered, and not-applicable classifications in a single run.

## What this demo proves

Running `python demos/gap-assessment/run.py` exercises the full governance path for a realistic multi-system AIMS:

1. A `TaskEnvelope` is built at the ingress boundary with `command="gap-assessment"`.
2. The workflow resolves the `gap-assessment` plugin from the sibling [aigovops](https://github.com/ZOLAtheCodeX/aigovops) repository.
3. The plugin's `generate_gap_assessment(inputs)` returns a structured dict with target_framework, rows (one per control), per-row classification and justification and next-step, a summary block with classification counts and coverage score, and an agent_signature.
4. `render_markdown(assessment)` and `render_csv(assessment)` produce human-readable and tabular forms suitable for management review.
5. All three renderings are persisted under `demos/gap-assessment/output/`.
6. Two `AuditEvent` records (workflow-started, workflow-completed) are appended to `demos/gap-assessment/output/audit-events.jsonl`.

## Prerequisites

- Python 3.10 or newer.
- A local checkout of [aigovops](https://github.com/ZOLAtheCodeX/aigovops). Searched in order:
  1. `$AIGOVOPS_PLUGINS_PATH/gap-assessment/plugin.py`
  2. `../aigovops/plugins/gap-assessment/plugin.py` (sibling layout)
  3. `~/Documents/CODING/aigovops/plugins/gap-assessment/plugin.py`
- No additional packages. Stdlib only.

## Run it

```bash
cd /path/to/aigovclaw
python demos/gap-assessment/run.py
```

Expected output on success:

```text
framework:            iso42001
agent_signature:      gap-assessment/0.2.0
rows:                 38
classification_counts: {'covered': 5, 'partially-covered': 1, 'not-covered': 30, 'not-applicable': 2}
coverage_score:       0.1527777777777778
json:                 demos/gap-assessment/output/iso42001-...Z.json
markdown:             demos/gap-assessment/output/iso42001-...Z.md
csv:                  demos/gap-assessment/output/iso42001-...Z.csv
audit events:         demos/gap-assessment/output/audit-events.jsonl
```

## Input fixture

[input.json](input.json) describes a two-system AIMS at Contoso Health Insurance:

- `ClaimsTriageAI-v1`: production clinical-triage system, risk_tier high.
- `ProviderNetworkSearchAI-v2`: consumer-facing provider-search ranker, risk_tier limited.

The fixture provides:

- `current_state_evidence` for five Annex A controls (A.2.2, A.3.2, A.6.2.3, A.6.2.8, A.9.2), populating the `covered` and `partially-covered` cases.
- `manual_classifications` for three controls (A.2.3 covered by cross-reference, A.4.5 not-applicable as a deployer-only organization, A.9.2 partially-covered with a dated implementation plan).
- `exclusion_justifications` for one control (A.10.2 out of AIMS scope via vendor-management).
- `scope_boundary` and `reviewed_by` for the resulting artifact header.

Controls without any of these inputs classify as `not-covered` with a `REQUIRES REVIEWER DECISION` next step. That is the plugin's "no silent guessing" stance.

## Output structure

The JSON output top-level keys:

- `target_framework`, `timestamp`, `scope_boundary`, `reviewed_by`, `agent_signature`.
- `rows`: list of per-control records with `target_id`, `target_title`, `citation`, `classification`, `justification`, `next_step`, `warnings`.
- `summary`: `total_targets`, `classification_counts`, `coverage_score` (float 0.0-1.0), `targets_with_warnings`.
- `citations`: main-body clauses referenced by the assessment.
- `warnings`, `crosswalk_gaps_surfaced`: reviewer-facing flags.

Every citation uses the STYLE.md canonical format: `ISO/IEC 42001:2023, Annex A, Control A.X.Y` for Annex A controls, `ISO/IEC 42001:2023, Clause X.X.X` for main-body clauses.

## Replay test

[test_gap_assessment_demo.py](test_gap_assessment_demo.py) runs the demo and asserts: all three renderings produced, valid per-row classification, citation format, summary shape (coverage score in [0.0, 1.0], counts match rows), Markdown contains no forbidden em-dashes, CSV header sane, and audit-events emit both workflow-started and workflow-completed. Gated in CI via the `pytest-suite` job.

## What this demo does not cover

- No approval queue routing. Gap assessments are non-destructive artifact generators; the action executor is not in the path for this demo.
- No downstream workflow triggers. The workflow doc specifies that not-covered rows feed the risk-register workflow and that the coverage score feeds the management-review-packager. Those cross-workflow integrations are exercised in their own demos (planned).
- No crosswalk-matrix enrichment. The plugin supports `surface_crosswalk_gaps=True` to attach cross-framework equivalents; the demo keeps the default off for clarity.
