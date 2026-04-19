"""Tests for the AIGovClaw tool registration layer.

Covers:
- Tool dataclass validation.
- Registry lifecycle (register, lookup, describe, invoke).
- Input schema validation.
- Actual registration of all AIGovOps plugins from the aigovops repo.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add tools/ parent so 'from tools import ...' resolves.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.registry import REGISTRY, Tool, ToolRegistry
from tools.aigovops_tools import PLUGIN_TOOL_DEFS, register_aigovops_tools, unregister_all


def _dummy_handler(inputs: dict) -> dict:
    return {"echo": inputs}


def _dummy_tool(name: str = "dummy") -> Tool:
    return Tool(
        name=name,
        description="test tool",
        handler=_dummy_handler,
        input_schema={"foo": {"type": "string", "required": True}},
        is_read_only=True,
        is_concurrency_safe=True,
        is_destructive=False,
    )


# --- Tool dataclass ---

def test_tool_construction():
    t = _dummy_tool()
    assert t.name == "dummy"
    assert t.is_read_only is True
    assert t.max_result_size_bytes == 1_000_000


# --- Registry lifecycle ---

def test_registry_register_and_get():
    r = ToolRegistry()
    tool = _dummy_tool()
    r.register(tool)
    assert r.get("dummy") is tool


def test_registry_rejects_duplicate_name():
    r = ToolRegistry()
    r.register(_dummy_tool())
    try:
        r.register(_dummy_tool())
    except ValueError as exc:
        assert "already registered" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_registry_rejects_non_tool():
    r = ToolRegistry()
    try:
        r.register({"name": "not-a-tool"})
    except TypeError as exc:
        assert "Tool instance" in str(exc)
        return
    raise AssertionError("expected TypeError")


def test_registry_rejects_blank_name():
    r = ToolRegistry()
    try:
        r.register(Tool(
            name="",
            description="x",
            handler=_dummy_handler,
            input_schema={},
            is_read_only=True,
            is_concurrency_safe=True,
            is_destructive=False,
        ))
    except ValueError as exc:
        assert "non-empty" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_registry_get_unknown_raises_keyerror():
    r = ToolRegistry()
    try:
        r.get("nope")
    except KeyError as exc:
        assert "not registered" in str(exc)
        return
    raise AssertionError("expected KeyError")


def test_registry_list_and_describe():
    r = ToolRegistry()
    r.register(_dummy_tool("a"))
    r.register(_dummy_tool("b"))
    assert r.list_tools() == ["a", "b"]
    desc = r.describe("a")
    assert desc["name"] == "a"
    assert desc["safety"]["is_read_only"] is True
    assert "input_schema" in desc


def test_registry_describe_all():
    r = ToolRegistry()
    r.register(_dummy_tool("a"))
    r.register(_dummy_tool("b"))
    all_desc = r.describe_all()
    assert len(all_desc) == 2


# --- Input validation ---

def test_validate_missing_required_surfaces_error():
    r = ToolRegistry()
    r.register(_dummy_tool())
    errors = r.validate_inputs("dummy", {})
    assert any("foo" in e and "missing" in e for e in errors)


def test_validate_enum_mismatch_surfaces_error():
    r = ToolRegistry()
    r.register(Tool(
        name="enum-tool",
        description="x",
        handler=_dummy_handler,
        input_schema={"framework": {"type": "string", "required": True, "enum": ["a", "b"]}},
        is_read_only=True,
        is_concurrency_safe=True,
        is_destructive=False,
    ))
    errors = r.validate_inputs("enum-tool", {"framework": "c"})
    assert any("not in enum" in e for e in errors)


def test_validate_type_mismatch_surfaces_error():
    r = ToolRegistry()
    r.register(Tool(
        name="typed",
        description="x",
        handler=_dummy_handler,
        input_schema={"n": {"type": "number", "required": True}},
        is_read_only=True,
        is_concurrency_safe=True,
        is_destructive=False,
    ))
    errors = r.validate_inputs("typed", {"n": "not-a-number"})
    assert any("wrong type" in e for e in errors)


def test_validate_passes_correct_inputs():
    r = ToolRegistry()
    r.register(_dummy_tool())
    errors = r.validate_inputs("dummy", {"foo": "bar"})
    assert errors == []


# --- Invocation ---

def test_invoke_runs_handler():
    r = ToolRegistry()
    r.register(_dummy_tool())
    result = r.invoke("dummy", {"foo": "bar"})
    assert result["echo"] == {"foo": "bar"}


def test_invoke_rejects_invalid_inputs():
    r = ToolRegistry()
    r.register(_dummy_tool())
    try:
        r.invoke("dummy", {})
    except ValueError as exc:
        assert "foo" in str(exc)
        return
    raise AssertionError("expected ValueError")


# --- aigovops_tools registration ---

AIGOVOPS_PLUGINS_PATH = Path(
    os.environ.get("AIGOVOPS_PLUGINS_PATH") or "/Users/zola/Documents/CODING/aigovops/plugins"
)


def test_plugin_tool_defs_cover_all_plugins():
    names = {d["name"] for d in PLUGIN_TOOL_DEFS}
    # Expected count updates as plugins are added. Each plugin directory has
    # exactly one tool entry.
    expected_count = 19
    assert len(names) == expected_count, f"expected {expected_count} tools, got {len(names)}: {sorted(names)}"
    assert len(PLUGIN_TOOL_DEFS) == expected_count


def test_plugin_tool_defs_have_required_keys():
    for d in PLUGIN_TOOL_DEFS:
        for key in ("name", "plugin", "function", "description", "input_schema", "source_skill", "artifact_type"):
            assert key in d, f"{d['name']} missing {key}"


def test_register_aigovops_tools_succeeds_against_real_plugins():
    if not AIGOVOPS_PLUGINS_PATH.is_dir():
        print(f"Skipping: aigovops plugins not found at {AIGOVOPS_PLUGINS_PATH}")
        return
    unregister_all()
    registered = register_aigovops_tools(AIGOVOPS_PLUGINS_PATH)
    # Count derived from PLUGIN_TOOL_DEFS so adding a plugin only requires
    # updating the defs list, not this assertion.
    assert len(registered) == len(PLUGIN_TOOL_DEFS)
    for d in PLUGIN_TOOL_DEFS:
        assert d["name"] in registered
        REGISTRY.get(d["name"])
    unregister_all()


def test_registered_tools_all_read_only():
    if not AIGOVOPS_PLUGINS_PATH.is_dir():
        print(f"Skipping: aigovops plugins not found at {AIGOVOPS_PLUGINS_PATH}")
        return
    unregister_all()
    register_aigovops_tools(AIGOVOPS_PLUGINS_PATH)
    for name in REGISTRY.list_tools():
        desc = REGISTRY.describe(name)
        assert desc["safety"]["is_read_only"] is True, f"{name} not read-only"
        assert desc["safety"]["is_concurrency_safe"] is True, f"{name} not concurrency-safe"
        assert desc["safety"]["is_destructive"] is False, f"{name} is destructive"
    unregister_all()


def test_invoke_a_real_plugin_tool():
    """Smoke test: invoke generate_audit_log through the registry."""
    if not AIGOVOPS_PLUGINS_PATH.is_dir():
        print(f"Skipping: aigovops plugins not found at {AIGOVOPS_PLUGINS_PATH}")
        return
    unregister_all()
    register_aigovops_tools(AIGOVOPS_PLUGINS_PATH)
    result = REGISTRY.invoke(
        "generate_audit_log",
        {
            "system_name": "TestSystem",
            "purpose": "Test purpose",
            "risk_tier": "limited",
            "data_processed": ["test"],
            "deployment_context": "test",
            "governance_decisions": ["Deployed for tool-registration smoke test."],
            "responsible_parties": ["AI Governance Officer"],
        },
    )
    assert "agent_signature" in result
    assert result["agent_signature"].startswith("audit-log-generator/")
    unregister_all()


def test_invoke_rejects_plugin_schema_violation():
    """Registry schema validation catches bad inputs before the plugin sees them."""
    if not AIGOVOPS_PLUGINS_PATH.is_dir():
        print(f"Skipping: aigovops plugins not found at {AIGOVOPS_PLUGINS_PATH}")
        return
    unregister_all()
    register_aigovops_tools(AIGOVOPS_PLUGINS_PATH)
    try:
        REGISTRY.invoke(
            "generate_audit_log",
            {
                "system_name": "X",
                "purpose": "X",
                "risk_tier": "not-a-valid-tier",  # enum violation
                "data_processed": [],
                "deployment_context": "x",
                "governance_decisions": [],
                "responsible_parties": [],
            },
        )
    except ValueError as exc:
        assert "not in enum" in str(exc)
        unregister_all()
        return
    unregister_all()
    raise AssertionError("expected ValueError for enum violation")


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
