"""notification handler.

Supports channels:
    local-file      append JSONL record to ~/.hermes/memory/aigovclaw/notifications/<date>.log
    stdout          print the record to process stdout
    slack, discord, telegram, email, desktop
                    route via Hermes Agent gateway (gateway/delivery.py)

Hermes Agent (https://github.com/NousResearch/hermes-agent) ships 18 built-in
channel adapters under `gateway/platforms/`. We do not reimplement delivery;
we call Hermes's deliver() API. Two routes:

1. In-process: if `hermes.gateway.delivery.deliver` is importable (AIGovClaw
   running inside a Hermes Agent Python environment), call it directly.
2. Out-of-process: if env var `HERMES_API_URL` is set (pointing at Hermes's
   api_server gateway platform), POST to its delivery endpoint. Optional
   `HERMES_API_TOKEN` env var for Bearer auth.

If neither route is available, the handler raises `NotImplementedError` with
an actionable message. No silent fallback; the operator must configure
Hermes or explicitly use `local-file` or `stdout`.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..action_registry import ActionRequest
from ..safety import DEFAULT_MEMORY_ROOT, utc_now_iso


HERMES_CHANNELS = {"slack", "telegram", "discord", "email", "desktop"}
LOCAL_CHANNELS = {"local-file", "stdout"}
HERMES_API_URL_ENV = "HERMES_API_URL"
HERMES_API_TOKEN_ENV = "HERMES_API_TOKEN"


def handle(request: ActionRequest, dry_run: bool) -> dict[str, Any]:
    args = request.args or {}
    channel = args.get("channel")
    message = args.get("message")
    severity = args.get("severity", "info")

    if not channel:
        raise ValueError("notification requires args['channel']")
    if message is None:
        raise ValueError("notification requires args['message']")

    record = {
        "timestamp": utc_now_iso(),
        "plugin": request.plugin,
        "request_id": request.request_id,
        "channel": channel,
        "severity": severity,
        "message": message,
    }

    if dry_run:
        return {
            "would_deliver_to": channel,
            "severity": severity,
            "message_preview": str(message)[:200],
            "delivery_route": _resolve_route(channel, probe_only=True),
        }

    if channel == "local-file":
        return _deliver_local_file(record)

    if channel == "stdout":
        return _deliver_stdout(record)

    if channel in HERMES_CHANNELS:
        return _deliver_hermes(channel, message, severity, record)

    raise ValueError(f"unknown notification channel {channel!r}")


# Local channels

def _deliver_local_file(record: dict[str, Any]) -> dict[str, Any]:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_dir = DEFAULT_MEMORY_ROOT / "notifications"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{day}.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return {"channel": "local-file", "delivered": True, "log_path": str(log_path)}


def _deliver_stdout(record: dict[str, Any]) -> dict[str, Any]:
    sys.stdout.write(json.dumps(record) + "\n")
    sys.stdout.flush()
    return {"channel": "stdout", "delivered": True}


# Hermes routes

def _resolve_route(channel: str, probe_only: bool = False) -> str:
    """Decide which Hermes route to use for this channel.

    Returns one of:
      "hermes-inprocess"       direct Python import of hermes.gateway.delivery
      "hermes-http"            HTTP POST to HERMES_API_URL gateway endpoint
      "unavailable"            neither route is configured

    probe_only=True means do not actually import; just report configured state.
    """
    if channel not in HERMES_CHANNELS:
        return "local"
    if probe_only:
        # Fast path: detect import availability without side effects.
        try:
            import importlib.util
            spec = importlib.util.find_spec("hermes.gateway.delivery")
            if spec is not None:
                return "hermes-inprocess"
        except (ImportError, ValueError):
            pass
        if os.environ.get(HERMES_API_URL_ENV):
            return "hermes-http"
        return "unavailable"
    # Actually try the import.
    try:
        from hermes.gateway import delivery  # noqa: F401
        return "hermes-inprocess"
    except ImportError:
        pass
    if os.environ.get(HERMES_API_URL_ENV):
        return "hermes-http"
    return "unavailable"


def _deliver_hermes(channel: str, message: Any, severity: str, record: dict[str, Any]) -> dict[str, Any]:
    route = _resolve_route(channel)

    if route == "hermes-inprocess":
        return _deliver_hermes_inprocess(channel, message, severity, record)

    if route == "hermes-http":
        return _deliver_hermes_http(channel, message, severity, record)

    raise NotImplementedError(
        f"Channel {channel!r} requires Hermes Agent gateway. "
        f"Either run AIGovClaw inside a Hermes Agent Python environment "
        f"(so `hermes.gateway.delivery` is importable), OR set the "
        f"{HERMES_API_URL_ENV} environment variable to a Hermes Agent api_server URL "
        f"(e.g. http://127.0.0.1:8765). See docs/channels.md. "
        f"For local development without Hermes, use channel 'local-file' or 'stdout'."
    )


def _deliver_hermes_inprocess(channel: str, message: Any, severity: str, record: dict[str, Any]) -> dict[str, Any]:
    """Direct Python call to hermes.gateway.delivery.deliver().

    Signature assumed to match Hermes Agent's published API:
        deliver(channel: str, message: str, severity: str = "info", **metadata) -> dict

    Hermes's implementation translates `channel` to the configured platform
    adapter (slack.py, discord.py, etc.). If the adapter is not configured
    for that channel, Hermes raises; we surface the error as an action
    failure (the executor writes action-failed audit entry + optional
    rollback).
    """
    from hermes.gateway import delivery as hermes_delivery

    result = hermes_delivery.deliver(
        channel=channel,
        message=message if isinstance(message, str) else json.dumps(message),
        severity=severity,
        source_plugin=record.get("plugin"),
        request_id=record.get("request_id"),
    )
    if not isinstance(result, dict):
        result = {"hermes_result": str(result)}
    result.setdefault("channel", channel)
    result.setdefault("delivered", True)
    result["route"] = "hermes-inprocess"
    return result


def _deliver_hermes_http(channel: str, message: Any, severity: str, record: dict[str, Any]) -> dict[str, Any]:
    """POST to Hermes Agent's api_server gateway delivery endpoint.

    Endpoint: `{HERMES_API_URL}/gateway/deliver`
    Body: JSON {channel, message, severity, source_plugin, request_id}
    Auth: optional Bearer token from HERMES_API_TOKEN env var.
    Timeout: 5 seconds (Hermes delivery is local-network; longer suggests
    a configuration problem, not a real delivery that takes time).
    """
    api_url = os.environ[HERMES_API_URL_ENV].rstrip("/")
    endpoint = f"{api_url}/gateway/deliver"
    body = {
        "channel": channel,
        "message": message if isinstance(message, str) else json.dumps(message),
        "severity": severity,
        "source_plugin": record.get("plugin"),
        "request_id": record.get("request_id"),
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    token = os.environ.get(HERMES_API_TOKEN_ENV)
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Hermes gateway HTTP delivery returned HTTP {exc.code}: {exc.reason}. "
            f"Endpoint: {endpoint}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Hermes gateway HTTP delivery could not connect to {endpoint}: {exc.reason}. "
            f"Verify Hermes Agent is running and HERMES_API_URL points at its api_server."
        ) from exc

    if not isinstance(payload, dict):
        payload = {"hermes_result": str(payload)}
    payload.setdefault("channel", channel)
    payload.setdefault("delivered", True)
    payload["route"] = "hermes-http"
    return payload
