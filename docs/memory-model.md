# Memory model

AIGovClaw maintains four distinct memory classes under a single local root. Each class has different retention, access, and promotion rules. A call site that writes to the wrong class is a defect.

Root: `~/.hermes/memory/aigovclaw/` (resolved from `aigovclaw.action_executor.safety.DEFAULT_MEMORY_ROOT`). Every subdirectory below sits under this root unless noted otherwise.

## Classes

### Class A: Operational session memory

Short-lived state produced during a single workflow invocation. Cleared aggressively. Never promoted to durable memory without a deliberate write into Class B or Class C.

- Paths: `action-snapshots/<request_id>/` and `cascade-queue/<request_id>.json`.
- Retention: bounded by the running process. Snapshots are retained until the action completes or rolls back, then eligible for cleanup.
- Writers: `action_executor.safety.snapshot_target`; `trigger_downstream` handler.
- Readers: `ActionExecutor._run_handler` for rollback; `PDCACycle` for cascade processing.
- Invariants:
  - Never shared across request_ids.
  - Never read by any workflow for evidence purposes.
  - Never included in audit evidence packages.

### Class B: Workflow memory

Task-scoped artifacts that constitute the output of a governed workflow. Subject to evidence and provenance rules. Retained for the life of the workflow artifact.

- Paths: `audit-log/<system_name>/<timestamp>.{json,md}`; `<plugin-name>/<timestamp>.json` written by the re-run-plugin handler; `hub-v2-tasks/<task_id>/state.json` and `stdout.log`.
- Retention: until an operator archives or deletes. Corrections are new files that reference the prior timestamp; the original is immutable.
- Writers: plugin handlers via the action-executor; Hub v2 task runner.
- Readers: workflow downstream consumers (management-review input package reads `audit-log/`; nonconformity tracker reads audit entries); Hub v2 HTTP API `/api/artifacts`.
- Invariants:
  - Files are byte-identical in shared fields between `.json` and `.md` renderings.
  - Every file carries an `agent_signature` identifying the writing plugin and version.
  - No in-place edits. Corrections produce new files.

### Class C: Skill and pattern memory

Reusable learned patterns and skill-derived state. Requires promotion rules before a pattern moves from observation to applied state. Not yet populated in the current runtime; reserved for the learning-loop workstream.

- Paths: `skills/<skill-id>/state.json` (reserved, not yet written).
- Retention: indefinite after validated promotion. Promotion requires an audit entry naming the evidence basis.
- Writers: reserved for future learning-loop implementation. Current value: zero.
- Readers: reserved.
- Invariants:
  - No direct writes from agent output. Every promotion goes through a workflow that records an audit entry.
  - Rollback from Class C requires an explicit demotion entry in the audit log.

### Class D: Protected governance memory

Policy artifacts, control mappings, and approval records. The source of truth for what the system is permitted to do and what it has been asked to do. Mediated access only.

- Paths: `approvals/<request_id>.json`; `audit-log/YYYY-MM-DD.jsonl`.
- Also read-only during runtime: `config/authority-policy.yaml`, `config/hermes.yaml`.
- Retention: indefinite. Audit entries are append-only. Approval records are overwritten on decision (approve or reject) and retained as the authoritative record for that request.
- Writers: `ActionExecutor` only (for approvals); `AuditLogger` only (for audit entries). No plugin writes to Class D.
- Readers: `ActionExecutor` for approval resolution; `RateLimiter` for hourly counts; Hub v2 HTTP API for operator display; external auditors via explicit export.
- Invariants:
  - Audit entries are append-only within a day-file. No rewrites.
  - Approval records reflect the final decision. Intermediate queue state does not persist after the decision.
  - HMAC signatures applied when `AIGOVCLAW_AUDIT_SIGNING_KEY` is set in the environment.

## Write rules

A call site that writes to aigovclaw memory must satisfy all of the following:

1. The target path resolves under one of the class roots listed above.
2. The writing module matches the class's writer list. For Class B and D, external plugins write indirectly through the action-executor.
3. The write produces an audit entry (Class D) or is covered by an audit entry written by the executor (Class A and B).
4. For Class C, the promotion step names the evidence basis.

`aigovclaw.action_executor.safety.allowed_roots()` returns the set of absolute paths the file-update handler is permitted to mutate. Writes outside that set fail.

## Read rules

Readers do not assume memory state is fresh. Every read that feeds a governance decision re-reads from disk; no in-memory cache substitutes for the authoritative file.

## Promotion rules

Class A to Class B: explicit workflow step. Never implicit. The promoting step writes the Class B artifact and an audit entry naming the request_id that produced it.

Class B to Class C: reserved. Requires the learning-loop implementation. Every promotion must write an audit entry naming the evidence basis.

Class C to Class B: demotion, not promotion. Triggered by a workflow that finds a skill pattern has stopped holding. The demotion writes an audit entry and does not delete the Class C entry; it marks it retired.

Class D is not promoted. It is the authority surface itself.

## Out-of-scope

User-facing memory such as Notion pages, calendar events, and chat thread state lives in upstream systems. AIGovClaw does not cache those. Reference them by stable identifier and re-query when needed.

## Cross-references

- Writers and handlers: [aigovclaw/action_executor/handlers/](../aigovclaw/action_executor/handlers/)
- Safety primitives: [aigovclaw/action_executor/safety.py](../aigovclaw/action_executor/safety.py)
- Authority policy surface: [config/authority-policy.yaml](../config/authority-policy.yaml)
- Audit event schema: [aigovclaw/action_executor/audit_event.py](../aigovclaw/action_executor/audit_event.py)
- Ingress task envelope: [aigovclaw/task_envelope.py](../aigovclaw/task_envelope.py)
