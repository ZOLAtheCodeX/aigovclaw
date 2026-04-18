"""Tests for the AIGovClaw MCP server.

Runnable under pytest or as a standalone script:

    python mcp_server/tests/test_server.py

If the mcp package is not installed in the environment, tests skip with a
printed message. No fake success; no network.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Locate the aigovclaw repo root (parent of mcp_server/). Put it on sys.path
# so the server module and its tools imports resolve without an install.
_TESTS_DIR = Path(__file__).resolve().parent
_MCP_SERVER_DIR = _TESTS_DIR.parent
_REPO_ROOT = _MCP_SERVER_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Default plugins path for local-dev checkouts. Users can override via env.
os.environ.setdefault(
    "AIGOVOPS_PLUGINS_PATH",
    "/Users/zola/Documents/CODING/aigovops/plugins",
)


def _mcp_available() -> bool:
    try:
        import mcp  # noqa: F401
        return True
    except ImportError:
        return False


def _skip_if_no_mcp() -> bool:
    if not _mcp_available():
        print(
            "SKIP: mcp package not installed. "
            "Run: pip install -r mcp_server/requirements.txt"
        )
        return True
    return False


# ---------------------------------------------------------------------------
# Test cases.
# ---------------------------------------------------------------------------


def test_tool_count_matches_catalogue() -> None:
    if _skip_if_no_mcp():
        return
    from mcp_server.server import build_server  # type: ignore
    from tools.aigovops_tools import PLUGIN_TOOL_DEFS  # type: ignore

    server = build_server()
    assert len(server._tools) == len(PLUGIN_TOOL_DEFS), (
        f"expected {len(PLUGIN_TOOL_DEFS)} tools, got {len(server._tools)}"
    )
    assert len(server._tools) == 12, "expected exactly 12 tools"


def test_every_tool_has_safety_annotations() -> None:
    if _skip_if_no_mcp():
        return
    from mcp_server.server import build_server  # type: ignore

    server = build_server()
    required_flags = {
        "x-aigovops-read-only": True,
        "x-aigovops-concurrency-safe": True,
        "x-aigovops-destructive": False,
    }
    for name, entry in server._tools.items():
        ann = entry["annotations"]
        for key, expected in required_flags.items():
            assert key in ann, f"tool {name} missing annotation {key}"
            assert ann[key] is expected, (
                f"tool {name} annotation {key} = {ann[key]!r}, "
                f"expected {expected!r}"
            )


def test_invalid_enum_rejected() -> None:
    if _skip_if_no_mcp():
        return
    from tools.registry import REGISTRY  # type: ignore
    from mcp_server.server import build_server  # type: ignore

    build_server()  # populates REGISTRY
    bad_input = {
        "system_name": "test-system",
        "purpose": "demo",
        "risk_tier": "definitely-not-a-real-tier",
        "data_processed": ["synthetic"],
        "deployment_context": "sandbox",
        "governance_decisions": ["approve"],
        "responsible_parties": ["alice"],
    }
    try:
        REGISTRY.invoke("generate_audit_log", bad_input)
    except ValueError as exc:
        assert "risk_tier" in str(exc) or "enum" in str(exc), (
            f"expected validation error mentioning risk_tier, got: {exc}"
        )
        return
    raise AssertionError("expected ValueError for invalid risk_tier enum")


def test_happy_path_audit_log() -> None:
    if _skip_if_no_mcp():
        return
    from tools.registry import REGISTRY  # type: ignore
    from mcp_server.server import build_server  # type: ignore

    build_server()
    good_input = {
        "system_name": "claims-triage-v1",
        "purpose": "triage incoming claims for human review",
        "risk_tier": "high",
        "data_processed": ["claim_text", "claim_metadata"],
        "deployment_context": "internal staging",
        "governance_decisions": [
            "enable human-in-the-loop override",
            "require weekly drift review",
        ],
        "responsible_parties": ["governance-lead", "product-owner"],
    }
    result = REGISTRY.invoke("generate_audit_log", good_input)
    assert isinstance(result, dict), "result must be a dict"
    assert "agent_signature" in result, (
        f"expected agent_signature in result, got keys: {list(result.keys())}"
    )
    assert result["agent_signature"].startswith("audit-log-generator/"), (
        f"unexpected agent_signature: {result['agent_signature']!r}"
    )


# ---------------------------------------------------------------------------
# Standalone runner.
# ---------------------------------------------------------------------------


def _run_all() -> int:
    tests = [
        test_tool_count_matches_catalogue,
        test_every_tool_has_safety_annotations,
        test_invalid_enum_rejected,
        test_happy_path_audit_log,
    ]
    if not _mcp_available():
        print(
            "SKIP ALL: mcp package not installed. "
            "Install with: pip install -r mcp_server/requirements.txt"
        )
        return 0
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}")
        except Exception as exc:
            failures += 1
            print(f"ERROR {fn.__name__}: {exc}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
