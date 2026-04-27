"""Authority-policy loader and resolver.

Reads config/authority-policy.yaml and computes the effective authority mode
for a given (plugin, action) pair with safety and autonomous-opt-in guards
applied.

YAML parsing falls back to a tiny stdlib parser when PyYAML is unavailable
so this module stays importable in test environments without the optional
dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .action_registry import (
    AUTHORITY_ASK,
    AUTHORITY_AUTONOMOUS,
    AUTHORITY_TAKE,
    VALID_AUTHORITY_MODES,
    ActionSpec,
)


DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "authority-policy.yaml"
)


@dataclass
class Resolution:
    """Result of resolving authority mode for a single request."""

    mode: str
    rate_limit_per_hour: int | None
    downgrade_reason: str | None


class AuthorityPolicy:
    """Loaded view of authority-policy.yaml."""

    def __init__(self, data: dict[str, Any]):
        self.data = data or {}
        defaults = self.data.get("defaults") or {}
        self.default_mode = defaults.get("mode", AUTHORITY_ASK)
        if self.default_mode not in VALID_AUTHORITY_MODES:
            raise ValueError(
                f"defaults.mode must be one of {VALID_AUTHORITY_MODES}; "
                f"got {self.default_mode!r}"
            )
        self.require_approval_for_destructive = bool(
            defaults.get("require_approval_for_destructive", True)
        )
        self.require_approval_for_external = bool(
            defaults.get("require_approval_for_external", True)
        )
        self.rate_limits: dict[str, int] = dict(
            defaults.get("max_rate_per_hour") or {}
        )
        self.overrides: list[dict[str, Any]] = list(self.data.get("overrides") or [])
        self.autonomous_opt_ins: list[str] = list(
            self.data.get("autonomous_opt_ins") or []
        )

    def resolve(self, plugin: str, action_spec: ActionSpec) -> Resolution:
        """Return the effective authority mode and rate limit.

        Order:
            1. Start from the action spec's default_authority.
            2. Apply the first matching (plugin, action) override. An explicit
               override signals the operator has already considered the
               safety trade-off, so destructive/external guards do NOT apply
               on top of it.
            3. When no override matched, apply destructive and external
               side-effect guards per the defaults.* flags.
            4. Autonomous mode requires an explicit autonomous_opt_ins entry
               regardless of how the mode was chosen.
        """
        # The policy-wide default is the starting point. Per-action overrides
        # supersede it. Safety guards then force ask-permission when a safety
        # flag is tripped and no explicit override was provided.
        mode = self.default_mode
        downgrade_reason: str | None = None

        explicit_override = False
        for override in self.overrides:
            if override.get("plugin") == plugin and override.get("action") == action_spec.id:
                candidate = override.get("mode")
                if candidate in VALID_AUTHORITY_MODES:
                    mode = candidate
                    explicit_override = True
                break

        if not explicit_override:
            if (
                action_spec.safety.get("destructive")
                and self.require_approval_for_destructive
                and mode != AUTHORITY_ASK
            ):
                downgrade_reason = "destructive action requires approval"
                mode = AUTHORITY_ASK

            if (
                action_spec.safety.get("external_side_effect")
                and self.require_approval_for_external
                and mode != AUTHORITY_ASK
            ):
                downgrade_reason = downgrade_reason or "external side-effect requires approval"
                mode = AUTHORITY_ASK

        if mode == AUTHORITY_AUTONOMOUS and plugin not in self.autonomous_opt_ins:
            downgrade_reason = downgrade_reason or "plugin not in autonomous_opt_ins"
            mode = AUTHORITY_ASK

        rate_limit = self.rate_limits.get(action_spec.id, action_spec.rate_limit_per_hour)
        return Resolution(mode=mode, rate_limit_per_hour=rate_limit, downgrade_reason=downgrade_reason)


def load_policy(path: Path | str | None = None) -> AuthorityPolicy:
    """Load authority-policy.yaml. Uses PyYAML when available, tiny parser otherwise."""
    p = Path(path) if path else DEFAULT_POLICY_PATH
    if not p.exists():
        return AuthorityPolicy({})
    text = p.read_text(encoding="utf-8")
    data = _parse_yaml(text)
    if not isinstance(data, dict):
        raise ValueError(f"authority-policy.yaml root must be a mapping; got {type(data).__name__}")
    return AuthorityPolicy(data)


def _parse_yaml(text: str) -> Any:
    """Parse YAML via PyYAML if available, else a minimal stdlib fallback."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        return _fallback_yaml(text)


class _FallbackYAMLParser:
    """Minimal YAML parser sufficient for authority-policy.yaml.

    Supports: nested mappings by indentation, lists of scalars or mappings,
    scalar values (strings, ints, bools, null), and line comments starting
    with #. No anchors, flow syntax, or multi-doc streams.
    """

    def __init__(self, text: str):
        self.lines: list[tuple[int, str]] = []
        for raw in text.splitlines():
            stripped = raw.split("#", 1)[0].rstrip()
            if not stripped.strip():
                continue
            indent = len(stripped) - len(stripped.lstrip(" "))
            self.lines.append((indent, stripped.lstrip(" ")))
        self.idx = 0

    def parse(self) -> Any:
        return self._parse_block(0)

    def _parse_block(self, indent: int) -> Any:
        # Decide whether this block is a mapping or a list based on first line.
        if self.idx >= len(self.lines):
            return None
        first_indent, first = self.lines[self.idx]
        if first_indent < indent:
            return None
        if first.startswith("- "):
            return self._parse_list(indent)
        return self._parse_map(indent)

    def _parse_map(self, indent: int) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while self.idx < len(self.lines):
            cur_indent, cur = self.lines[self.idx]
            if cur_indent < indent:
                break
            if cur_indent > indent:
                break
            if ":" not in cur:
                break
            key, _, value = cur.partition(":")
            key = key.strip()
            value = value.strip()
            self.idx += 1
            if value == "":
                # Nested block
                sub = self._parse_block(indent + 2) if self.idx < len(self.lines) else None
                result[key] = sub if sub is not None else {}
            else:
                result[key] = self._scalar(value)
        return result

    def _parse_list(self, indent: int) -> list[Any]:
        result: list[Any] = []
        while self.idx < len(self.lines):
            cur_indent, cur = self.lines[self.idx]
            if cur_indent != indent or not cur.startswith("- "):
                break
            rest = cur[2:].strip()
            self.idx += 1
            if rest == "":
                sub = self._parse_block(indent + 2)
                result.append(sub if sub is not None else None)
                continue
            if ":" in rest:
                # Inline mapping entry: parse the first kv, then continue with
                # same indent + 2 for additional keys.
                key, _, value = rest.partition(":")
                entry: dict[str, Any] = {key.strip(): self._scalar(value.strip()) if value.strip() else None}
                while self.idx < len(self.lines):
                    ni, nc = self.lines[self.idx]
                    if ni != indent + 2 or nc.startswith("- "):
                        break
                    if ":" not in nc:
                        break
                    k2, _, v2 = nc.partition(":")
                    entry[k2.strip()] = self._scalar(v2.strip())
                    self.idx += 1
                result.append(entry)
            else:
                result.append(self._scalar(rest))
        return result

    def _scalar(self, value: str) -> Any:
        if value == "" or value.lower() == "null" or value == "~":
            return None
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                return []
            return [self._scalar(x.strip()) for x in inner.split(",")]
        try:
            return int(value)
        except ValueError:
            pass
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            return value[1:-1]
        return value


def _fallback_yaml(text: str) -> Any:
    return _FallbackYAMLParser(text).parse()
