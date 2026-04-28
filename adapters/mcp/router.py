"""
AIGovClaw: MCP Router

Translates AIGovClaw artifact dicts into Model Context Protocol tool-invocation
specifications. The Hermes harness reads these specifications and invokes the
configured MCP tools; this module does not call MCP servers directly.

Design decision: MCP servers exist for most destinations users care about
(Notion, Linear, Google Drive, GitHub, Gmail, and so on). This router
reuses them via configuration rather than duplicating destination-specific
HTTP clients in AIGovClaw.

Status: functional. Supports single-artifact and multi-row routing, each
artifact type optionally mapping to multiple MCP tools in parallel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ROUTER_VERSION = "0.1.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _classify_action(artifact: dict[str, Any]) -> str:
    """Derive the action-item classification tag from warnings."""
    warnings = artifact.get("warnings") or []
    row_warnings = 0
    for key in ("rows", "records", "sections", "kpi_records"):
        items = artifact.get(key) or []
        for item in items:
            if isinstance(item, dict) and item.get("warnings"):
                row_warnings += len(item["warnings"])
    if warnings or row_warnings > 0 or artifact.get("unassigned_rows"):
        return "action-required-human"
    if artifact.get("scaffold_rows") or artifact.get("scaffold_sections"):
        return "completed-autonomously-low-confidence"
    return "completed-autonomously-high-confidence"


def _get_nested(obj: Any, path: str) -> Any:
    """Navigate a dotted path through a nested dict, returning None on miss."""
    if not path:
        return None
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _apply_property_mapping(source: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """Return dict mapping destination property names to values read from source."""
    result: dict[str, Any] = {}
    for destination_field, source_path in mapping.items():
        value = _get_nested(source, source_path)
        if value is not None:
            result[destination_field] = value
    return result


def _is_multi_row(artifact_type: str) -> bool:
    """Artifact types where the artifact dict contains a list of rows to route individually."""
    return artifact_type in (
        "risk-register",
        "soa",
        "nonconformity-register",
    )


def _rows_key(artifact_type: str) -> str:
    return "records" if artifact_type == "nonconformity-register" else "rows"


def _row_to_artifact_type(artifact_type: str) -> str:
    """Map a multi-row artifact type to its row-level artifact type."""
    return {
        "risk-register": "risk-register-row",
        "soa": "SoA-row",
        "nonconformity-register": "nonconformity-record",
    }.get(artifact_type, artifact_type)


class MCPRouter:
    """Translates AIGovClaw artifacts into MCP tool-invocation specifications.

    The router does NOT invoke MCP tools; it returns specifications the
    Hermes harness invokes. This separation keeps MCP transport concerns
    out of this module and lets the harness handle retries, concurrency,
    and error surfacing uniformly across every adapter.
    """

    version = ROUTER_VERSION

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Args:
            config: dict with a 'routes' key mapping artifact_type to a list
                    of route definitions. Each route has:
                      mcp_server: server name as known to the Hermes harness.
                      tool_name: MCP tool name to invoke.
                      arguments: static arguments merged into every invocation.
                      property_mapping: optional dict from destination property
                                        name to dotted source path in the
                                        artifact (or row).
        """
        self.config = config or {}
        self.routes: dict[str, list[dict[str, Any]]] = {}
        self._load_routes(self.config.get("routes") or {})

    def _load_routes(self, routes_config: dict[str, Any]) -> None:
        for artifact_type, route_list in routes_config.items():
            if not isinstance(route_list, list):
                raise ValueError(
                    f"routes[{artifact_type!r}] must be a list of route definitions"
                )
            for i, route in enumerate(route_list):
                if not isinstance(route, dict):
                    raise ValueError(f"routes[{artifact_type!r}][{i}] must be a dict")
                if "mcp_server" not in route or "tool_name" not in route:
                    raise ValueError(
                        f"routes[{artifact_type!r}][{i}] must include mcp_server and tool_name"
                    )
            self.routes[artifact_type] = route_list

    def configured_artifact_types(self) -> list[str]:
        """Artifact types that have at least one route configured."""
        return sorted(self.routes.keys())

    def route(self, artifact: dict[str, Any], artifact_type: str) -> dict[str, Any]:
        """Translate an artifact into MCP tool-invocation specifications.

        Returns:
            Dict with:
              status: 'ok' if at least one route emitted or no routes configured;
                      'no-config' if no routes exist for this artifact type.
              invocations: list of invocation specs to pass to the harness.
              action_tag: the action-item classification tag.
              timestamp: ISO 8601 UTC timestamp.
              artifact_type: echoed.
        """
        action_tag = _classify_action(artifact)
        timestamp = _utc_now_iso()

        invocations: list[dict[str, Any]] = []

        if _is_multi_row(artifact_type):
            # Multi-row: one invocation per row per route at the row-level type.
            row_type = _row_to_artifact_type(artifact_type)
            row_routes = self.routes.get(row_type) or self.routes.get(artifact_type, [])
            rows = artifact.get(_rows_key(artifact_type)) or []

            if rows and row_routes:
                row_action_tags = [
                    _classify_action(row) if row.get("warnings") else action_tag
                    for row in rows
                ]

                processed_routes = []
                for route in row_routes:
                    mcp_server = route["mcp_server"]
                    tool_name = route["tool_name"]
                    base_args = route.get("arguments") or {}

                    split_map = None
                    prop_map = route.get("property_mapping")
                    if prop_map:
                        split_map = []
                        for dest, path in prop_map.items():
                            parts = tuple(path.split("."))
                            if len(parts) == 1:
                                split_map.append((dest, parts[0], None))
                            else:
                                split_map.append((dest, None, parts))

                    processed_routes.append((mcp_server, tool_name, base_args, split_map))

                # We can swap the loops to iterate routes then rows, or rows then routes.
                # However, original order is row1 route1, row1 route2, row2 route1...
                # So we keep rows outer loop.
                for row, r_action_tag in zip(rows, row_action_tags):
                    for mcp_server, tool_name, base_args, split_map in processed_routes:
                        if split_map:
                            mapped = {}
                            for dest, single_part, parts in split_map:
                                if single_part is not None:
                                    val = row.get(single_part)
                                    if val is not None:
                                        mapped[dest] = val
                                else:
                                    cur = row
                                    for part in parts:
                                        if isinstance(cur, dict) and part in cur:
                                            cur = cur[part]
                                        else:
                                            cur = None
                                            break
                                    if cur is not None:
                                        mapped[dest] = cur

                            args = dict(base_args)
                            existing = args.get("properties")
                            if existing is None:
                                args["properties"] = mapped
                            elif isinstance(existing, dict):
                                merged = dict(existing)
                                merged.update(mapped)
                                args["properties"] = merged
                            else:
                                args["properties"] = mapped
                        else:
                            args = dict(base_args)

                        invocations.append({
                            "mcp_server": mcp_server,
                            "tool_name": tool_name,
                            "arguments": args,
                            "action_tag": r_action_tag,
                            "source_artifact_type": row_type,
                            "parent_artifact_type": artifact_type,
                            "timestamp": timestamp,
                            "router_version": ROUTER_VERSION,
                        })
            # Also allow routes targeting the whole-document (multi-row) artifact
            # type, which pushes one page representing the full register.
            doc_routes = self.routes.get(artifact_type, [])
            for route in doc_routes:
                invocations.append(self._build_invocation(
                    source=artifact,
                    route=route,
                    artifact_type=artifact_type,
                    parent_artifact_type=None,
                    timestamp=timestamp,
                    action_tag=action_tag,
                ))
        else:
            # Single-artifact: one invocation per route.
            routes = self.routes.get(artifact_type, [])
            for route in routes:
                invocations.append(self._build_invocation(
                    source=artifact,
                    route=route,
                    artifact_type=artifact_type,
                    parent_artifact_type=None,
                    timestamp=timestamp,
                    action_tag=action_tag,
                ))

        status = "ok" if invocations else "no-config"
        return {
            "status": status,
            "invocations": invocations,
            "action_tag": action_tag,
            "timestamp": timestamp,
            "artifact_type": artifact_type,
            "router_version": ROUTER_VERSION,
        }

    def _build_invocation(
        self,
        source: dict[str, Any],
        route: dict[str, Any],
        artifact_type: str,
        parent_artifact_type: str | None,
        timestamp: str,
        action_tag: str,
    ) -> dict[str, Any]:
        arguments = dict(route.get("arguments") or {})
        if route.get("property_mapping"):
            mapped = _apply_property_mapping(source, route["property_mapping"])
            # Merge mapped properties under 'properties'. If the static arguments
            # already have 'properties', merge rather than overwrite.
            existing = arguments.get("properties") or {}
            if isinstance(existing, dict):
                merged = dict(existing)
                merged.update(mapped)
                arguments["properties"] = merged
            else:
                arguments["properties"] = mapped
        return {
            "mcp_server": route["mcp_server"],
            "tool_name": route["tool_name"],
            "arguments": arguments,
            "action_tag": action_tag,
            "source_artifact_type": artifact_type,
            "parent_artifact_type": parent_artifact_type,
            "timestamp": timestamp,
            "router_version": ROUTER_VERSION,
        }

    def route_batch(self, artifacts: list[tuple[dict[str, Any], str]]) -> list[dict[str, Any]]:
        return [self.route(a, t) for a, t in artifacts]
