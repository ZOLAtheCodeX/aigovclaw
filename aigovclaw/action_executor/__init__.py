"""Action-executor layer.

Bridges AIGovOps plugins from generating artifacts to taking operational
actions. Accepts ActionRequests, resolves authority policy, routes to an
approval queue or executes immediately, records audit-log entries before
and after every action, and invokes rollback on handler failure.

Public surface:
    ActionExecutor      the core execute/approve/reject coordinator
    ActionRequest       input schema
    ActionResult        output schema
    ActionValidationError raised for malformed requests or unknown actions

Downstream subagents (PDCA orchestrator, cascade-impact-analyzer) depend
only on these four names. The registry, authority policy, safety layer,
and handlers are implementation details and may change without notice.
"""

from .executor import ActionExecutor, ActionValidationError
from .action_registry import ActionRequest, ActionResult

__all__ = [
    "ActionExecutor",
    "ActionRequest",
    "ActionResult",
    "ActionValidationError",
]
