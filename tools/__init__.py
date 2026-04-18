"""AIGovClaw tool registration for the Hermes harness."""

from .registry import REGISTRY, Tool, ToolRegistry
from .aigovops_tools import PLUGIN_TOOL_DEFS, register_aigovops_tools

__all__ = [
    "REGISTRY",
    "Tool",
    "ToolRegistry",
    "PLUGIN_TOOL_DEFS",
    "register_aigovops_tools",
]
