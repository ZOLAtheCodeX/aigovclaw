"""AIGovClaw runtime package.

Hosts the runtime layers that turn AIGovOps plugin artifacts into operational
actions: action-executor, cascade handling, PDCA orchestration.

The aigovclaw runtime is distinct from the aigovops catalogue. Plugins in
aigovops generate artifacts (audit logs, risk registers, etc). Modules in
aigovclaw decide what to do with those artifacts, ask for approval when
required, take action, record audit entries, and roll back on failure.

Public schemas (stdlib dataclasses, no third-party deps):
    TaskEnvelope      canonical input at the ingress boundary.
    ActionRequest     action-executor input (one envelope may yield many).
    ActionResult      action-executor output.
    AuditEvent        canonical audit log entry shape.
"""

from .task_envelope import TaskEnvelope, TaskEnvelopeError

__all__ = [
    "TaskEnvelope",
    "TaskEnvelopeError",
]
