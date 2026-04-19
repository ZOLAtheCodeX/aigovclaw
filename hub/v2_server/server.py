"""Hub v2 command-center HTTP server (stdlib only).

Endpoints (all return JSON unless noted):

  GET  /                             The Hub v2 single-file HTML.
  GET  /api/health                   Composite system health.
  GET  /api/commands                 Public command registry.
  POST /api/tasks                    Enqueue a task. Body: {command, args}.
  GET  /api/tasks                    List tasks. Query: limit, since, status.
  GET  /api/tasks/{id}               Single task detail (includes stdout_tail).
  POST /api/tasks/{id}/pause         Suspend a running task.
  POST /api/tasks/{id}/resume        Resume a paused task.
  POST /api/tasks/{id}/cancel        Terminate a task.
  GET  /api/artifacts                Metadata for artifacts in the evidence store.
  GET  /api/approvals                Pending approvals.
  POST /api/approvals/{id}/approve   Approve and promote the task.
  POST /api/approvals/{id}/reject    Reject and cancel the task.

Design choices (documented here because the prompt calls them out):
  - Polling, not WebSockets. The Hub polls /api/tasks every 2s and /api/health
    every 10s. stdlib-only; WebSockets would require a second event loop.
  - Same-origin only. The server serves the HTML and the API, so CORS is not
    configured. Non-127.0.0.1 binds require --host. Document this before
    enabling remote access.
  - No multi-user auth. Local use only. Anyone who can reach the port can
    enqueue tasks. Do not expose the port on untrusted networks.
  - No persistent queue. In-flight tasks at shutdown are marked INTERRUPTED on
    restart via TaskRunner._reap_orphans_on_startup. Completed task state
    persists on disk.
"""

from __future__ import annotations

import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
import urllib.parse
from pathlib import Path
from typing import Any

from ..generator import resolve_evidence_path
from ..v2.generator import generate as generate_v2_html, VendorMissingError, DEFAULT_AIGOVOPS_ROOT
from . import task_runner
from .approval_queue import ApprovalQueue
from .command_registry import build_registry, public_registry, resolve_aigovops_root
from .health import compute_health


class CommandCenterState:
    """Container for server-wide dependencies. One instance per server."""

    def __init__(
        self,
        *,
        evidence_path: Path,
        aigovops_root: Path | None,
        tasks_dir: Path | None = None,
        approvals_dir: Path | None = None,
        html_cache_dir: Path | None = None,
    ) -> None:
        self.evidence_path = evidence_path
        self.aigovops_root = aigovops_root
        self.runner = task_runner.TaskRunner(tasks_dir=tasks_dir)
        self.approvals = ApprovalQueue(self.runner, approvals_dir=approvals_dir)
        self.registry = build_registry(aigovops_root=aigovops_root)
        self.html_cache_dir = Path(html_cache_dir) if html_cache_dir else Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v2-cc-"))
        self.html_cache_dir.mkdir(parents=True, exist_ok=True)
        self._html_lock = threading.Lock()
        self._html_mtime: float | None = None

    def regenerate_html(self) -> Path:
        out = self.html_cache_dir / "index.html"
        with self._html_lock:
            generate_v2_html(
                out,
                evidence_path=self.evidence_path,
                aigovops_root=str(self.aigovops_root) if self.aigovops_root else None,
            )
            self._html_mtime = out.stat().st_mtime
        return out


def _write_json(handler: http.server.BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _write_html(handler: http.server.BaseHTTPRequestHandler, path: Path) -> None:
    try:
        body = path.read_bytes()
    except OSError as exc:
        _write_json(handler, 500, {"error": "html_read_failed", "detail": str(exc)})
        return
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _list_artifacts(evidence_path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not evidence_path.exists():
        return out
    for f in sorted(evidence_path.rglob("*.json")):
        try:
            st = f.stat()
        except OSError:
            continue
        out.append({
            "path": str(f.relative_to(evidence_path)),
            "absolute_path": str(f),
            "size": st.st_size,
            "mtime": st.st_mtime,
        })
        if len(out) >= 500:
            break
    return out


def build_handler(state: CommandCenterState):
    """Build an http.server.BaseHTTPRequestHandler bound to the given state."""

    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "aigovclaw-hub-v2-command-center/1.0"

        def log_message(self, fmt: str, *args) -> None:  # pragma: no cover - noisy
            sys.stderr.write("[hub-v2-cc] " + (fmt % args) + "\n")

        # ------------------------------------------------------------------
        # Dispatch helpers
        # ------------------------------------------------------------------

        def _parsed_path(self) -> tuple[str, dict[str, str]]:
            parts = urllib.parse.urlsplit(self.path)
            query = {}
            for k, v in urllib.parse.parse_qsl(parts.query):
                query[k] = v
            return parts.path, query

        def _read_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                return {}
            return data if isinstance(data, dict) else {}

        # ------------------------------------------------------------------
        # GET
        # ------------------------------------------------------------------

        def do_GET(self):  # noqa: N802 (http.server convention)
            path, query = self._parsed_path()
            if path == "/" or path == "/index.html":
                try:
                    html = state.regenerate_html()
                except VendorMissingError as exc:
                    _write_json(self, 500, {"error": "vendor_missing", "detail": str(exc)})
                    return
                _write_html(self, html)
                return

            if path == "/api/health":
                payload = compute_health(
                    runner=state.runner,
                    evidence_path=state.evidence_path,
                    aigovops_root=state.aigovops_root,
                )
                _write_json(self, 200, payload)
                return

            if path == "/api/commands":
                _write_json(self, 200, {"commands": public_registry(state.registry)})
                return

            if path == "/api/tasks":
                limit = int(query.get("limit") or 50)
                status = query.get("status")
                since = query.get("since")
                tasks = state.runner.list_tasks(status=status, limit=limit, since=since)
                _write_json(self, 200, {"tasks": tasks})
                return

            if path.startswith("/api/tasks/"):
                task_id = path[len("/api/tasks/"):].strip("/")
                if not task_id or "/" in task_id:
                    _write_json(self, 400, {"error": "bad_task_id"})
                    return
                rec = state.runner.get(task_id)
                if rec is None:
                    _write_json(self, 404, {"error": "not_found"})
                    return
                _write_json(self, 200, rec)
                return

            if path == "/api/artifacts":
                _write_json(self, 200, {"artifacts": _list_artifacts(state.evidence_path)})
                return

            if path == "/api/approvals":
                _write_json(self, 200, {"approvals": state.approvals.pending()})
                return

            _write_json(self, 404, {"error": "not_found", "path": path})

        # ------------------------------------------------------------------
        # POST
        # ------------------------------------------------------------------

        def do_POST(self):  # noqa: N802
            path, _ = self._parsed_path()

            if path == "/api/tasks":
                body = self._read_body()
                command_id = body.get("command")
                args = body.get("args") or {}
                if not isinstance(command_id, str) or command_id not in state.registry:
                    _write_json(self, 400, {"error": "unknown_command", "command": command_id})
                    return
                if not isinstance(args, dict):
                    _write_json(self, 400, {"error": "args_must_be_object"})
                    return
                spec = state.registry[command_id]
                try:
                    argv = spec["build_argv"](args)
                except Exception as exc:
                    _write_json(self, 400, {"error": "build_argv_failed", "detail": str(exc)})
                    return
                if not isinstance(argv, list) or not argv:
                    _write_json(self, 500, {"error": "invalid_argv"})
                    return
                rec = state.runner.enqueue(
                    command_id,
                    args,
                    argv,
                    requires_approval=bool(spec.get("requires_approval")),
                )
                if rec.get("requires_approval"):
                    state.approvals.register(rec)
                _write_json(self, 200, rec)
                return

            if path.startswith("/api/tasks/"):
                tail = path[len("/api/tasks/"):].strip("/")
                if "/" in tail:
                    task_id, action = tail.split("/", 1)
                else:
                    task_id, action = tail, ""
                if not task_id or not action:
                    _write_json(self, 400, {"error": "bad_action"})
                    return
                try:
                    if action == "pause":
                        rec = state.runner.pause(task_id)
                    elif action == "resume":
                        rec = state.runner.resume(task_id)
                    elif action == "cancel":
                        rec = state.runner.cancel(task_id)
                    else:
                        _write_json(self, 400, {"error": "unknown_action", "action": action})
                        return
                except KeyError:
                    _write_json(self, 404, {"error": "not_found"})
                    return
                _write_json(self, 200, rec)
                return

            if path.startswith("/api/approvals/"):
                tail = path[len("/api/approvals/"):].strip("/")
                if "/" in tail:
                    task_id, action = tail.split("/", 1)
                else:
                    task_id, action = tail, ""
                if not task_id or not action:
                    _write_json(self, 400, {"error": "bad_action"})
                    return
                body = self._read_body()
                try:
                    if action == "approve":
                        rec = state.approvals.approve(
                            task_id,
                            approver=str(body.get("approver") or "operator"),
                        )
                    elif action == "reject":
                        rec = state.approvals.reject(
                            task_id,
                            approver=str(body.get("approver") or "operator"),
                            reason=body.get("reason"),
                        )
                    else:
                        _write_json(self, 400, {"error": "unknown_action", "action": action})
                        return
                except KeyError:
                    _write_json(self, 404, {"error": "not_found"})
                    return
                _write_json(self, 200, rec)
                return

            _write_json(self, 404, {"error": "not_found", "path": path})

    return Handler


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    evidence_path: str | os.PathLike | None = None,
    aigovops_root: str | os.PathLike | None = None,
) -> None:
    evidence = resolve_evidence_path(evidence_path)
    ago = resolve_aigovops_root(aigovops_root) if not isinstance(aigovops_root, Path) else aigovops_root
    state = CommandCenterState(evidence_path=evidence, aigovops_root=ago)
    handler = build_handler(state)
    with ThreadedHTTPServer((host, port), handler) as httpd:
        url = f"http://{host}:{port}/"
        sys.stderr.write(f"[hub-v2-cc] serving command center at {url}\n")
        sys.stderr.write(f"[hub-v2-cc] evidence: {evidence}\n")
        sys.stderr.write(f"[hub-v2-cc] aigovops root: {ago}\n")
        sys.stderr.write("[hub-v2-cc] Ctrl-C to stop.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            sys.stderr.write("\n[hub-v2-cc] stopped.\n")


def build_server(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    evidence_path: Path | None = None,
    aigovops_root: Path | None = None,
    tasks_dir: Path | None = None,
    approvals_dir: Path | None = None,
) -> tuple[ThreadedHTTPServer, CommandCenterState]:
    """Build a server without starting it. Used by tests."""
    evidence = Path(evidence_path) if evidence_path else resolve_evidence_path(None)
    state = CommandCenterState(
        evidence_path=evidence,
        aigovops_root=aigovops_root,
        tasks_dir=tasks_dir,
        approvals_dir=approvals_dir,
    )
    handler = build_handler(state)
    server = ThreadedHTTPServer((host, port), handler)
    return server, state
