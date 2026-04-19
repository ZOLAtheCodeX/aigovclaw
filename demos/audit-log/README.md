# Demo: audit-log workflow

End-to-end demonstration of the audit-log workflow. Shows: TaskEnvelope at ingress, AIGovOps plugin invocation, structured JSON plus human-readable Markdown outputs, audit-event trail.

## What this demo proves

Running `python demos/audit-log/run.py` exercises the full governance path for one workflow without human approval (the persistence target is the demo directory, not a shared store):

1. An ingress-layer `TaskEnvelope` is built, validated, and recorded.
2. The workflow resolves the `audit-log-generator` plugin from the sibling [aigovops](https://github.com/ZOLAtheCodeX/aigovops) repository.
3. The plugin's `generate_audit_log(system_description)` returns a structured dict with timestamp, clause mappings, Annex A control mappings, governance decisions, responsible parties, evidence items, human-readable summary, and agent signature.
4. The plugin's `render_markdown(entry)` produces a Markdown document suitable for inclusion in an audit evidence package.
5. Both renderings are persisted under `demos/audit-log/output/`.
6. Two `AuditEvent` records (workflow-started, workflow-completed) are appended to `demos/audit-log/output/audit-events.jsonl`.

## Prerequisites

- Python 3.10 or newer.
- A local checkout of [aigovops](https://github.com/ZOLAtheCodeX/aigovops) adjacent to this repo. The runner searches `../aigovops/plugins/audit-log-generator/plugin.py` and `~/Documents/CODING/aigovops/plugins/audit-log-generator/plugin.py`.
- No additional packages. The demo uses stdlib only.

## Run it

```bash
cd /path/to/aigovclaw
python demos/audit-log/run.py
```

Expected output on success:

```text
system_name:     ClaimsTriageAI-v1
agent_signature: audit-log-generator/0.2.0
annex_a:         ['A.6.2.3', 'A.6.2.8', 'A.3.2', 'A.5.4', 'A.6.2.4', 'A.6.2.6', 'A.7.2', 'A.7.5', 'A.5.5', 'A.8.3']
json:            demos/audit-log/output/ClaimsTriageAI-v1-...Z.json
markdown:        demos/audit-log/output/ClaimsTriageAI-v1-...Z.md
audit events:    demos/audit-log/output/audit-events.jsonl
```

## Input fixture

The input lives at [input.json](input.json). It describes `ClaimsTriageAI-v1`, a clinical-triage system at a regional health-insurance carrier. Risk tier is `high`; data categories include protected health information. The fixture intentionally includes governance decisions and responsible parties so the plugin's full control-mapping path is exercised.

## Output structure

`demos/audit-log/output/<system_name>-<timestamp>.json` contains:

- `timestamp`: ISO 8601 UTC timestamp of workflow completion.
- `system_name`: echoed from input.
- `clause_mappings`: list of canonical ISO 42001 main-body clause citations in STYLE.md format.
- `annex_a_mappings`: list of `{control_id, citation, rationale}` entries for each applicable Annex A control.
- `evidence_items`, `human_readable_summary`, `governance_decisions`, `responsible_parties`: echoed and structured from input.
- `agent_signature`: fixed to `audit-log-generator/0.<minor>.<patch>` at generation time.

`demos/audit-log/output/<system_name>-<timestamp>.md` contains the human-readable rendering suitable for inclusion in an audit evidence package.

`demos/audit-log/output/audit-events.jsonl` contains one line per audit event: workflow-started, workflow-completed. Schema: [aigovclaw.action_executor.audit_event.AuditEvent](../../aigovclaw/action_executor/audit_event.py).

## Replay test

[test_demo.py](test_demo.py) runs the demo programmatically and asserts the output shape. Run with:

```bash
python -m pytest demos/audit-log/test_demo.py -v
```

This test gates merges: the demo must stay green or the PR does not land.

## What this demo does not prove

- It does not exercise the approval queue. The persistence target is local to the demo directory and the workflow is non-destructive; the runner bypasses `ActionExecutor` for this reason.
- It does not route through Hermes channels. Channel routing is covered by `aigovclaw/action_executor/handlers/notification.py` and its separate tests.
- It does not cover the PDCA orchestrator. That is covered by `aigovclaw/agent_loop/tests/`.

Those paths are exercised in their own test suites. This demo's scope is strictly ingress, plugin invocation, artifact persistence, and audit-event emission.
