"""
Jules Dispatcher CLI

Operator-facing command-line interface. Exposes enqueue, dispatch, poll,
list, show, cancel, and audit subcommands. All subcommands operate against
the `jules/` directory at the current working directory unless
--root overrides it.

The `dispatch --dry-run` mode prints the exact API calls and prompts the
dispatcher would make without making any of them. Use this for validation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from .dispatcher import (
    AGENT_SIGNATURE,
    ConfigurationError,
    Dispatcher,
    FlaggedIssue,
    FlaggedIssueStore,
    JulesApiError,
    JulesClient,
    PLAYBOOK_NAMES,
    VALID_STATES,
    _deterministic_id,
    _now_iso,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jules.cli",
        description="Jules dispatcher CLI for AIGovClaw.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("jules"),
        help="Path to the jules/ directory. Default: ./jules",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=AGENT_SIGNATURE,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_enq = sub.add_parser("enqueue", help="Create a new FlaggedIssue.")
    p_enq.add_argument("--type", dest="issue_type", required=True)
    p_enq.add_argument("--playbook", required=True, choices=PLAYBOOK_NAMES)
    p_enq.add_argument("--target-repo", required=True)
    p_enq.add_argument("--target-branch", default="main")
    p_enq.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    p_enq.add_argument("--source", default="human", choices=["claude-code", "human", "scheduled", "framework-monitor", "ci"])
    p_enq.add_argument("--payload-json", type=Path, default=None)
    p_enq.add_argument("--id", dest="issue_id", default=None)

    p_dis = sub.add_parser("dispatch", help="Dispatch queued issues to Jules.")
    p_dis.add_argument("--max-parallel", type=int, default=3)
    p_dis.add_argument("--dry-run", action="store_true")

    sub.add_parser("poll", help="Poll in-progress sessions.")

    p_list = sub.add_parser("list", help="List issues.")
    p_list.add_argument("--state", default=None, choices=list(VALID_STATES))

    p_show = sub.add_parser("show", help="Print full JSON for an issue.")
    p_show.add_argument("issue_id")

    p_can = sub.add_parser("cancel", help="Cancel a running session and mark rejected.")
    p_can.add_argument("issue_id")

    p_aud = sub.add_parser("audit", help="Re-emit the audit log entry for an issue.")
    p_aud.add_argument("issue_id")

    return parser


def _make_client_if_possible(dry_run: bool) -> Optional[JulesClient]:
    if dry_run:
        return None
    if not os.environ.get("JULES_API_KEY"):
        sys.stderr.write(
            "JULES_API_KEY not set. Re-run with --dry-run or set the env var.\n"
        )
        return None
    try:
        return JulesClient()
    except ConfigurationError as exc:
        sys.stderr.write(f"{exc}\n")
        return None


def _make_dispatcher(root: Path, client: Optional[JulesClient]) -> Dispatcher:
    store = FlaggedIssueStore(root)
    playbook_dir = root / "playbook"
    return Dispatcher(
        store=store,
        client=client,
        playbook_dir=playbook_dir,
        tool_registry=None,
    )


def cmd_enqueue(args: argparse.Namespace) -> int:
    payload = {}
    if args.payload_json is not None:
        payload = json.loads(Path(args.payload_json).read_text(encoding="utf-8"))
    issue = FlaggedIssue(
        id=args.issue_id or _deterministic_id(),
        type=args.issue_type,
        source=args.source,
        playbook=args.playbook,
        target_repo=args.target_repo,
        target_branch=args.target_branch,
        priority=args.priority,
        created_at=_now_iso(),
        state="flagged",
        payload=payload,
    )
    dispatcher = _make_dispatcher(args.root, client=None)
    dispatcher.enqueue(issue)
    sys.stdout.write(json.dumps(issue.to_dict(), indent=2, sort_keys=True) + "\n")
    return 0


def cmd_dispatch(args: argparse.Namespace) -> int:
    client = _make_client_if_possible(args.dry_run)
    dispatcher = _make_dispatcher(args.root, client=client)
    changed = dispatcher.dispatch_queued(
        max_parallel=args.max_parallel, dry_run=args.dry_run
    )
    sys.stdout.write(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "changed_ids": [i.id for i in changed],
            },
            indent=2,
        )
        + "\n"
    )
    return 0


def cmd_poll(args: argparse.Namespace) -> int:
    client = _make_client_if_possible(dry_run=False)
    dispatcher = _make_dispatcher(args.root, client=client)
    changed = dispatcher.poll_in_progress()
    sys.stdout.write(
        json.dumps({"changed_ids": [i.id for i in changed]}, indent=2) + "\n"
    )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    dispatcher = _make_dispatcher(args.root, client=None)
    if args.state:
        issues = dispatcher.store.list_by_state(args.state)
    else:
        issues = dispatcher.store.list_all()
    out = [
        {
            "id": i.id,
            "playbook": i.playbook,
            "state": i.state,
            "priority": i.priority,
            "target_repo": i.target_repo,
            "created_at": i.created_at,
            "retry_count": i.retry_count,
            "session_id": i.session_id,
            "pr_url": i.pr_url,
        }
        for i in issues
    ]
    sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    dispatcher = _make_dispatcher(args.root, client=None)
    issue = dispatcher.store.load(args.issue_id)
    sys.stdout.write(json.dumps(issue.to_dict(), indent=2, sort_keys=True) + "\n")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    client = _make_client_if_possible(dry_run=False)
    dispatcher = _make_dispatcher(args.root, client=client)
    issue = dispatcher.store.load(args.issue_id)
    if client is not None and issue.session_id:
        try:
            client.cancel_session(issue.session_id)
        except JulesApiError as exc:
            sys.stderr.write(f"cancel_session failed: {exc}\n")
    # Force-route to rejected via valid intermediate states.
    if issue.state in ("dispatched", "in-progress"):
        issue.transition("failed")
    if issue.state == "draft-pr":
        issue.transition("rejected")
    elif issue.state == "failed":
        issue.transition("escalated")
    dispatcher.store.save(issue)
    dispatcher.emit_audit_log(issue, outcome=issue.state)
    sys.stdout.write(json.dumps(issue.to_dict(), indent=2, sort_keys=True) + "\n")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    dispatcher = _make_dispatcher(args.root, client=None)
    issue = dispatcher.store.load(args.issue_id)
    audit_id = dispatcher.emit_audit_log(issue)
    sys.stdout.write(
        json.dumps({"issue_id": issue.id, "audit_event_id": audit_id}, indent=2) + "\n"
    )
    return 0


_DISPATCH = {
    "enqueue": cmd_enqueue,
    "dispatch": cmd_dispatch,
    "poll": cmd_poll,
    "list": cmd_list,
    "show": cmd_show,
    "cancel": cmd_cancel,
    "audit": cmd_audit,
}


def main(argv: Optional[list] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _DISPATCH.get(args.command)
    if handler is None:
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
