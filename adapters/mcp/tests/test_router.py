"""Tests for the MCP router."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import router  # noqa: E402


def _base_config() -> dict:
    return {
        "routes": {
            "audit-log-entry": [
                {
                    "mcp_server": "google-drive",
                    "tool_name": "google-drive-create-document",
                    "arguments": {"folder_id": "drive-folder-governance"},
                },
            ],
            "risk-register-row": [
                {
                    "mcp_server": "notion",
                    "tool_name": "notion-create-page",
                    "arguments": {"parent": {"database_id": "notion-risk-db"}},
                    "property_mapping": {
                        "Title": "description",
                        "System": "system_name",
                        "Category": "category",
                        "Owner": "owner_role",
                    },
                },
                {
                    "mcp_server": "linear",
                    "tool_name": "linear-create-issue",
                    "arguments": {"team": "linear-team-governance"},
                    "property_mapping": {
                        "title": "description",
                        "description": "category",
                    },
                },
            ],
            "nonconformity-record": [
                {
                    "mcp_server": "linear",
                    "tool_name": "linear-create-issue",
                    "arguments": {"team": "linear-team-governance"},
                    "property_mapping": {
                        "title": "description",
                        "state": "status",
                    },
                },
            ],
        },
    }


def test_router_routes_single_artifact():
    r = router.MCPRouter(_base_config())
    entry = {
        "timestamp": "2026-04-18T12:00:00Z",
        "system_name": "ResumeScreen",
        "agent_signature": "audit-log-generator/0.1.0",
        "warnings": [],
    }
    result = r.route(entry, "audit-log-entry")
    assert result["status"] == "ok"
    assert len(result["invocations"]) == 1
    inv = result["invocations"][0]
    assert inv["mcp_server"] == "google-drive"
    assert inv["tool_name"] == "google-drive-create-document"
    assert inv["arguments"]["folder_id"] == "drive-folder-governance"
    assert inv["action_tag"] == "completed-autonomously-high-confidence"


def test_router_emits_one_invocation_per_configured_route():
    r = router.MCPRouter(_base_config())
    # risk-register-row has 2 routes (notion + linear).
    row = {
        "id": "RR-0001",
        "description": "Disparity risk.",
        "system_name": "ResumeScreen",
        "category": "bias",
        "owner_role": "AI Governance Officer",
        "warnings": [],
    }
    register = {"rows": [row], "warnings": []}
    result = r.route(register, "risk-register")
    # 1 row x 2 routes = 2 invocations.
    assert len(result["invocations"]) == 2
    servers = {inv["mcp_server"] for inv in result["invocations"]}
    assert servers == {"notion", "linear"}


def test_property_mapping_applied():
    r = router.MCPRouter(_base_config())
    row = {
        "id": "RR-0001",
        "description": "Disparity risk.",
        "system_name": "ResumeScreen",
        "category": "bias",
        "owner_role": "AI Governance Officer",
        "warnings": [],
    }
    register = {"rows": [row], "warnings": []}
    result = r.route(register, "risk-register")
    notion_inv = next(inv for inv in result["invocations"] if inv["mcp_server"] == "notion")
    props = notion_inv["arguments"]["properties"]
    assert props["Title"] == "Disparity risk."
    assert props["System"] == "ResumeScreen"
    assert props["Category"] == "bias"
    assert props["Owner"] == "AI Governance Officer"


def test_multi_row_emits_one_invocation_per_row():
    r = router.MCPRouter(_base_config())
    register = {
        "rows": [
            {"id": "RR-1", "description": "R1", "system_name": "S1", "warnings": []},
            {"id": "RR-2", "description": "R2", "system_name": "S1", "warnings": []},
            {"id": "RR-3", "description": "R3", "system_name": "S1", "warnings": []},
        ],
        "warnings": [],
    }
    result = r.route(register, "risk-register")
    # 3 rows x 2 routes each = 6 invocations.
    assert len(result["invocations"]) == 6


def test_nonconformity_register_uses_records_key():
    r = router.MCPRouter(_base_config())
    register = {
        "records": [
            {"id": "NC-1", "description": "NC description", "status": "investigated", "warnings": []},
            {"id": "NC-2", "description": "NC2", "status": "closed", "warnings": []},
        ],
        "warnings": [],
    }
    result = r.route(register, "nonconformity-register")
    assert len(result["invocations"]) == 2
    for inv in result["invocations"]:
        assert inv["mcp_server"] == "linear"
    # Property mapping worked.
    assert result["invocations"][0]["arguments"]["properties"]["title"] == "NC description"
    assert result["invocations"][0]["arguments"]["properties"]["state"] == "investigated"


def test_no_routes_returns_no_config_status():
    r = router.MCPRouter({"routes": {}})
    result = r.route({"timestamp": "2026-04-18T00:00:00Z"}, "audit-log-entry")
    assert result["status"] == "no-config"
    assert result["invocations"] == []


def test_empty_config_initializes():
    r = router.MCPRouter()
    assert r.configured_artifact_types() == []


def test_action_tag_required_on_warnings():
    r = router.MCPRouter(_base_config())
    entry = {"timestamp": "2026-04-18T12:00:00Z", "warnings": ["owner missing"]}
    result = r.route(entry, "audit-log-entry")
    assert result["action_tag"] == "action-required-human"
    assert result["invocations"][0]["action_tag"] == "action-required-human"


def test_action_tag_low_confidence_on_scaffold():
    r = router.MCPRouter(_base_config())
    register = {"rows": [], "scaffold_rows": [{"placeholder": 1}], "warnings": []}
    result = r.route(register, "risk-register")
    assert result["action_tag"] == "completed-autonomously-low-confidence"


def test_row_level_action_tag_derived_from_row_warnings():
    r = router.MCPRouter(_base_config())
    register = {
        "rows": [
            {"id": "RR-1", "description": "R1", "warnings": []},
            {"id": "RR-2", "description": "R2", "warnings": ["missing owner"]},
        ],
        "warnings": [],
    }
    result = r.route(register, "risk-register")
    # Find invocations per row.
    by_title = {}
    for inv in result["invocations"]:
        if "properties" in inv["arguments"]:
            by_title.setdefault(inv["arguments"]["properties"].get("Title", ""), []).append(inv)
    # Row RR-1 has no warnings; RR-2 has warnings => should carry action-required tag.
    rr2_invocations = by_title.get("R2", [])
    assert any(inv["action_tag"] == "action-required-human" for inv in rr2_invocations)


def test_config_validation_rejects_bad_route_list():
    try:
        router.MCPRouter({"routes": {"audit-log-entry": "not-a-list"}})
    except ValueError as exc:
        assert "list" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_config_validation_rejects_missing_tool_name():
    try:
        router.MCPRouter({"routes": {"audit-log-entry": [{"mcp_server": "notion"}]}})
    except ValueError as exc:
        assert "tool_name" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_route_result_includes_router_version_and_timestamp():
    r = router.MCPRouter(_base_config())
    result = r.route({"timestamp": "2026-04-18T00:00:00Z", "warnings": []}, "audit-log-entry")
    assert "timestamp" in result
    assert result["router_version"] == router.ROUTER_VERSION
    assert result["invocations"][0]["router_version"] == router.ROUTER_VERSION


def test_configured_artifact_types_sorted():
    r = router.MCPRouter(_base_config())
    types = r.configured_artifact_types()
    assert types == sorted(types)
    assert "audit-log-entry" in types
    assert "risk-register-row" in types
    assert "nonconformity-record" in types


def test_route_batch_preserves_order():
    r = router.MCPRouter(_base_config())
    results = r.route_batch([
        ({"timestamp": "2026-04-18T00:00:00Z", "warnings": []}, "audit-log-entry"),
        ({"rows": [], "warnings": []}, "risk-register"),
    ])
    assert len(results) == 2
    assert results[0]["artifact_type"] == "audit-log-entry"
    assert results[1]["artifact_type"] == "risk-register"


def test_get_nested():
    obj = {"a": {"b": {"c": 1}}}
    assert router._get_nested(obj, "a.b.c") == 1
    assert router._get_nested(obj, "a.x.c") is None
    assert router._get_nested(obj, "a.b.c.d") is None
    assert router._get_nested(obj, "x") is None
    assert router._get_nested(obj, "") is None
    assert router._get_nested(None, "a") is None
    assert router._get_nested([1, 2], "a") is None
    assert router._get_nested("string", "a") is None


def _run_all():
    import inspect
    tests = [(n, o) for n, o in inspect.getmembers(sys.modules[__name__])
             if n.startswith("test_") and callable(o)]
    failures = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
