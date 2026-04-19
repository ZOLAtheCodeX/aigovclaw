"""ActionExecutor: core coordinator for the action-executor layer.

Responsibilities:
    - Validate incoming ActionRequests against the action registry.
    - Resolve the effective authority mode via AuthorityPolicy.
    - Enforce rate limits, safety downgrades, and autonomous opt-ins.
    - Write PRE- and POST-action audit entries.
    - Snapshot the target before mutating handlers run.
    - Invoke the handler and, on failure, attempt a rollback.
    - Manage an approval queue for deferred execution.

The executor is synchronous. Concurrent callers are serialized via a
per-executor RLock; per-request rollback snapshots are keyed by request_id
so they do not collide.
"""

from __future__ import annotations

import importlib
import threading
from pathlib import Path
from typing import Any

from .action_registry import (
    AUTHORITY_ASK,
    AUTHORITY_AUTONOMOUS,
    AUTHORITY_TAKE,
    ActionRequest,
    ActionResult,
    ActionSpec,
    build_registry,
)
from .authority_policy import AuthorityPolicy, load_policy
from .safety import (
    DEFAULT_MEMORY_ROOT,
    AuditLogger,
    RateLimiter,
    new_request_id,
    rollback as safety_rollback,
    snapshot_target,
    utc_now_iso,
)


class ActionValidationError(ValueError):
    """Raised when an ActionRequest is structurally invalid or targets unknown action."""


class ActionExecutor:
    """Central action-executor coordinator.

    Typical lifecycle:
        executor = ActionExecutor()
        result = executor.execute(ActionRequest(...))
        if result.status == "approved-pending":
            executor.approve(result.request_id)  # or reject(...)

    Memory layout (under memory_root):
        action-snapshots/<request_id>/original
        audit-log/YYYY-MM-DD.jsonl
        approvals/<request_id>.json
        notifications/YYYY-MM-DD.log
        cascade-queue/<request_id>.json
        <plugin-name>/<timestamp>.json        (from re-run-plugin)
    """

    def __init__(
        self,
        *,
        memory_root: Path | None = None,
        policy_path: Path | str | None = None,
        policy: AuthorityPolicy | None = None,
    ):
        self.memory_root = Path(memory_root) if memory_root else DEFAULT_MEMORY_ROOT
        self.memory_root.mkdir(parents=True, exist_ok=True)
        self.registry = build_registry()
        self.policy = policy if policy is not None else load_policy(policy_path)
        self.audit = AuditLogger(self.memory_root)
        self.rate_limiter = RateLimiter(self.audit)
        self.approvals_dir = self.memory_root / "approvals"
        self.approvals_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._pending: dict[str, dict[str, Any]] = {}
        self._load_pending_from_disk()

    # ------------------------------------------------------------------
    # Public API.
    # ------------------------------------------------------------------

    def execute(self, request: ActionRequest) -> ActionResult:
        """Execute or queue an ActionRequest. See ActionResult for status values."""
        started = utc_now_iso()
        try:
            spec = self._validate_request(request)
        except ActionValidationError as exc:
            audit_id = self.audit.write({
                "event": "action-rejected",
                "plugin": request.plugin,
                "action": request.action_id,
                "target": request.target,
                "request_id": request.request_id,
                "reason": f"validation: {exc}",
            })
            return ActionResult(
                request_id=request.request_id,
                status="failed",
                authority_mode_used="n/a",
                audit_entry_id=audit_id,
                rollback_snapshot_path=None,
                started_at=started,
                ended_at=utc_now_iso(),
                error=str(exc),
            )

        resolution = self.policy.resolve(request.plugin, spec)

        if self.rate_limiter.over_limit(request.plugin, spec.id, resolution.rate_limit_per_hour):
            audit_id = self.audit.write({
                "event": "action-rate-limited",
                "plugin": request.plugin,
                "action": request.action_id,
                "target": request.target,
                "request_id": request.request_id,
                "limit": resolution.rate_limit_per_hour,
            })
            return ActionResult(
                request_id=request.request_id,
                status="skipped-rate-limit",
                authority_mode_used=resolution.mode,
                audit_entry_id=audit_id,
                rollback_snapshot_path=None,
                started_at=started,
                ended_at=utc_now_iso(),
                output={"rate_limit": resolution.rate_limit_per_hour},
            )

        # git-commit-and-push is hard-forced to ask-permission regardless.
        if spec.id == "git-commit-and-push" and resolution.mode != AUTHORITY_ASK:
            resolution.downgrade_reason = (
                resolution.downgrade_reason
                or "git-commit-and-push is hard-forced to ask-permission"
            )
            resolution.mode = AUTHORITY_ASK

        intent_id = self.audit.write({
            "event": "action-intent",
            "request_id": request.request_id,
            "plugin": request.plugin,
            "action": request.action_id,
            "target": request.target,
            "authority_mode": resolution.mode,
            "authority_downgrade_reason": resolution.downgrade_reason,
            "risk_tier": spec.risk_tier,
            "dry_run": request.dry_run,
            "rationale": request.rationale,
        })

        if resolution.mode == AUTHORITY_ASK and not request.dry_run:
            return self._enqueue_for_approval(request, spec, resolution.mode, intent_id, started)

        return self._run_handler(request, spec, resolution.mode, intent_id, started)

    def approve(self, request_id: str, *, approver: str = "operator") -> ActionResult:
        """Unblock a queued request and run it through the handler."""
        with self._lock:
            record = self._pending.get(request_id)
        if record is None:
            raise KeyError(f"no pending approval for request_id={request_id}")
        if record.get("decision") is not None:
            raise RuntimeError(
                f"request {request_id} already decided: {record['decision']}"
            )

        self.audit.write({
            "event": "action-approved",
            "request_id": request_id,
            "approver": approver,
            "plugin": record["request"].plugin,
            "action": record["request"].action_id,
        })
        record["decision"] = "approved"
        record["decided_by"] = approver
        self._persist_pending(record)

        request: ActionRequest = record["request"]
        spec: ActionSpec = self.registry[request.action_id]
        started = utc_now_iso()

        with self._lock:
            self._pending.pop(request_id, None)

        return self._run_handler(request, spec, AUTHORITY_ASK, record["intent_audit_id"], started)

    def reject(self, request_id: str, reason: str, *, approver: str = "operator") -> ActionResult:
        """Mark a pending request as rejected. Never invokes the handler."""
        with self._lock:
            record = self._pending.get(request_id)
        if record is None:
            raise KeyError(f"no pending approval for request_id={request_id}")

        audit_id = self.audit.write({
            "event": "action-rejected",
            "request_id": request_id,
            "plugin": record["request"].plugin,
            "action": record["request"].action_id,
            "approver": approver,
            "reason": reason,
        })
        record["decision"] = "rejected"
        record["decided_by"] = approver
        record["reason"] = reason
        self._persist_pending(record)
        with self._lock:
            self._pending.pop(request_id, None)

        now = utc_now_iso()
        return ActionResult(
            request_id=request_id,
            status="rejected",
            authority_mode_used=AUTHORITY_ASK,
            audit_entry_id=audit_id,
            rollback_snapshot_path=None,
            started_at=now,
            ended_at=now,
            error=reason,
        )

    def pending(self) -> list[dict[str, Any]]:
        """Snapshot of pending approval records (excludes decision metadata only)."""
        with self._lock:
            out: list[dict[str, Any]] = []
            for rid, rec in self._pending.items():
                req: ActionRequest = rec["request"]
                spec = self.registry.get(req.action_id)
                out.append({
                    "request_id": rid,
                    "plugin": req.plugin,
                    "action": req.action_id,
                    "target": req.target,
                    "rationale": req.rationale,
                    "queued_at": rec.get("queued_at"),
                    "risk_tier": spec.risk_tier if spec else None,
                })
            return out

    # ------------------------------------------------------------------
    # Internal helpers.
    # ------------------------------------------------------------------

    def _validate_request(self, request: ActionRequest) -> ActionSpec:
        if not isinstance(request, ActionRequest):
            raise ActionValidationError("request must be an ActionRequest instance")
        if not request.action_id:
            raise ActionValidationError("request.action_id is required")
        if not request.plugin:
            raise ActionValidationError("request.plugin is required")
        if not request.request_id:
            raise ActionValidationError("request.request_id is required")
        if not request.requested_at:
            raise ActionValidationError("request.requested_at is required")
        if not isinstance(request.args, dict):
            raise ActionValidationError("request.args must be a dict")
        spec = self.registry.get(request.action_id)
        if spec is None:
            raise ActionValidationError(
                f"unknown action_id {request.action_id!r}; "
                f"known: {sorted(self.registry)}"
            )
        missing = [k for k in spec.args_schema if k not in request.args]
        # For args_schema listed fields, require at least the first one as
        # "primary" (path / mcp_server / plugin_name / channel / cascade_node_id /
        # repo_path). Remaining fields are soft-required and handler-validated.
        if spec.args_schema and spec.args_schema[0] not in request.args:
            raise ActionValidationError(
                f"action {spec.id!r} requires args[{spec.args_schema[0]!r}]; "
                f"missing: {missing}"
            )
        return spec

    def _enqueue_for_approval(
        self,
        request: ActionRequest,
        spec: ActionSpec,
        mode: str,
        intent_audit_id: str,
        started: str,
    ) -> ActionResult:
        queued_at = utc_now_iso()
        record = {
            "request_id": request.request_id,
            "request": request,
            "intent_audit_id": intent_audit_id,
            "queued_at": queued_at,
            "decision": None,
            "decided_by": None,
            "reason": None,
        }
        with self._lock:
            self._pending[request.request_id] = record
        self._persist_pending(record)
        return ActionResult(
            request_id=request.request_id,
            status="approved-pending",
            authority_mode_used=mode,
            audit_entry_id=intent_audit_id,
            rollback_snapshot_path=None,
            started_at=started,
            ended_at=utc_now_iso(),
            output={"queued_at": queued_at},
        )

    def _run_handler(
        self,
        request: ActionRequest,
        spec: ActionSpec,
        mode: str,
        intent_audit_id: str,
        started: str,
    ) -> ActionResult:
        if request.dry_run:
            try:
                handler = importlib.import_module(spec.handler_module)
                output = handler.handle(request, dry_run=True)
            except Exception as exc:
                audit_id = self.audit.write({
                    "event": "action-failed",
                    "request_id": request.request_id,
                    "plugin": request.plugin,
                    "action": request.action_id,
                    "dry_run": True,
                    "error": f"{type(exc).__name__}: {exc}",
                    "rollback_attempted": False,
                })
                return ActionResult(
                    request_id=request.request_id,
                    status="failed",
                    authority_mode_used=mode,
                    audit_entry_id=audit_id,
                    rollback_snapshot_path=None,
                    started_at=started,
                    ended_at=utc_now_iso(),
                    error=str(exc),
                )
            audit_id = self.audit.write({
                "event": "action-dry-run",
                "request_id": request.request_id,
                "plugin": request.plugin,
                "action": request.action_id,
                "output": output,
            })
            return ActionResult(
                request_id=request.request_id,
                status="skipped-dry-run",
                authority_mode_used=mode,
                audit_entry_id=audit_id,
                rollback_snapshot_path=None,
                started_at=started,
                ended_at=utc_now_iso(),
                output=output,
            )

        # Snapshot when handler mutates local files.
        snapshot_dir: Path | None = None
        snapshot_target_path: Path | None = None
        if spec.id == "file-update":
            path_str = request.args.get("path")
            if path_str:
                snapshot_target_path = Path(str(path_str)).expanduser().resolve()
                snapshot_dir = snapshot_target(
                    self.memory_root, request.request_id, snapshot_target_path
                )
        elif spec.id == "re-run-plugin":
            # Snapshot the plugin's output dir so rerun can be undone.
            plugin_name = request.args.get("plugin_name") or request.target
            if plugin_name:
                snapshot_target_path = self.memory_root / str(plugin_name)
                snapshot_dir = snapshot_target(
                    self.memory_root, request.request_id, snapshot_target_path
                )

        try:
            handler = importlib.import_module(spec.handler_module)
            output = handler.handle(request, dry_run=False)
        except Exception as exc:
            rollback_attempted = snapshot_dir is not None and snapshot_target_path is not None
            rollback_ok = False
            if rollback_attempted:
                rollback_ok = safety_rollback(snapshot_dir, snapshot_target_path)
            audit_id = self.audit.write({
                "event": "action-failed",
                "request_id": request.request_id,
                "plugin": request.plugin,
                "action": request.action_id,
                "target": request.target,
                "error": f"{type(exc).__name__}: {exc}",
                "rollback_attempted": rollback_attempted,
                "rollback_successful": rollback_ok,
                "rollback_snapshot_path": str(snapshot_dir) if snapshot_dir else None,
            })
            status = "rolled-back" if rollback_attempted and rollback_ok else "failed"
            return ActionResult(
                request_id=request.request_id,
                status=status,
                authority_mode_used=mode,
                audit_entry_id=audit_id,
                rollback_snapshot_path=str(snapshot_dir) if snapshot_dir else None,
                started_at=started,
                ended_at=utc_now_iso(),
                error=str(exc),
            )

        audit_id = self.audit.write({
            "event": "action-completed",
            "request_id": request.request_id,
            "plugin": request.plugin,
            "action": request.action_id,
            "target": request.target,
            "output": output,
            "rollback_snapshot_path": str(snapshot_dir) if snapshot_dir else None,
        })
        return ActionResult(
            request_id=request.request_id,
            status="executed",
            authority_mode_used=mode,
            audit_entry_id=audit_id,
            rollback_snapshot_path=str(snapshot_dir) if snapshot_dir else None,
            started_at=started,
            ended_at=utc_now_iso(),
            output=output,
        )

    # ------------------------------------------------------------------
    # Persistence of pending approvals (survives process restart).
    # ------------------------------------------------------------------

    def _persist_pending(self, record: dict[str, Any]) -> None:
        path = self.approvals_dir / f"{record['request_id']}.json"
        req: ActionRequest = record["request"]
        import json
        payload = {
            "request_id": req.request_id,
            "action_id": req.action_id,
            "plugin": req.plugin,
            "target": req.target,
            "args": req.args,
            "rationale": req.rationale,
            "dry_run": req.dry_run,
            "requested_at": req.requested_at,
            "queued_at": record.get("queued_at"),
            "intent_audit_id": record.get("intent_audit_id"),
            "decision": record.get("decision"),
            "decided_by": record.get("decided_by"),
            "reason": record.get("reason"),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_pending_from_disk(self) -> None:
        import json
        for child in sorted(self.approvals_dir.iterdir()) if self.approvals_dir.exists() else []:
            if child.suffix != ".json":
                continue
            try:
                data = json.loads(child.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            if data.get("decision") is not None:
                continue
            req = ActionRequest(
                action_id=data["action_id"],
                plugin=data["plugin"],
                target=data["target"],
                args=data.get("args") or {},
                rationale=data.get("rationale") or "",
                dry_run=bool(data.get("dry_run")),
                requested_at=data["requested_at"],
                request_id=data["request_id"],
            )
            self._pending[req.request_id] = {
                "request_id": req.request_id,
                "request": req,
                "intent_audit_id": data.get("intent_audit_id") or "",
                "queued_at": data.get("queued_at"),
                "decision": None,
                "decided_by": None,
                "reason": None,
            }
