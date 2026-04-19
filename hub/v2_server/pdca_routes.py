"""Command Centre HTTP routes for the PDCA orchestrator.

Exposes:

    POST /api/pdca/start          Kick off a new PDCA cycle.
    GET  /api/pdca/status         Current cycle state (or latest cycle).
    GET  /api/pdca/status/<id>    State for a specific cycle.
    POST /api/pdca/pause          Pause the current cycle.
    POST /api/pdca/resume         Resume the current cycle.
    POST /api/pdca/abort          Abort the current cycle.

Wiring: server.py includes an instance of PDCARouteState in its command
center state. Routes are dispatched from the same Handler that dispatches
task and approval routes. Integration is read-only additive: removing
these routes leaves the rest of Hub v2 unaffected.

The handler deliberately does NOT construct real planner or readiness
instances; the orchestrator is dependency-injected. Callers must register
a factory via `PDCARouteState.register_factory` before POST /api/pdca/start
will succeed. This keeps the server stdlib-only while allowing production
deployments to wire in the certification-path-planner and
certification-readiness plugins.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from aigovclaw.agent_loop import PDCACycle
from aigovclaw.agent_loop.state import default_state_dir, load_state


class PDCARouteState:
    """Holds the active PDCACycle (if any) plus an optional factory.

    register_factory(fn) installs a callable that, when called with
    ({organization_ref, target_certification, target_date}), returns a
    fully-constructed PDCACycle. Tests register a factory that injects
    mock planner / assessor; production registers one that loads the real
    plugins.
    """

    def __init__(self, *, state_dir: Path | None = None) -> None:
        self.state_dir = Path(state_dir) if state_dir else default_state_dir()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.active: PDCACycle | None = None
        self._factory: Callable[[dict[str, Any]], PDCACycle] | None = None

    def register_factory(self, factory: Callable[[dict[str, Any]], PDCACycle]) -> None:
        self._factory = factory

    def handle(self, method: str, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
        """Dispatch a PDCA route. Returns (status_code, payload) or None if
        the path does not belong to this module.
        """
        if not path.startswith("/api/pdca"):
            return None

        if method == "POST" and path == "/api/pdca/start":
            return self._start(body)
        if method == "GET" and path == "/api/pdca/status":
            return self._status(None)
        if method == "GET" and path.startswith("/api/pdca/status/"):
            cycle_id = path[len("/api/pdca/status/"):]
            return self._status(cycle_id)
        if method == "POST" and path == "/api/pdca/pause":
            return self._pause()
        if method == "POST" and path == "/api/pdca/resume":
            return self._resume()
        if method == "POST" and path == "/api/pdca/abort":
            return self._abort(body)

        return 404, {"error": "not_found", "path": path}

    # ------------------------------------------------------------------
    # Route implementations.
    # ------------------------------------------------------------------

    def _start(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if self._factory is None:
            return 503, {
                "error": "factory_not_registered",
                "detail": "PDCARouteState.register_factory must be called before /api/pdca/start",
            }
        required = ("organization_ref", "target_certification", "target_date")
        missing = [k for k in required if k not in body]
        if missing:
            return 400, {"error": "missing_fields", "missing": missing}
        try:
            cycle = self._factory(body)
        except Exception as exc:
            return 500, {"error": "factory_failed", "detail": f"{type(exc).__name__}: {exc}"}
        state = cycle.start()
        self.active = cycle
        return 200, {"cycle": state}

    def _status(self, cycle_id: str | None) -> tuple[int, dict[str, Any]]:
        if cycle_id is None:
            if self.active is None:
                return 200, {"cycle": None}
            return 200, {"cycle": self.active.state.to_dict()}
        try:
            loaded = load_state(cycle_id, state_dir=self.state_dir)
        except FileNotFoundError:
            return 404, {"error": "cycle_not_found", "cycle_id": cycle_id}
        return 200, {"cycle": loaded.to_dict()}

    def _pause(self) -> tuple[int, dict[str, Any]]:
        if self.active is None:
            return 404, {"error": "no_active_cycle"}
        return 200, {"cycle": self.active.pause()}

    def _resume(self) -> tuple[int, dict[str, Any]]:
        if self.active is None:
            return 404, {"error": "no_active_cycle"}
        return 200, {"cycle": self.active.resume()}

    def _abort(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if self.active is None:
            return 404, {"error": "no_active_cycle"}
        reason = str(body.get("reason") or "operator-requested")
        return 200, {"cycle": self.active.abort(reason)}


def render_pdca_panel_html(cycle_state: dict[str, Any] | None) -> str:
    """Render a minimal HTML fragment for the Command Centre PDCA panel.

    Included as a module-level helper so hub.v2.templates can opt in by
    calling render_pdca_panel_html(state) and injecting the result. The
    fragment is pure HTML with inline styles matching the existing
    Deep-Slate-Blue palette; no JavaScript dependencies.
    """
    if cycle_state is None:
        return (
            '<div class="pdca-panel">'
            '<h3>PDCA Cycle</h3>'
            '<p>No active cycle. POST to /api/pdca/start to begin.</p>'
            '</div>'
        )
    phase = cycle_state.get("phase", "unknown")
    iteration = cycle_state.get("iteration", 0)
    target = cycle_state.get("target_certification", "unknown")
    paused = cycle_state.get("paused_for_user", False)
    pending = cycle_state.get("pending_user_interaction_id")
    history = cycle_state.get("readiness_history", []) or []
    latest_verdict = history[-1]["readiness_level"] if history else "not-assessed"

    return (
        '<div class="pdca-panel">'
        '<h3>PDCA Cycle</h3>'
        f'<p><b>Target:</b> {target}</p>'
        f'<p><b>Phase:</b> {phase}</p>'
        f'<p><b>Iteration:</b> {iteration}</p>'
        f'<p><b>Latest verdict:</b> {latest_verdict}</p>'
        f'<p><b>Paused for user:</b> {paused}</p>'
        + (f'<p><b>Pending interaction:</b> {pending}</p>' if pending else '')
        + '</div>'
    )
