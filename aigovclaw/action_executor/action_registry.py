"""Action registry and core dataclasses.

Defines ActionRequest and ActionResult schemas and the static catalogue of
supported action types. Each entry declares the handler module, safety
properties, default authority mode, rate limit, and required argument
fields.

The registry is intentionally static. Adding a new action type requires
(a) a handler module under handlers/, (b) a registry entry here, and
(c) an authority-policy default entry in config/authority-policy.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


AUTHORITY_ASK = "ask-permission"
AUTHORITY_TAKE = "take-resolving-action"
AUTHORITY_AUTONOMOUS = "autonomous"

VALID_AUTHORITY_MODES = (AUTHORITY_ASK, AUTHORITY_TAKE, AUTHORITY_AUTONOMOUS)


@dataclass
class ActionRequest:
    """Input to ActionExecutor.execute.

    Fields:
        action_id: stable id of the action type (e.g. "file-update").
        plugin: name of the plugin issuing the request.
        target: primary target string (filepath, plugin name, MCP server, etc).
        args: per-action-type arguments.
        rationale: free-text reason for the action; recorded in the audit log.
        dry_run: when True, handlers return what would happen without mutating.
        requested_at: ISO 8601 UTC timestamp.
        request_id: deterministic ULID-like identifier.
    """

    action_id: str
    plugin: str
    target: str
    args: dict[str, Any]
    rationale: str
    requested_at: str
    request_id: str
    dry_run: bool = False


@dataclass
class ActionResult:
    """Output of ActionExecutor.execute and related methods.

    status values:
        executed             handler ran successfully.
        approved-pending     queued awaiting approval; execution deferred.
        rejected             approval explicitly denied.
        failed               handler raised; rollback not needed or not attempted.
        rolled-back          handler raised; snapshot restored successfully.
        skipped-rate-limit   rate limit hit; no handler invocation.
        skipped-dry-run      dry_run=True; handler returned a preview only.
    """

    request_id: str
    status: str
    authority_mode_used: str
    audit_entry_id: str
    rollback_snapshot_path: str | None
    started_at: str
    ended_at: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ActionSpec:
    """Static registry entry for an action type."""

    id: str
    display_name: str
    description: str
    handler_module: str
    safety: dict[str, bool]
    default_authority: str
    rate_limit_per_hour: int | None
    args_schema: list[str]


def build_registry() -> dict[str, ActionSpec]:
    """Return the canonical action registry.

    Keep this in sync with config/authority-policy.yaml. Rate limits here
    are hard-coded defaults; authority-policy.yaml can override per-action.
    """
    return {
        "file-update": ActionSpec(
            id="file-update",
            display_name="Update a local file",
            description=(
                "Mutate a file inside an allowed root. Snapshots the target "
                "before mutation; rollback restores from the snapshot."
            ),
            handler_module="aigovclaw.action_executor.handlers.file_update",
            safety={"reversible": True, "destructive": False, "external_side_effect": False},
            default_authority=AUTHORITY_ASK,
            rate_limit_per_hour=60,
            args_schema=["path", "updates_dict", "diff_mode"],
        ),
        "mcp-push": ActionSpec(
            id="mcp-push",
            display_name="Push artifact via MCP",
            description=(
                "Route an artifact to an external destination via an MCP tool. "
                "Not locally reversible; destination may accept or reject."
            ),
            handler_module="aigovclaw.action_executor.handlers.mcp_push",
            safety={"reversible": False, "destructive": False, "external_side_effect": True},
            default_authority=AUTHORITY_ASK,
            rate_limit_per_hour=20,
            args_schema=["mcp_server", "tool_name", "payload"],
        ),
        "notification": ActionSpec(
            id="notification",
            display_name="Emit a notification",
            description=(
                "Write a notification record to a channel. Local-file and "
                "stdout are supported now; chat and email channels land in a "
                "later sprint."
            ),
            handler_module="aigovclaw.action_executor.handlers.notification",
            safety={"reversible": False, "destructive": False, "external_side_effect": True},
            default_authority=AUTHORITY_TAKE,
            rate_limit_per_hour=120,
            args_schema=["channel", "message", "severity"],
        ),
        "re-run-plugin": ActionSpec(
            id="re-run-plugin",
            display_name="Re-run an AIGovOps plugin",
            description=(
                "Invoke an aigovops plugin by name with the given inputs and "
                "write the output to the aigovclaw memory store."
            ),
            handler_module="aigovclaw.action_executor.handlers.re_run_plugin",
            safety={"reversible": True, "destructive": False, "external_side_effect": False},
            default_authority=AUTHORITY_TAKE,
            rate_limit_per_hour=60,
            args_schema=["plugin_name"],
        ),
        "trigger-downstream": ActionSpec(
            id="trigger-downstream",
            display_name="Trigger a cascade-downstream action",
            description=(
                "Enqueue a new ActionRequest for a cascade node. The PDCA "
                "orchestrator consumes the resulting cascade-queue entry."
            ),
            handler_module="aigovclaw.action_executor.handlers.trigger_downstream",
            safety={"reversible": True, "destructive": False, "external_side_effect": False},
            default_authority=AUTHORITY_TAKE,
            rate_limit_per_hour=60,
            args_schema=["cascade_node_id"],
        ),
        "git-commit-and-push": ActionSpec(
            id="git-commit-and-push",
            display_name="Git commit and push",
            description=(
                "Always ask-permission. Produces a commit and optionally "
                "pushes to a remote. Partially reversible via git revert; "
                "push to a shared remote cannot be fully rolled back."
            ),
            handler_module="aigovclaw.action_executor.handlers.git_commit",
            safety={"reversible": False, "destructive": False, "external_side_effect": True},
            default_authority=AUTHORITY_ASK,
            rate_limit_per_hour=10,
            args_schema=["repo_path", "files", "commit_message", "branch", "push_remote"],
        ),
    }
