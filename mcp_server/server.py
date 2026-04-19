"""
AIGovClaw MCP Server

Exposes the AIGovOps plugin catalogue (19 plugins) as Model Context Protocol
tools over stdio transport. Any MCP-capable client (Claude Desktop, Cursor,
Zed, a future VerifyWise or Vanta MCP adapter) can invoke AIGovOps governance
plugins through this server.

Design:

- The tool catalogue is sourced directly from aigovclaw.tools.aigovops_tools.
  PLUGIN_TOOL_DEFS. This module does not re-author tool definitions.
- Plugins are loaded at startup from the filesystem path given by the
  AIGOVOPS_PLUGINS_PATH environment variable (default
  /Users/zola/Documents/CODING/aigovops/plugins).
- Every tool is annotated with the safety flags carried by the underlying
  Hermes Tool: x-aigovops-read-only, x-aigovops-concurrency-safe,
  x-aigovops-destructive. All AIGovOps plugins are read-only and
  non-destructive by contract.
- Input validation reuses the Hermes ToolRegistry validator. Validation
  failures surface as MCP errors (not silently swallowed).
- Every invocation is logged to stderr with timestamp, tool name, input
  size, output size, and duration. No payloads are logged.

Invocation:

    python -m aigovclaw.mcp_server.server

The server speaks MCP over stdio.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Import the canonical tool catalogue and registry. Support both layouts:
# (a) aigovclaw is on PYTHONPATH as a package root, so imports use
#     aigovclaw.tools.*; (b) the parent of aigovclaw is on PYTHONPATH.
try:
    from aigovclaw.tools.aigovops_tools import (  # type: ignore
        PLUGIN_TOOL_DEFS,
        register_aigovops_tools,
    )
    from aigovclaw.tools.registry import REGISTRY  # type: ignore
except ImportError:
    # Fall back to bare-package layout where aigovclaw/ itself is on
    # PYTHONPATH. This is the common developer-checkout layout.
    _REPO_ROOT = Path(__file__).resolve().parent.parent
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    from tools.aigovops_tools import (  # type: ignore
        PLUGIN_TOOL_DEFS,
        register_aigovops_tools,
    )
    from tools.registry import REGISTRY  # type: ignore


DEFAULT_PLUGINS_PATH = "/Users/zola/Documents/CODING/aigovops/plugins"

# Configure a stderr logger. MCP stdio transport reserves stdout for JSON-RPC
# frames, so logs must go to stderr. The format intentionally excludes any
# payload fields; only metadata is logged.
_LOG_FORMAT = "%(asctime)sZ aigovclaw-mcp %(levelname)s %(message)s"
logging.basicConfig(
    level=os.environ.get("AIGOVOPS_MCP_LOG_LEVEL", "INFO"),
    format=_LOG_FORMAT,
    stream=sys.stderr,
)
_log = logging.getLogger("aigovclaw.mcp_server")


# ---------------------------------------------------------------------------
# Schema translation: Hermes input_schema -> JSON Schema for MCP.
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "string": "string",
    "number": "number",
    "bool": "boolean",
    "boolean": "boolean",
    "dict": "object",
    "any": None,  # omit type keyword for any
}


def _hermes_field_to_json_schema(spec: dict[str, Any]) -> dict[str, Any]:
    """Translate one Hermes field spec into a JSON Schema fragment."""
    declared = str(spec.get("type", "any")).strip().lower()
    fragment: dict[str, Any] = {}
    if declared.startswith("list"):
        fragment["type"] = "array"
        fragment["items"] = {}
    elif declared in _TYPE_MAP:
        mapped = _TYPE_MAP[declared]
        if mapped is not None:
            fragment["type"] = mapped
    else:
        # Unknown declared type: leave unconstrained.
        pass

    enum = spec.get("enum")
    if enum is not None:
        fragment["enum"] = list(enum)

    description = spec.get("description")
    if description:
        fragment["description"] = description

    return fragment


def _build_json_schema(definition: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON Schema for the tool's input object."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field_name, spec in definition["input_schema"].items():
        properties[field_name] = _hermes_field_to_json_schema(spec)
        if spec.get("required", False):
            required.append(field_name)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": True,
    }
    if required:
        schema["required"] = required
    return schema


def _build_description(definition: dict[str, Any]) -> str:
    """Compose a description including source_skill and artifact_type."""
    parts = [definition["description"].strip()]
    source_skill = definition.get("source_skill")
    artifact_type = definition.get("artifact_type")
    if source_skill:
        parts.append(f"Source skill: {source_skill}.")
    if artifact_type:
        parts.append(f"Artifact type: {artifact_type}.")
    parts.append(
        "Read-only, concurrency-safe, non-destructive. "
        "Returns a structured governance artifact dict."
    )
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Server construction.
# ---------------------------------------------------------------------------


def _resolve_plugins_path() -> Path:
    raw = os.environ.get("AIGOVOPS_PLUGINS_PATH", DEFAULT_PLUGINS_PATH)
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(
            f"AIGOVOPS_PLUGINS_PATH {path} is not a directory"
        )
    return path


def _load_mcp_types() -> Any:
    """Import the MCP library lazily so this module can be inspected even
    when mcp is not installed. Returns the types namespace.

    Raises ImportError with a clear message if mcp is unavailable.
    """
    try:
        from mcp.server import Server  # type: ignore
        from mcp import types as mcp_types  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "The mcp package is not installed. "
            "Run: pip install -r mcp_server/requirements.txt"
        ) from exc
    return Server, mcp_types


def _populate_registry() -> list[dict[str, Any]]:
    """Load plugins into the Hermes registry. Returns the catalogue list."""
    plugins_path = _resolve_plugins_path()
    # Clear first so that repeated build_server() calls in tests do not raise
    # on duplicate registration.
    REGISTRY.clear()
    register_aigovops_tools(plugins_path)
    return PLUGIN_TOOL_DEFS


def build_server() -> Any:
    """Construct and return a configured MCP Server with the full tool catalogue.

    The returned object has an internal dict _tools keyed by tool name for
    introspection by tests. Callers who want to run stdio must call
    run_stdio().
    """
    Server, mcp_types = _load_mcp_types()
    definitions = _populate_registry()

    server = Server("aigovclaw")
    tools_by_name: dict[str, dict[str, Any]] = {}

    # Build and cache the MCP-shaped tool descriptors once.
    for definition in definitions:
        tool_name = definition["name"]
        schema = _build_json_schema(definition)
        description = _build_description(definition)
        annotations: dict[str, Any] = {
            "x-aigovops-read-only": True,
            "x-aigovops-concurrency-safe": True,
            "x-aigovops-destructive": False,
            "x-aigovops-source-skill": definition.get("source_skill"),
            "x-aigovops-artifact-type": definition.get("artifact_type"),
        }
        tools_by_name[tool_name] = {
            "name": tool_name,
            "description": description,
            "inputSchema": schema,
            "annotations": annotations,
        }

    # Expose a dict for tests. Not part of the MCP public surface.
    server._tools = tools_by_name  # type: ignore[attr-defined]

    @server.list_tools()
    async def _list_tools():  # type: ignore[misc]
        return [
            mcp_types.Tool(
                name=entry["name"],
                description=entry["description"],
                inputSchema=entry["inputSchema"],
                annotations=entry["annotations"],
            )
            for entry in tools_by_name.values()
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None):  # type: ignore[misc]
        return await _dispatch(name, arguments or {}, mcp_types)

    return server


async def _dispatch(
    name: str, arguments: dict[str, Any], mcp_types: Any
) -> list[Any]:
    """Validate, invoke, serialize. Logs metadata; never payloads."""
    t0 = time.perf_counter()
    input_size = len(json.dumps(arguments, default=str))
    try:
        # Registry.invoke validates then calls. ValueError on schema issues.
        result = REGISTRY.invoke(name, arguments)
    except KeyError as exc:
        _log.warning("tool=%s status=unknown", name)
        raise ValueError(f"unknown tool: {name}") from exc
    except ValueError as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        _log.info(
            "tool=%s status=validation_error input_bytes=%d duration_ms=%.2f",
            name,
            input_size,
            duration_ms,
        )
        # Let MCP surface this as a tool error. Re-raise so the MCP library
        # produces a standard error response rather than a success payload.
        raise
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        _log.error(
            "tool=%s status=handler_error input_bytes=%d duration_ms=%.2f error=%s",
            name,
            input_size,
            duration_ms,
            type(exc).__name__,
        )
        raise

    payload = json.dumps(result, default=str, indent=2)
    output_size = len(payload)
    duration_ms = (time.perf_counter() - t0) * 1000
    _log.info(
        "tool=%s status=ok input_bytes=%d output_bytes=%d duration_ms=%.2f",
        name,
        input_size,
        output_size,
        duration_ms,
    )
    return [mcp_types.TextContent(type="text", text=payload)]


async def run_stdio() -> None:
    """Run the server over stdio transport."""
    from mcp.server.stdio import stdio_server  # type: ignore

    server = build_server()
    _log.info(
        "aigovclaw MCP server starting tools=%d plugins_path=%s",
        len(server._tools),  # type: ignore[attr-defined]
        _resolve_plugins_path(),
    )
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
