"""
Jules Dispatcher for AIGovClaw

Orchestrates Google Jules background-maintenance sessions against the
AIGovOps catalogue. This module owns the full lifecycle of a FlaggedIssue
record: persistence, state transitions, Jules REST API calls, activity
polling, failure classification, retry, and audit-log emission.

Design reference: aigovclaw/docs/jules-integration-design.md. This module
implements Section 3 (dispatch model), Section 8 (failure handling), and
Section 9 (observability and audit).

Authoritative facts pinned to code here:

- API base: https://jules.googleapis.com/v1alpha/
- Auth header: X-Goog-Api-Key (loaded from JULES_API_KEY env var)
- State machine transitions per design Section 3.2.
- Every terminal transition (merged, rejected, escalated) emits an audit
  event via the AIGovOps audit-log-generator plugin (ISO 42001 Clause 9.1).

This module is standard-library only except for `requests` (declared in
requirements.txt). It does not install anything. Logging goes to stderr
with structured metadata only; payloads are never logged.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


AGENT_SIGNATURE = "jules-dispatcher/0.1.0"

JULES_API_BASE = "https://jules.googleapis.com/v1alpha/"
JULES_API_KEY_ENV = "JULES_API_KEY"

DEFAULT_MAX_PARALLEL = 3
DEFAULT_MAX_RETRIES = 2
DEFAULT_POLL_INTERVAL_ACTIVE_SECONDS = 15
DEFAULT_POLL_INTERVAL_PLAN_WAIT_SECONDS = 60
DEFAULT_TERMINAL_GRACE_SECONDS = 120


# State machine. See design Section 3.2.
VALID_STATES = (
    "flagged",
    "queued",
    "dispatched",
    "in-progress",
    "draft-pr",
    "reviewed",
    "merged",
    "failed",
    "escalated",
    "rejected",
)

TERMINAL_STATES = ("merged", "rejected", "escalated")

VALID_TRANSITIONS = {
    "flagged": ("queued",),
    "queued": ("dispatched",),
    "dispatched": ("in-progress", "failed"),
    "in-progress": ("draft-pr", "failed"),
    "draft-pr": ("reviewed", "rejected", "failed"),
    "reviewed": ("merged",),
    "failed": ("queued", "escalated"),
    "merged": (),
    "rejected": (),
    "escalated": (),
}


# Retriable failure classes. See design Section 8.3.
RETRIABLE_FAILURE_CLASSES = (
    "install-failure",
    "vm-timeout",
    "network-error",
)

TERMINAL_FAILURE_CLASSES = (
    "plan-out-of-scope",
    "plan-exceeds-max-files",
    "ci-failed-after-pr",
    "forbidden-file-touched",
    "model-refused",
)


_log = logging.getLogger("jules.dispatcher")


def _configure_logger() -> None:
    if _log.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    _log.addHandler(handler)
    _log.setLevel(logging.INFO)


_configure_logger()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class JulesError(Exception):
    """Base class for all dispatcher errors."""


class JulesApiError(JulesError):
    """Raised when the Jules REST API returns a non-2xx response."""

    def __init__(self, status_code: int, body: Any, url: str) -> None:
        self.status_code = status_code
        self.body = body
        self.url = url
        super().__init__(f"jules api error {status_code} at {url}: {body!r}")


class StateTransitionError(JulesError):
    """Raised when an invalid state transition is attempted."""


class ConfigurationError(JulesError):
    """Raised when required configuration (env var, file) is missing."""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _deterministic_id(prefix: str = "fi") -> str:
    """Generate a deterministic-ish unique id.

    Uses uuid4 for uniqueness but without randomness elsewhere in the
    dispatcher. Callers that need fully deterministic ids should pass
    their own id to FlaggedIssue.
    """
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ---------------------------------------------------------------------------
# FlaggedIssue dataclass
# ---------------------------------------------------------------------------


@dataclass
class FlaggedIssue:
    """Record describing a single maintenance task dispatched to Jules.

    Matches the schema in design Section 3.1. Optional fields populated
    as the lifecycle advances. Use to_dict / from_dict for JSON persistence.
    """

    id: str
    type: str
    source: str
    playbook: str
    target_repo: str
    target_branch: str = "main"
    priority: str = "normal"
    created_at: str = field(default_factory=_now_iso)
    state: str = "flagged"
    retry_count: int = 0
    session_id: Optional[str] = None
    session_url: Optional[str] = None
    pr_url: Optional[str] = None
    final_state: Optional[str] = None
    audit_event_id: Optional[str] = None
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FlaggedIssue":
        allowed = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)

    def transition(self, target: str) -> None:
        """Move to a new state. Raises StateTransitionError if invalid."""
        if target not in VALID_STATES:
            raise StateTransitionError(f"unknown target state {target!r}")
        allowed = VALID_TRANSITIONS.get(self.state, ())
        if target not in allowed:
            raise StateTransitionError(
                f"invalid transition {self.state!r} -> {target!r}; "
                f"allowed: {list(allowed)}"
            )
        self.state = target
        if target in TERMINAL_STATES:
            self.final_state = target


# ---------------------------------------------------------------------------
# Flagged issue store (JSON file backend)
# ---------------------------------------------------------------------------


class FlaggedIssueStore:
    """Filesystem-backed persistence for FlaggedIssue records.

    Default layout:
      <root>/flagged/<id>.json      active records
      <root>/archive/YYYY-MM/<id>.json  archived terminal records

    Not thread-safe. Single-owner pattern expected per the harness
    paradigm.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.flagged_dir = self.root / "flagged"
        self.archive_dir = self.root / "archive"
        self.flagged_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, issue_id: str) -> Path:
        safe = issue_id.replace("/", "_")
        return self.flagged_dir / f"{safe}.json"

    def save(self, issue: FlaggedIssue) -> None:
        path = self._path(issue.id)
        payload = json.dumps(issue.to_dict(), indent=2, sort_keys=True)
        path.write_text(payload, encoding="utf-8")
        _log.info(
            "issue_saved id=%s state=%s playbook=%s bytes=%d",
            issue.id, issue.state, issue.playbook, len(payload),
        )

    def load(self, issue_id: str) -> FlaggedIssue:
        path = self._path(issue_id)
        if not path.is_file():
            # Look in archive as fallback.
            for sub in sorted(self.archive_dir.glob("*/")):
                candidate = sub / f"{issue_id}.json"
                if candidate.is_file():
                    path = candidate
                    break
            else:
                raise FileNotFoundError(f"flagged issue {issue_id!r} not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        return FlaggedIssue.from_dict(data)

    def list_all(self) -> list[FlaggedIssue]:
        out: list[FlaggedIssue] = []
        for p in sorted(self.flagged_dir.glob("*.json")):
            try:
                out.append(FlaggedIssue.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except Exception as exc:
                _log.warning("skip_unreadable_record path=%s err=%s", p, exc)
        return out

    def list_by_state(self, state: str) -> list[FlaggedIssue]:
        if state not in VALID_STATES:
            raise ValueError(f"unknown state {state!r}")
        return [i for i in self.list_all() if i.state == state]

    def archive(self, issue_id: str) -> Path:
        """Move a terminal-state record into archive/YYYY-MM/."""
        issue = self.load(issue_id)
        if issue.state not in TERMINAL_STATES:
            raise ValueError(
                f"cannot archive {issue_id!r} in non-terminal state {issue.state!r}"
            )
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        month_dir = self.archive_dir / month
        month_dir.mkdir(parents=True, exist_ok=True)
        src = self._path(issue_id)
        dst = month_dir / src.name
        if src.is_file():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            src.unlink()
        _log.info("issue_archived id=%s dst=%s", issue_id, dst)
        return dst


# ---------------------------------------------------------------------------
# Jules REST client
# ---------------------------------------------------------------------------


class JulesClient:
    """Thin wrapper around the Jules REST API (v1alpha).

    Endpoints used:
      POST   /sessions
      POST   /sessions/{id}:sendMessage
      POST   /sessions/{id}:approvePlan
      GET    /sessions/{id}
      GET    /sessions/{id}/activities
      POST   /sessions/{id}:cancel

    Auth header: X-Goog-Api-Key: $JULES_API_KEY. No other auth is accepted.

    The `requests` library is imported lazily so this module remains
    importable in test environments where requests is not installed.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = JULES_API_BASE,
        session: Any = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        key = api_key or os.environ.get(JULES_API_KEY_ENV)
        if not key:
            raise ConfigurationError(
                f"{JULES_API_KEY_ENV} env var not set; refusing to start"
            )
        self._api_key = key
        self._base_url = base_url.rstrip("/") + "/"
        self._timeout = timeout_seconds
        self._session = session  # may be None; lazy-init
        self._user_agent = AGENT_SIGNATURE

    def _require_session(self) -> Any:
        if self._session is not None:
            return self._session
        try:
            import requests  # type: ignore
        except ImportError as exc:
            raise ConfigurationError(
                "requests library not available; install requests>=2.31.0"
            ) from exc
        self._session = requests.Session()
        return self._session

    def _headers(self) -> dict[str, str]:
        return {
            "X-Goog-Api-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }

    def _url(self, path: str) -> str:
        return self._base_url + path.lstrip("/")

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        session = self._require_session()
        url = self._url(path)
        start = time.monotonic()
        resp = session.request(
            method=method,
            url=url,
            headers=self._headers(),
            data=(json.dumps(body) if body is not None else None),
            timeout=self._timeout,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        status = getattr(resp, "status_code", 0)
        content = getattr(resp, "content", b"") or b""
        _log.info(
            "jules_api method=%s path=%s status=%d bytes=%d duration_ms=%d",
            method, path, status, len(content), duration_ms,
        )
        if status < 200 or status >= 300:
            try:
                body_parsed = resp.json()
            except Exception:
                body_parsed = getattr(resp, "text", "")
            raise JulesApiError(status, body_parsed, url)
        if not content:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    # -- typed endpoints --

    def create_session(
        self,
        repo: str,
        prompt: str,
        branch: str = "main",
        parallel: int = 1,
        require_plan_approval: bool = True,
    ) -> dict:
        if not repo or not isinstance(repo, str):
            raise ValueError("repo must be a non-empty string")
        if not prompt or not isinstance(prompt, str):
            raise ValueError("prompt must be a non-empty string")
        if parallel < 1 or parallel > 60:
            raise ValueError("parallel must be between 1 and 60")
        body = {
            "prompt": prompt,
            "requirePlanApproval": require_plan_approval,
            "sources": [
                {
                    "githubRepo": {
                        "repo": repo,
                        "branch": branch,
                    }
                }
            ],
            "parallel": parallel,
        }
        return self._request("POST", "sessions", body)

    def send_message(self, session_id: str, text: str) -> dict:
        self._require_session_id(session_id)
        if not text or not isinstance(text, str):
            raise ValueError("text must be a non-empty string")
        return self._request(
            "POST", f"sessions/{session_id}:sendMessage", {"text": text}
        )

    def approve_plan(self, session_id: str) -> dict:
        self._require_session_id(session_id)
        return self._request("POST", f"sessions/{session_id}:approvePlan", {})

    def get_session(self, session_id: str) -> dict:
        self._require_session_id(session_id)
        return self._request("GET", f"sessions/{session_id}")

    def list_activities(self, session_id: str) -> dict:
        self._require_session_id(session_id)
        return self._request("GET", f"sessions/{session_id}/activities")

    def cancel_session(self, session_id: str) -> dict:
        self._require_session_id(session_id)
        return self._request("POST", f"sessions/{session_id}:cancel", {})

    @staticmethod
    def _require_session_id(session_id: str) -> None:
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id must be a non-empty string")


# ---------------------------------------------------------------------------
# Playbook loader
# ---------------------------------------------------------------------------


PLAYBOOK_NAMES = (
    "framework-drift",
    "test-coverage-gap",
    "dep-bump",
    "citation-drift",
    "markdown-lint",
    "new-plugin-scaffold",
    "link-toc",
    "prohibited-content-sweep",
)


def load_playbook_prompt(playbook_dir: Path, name: str) -> str:
    if name not in PLAYBOOK_NAMES:
        raise ValueError(f"unknown playbook {name!r}; valid: {PLAYBOOK_NAMES}")
    path = Path(playbook_dir) / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"playbook file missing: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------


def classify_failure(reason: str) -> str:
    """Map a failure reason string to a class label.

    Best-effort keyword match. Unknown reasons are classified as
    model-refused (terminal) to force escalation and avoid silent loops.
    """
    text = (reason or "").lower()
    if "install" in text or "npm" in text or "pip" in text:
        return "install-failure"
    if "timeout" in text:
        return "vm-timeout"
    if "network" in text or "dns" in text or "connection" in text:
        return "network-error"
    if "out-of-scope" in text or "forbidden" in text:
        return "plan-out-of-scope"
    if "max-files" in text or "too many files" in text:
        return "plan-exceeds-max-files"
    if "ci" in text and "fail" in text:
        return "ci-failed-after-pr"
    if "refuse" in text or "refused" in text:
        return "model-refused"
    return "model-refused"


def is_retriable(failure_class: str) -> bool:
    return failure_class in RETRIABLE_FAILURE_CLASSES


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class Dispatcher:
    """Orchestrates FlaggedIssue lifecycle against the Jules REST API.

    Single-owner of the FlaggedIssueStore. Invokes the AIGovOps
    audit-log-generator tool via the AIGovClaw tool registry (if present)
    on every terminal transition.

    Parameters:
      store: FlaggedIssueStore backing the queue.
      client: JulesClient for REST calls. None means dry-run mode (no API).
      playbook_dir: Directory containing the playbook .md files.
      tool_registry: optional AIGovClaw tool registry. When present the
                     audit-log-generator tool is invoked on terminal states.
      max_retries: maximum retry_count before forced escalation.
    """

    def __init__(
        self,
        store: FlaggedIssueStore,
        client: Optional[JulesClient],
        playbook_dir: Path,
        tool_registry: Any = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.store = store
        self.client = client
        self.playbook_dir = Path(playbook_dir)
        self.tool_registry = tool_registry
        self.max_retries = max_retries

    # -- enqueue --

    def enqueue(self, issue: FlaggedIssue) -> FlaggedIssue:
        """Persist a new issue in state 'flagged' and advance it to 'queued'.

        Validation happens here: state must be 'flagged', playbook must be
        known, target_repo must be set.
        """
        if issue.state != "flagged":
            raise StateTransitionError(
                f"issue {issue.id!r} must be in 'flagged' to enqueue, got {issue.state!r}"
            )
        if issue.playbook not in PLAYBOOK_NAMES:
            raise ValueError(
                f"unknown playbook {issue.playbook!r}; valid: {PLAYBOOK_NAMES}"
            )
        if not issue.target_repo:
            raise ValueError("target_repo is required")
        issue.transition("queued")
        self.store.save(issue)
        _log.info(
            "issue_enqueued id=%s playbook=%s target_repo=%s priority=%s",
            issue.id, issue.playbook, issue.target_repo, issue.priority,
        )
        return issue

    # -- dispatch queued --

    def dispatch_queued(
        self,
        max_parallel: int = DEFAULT_MAX_PARALLEL,
        dry_run: bool = False,
    ) -> list[FlaggedIssue]:
        """Dispatch up to max_parallel queued issues to Jules.

        Dry run prints the intended API calls to stderr without making them.
        Returns the list of issues whose state changed.
        """
        queued = self.store.list_by_state("queued")
        in_progress = self.store.list_by_state("dispatched") + self.store.list_by_state("in-progress")
        slots = max(0, max_parallel - len(in_progress))
        _log.info(
            "dispatch_queued queued=%d in_progress=%d slots=%d dry_run=%s",
            len(queued), len(in_progress), slots, dry_run,
        )
        # Priority order: high > normal > low; stable by created_at.
        priority_rank = {"high": 0, "normal": 1, "low": 2}
        queued.sort(key=lambda i: (priority_rank.get(i.priority, 1), i.created_at))
        changed: list[FlaggedIssue] = []
        for issue in queued[:slots]:
            try:
                prompt = load_playbook_prompt(self.playbook_dir, issue.playbook)
            except FileNotFoundError as exc:
                _log.error("playbook_missing id=%s err=%s", issue.id, exc)
                continue
            full_prompt = _render_prompt(prompt, issue)
            if dry_run or self.client is None:
                sys.stderr.write(
                    f"[dry-run] POST /sessions repo={issue.target_repo} "
                    f"branch={issue.target_branch} playbook={issue.playbook} "
                    f"prompt_bytes={len(full_prompt)}\n"
                )
                continue
            try:
                resp = self.client.create_session(
                    repo=issue.target_repo,
                    prompt=full_prompt,
                    branch=issue.target_branch,
                    parallel=1,
                )
            except JulesApiError as exc:
                _log.error("create_session_failed id=%s status=%d", issue.id, exc.status_code)
                continue
            session_id = resp.get("id") or resp.get("name", "").split("/")[-1]
            session_url = resp.get("url") or resp.get("webUrl")
            issue.session_id = session_id
            issue.session_url = session_url
            issue.transition("dispatched")
            self.store.save(issue)
            changed.append(issue)
            _log.info(
                "issue_dispatched id=%s session_id=%s",
                issue.id, session_id,
            )
        return changed

    # -- poll in-progress --

    def poll_in_progress(self) -> list[FlaggedIssue]:
        """Poll active sessions and advance state based on activity feed."""
        if self.client is None:
            _log.info("poll_skipped reason=no_client")
            return []
        changed: list[FlaggedIssue] = []
        active = self.store.list_by_state("dispatched") + self.store.list_by_state("in-progress")
        for issue in active:
            if not issue.session_id:
                continue
            try:
                activities = self.client.list_activities(issue.session_id)
            except JulesApiError as exc:
                _log.error(
                    "list_activities_failed id=%s status=%d",
                    issue.id, exc.status_code,
                )
                continue
            advanced = self._advance_from_activities(issue, activities)
            if advanced:
                self.store.save(issue)
                changed.append(issue)
        return changed

    def _advance_from_activities(self, issue: FlaggedIssue, activities: dict) -> bool:
        """Advance the issue's state based on the activity feed payload.

        The activity feed shape is thin here: the dispatcher looks for
        known activity kinds. Unknown kinds do not advance state.
        """
        items = activities.get("activities") or activities.get("items") or []
        advanced = False
        for item in items:
            kind = (item.get("kind") or item.get("type") or "").lower()
            if issue.state == "dispatched" and kind and kind != "setup":
                issue.transition("in-progress")
                advanced = True
            if "pullrequest" in kind or "pr-opened" in kind or kind == "pr":
                pr_url = item.get("url") or item.get("prUrl")
                if pr_url:
                    issue.pr_url = pr_url
                if issue.state == "in-progress":
                    issue.transition("draft-pr")
                    advanced = True
            if "failure" in kind or "failed" in kind:
                reason = item.get("reason") or item.get("message") or ""
                failure_class = classify_failure(reason)
                _log.warning(
                    "jules_failure id=%s class=%s reason=%s",
                    issue.id, failure_class, reason[:200],
                )
                if issue.state in ("dispatched", "in-progress", "draft-pr"):
                    issue.transition("failed")
                    advanced = True
                    self.handle_terminal_failure(issue, failure_class)
                    break
        return advanced

    # -- terminal handling --

    def handle_terminal_failure(self, issue: FlaggedIssue, failure_class: str) -> None:
        """Apply the failure decision tree from design Section 8.3."""
        retriable = is_retriable(failure_class)
        if retriable and issue.retry_count < self.max_retries:
            issue.retry_count += 1
            issue.transition("queued")
            _log.info(
                "failure_retry id=%s class=%s retry_count=%d",
                issue.id, failure_class, issue.retry_count,
            )
            self.store.save(issue)
            return
        # Escalate.
        issue.transition("escalated")
        _log.info(
            "failure_escalated id=%s class=%s retry_count=%d",
            issue.id, failure_class, issue.retry_count,
        )
        self.store.save(issue)
        self.emit_audit_log(issue, outcome="escalated")

    def handle_terminal(self, session_id: str, outcome: str) -> FlaggedIssue:
        """Resolve a session_id to its FlaggedIssue, transition to terminal
        state, and emit the audit log.

        Valid outcomes: merged, rejected, escalated. The issue must be in
        a state from which this outcome is reachable.
        """
        if outcome not in TERMINAL_STATES:
            raise ValueError(f"outcome must be one of {TERMINAL_STATES}")
        match = None
        for issue in self.store.list_all():
            if issue.session_id == session_id:
                match = issue
                break
        if match is None:
            raise KeyError(f"no flagged issue has session_id={session_id!r}")
        # Route to the appropriate pre-state if needed.
        if outcome == "merged" and match.state == "draft-pr":
            match.transition("reviewed")
        if outcome == "merged":
            match.transition("merged")
        elif outcome == "rejected":
            match.transition("rejected")
        elif outcome == "escalated":
            if match.state != "failed":
                # Force a valid path: only transition if permitted.
                if "failed" in VALID_TRANSITIONS.get(match.state, ()):
                    match.transition("failed")
            match.transition("escalated")
        self.store.save(match)
        self.emit_audit_log(match, outcome=outcome)
        return match

    # -- audit --

    def emit_audit_log(self, issue: FlaggedIssue, outcome: Optional[str] = None) -> Optional[str]:
        """Invoke the AIGovOps audit-log-generator tool and record the
        audit_event_id on the issue.

        When the tool registry is not present (dry-run, test), this logs
        metadata and stamps a synthetic audit_event_id derived from the
        issue id and timestamp. That id is deterministic and the absence of
        a registry is a governance defect in production.
        """
        effective_outcome = outcome or issue.final_state or issue.state
        event_metadata = {
            "event_type": "autonomous-agent-action",
            "actor": "jules",
            "playbook": issue.playbook,
            "outcome": effective_outcome,
            "iso_42001_clause": "9.1",
            "linked_records": [
                f"flagged-issue:{issue.id}",
                f"jules-session:{issue.session_id or 'none'}",
                f"pr:{issue.pr_url or 'none'}",
            ],
            "agent_signature": AGENT_SIGNATURE,
        }
        audit_event_id: Optional[str] = None
        if self.tool_registry is not None:
            try:
                tool_inputs = {
                    "system_name": f"aigovclaw/jules-dispatcher",
                    "purpose": f"Autonomous maintenance action by Jules via playbook {issue.playbook}.",
                    "risk_tier": "limited",
                    "data_processed": ["flagged-issue-metadata", "jules-session-metadata"],
                    "deployment_context": f"target_repo={issue.target_repo}",
                    "governance_decisions": [
                        f"Jules session {issue.session_id or 'none'} outcome: {effective_outcome}.",
                    ],
                    "responsible_parties": ["AIGovClaw Dispatcher", "Human Reviewer"],
                }
                result = self.tool_registry.invoke("generate_audit_log", tool_inputs)
                audit_event_id = (
                    result.get("audit_event_id")
                    or result.get("id")
                    or _synthetic_audit_id(issue)
                )
            except Exception as exc:
                _log.error(
                    "audit_emit_failed id=%s err=%s",
                    issue.id, exc,
                )
                audit_event_id = _synthetic_audit_id(issue)
        else:
            audit_event_id = _synthetic_audit_id(issue)
            _log.info(
                "audit_emit_synthetic id=%s audit_event_id=%s outcome=%s",
                issue.id, audit_event_id, effective_outcome,
            )
        issue.audit_event_id = audit_event_id
        self.store.save(issue)
        _log.info(
            "audit_emitted id=%s audit_event_id=%s outcome=%s metadata_keys=%d",
            issue.id, audit_event_id, effective_outcome, len(event_metadata),
        )
        return audit_event_id


def _synthetic_audit_id(issue: FlaggedIssue) -> str:
    return f"audit-synth-{issue.id}-{_now_iso().replace(':', '').replace('-', '')}"


def _render_prompt(template: str, issue: FlaggedIssue) -> str:
    """Substitute simple placeholders in a playbook template.

    Placeholders: {{ISSUE_ID}}, {{TARGET_REPO}}, {{TARGET_BRANCH}},
    {{PAYLOAD_JSON}}, {{BRANCH_NAME}}, {{PR_TITLE}}. No templating
    library dependency.
    """
    branch_name = f"jules/{issue.playbook}-{issue.id}"
    pr_title = f"[jules:{issue.playbook}] {issue.type} ({issue.id})"
    payload_json = json.dumps(issue.payload, indent=2, sort_keys=True)
    replacements = {
        "{{ISSUE_ID}}": issue.id,
        "{{TARGET_REPO}}": issue.target_repo,
        "{{TARGET_BRANCH}}": issue.target_branch,
        "{{PAYLOAD_JSON}}": payload_json,
        "{{BRANCH_NAME}}": branch_name,
        "{{PR_TITLE}}": pr_title,
        "{{PLAYBOOK}}": issue.playbook,
    }
    rendered = template
    for k, v in replacements.items():
        rendered = rendered.replace(k, v)
    return rendered


__all__ = [
    "AGENT_SIGNATURE",
    "FlaggedIssue",
    "FlaggedIssueStore",
    "JulesClient",
    "JulesApiError",
    "JulesError",
    "StateTransitionError",
    "ConfigurationError",
    "Dispatcher",
    "PLAYBOOK_NAMES",
    "VALID_STATES",
    "VALID_TRANSITIONS",
    "TERMINAL_STATES",
    "RETRIABLE_FAILURE_CLASSES",
    "TERMINAL_FAILURE_CLASSES",
    "classify_failure",
    "is_retriable",
    "load_playbook_prompt",
]
