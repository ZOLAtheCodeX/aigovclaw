"""
AIGovClaw: Tool Registration Layer for the Hermes Harness

Implements the tool-registration contract that the Hermes Agent harness
uses to invoke AIGovOps plugins. Every plugin is wrapped as a Tool with:

- A declared input schema (field name, type, required flag, optional enum).
- Explicit safety properties: is_read_only, is_concurrency_safe,
  is_destructive, requires_human_approval.
- A source_skill pointer so the harness knows which SKILL.md motivates
  the tool.
- A max_result_size_bytes cap to prevent context explosion.

Design informed by the harness paradigm analysis at
https://kenhuangus.substack.com/p/chapter-1-the-harness-paradigm-claude
which describes the Claude Code typed-Tool interface and the Hermes
registry-at-import-time pattern. This module implements the intersection:
declarative safety properties (Claude Code style) exposed via a registry
(Hermes style) that Hermes can read at startup.

The harness enforces permissions, iteration budgets, and human-approval
gates. The tool itself does not; it trusts the harness. This mirrors the
"single-owner of mutable state" pattern from the harness paradigm article.

Status: functional. Registry supports registration, lookup, introspection,
and direct invocation for testing. Production invocation flows through
the Hermes harness, which this module exposes its tools to.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    """Wraps a plugin function as a registerable tool.

    Fields:
        name: unique identifier inside the registry. Hermes uses this
              identifier when the model requests the tool.
        description: short natural-language description shown to the model.
        handler: the callable that implements the tool. Signature:
                 handler(inputs: dict) -> dict.
        input_schema: dict mapping field_name to a schema dict with keys
                      'type' (string: 'string'|'number'|'bool'|'list[...]'|'dict'),
                      'required' (bool), optional 'enum' (list), optional
                      'description' (string).
        is_read_only: True when the tool does not mutate any persistent
                      state. All AIGovOps plugins are read-only; the
                      workflows handle persistence separately.
        is_concurrency_safe: True when the tool can be invoked in parallel
                             with itself or other tools without
                             coordination.
        is_destructive: True when the tool deletes, rewrites, or overwrites
                        state that cannot be cheaply restored.
        requires_human_approval: True when the harness must prompt a
                                 human before invoking the tool.
        max_result_size_bytes: hard cap on the serialized result size.
                               Exceeded results are truncated by the
                               harness and flagged as over-cap.
        source_skill: name of the SKILL.md file that describes this tool
                      at the governance-knowledge layer. The harness uses
                      this to surface the tool only when the relevant
                      skill is loaded.
        artifact_type: the aigovclaw artifact type produced by the tool
                       (for adapter routing). Matches adapter
                       SUPPORTED_ARTIFACT_TYPES vocabulary.
    """

    name: str
    description: str
    handler: Callable[..., Any]
    input_schema: dict[str, dict[str, Any]]
    is_read_only: bool
    is_concurrency_safe: bool
    is_destructive: bool
    source_skill: str | None = None
    artifact_type: str | None = None
    requires_human_approval: bool = False
    max_result_size_bytes: int = 1_000_000


class ToolRegistry:
    """Registry of available tools in the AIGovClaw harness.

    Not thread-safe by itself; the Hermes harness provides single-owner
    ownership of the registry instance consistent with the harness
    paradigm's single-owner-of-mutable-state pattern.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool. Raises if the name is already taken."""
        if not isinstance(tool, Tool):
            raise TypeError("tool must be a Tool instance")
        if not tool.name or not isinstance(tool.name, str):
            raise ValueError("tool.name must be a non-empty string")
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} already registered")
        if not callable(tool.handler):
            raise TypeError(f"tool {tool.name!r} handler must be callable")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool. Raises KeyError if not registered."""
        del self._tools[name]

    def clear(self) -> None:
        """Drop all registrations. For test-only use."""
        self._tools.clear()

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"tool {name!r} not registered; available: {self.list_tools()}")
        return self._tools[name]

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def describe(self, name: str) -> dict[str, Any]:
        """Return a harness-consumable description of the tool."""
        t = self.get(name)
        return {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
            "safety": {
                "is_read_only": t.is_read_only,
                "is_concurrency_safe": t.is_concurrency_safe,
                "is_destructive": t.is_destructive,
                "requires_human_approval": t.requires_human_approval,
            },
            "max_result_size_bytes": t.max_result_size_bytes,
            "source_skill": t.source_skill,
            "artifact_type": t.artifact_type,
        }

    def describe_all(self) -> list[dict[str, Any]]:
        return [self.describe(name) for name in self.list_tools()]

    def _validate_required_fields(self, input_schema: dict[str, Any], inputs: dict[str, Any], errors: list[str]) -> None:
        """Check that all required fields from the schema are present in inputs."""
        for field_name, spec in input_schema.items():
            if spec.get("required", False) and field_name not in inputs:
                errors.append(f"required field {field_name!r} missing")

    def _validate_field_types(self, input_schema: dict[str, Any], inputs: dict[str, Any], errors: list[str]) -> None:
        """Check that all provided inputs match their declared types and enums."""
        for field_name, value in inputs.items():
            if field_name not in input_schema:
                # Extra fields are not an error by default; the handler
                # may choose to tolerate them. Flag for visibility.
                continue
            spec = input_schema[field_name]
            enum = spec.get("enum")
            if enum is not None and value not in enum:
                errors.append(f"field {field_name!r} value {value!r} not in enum {enum}")
            declared_type = spec.get("type")
            if declared_type and not _type_matches(value, declared_type):
                errors.append(
                    f"field {field_name!r} has wrong type: expected {declared_type}, got {type(value).__name__}"
                )

    def validate_inputs(self, name: str, inputs: dict[str, Any]) -> list[str]:
        """Check inputs against the tool's declared schema. Returns a list
        of validation error strings; empty list means inputs are valid."""
        tool = self.get(name)
        errors: list[str] = []
        if not isinstance(inputs, dict):
            return ["inputs must be a dict"]

        self._validate_required_fields(tool.input_schema, inputs, errors)
        self._validate_field_types(tool.input_schema, inputs, errors)

        return errors

    def invoke(self, name: str, inputs: dict[str, Any]) -> Any:
        """Invoke a tool directly. Intended for testing or harness-less
        execution. Production invocations flow through the harness, which
        applies permissions, iteration budgets, and human-approval gates
        BEFORE calling this method.

        Raises:
            KeyError: if the tool is not registered.
            ValueError: if inputs fail schema validation.
        """
        errors = self.validate_inputs(name, inputs)
        if errors:
            raise ValueError(f"invalid inputs for tool {name!r}: {errors}")
        handler = self.get(name).handler
        # Handler signature may be (inputs: dict) or (inputs: dict, **kwargs);
        # our convention is positional-arg dict.
        sig = inspect.signature(handler)
        if len(sig.parameters) == 1:
            return handler(inputs)
        raise TypeError(
            f"tool {name!r} handler has unsupported signature; expected (inputs: dict)"
        )


def _type_matches(value: Any, declared: str) -> bool:
    """Lightweight type check that tolerates declared types like
    'list[string]' without a real type system."""
    declared = declared.strip().lower()
    if declared == "string":
        return isinstance(value, str)
    if declared == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared in ("bool", "boolean"):
        return isinstance(value, bool)
    if declared == "dict":
        return isinstance(value, dict)
    if declared.startswith("list"):
        return isinstance(value, list)
    if declared == "any":
        return True
    # Unknown declared type: pass (the handler's own validation catches it).
    return True


# Module-level singleton registry. The Hermes harness imports this at
# startup, optionally calls register_aigovops_tools() to populate it,
# and then consults it to respond to tool invocation requests.
REGISTRY = ToolRegistry()
