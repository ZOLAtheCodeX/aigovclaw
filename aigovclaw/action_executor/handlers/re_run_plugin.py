"""re-run-plugin handler.

Dynamically imports an aigovops plugin from the sibling checkout and
invokes its canonical entry point. Output lands under
~/.hermes/memory/aigovclaw/<plugin-name>/<timestamp>.json.

Entry-point discovery:
    1. The plugin module exposes `PLUGIN_DISPATCH[name]['entry']` (rare).
    2. The plugin module exposes a top-level callable matching one of the
       well-known names: generate_audit_log, generate, pack_bundle,
       build_risk_register, build, run.
    3. Otherwise: raise.
"""

from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..action_registry import ActionRequest
from ..safety import AIGOVOPS_ROOT_CANDIDATES, DEFAULT_MEMORY_ROOT


WELL_KNOWN_ENTRIES = (
    "generate_audit_log",
    "generate",
    "pack_bundle",
    "build",
    "run",
    "build_risk_register",
    "produce",
)


def _resolve_aigovops_root() -> Path:
    override = os.environ.get("AIGOVOPS_ROOT")
    if override:
        p = Path(override).expanduser().resolve()
        if p.exists():
            return p
    for candidate in AIGOVOPS_ROOT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"aigovops checkout not found. Tried {[str(c) for c in AIGOVOPS_ROOT_CANDIDATES]} "
        f"and AIGOVOPS_ROOT env var."
    )


def _load_plugin_module(root: Path, plugin_name: str) -> Any:
    plugin_path = root / "plugins" / plugin_name / "plugin.py"
    if not plugin_path.exists():
        raise FileNotFoundError(f"plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        f"_aigovclaw_plugin_{plugin_name.replace('-', '_')}", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not import plugin module at {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_entry(module: Any, plugin_name: str) -> Callable[..., Any]:
    dispatch = getattr(module, "PLUGIN_DISPATCH", None)
    if isinstance(dispatch, dict) and plugin_name in dispatch:
        entry_name = dispatch[plugin_name].get("entry")
        if entry_name and hasattr(module, entry_name):
            return getattr(module, entry_name)
    for name in WELL_KNOWN_ENTRIES:
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(
        f"plugin {plugin_name!r} exposes no well-known entry point "
        f"({WELL_KNOWN_ENTRIES!r}) and has no PLUGIN_DISPATCH entry."
    )


def _load_inputs(args: dict[str, Any]) -> dict[str, Any]:
    if "inputs" in args:
        inputs = args["inputs"]
        if not isinstance(inputs, dict):
            raise ValueError("args['inputs'] must be a dict")
        return inputs
    if "inputs_ref" in args:
        ref = Path(str(args["inputs_ref"])).expanduser().resolve()
        if not ref.exists():
            raise FileNotFoundError(f"inputs_ref not found: {ref}")
        text = ref.read_text(encoding="utf-8")
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"inputs_ref is not JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError("inputs_ref must decode to a dict")
        return obj
    return {}


def handle(request: ActionRequest, dry_run: bool) -> dict[str, Any]:
    args = request.args or {}
    plugin_name = args.get("plugin_name") or request.target
    if not plugin_name:
        raise ValueError("re-run-plugin requires args['plugin_name']")

    root = _resolve_aigovops_root()

    if dry_run:
        plugin_path = root / "plugins" / plugin_name / "plugin.py"
        return {
            "plugin": plugin_name,
            "would_import_from": str(plugin_path),
            "would_write_under": str(DEFAULT_MEMORY_ROOT / plugin_name),
        }

    module = _load_plugin_module(root, plugin_name)
    entry = _find_entry(module, plugin_name)
    inputs = _load_inputs(args)
    result = entry(inputs)

    out_dir = DEFAULT_MEMORY_ROOT / plugin_name
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{ts}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    warnings_count = 0
    if isinstance(result, dict):
        w = result.get("warnings")
        if isinstance(w, list):
            warnings_count = len(w)

    return {
        "plugin": plugin_name,
        "output_path": str(out_path),
        "warnings_count": warnings_count,
    }
