"""file-update handler.

Mutates a file under an allowed root. Supports three diff modes:

    "replace"       overwrite file content with args["content"].
    "merge-json"    load existing JSON, deep-merge args["updates_dict"], write back.
    "merge-yaml"    same for YAML (uses PyYAML when available, else safe replace).

The handler validates the target path against safety.allowed_roots() before
any read or write.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

from ..action_registry import ActionRequest
from ..safety import allowed_roots, is_under


def _verify_path(path: Path) -> None:
    roots = allowed_roots()
    if not any(is_under(path, r) for r in roots):
        raise PermissionError(
            f"file-update target {path} is outside the allowed roots "
            f"{[str(r) for r in roots]}; refusing to write."
        )


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for k, v in override.items():
            merged[k] = _deep_merge(base.get(k), v) if k in merged else v
        return merged
    return override


def _apply_updates(existing_text: str, args: dict[str, Any]) -> str:
    diff_mode = args.get("diff_mode") or "replace"
    if diff_mode == "replace":
        content = args.get("content")
        if content is None:
            raise ValueError("diff_mode='replace' requires args['content']")
        return str(content)
    if diff_mode == "merge-json":
        updates = args.get("updates_dict") or {}
        if not isinstance(updates, dict):
            raise ValueError("args['updates_dict'] must be a dict")
        try:
            existing_obj = json.loads(existing_text) if existing_text.strip() else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"existing file is not valid JSON: {exc}") from exc
        merged = _deep_merge(existing_obj, updates)
        return json.dumps(merged, indent=2, sort_keys=True) + "\n"
    if diff_mode == "merge-yaml":
        updates = args.get("updates_dict") or {}
        if not isinstance(updates, dict):
            raise ValueError("args['updates_dict'] must be a dict")
        try:
            import yaml  # type: ignore
        except ImportError:
            raise ValueError(
                "diff_mode='merge-yaml' requires PyYAML; not installed. "
                "Fall back to merge-json or replace."
            )
        existing_obj = yaml.safe_load(existing_text) if existing_text.strip() else {}
        if not isinstance(existing_obj, dict):
            existing_obj = {}
        merged = _deep_merge(existing_obj, updates)
        return yaml.safe_dump(merged, sort_keys=True)
    raise ValueError(
        f"unknown diff_mode {diff_mode!r}; expected replace | merge-json | merge-yaml"
    )


def handle(request: ActionRequest, dry_run: bool) -> dict[str, Any]:
    args = request.args or {}
    path_str = args.get("path")
    if not path_str:
        raise ValueError("file-update requires args['path']")
    path = Path(path_str).expanduser().resolve()
    _verify_path(path)

    existing_text = path.read_text(encoding="utf-8") if path.exists() else ""
    new_text = _apply_updates(existing_text, args)

    if dry_run:
        diff_preview = "\n".join(
            difflib.unified_diff(
                existing_text.splitlines(),
                new_text.splitlines(),
                fromfile=str(path) + " (current)",
                tofile=str(path) + " (proposed)",
                lineterm="",
            )
        )
        return {
            "path": str(path),
            "would_change_bytes": abs(len(new_text.encode("utf-8")) - len(existing_text.encode("utf-8"))),
            "diff_preview": diff_preview[:4000],
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    new_bytes = new_text.encode("utf-8")
    return {
        "path": str(path),
        "bytes_changed": abs(len(new_bytes) - len(existing_text.encode("utf-8"))),
        "new_sha256": hashlib.sha256(new_bytes).hexdigest(),
    }
