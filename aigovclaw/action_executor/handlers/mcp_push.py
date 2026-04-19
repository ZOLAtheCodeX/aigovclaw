"""mcp-push handler.

Translates the request into an MCP invocation spec via adapters.mcp.router,
then hands off to a configured MCP client. In this sprint the client may
not be wired; when it is not, the handler raises a descriptive error rather
than silently no-op.
"""

from __future__ import annotations

from typing import Any

from ..action_registry import ActionRequest


def _load_router() -> Any | None:
    try:
        from adapters.mcp.router import MCPRouter  # type: ignore
        return MCPRouter
    except Exception:
        return None


def handle(request: ActionRequest, dry_run: bool) -> dict[str, Any]:
    args = request.args or {}
    mcp_server = args.get("mcp_server")
    tool_name = args.get("tool_name")
    payload = args.get("payload")
    if not mcp_server or not tool_name:
        raise ValueError("mcp-push requires args['mcp_server'] and args['tool_name']")
    if not isinstance(payload, dict):
        raise ValueError("mcp-push requires args['payload'] to be a dict")

    router_cls = _load_router()
    if router_cls is not None:
        # Build a single-artifact route spec so callers benefit from the same
        # property-mapping and action-tag classification the artifact-level
        # router emits. Artifact type is carried in the payload under
        # 'artifact_type'; default to 'generic-artifact'.
        artifact_type = payload.get("artifact_type", "generic-artifact")
        router = router_cls(
            {
                "routes": {
                    artifact_type: [
                        {
                            "mcp_server": mcp_server,
                            "tool_name": tool_name,
                            "arguments": payload.get("arguments") or {},
                            "property_mapping": payload.get("property_mapping") or {},
                        }
                    ]
                }
            }
        )
        spec = router.route(payload, artifact_type)
    else:
        spec = {
            "status": "router-unavailable",
            "invocations": [
                {
                    "mcp_server": mcp_server,
                    "tool_name": tool_name,
                    "arguments": payload.get("arguments") or {},
                }
            ],
        }

    if dry_run:
        payload_bytes = len(str(payload).encode("utf-8"))
        return {
            "would_push_to": mcp_server,
            "tool_name": tool_name,
            "payload_bytes": payload_bytes,
            "invocation_count": len(spec.get("invocations") or []),
            "status": spec.get("status"),
        }

    # Actual MCP client dispatch is not wired in this sprint. The executor
    # contract requires surfacing this as a failure, not a silent no-op.
    raise RuntimeError(
        "MCP client not configured; queue this request for after MCP server "
        "setup. Invocation specs computed: "
        f"{len(spec.get('invocations') or [])}."
    )
