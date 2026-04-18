"""
Jules Tool Registration

Exposes a `dispatch_jules_session` tool to the AIGovClaw Hermes tool
registry. This tool lets the Hermes agent enqueue a FlaggedIssue and
trigger a Jules dispatch cycle against one of the eight known playbooks.

Safety metadata:

- is_read_only=False: the tool creates a FlaggedIssue record on disk and
  (when not dry-run) initiates a Jules session that will open a pull
  request on the target repo.
- is_concurrency_safe=False: the dispatcher uses a single-owner store.
  Concurrent invocations against the same store risk lost updates.
- is_destructive=False: the tool creates external state (a Jules session
  and eventually a PR) but does not delete or overwrite existing state.
- requires_human_approval=True: every Jules session eventually leads to a
  PR that the human merges. The harness must prompt the human before
  enqueue.

Input schema:

- playbook (enum of the eight playbook names)
- target_repo (string, for example "ZOLAtheCodeX/aigovops")
- payload (dict with playbook-specific fields; may be empty)

Optional:

- target_branch (string, default "main")
- priority (enum: "low", "normal", "high", default "normal")
- source (enum of FlaggedIssue source values, default "human")
- dry_run (bool, default True). When True, the tool persists the
  FlaggedIssue but does not call the Jules API. The operator runs
  `python3 -m jules.cli dispatch` separately to trigger real dispatch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import REGISTRY, Tool

DEFAULT_JULES_ROOT = Path(__file__).resolve().parents[1] / "jules"


PLAYBOOK_ENUM = [
    "framework-drift",
    "test-coverage-gap",
    "dep-bump",
    "citation-drift",
    "markdown-lint",
    "new-plugin-scaffold",
    "link-toc",
    "prohibited-content-sweep",
]


def _handler(inputs: dict[str, Any]) -> dict[str, Any]:
    """Enqueue a FlaggedIssue. Does not make Jules API calls by default.

    Returns a dict with the issue id, state, and a note describing the
    next operator action. The handler never logs the payload.
    """
    from jules.dispatcher import (  # lazy import to avoid module load cost
        AGENT_SIGNATURE,
        Dispatcher,
        FlaggedIssue,
        FlaggedIssueStore,
        _deterministic_id,
        _now_iso,
    )

    playbook = inputs["playbook"]
    target_repo = inputs["target_repo"]
    payload = inputs.get("payload", {}) or {}
    target_branch = inputs.get("target_branch", "main")
    priority = inputs.get("priority", "normal")
    source = inputs.get("source", "human")
    root = Path(inputs.get("jules_root") or DEFAULT_JULES_ROOT)

    issue = FlaggedIssue(
        id=_deterministic_id(),
        type=f"tool-initiated:{playbook}",
        source=source,
        playbook=playbook,
        target_repo=target_repo,
        target_branch=target_branch,
        priority=priority,
        created_at=_now_iso(),
        state="flagged",
        payload=payload,
    )
    store = FlaggedIssueStore(root)
    playbook_dir = root / "playbook"
    dispatcher = Dispatcher(
        store=store, client=None, playbook_dir=playbook_dir, tool_registry=REGISTRY
    )
    dispatcher.enqueue(issue)
    return {
        "agent_signature": AGENT_SIGNATURE,
        "issue_id": issue.id,
        "state": issue.state,
        "next_action": (
            "Run `python3 -m jules.cli dispatch` to advance queued issues "
            "to Jules. Use --dry-run first to confirm the prompt."
        ),
    }


DISPATCH_JULES_SESSION_TOOL = Tool(
    name="dispatch_jules_session",
    description=(
        "Enqueue a FlaggedIssue for the Jules dispatcher. Creates a record "
        "on disk in jules/flagged/ in state 'queued'. Does not make real "
        "API calls; the operator advances the queue separately. Every "
        "Jules session ultimately opens a pull request that requires "
        "human merge."
    ),
    handler=_handler,
    input_schema={
        "playbook": {
            "type": "string",
            "required": True,
            "enum": PLAYBOOK_ENUM,
            "description": "Named playbook; determines prompt template and success criteria.",
        },
        "target_repo": {
            "type": "string",
            "required": True,
            "description": "GitHub slug, e.g. 'ZOLAtheCodeX/aigovops'.",
        },
        "payload": {
            "type": "dict",
            "required": True,
            "description": "Playbook-specific structured input.",
        },
        "target_branch": {
            "type": "string",
            "required": False,
            "description": "Branch to base Jules work on. Default 'main'.",
        },
        "priority": {
            "type": "string",
            "required": False,
            "enum": ["low", "normal", "high"],
            "description": "Dispatch priority.",
        },
        "source": {
            "type": "string",
            "required": False,
            "enum": ["claude-code", "human", "scheduled", "framework-monitor", "ci"],
            "description": "What produced this record.",
        },
        "jules_root": {
            "type": "string",
            "required": False,
            "description": "Override for jules/ root. Used by tests.",
        },
    },
    is_read_only=False,
    is_concurrency_safe=False,
    is_destructive=False,
    requires_human_approval=True,
    source_skill="jules-integration",
    artifact_type="jules-flagged-issue",
)


def register_jules_tools() -> str:
    """Register the Jules dispatch tool with the shared REGISTRY.

    Idempotent: if the tool is already registered, returns its name
    without raising.
    """
    if DISPATCH_JULES_SESSION_TOOL.name in REGISTRY.list_tools():
        return DISPATCH_JULES_SESSION_TOOL.name
    REGISTRY.register(DISPATCH_JULES_SESSION_TOOL)
    return DISPATCH_JULES_SESSION_TOOL.name


def unregister_jules_tools() -> None:
    """Remove the Jules dispatch tool. Idempotent."""
    if DISPATCH_JULES_SESSION_TOOL.name in REGISTRY.list_tools():
        REGISTRY.unregister(DISPATCH_JULES_SESSION_TOOL.name)


__all__ = [
    "DISPATCH_JULES_SESSION_TOOL",
    "PLAYBOOK_ENUM",
    "register_jules_tools",
    "unregister_jules_tools",
]
