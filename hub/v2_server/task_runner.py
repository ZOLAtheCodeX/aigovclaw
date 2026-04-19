"""Subprocess task runner for the Hub v2 command center.

Lifecycle:
  queued  -> running -> succeeded | failed | cancelled | interrupted
             |          (running can be suspended via pause/resume)

Persistence:
  ~/.hermes/memory/aigovclaw/hub-v2-tasks/<task_id>/
    state.json    Current task record.
    stdout.log    Captured stdout+stderr tail.

State records are the single source of truth. On server restart, the runner
scans the tasks directory and reaps any task whose pid no longer exists.

Signals:
  pause   SIGSTOP on the child process group.
  resume  SIGCONT.
  cancel  SIGTERM, escalates to SIGKILL after a grace period (default 5s).

Thread safety:
  A single threading.RLock guards in-memory state. Each task has a dedicated
  background thread that waits on the subprocess and writes the final state
  when it exits. The server handler thread enqueues tasks and responds to
  status queries without blocking on child processes.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


STATUS_QUEUED = "queued"
STATUS_AWAITING_APPROVAL = "awaiting-approval"
STATUS_RUNNING = "running"
STATUS_PAUSED = "paused"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_INTERRUPTED = "interrupted"

TERMINAL_STATES = {
    STATUS_SUCCEEDED, STATUS_FAILED, STATUS_CANCELLED, STATUS_INTERRUPTED,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_tasks_dir() -> Path:
    return Path.home() / ".hermes" / "memory" / "aigovclaw" / "hub-v2-tasks"


class TaskRunner:
    """Manages subprocess-backed tasks for the command center.

    The runner owns:
      - A tasks directory on disk where per-task state.json and stdout.log live.
      - An in-memory dict of task_id -> record for fast query responses.
      - One background thread per running task that captures output and
        writes the terminal record when the child exits.
    """

    STDOUT_TAIL_LINES = 100

    def __init__(
        self,
        *,
        tasks_dir: Path | None = None,
        cancel_grace_seconds: float = 5.0,
        max_completed_in_memory: int = 200,
    ) -> None:
        self.tasks_dir = Path(tasks_dir) if tasks_dir else _default_tasks_dir()
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.cancel_grace_seconds = cancel_grace_seconds
        self._lock = threading.RLock()
        self._tasks: dict[str, dict[str, Any]] = {}
        self._procs: dict[str, subprocess.Popen] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._max_completed_in_memory = max_completed_in_memory
        self._reap_orphans_on_startup()

    # ------------------------------------------------------------------
    # Startup: reap orphaned running tasks.
    # ------------------------------------------------------------------

    def _reap_orphans_on_startup(self) -> None:
        for sub in sorted(self.tasks_dir.iterdir()) if self.tasks_dir.exists() else []:
            state_path = sub / "state.json"
            if not state_path.exists():
                continue
            try:
                rec = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(rec, dict):
                continue
            status = rec.get("status")
            pid = rec.get("pid")
            if status in (STATUS_RUNNING, STATUS_PAUSED) and pid:
                alive = self._pid_is_alive(int(pid))
                if not alive:
                    rec["status"] = STATUS_INTERRUPTED
                    rec["ended_at"] = rec.get("ended_at") or _utc_now()
                    rec["exit_code"] = rec.get("exit_code")
                    rec["summary"] = rec.get("summary") or "Interrupted by server restart."
                    state_path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            self._tasks[rec.get("task_id") or sub.name] = rec

    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    # ------------------------------------------------------------------
    # Enqueue.
    # ------------------------------------------------------------------

    def enqueue(
        self,
        command_id: str,
        args: dict[str, Any],
        argv: list[str],
        *,
        requires_approval: bool = False,
        cwd: str | os.PathLike | None = None,
        env: dict[str, str] | None = None,
        start_immediately: bool = True,
    ) -> dict[str, Any]:
        task_id = uuid.uuid4().hex[:16]
        now = _utc_now()
        rec: dict[str, Any] = {
            "task_id": task_id,
            "command": command_id,
            "args": args or {},
            "argv": argv,
            "status": STATUS_AWAITING_APPROVAL if requires_approval else STATUS_QUEUED,
            "requires_approval": bool(requires_approval),
            "queued_at": now,
            "started_at": None,
            "ended_at": None,
            "pid": None,
            "exit_code": None,
            "summary": None,
            "stdout_tail": [],
            "cwd": str(cwd) if cwd else None,
        }
        sub = self.tasks_dir / task_id
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "state.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

        with self._lock:
            self._tasks[task_id] = rec

        if requires_approval:
            # Will transition to queued when approved.
            return dict(rec)

        if start_immediately:
            self._start(task_id, cwd=cwd, env=env)
        return dict(self._tasks[task_id])

    # ------------------------------------------------------------------
    # Internal: start a queued task.
    # ------------------------------------------------------------------

    def _start(self, task_id: str, *, cwd=None, env=None) -> None:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                raise KeyError(task_id)
            if rec["status"] not in (STATUS_QUEUED,):
                raise RuntimeError(
                    f"task {task_id} is not in a startable state (status={rec['status']})"
                )
            argv = rec["argv"]
            sub = self.tasks_dir / task_id
            log_path = sub / "stdout.log"
            log_fh = open(log_path, "w", encoding="utf-8", buffering=1)
            try:
                # Start in its own process group so we can signal the whole group.
                proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=cwd,
                    env=env,
                    bufsize=1,
                    text=True,
                    start_new_session=True,
                )
            except FileNotFoundError as exc:
                log_fh.write(f"FileNotFoundError: {exc}\n")
                log_fh.close()
                rec["status"] = STATUS_FAILED
                rec["started_at"] = _utc_now()
                rec["ended_at"] = rec["started_at"]
                rec["exit_code"] = -1
                rec["summary"] = f"Failed to start: {exc}"
                self._persist(task_id)
                return

            rec["status"] = STATUS_RUNNING
            rec["started_at"] = _utc_now()
            rec["pid"] = proc.pid
            self._procs[task_id] = proc
            self._persist(task_id)

        # Capture thread runs outside the lock.
        t = threading.Thread(
            target=self._capture_loop,
            args=(task_id, proc, log_fh),
            name=f"hub-v2-task-{task_id}",
            daemon=True,
        )
        self._threads[task_id] = t
        t.start()

    def _capture_loop(self, task_id: str, proc: subprocess.Popen, log_fh) -> None:
        tail: deque[str] = deque(maxlen=self.STDOUT_TAIL_LINES)
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                log_fh.write(line)
                tail.append(line.rstrip("\n"))
                # Periodically flush tail into state for live polling.
                with self._lock:
                    rec = self._tasks.get(task_id)
                    if rec is not None:
                        rec["stdout_tail"] = list(tail)
                # Throttle persistence to avoid disk churn; snapshot every 20 lines.
                if len(tail) % 20 == 0:
                    self._persist(task_id)
        finally:
            try:
                log_fh.close()
            except Exception:
                pass
            rc = proc.wait()
            with self._lock:
                rec = self._tasks.get(task_id)
                if rec is None:
                    return
                if rec["status"] == STATUS_CANCELLED:
                    # Cancellation already marked terminal; just capture exit code.
                    rec["exit_code"] = rc
                else:
                    rec["status"] = STATUS_SUCCEEDED if rc == 0 else STATUS_FAILED
                    rec["exit_code"] = rc
                rec["ended_at"] = _utc_now()
                rec["stdout_tail"] = list(tail)
                if rec["summary"] is None:
                    rec["summary"] = (
                        tail[-1] if tail else ("exit " + str(rc))
                    )
                self._procs.pop(task_id, None)
                self._persist(task_id)

    # ------------------------------------------------------------------
    # Persistence.
    # ------------------------------------------------------------------

    def _persist(self, task_id: str) -> None:
        rec = self._tasks.get(task_id)
        if rec is None:
            return
        state_path = self.tasks_dir / task_id / "state.json"
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Query.
    # ------------------------------------------------------------------

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            rec = self._tasks.get(task_id)
            return dict(rec) if rec is not None else None

    def list_tasks(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._tasks.values())
        items.sort(
            key=lambda r: r.get("started_at") or r.get("queued_at") or "",
            reverse=True,
        )
        if status:
            wanted = {s.strip() for s in status.split(",") if s.strip()}
            items = [r for r in items if r.get("status") in wanted]
        if since:
            items = [
                r for r in items
                if (r.get("started_at") or r.get("queued_at") or "") >= since
            ]
        return [dict(r) for r in items[:limit]]

    # ------------------------------------------------------------------
    # Control.
    # ------------------------------------------------------------------

    def pause(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                raise KeyError(task_id)
            if rec["status"] != STATUS_RUNNING:
                return dict(rec)
            pid = rec.get("pid")
            if not pid:
                return dict(rec)
            try:
                os.killpg(pid, signal.SIGSTOP)
            except (ProcessLookupError, PermissionError):
                pass
            rec["status"] = STATUS_PAUSED
            self._persist(task_id)
            return dict(rec)

    def resume(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                raise KeyError(task_id)
            if rec["status"] == STATUS_AWAITING_APPROVAL:
                # Approval flow promotes to queued then starts.
                rec["status"] = STATUS_QUEUED
                self._persist(task_id)
                self._start(task_id)
                return dict(self._tasks[task_id])
            if rec["status"] != STATUS_PAUSED:
                return dict(rec)
            pid = rec.get("pid")
            if not pid:
                return dict(rec)
            try:
                os.killpg(pid, signal.SIGCONT)
            except (ProcessLookupError, PermissionError):
                pass
            rec["status"] = STATUS_RUNNING
            self._persist(task_id)
            return dict(rec)

    def cancel(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                raise KeyError(task_id)
            if rec["status"] in TERMINAL_STATES:
                return dict(rec)
            if rec["status"] == STATUS_AWAITING_APPROVAL:
                rec["status"] = STATUS_CANCELLED
                rec["ended_at"] = _utc_now()
                rec["summary"] = "Cancelled before approval."
                self._persist(task_id)
                return dict(rec)
            proc = self._procs.get(task_id)
            rec["status"] = STATUS_CANCELLED
            rec["summary"] = "Cancelled by operator."
            self._persist(task_id)
        # Signal outside the lock so the capture thread can transition cleanly.
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            # Escalate after grace period on a helper thread.
            def _escalate(p=proc, grace=self.cancel_grace_seconds):
                deadline = time.monotonic() + grace
                while time.monotonic() < deadline:
                    if p.poll() is not None:
                        return
                    time.sleep(0.1)
                if p.poll() is None:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
            threading.Thread(target=_escalate, daemon=True).start()
        with self._lock:
            return dict(self._tasks[task_id])

    # ------------------------------------------------------------------
    # Approval promotion (called by ApprovalQueue).
    # ------------------------------------------------------------------

    def approve(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                raise KeyError(task_id)
            if rec["status"] != STATUS_AWAITING_APPROVAL:
                return dict(rec)
            rec["status"] = STATUS_QUEUED
            self._persist(task_id)
        self._start(task_id)
        with self._lock:
            return dict(self._tasks[task_id])

    def reject(self, task_id: str, *, reason: str | None = None) -> dict[str, Any]:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                raise KeyError(task_id)
            if rec["status"] != STATUS_AWAITING_APPROVAL:
                return dict(rec)
            rec["status"] = STATUS_CANCELLED
            rec["ended_at"] = _utc_now()
            rec["summary"] = reason or "Rejected by approver."
            self._persist(task_id)
            return dict(rec)

    # ------------------------------------------------------------------
    # Diagnostics / testing.
    # ------------------------------------------------------------------

    def wait(self, task_id: str, timeout: float = 10.0) -> dict[str, Any]:
        """Block until a task reaches a terminal state. Test helper."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rec = self.get(task_id)
            if rec is None:
                raise KeyError(task_id)
            if rec["status"] in TERMINAL_STATES:
                return rec
            time.sleep(0.05)
        raise TimeoutError(f"task {task_id} did not terminate within {timeout}s")
