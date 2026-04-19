"""Command registry for the Hub v2 command center.

Each command maps a stable id to a concrete CLI invocation (argv list) and
metadata used by the UI: display name, category, description, argument
schema, and whether enqueueing the command requires a human approval step.

Commands deliberately shell out via subprocess rather than importing plugin
modules in-process. That isolation keeps long runs from blocking the server
thread, lets us signal pause/resume/cancel, and matches how operators run
these pipelines today.

The server resolves paths at enqueue time. Commands reference binaries by
absolute path where possible (aigovops CLI in the sibling repo, local
python3 for internal helpers). Every command is overridable via the
AIGOVCLAW_COMMAND_OVERRIDES environment variable for tests.

Categories:
  pipeline    Full or partial AIMS pipeline runs.
  bundle      Evidence-bundle operations (pack, verify, inspect, export).
  diagnostic  Non-destructive reads (readiness, doctor).
  artifact    Operations that produce a single artifact.
  agent       Hub v2 specific refreshes and regeneration.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
AIGOVCLAW_ROOT = REPO_ROOT
AIGOVOPS_ROOT_CANDIDATES = (
    REPO_ROOT.parent / "aigovops",
    Path.home() / "Documents" / "CODING" / "aigovops",
)


def resolve_aigovops_root(override: str | os.PathLike | None = None) -> Path | None:
    if override:
        p = Path(override).expanduser().resolve()
        return p if p.exists() else None
    for cand in AIGOVOPS_ROOT_CANDIDATES:
        if cand.exists():
            return cand
    return None


def _aigovops_bin(root: Path | None) -> list[str]:
    """Return argv prefix that invokes the aigovops CLI.

    Prefer the packaged bin/aigovops script. Fall back to running cli.runner
    as a module with the repo root on PYTHONPATH when the script is absent.
    """
    if root is None:
        return [sys.executable, "-c", "raise SystemExit('aigovops repo not found')"]
    script = root / "bin" / "aigovops"
    if script.exists() and os.access(script, os.X_OK):
        return [str(script)]
    return [sys.executable, "-c",
            "import sys; sys.path.insert(0, %r); "
            "from cli.runner import main; "
            "raise SystemExit(main(sys.argv[1:]))" % str(root)]


def build_registry(
    *,
    aigovops_root: Path | None = None,
    aigovclaw_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Return a dict of command_id -> command spec.

    Spec shape:
      {
        id, display_name, description, category,
        args_schema: [{name, type, required, default, help}],
        requires_approval: bool,
        build_argv: callable(args: dict) -> list[str],
      }
    """
    ago = resolve_aigovops_root(aigovops_root) if not isinstance(aigovops_root, Path) else aigovops_root
    agc = aigovclaw_root or AIGOVCLAW_ROOT
    aigovops = _aigovops_bin(ago)

    def _run_full_pipeline(args: dict) -> list[str]:
        org = args.get("org") or ""
        output = args.get("output") or str(Path.home() / ".hermes" / "memory" / "aigovclaw" / "pipeline-run")
        argv = list(aigovops) + ["run", "--org", str(org), "--output", str(output)]
        if args.get("framework"):
            argv += ["--framework", str(args["framework"])]
        if args.get("include_crosswalk"):
            argv += ["--include-crosswalk-export"]
        return argv

    def _run_plugin(args: dict) -> list[str]:
        org = args.get("org") or ""
        output = args.get("output") or str(Path.home() / ".hermes" / "memory" / "aigovclaw" / "plugin-run")
        plugin = args.get("plugin") or ""
        # Reuse full-pipeline with --skip-plugin for every other plugin is
        # expensive. Instead we isolate via a small shim script that imports
        # the plugin directly. The shim is emitted in-line to keep this
        # registry self-contained.
        shim = (
            "import sys, json, pathlib; "
            f"sys.path.insert(0, {str(ago) if ago else repr('')!r}); "
            "from cli.runner import load_plugin_module, PLUGIN_DISPATCH, write_json, write_text; "
            f"name = {plugin!r}; "
            f"out_root = pathlib.Path({str(output)!r}) / 'artifacts' / name; "
            "out_root.mkdir(parents=True, exist_ok=True); "
            "module = load_plugin_module(name); "
            "dispatch = PLUGIN_DISPATCH[name]; "
            "entry = getattr(module, dispatch['entry']); "
            "result = entry({}); "
            "write_json(out_root / (dispatch['stem'] + '.json'), result); "
            "print('wrote ' + str(out_root))"
        )
        return [sys.executable, "-c", shim]

    def _pack_bundle(args: dict) -> list[str]:
        artifacts = args.get("artifacts") or ""
        output = args.get("output") or ""
        alg = args.get("signing_algorithm") or "hmac-sha256"
        return list(aigovops) + ["pack", "--artifacts", str(artifacts), "--output", str(output), "--signing-algorithm", alg]

    def _verify_bundle(args: dict) -> list[str]:
        bundle = args.get("bundle") or ""
        return list(aigovops) + ["verify", "--bundle", str(bundle)]

    def _inspect_bundle(args: dict) -> list[str]:
        bundle = args.get("bundle") or ""
        return list(aigovops) + ["inspect", "--bundle", str(bundle)]

    def _check_readiness(args: dict) -> list[str]:
        # Thin wrapper: run certification-readiness plugin via plugin dispatch.
        output = args.get("output") or str(Path.home() / ".hermes" / "memory" / "aigovclaw" / "readiness")
        return _run_plugin({"plugin": "certification-readiness", "output": output})

    def _doctor(_args: dict) -> list[str]:
        return list(aigovops) + ["doctor"]

    def _generate_demo(args: dict) -> list[str]:
        demo = Path(ago) / "examples" / "demo-scenario" / "run_demo.py" if ago else Path("missing-demo")
        return [sys.executable, str(demo)]

    def _export_bundle_zip(args: dict) -> list[str]:
        bundle = args.get("bundle") or ""
        dest = args.get("dest") or ""
        # Use python -m zipfile for portability (stdlib).
        return [sys.executable, "-m", "zipfile", "-c", str(dest), str(bundle)]

    def _regenerate_hub(args: dict) -> list[str]:
        output = args.get("output") or str(Path.home() / ".hermes" / "memory" / "aigovclaw" / "hub-v2.html")
        return [sys.executable, "-m", "hub.v2.cli", "generate", "--output", str(output)]

    def _action_executor_shim(args: dict) -> list[str]:
        """Invoke a one-shot action through the action-executor layer.

        The Command Center UI posts {action_id, plugin, target, args, rationale}
        and this shim materializes an ActionRequest, calls execute, and prints
        the resulting ActionResult as JSON so the task runner can surface it
        in the task-detail view.
        """
        payload = {
            "action_id": args.get("action_id") or "",
            "plugin": args.get("plugin") or "hub-v2-operator",
            "target": args.get("target") or "",
            "args": args.get("action_args") or {},
            "rationale": args.get("rationale") or "Hub v2 Command Center invocation",
            "dry_run": bool(args.get("dry_run", False)),
        }
        shim = (
            "import sys, json; "
            f"sys.path.insert(0, {str(agc)!r}); "
            "from aigovclaw.action_executor import ActionExecutor, ActionRequest; "
            "from aigovclaw.action_executor.safety import utc_now_iso, new_request_id; "
            f"p = {payload!r}; "
            "req = ActionRequest(action_id=p['action_id'], plugin=p['plugin'], "
            "target=p['target'], args=p['args'], rationale=p['rationale'], "
            "dry_run=p['dry_run'], requested_at=utc_now_iso(), request_id=new_request_id()); "
            "ex = ActionExecutor(); res = ex.execute(req); "
            "print(json.dumps({"
            "'request_id': res.request_id, 'status': res.status, "
            "'authority_mode_used': res.authority_mode_used, "
            "'audit_entry_id': res.audit_entry_id, 'error': res.error, "
            "'output': res.output}, default=str))"
        )
        return [sys.executable, "-c", shim]

    def _action_approve(args: dict) -> list[str]:
        request_id = args.get("request_id") or ""
        reason = args.get("reason") or "Hub v2 operator approved"
        shim = (
            "import sys, json; "
            f"sys.path.insert(0, {str(agc)!r}); "
            "from aigovclaw.action_executor import ActionExecutor; "
            f"rid = {request_id!r}; reason = {reason!r}; "
            "ex = ActionExecutor(); "
            "res = ex.approve(rid, approver='hub-v2-operator'); "
            "print(json.dumps({"
            "'request_id': res.request_id, 'status': res.status, "
            "'error': res.error, 'output': res.output}, default=str))"
        )
        return [sys.executable, "-c", shim]

    def _action_reject(args: dict) -> list[str]:
        request_id = args.get("request_id") or ""
        reason = args.get("reason") or "Hub v2 operator rejected"
        shim = (
            "import sys, json; "
            f"sys.path.insert(0, {str(agc)!r}); "
            "from aigovclaw.action_executor import ActionExecutor; "
            f"rid = {request_id!r}; reason = {reason!r}; "
            "ex = ActionExecutor(); "
            "res = ex.reject(rid, reason=reason, approver='hub-v2-operator'); "
            "print(json.dumps({"
            "'request_id': res.request_id, 'status': res.status, "
            "'error': res.error}, default=str))"
        )
        return [sys.executable, "-c", shim]

    registry: dict[str, dict[str, Any]] = {
        "run-full-pipeline": {
            "id": "run-full-pipeline",
            "display_name": "Run full pipeline",
            "description": "Execute the AIMS pipeline against an organization.yaml.",
            "category": "pipeline",
            "args_schema": [
                {"name": "org", "type": "path", "required": True, "help": "organization.yaml"},
                {"name": "output", "type": "path", "required": False, "help": "output directory"},
                {"name": "framework", "type": "string", "required": False, "help": "iso42001 | nist-ai-rmf | eu-ai-act"},
                {"name": "include_crosswalk", "type": "bool", "required": False, "default": False},
            ],
            "requires_approval": False,
            "build_argv": _run_full_pipeline,
        },
        "run-plugin": {
            "id": "run-plugin",
            "display_name": "Run a single plugin",
            "description": "Invoke one plugin by name (bypasses the pipeline orchestrator).",
            "category": "pipeline",
            "args_schema": [
                {"name": "plugin", "type": "string", "required": True, "help": "plugin slug, e.g. risk-register-builder"},
                {"name": "output", "type": "path", "required": False},
            ],
            "requires_approval": False,
            "build_argv": _run_plugin,
        },
        "pack-bundle": {
            "id": "pack-bundle",
            "display_name": "Pack evidence bundle",
            "description": "Produce a signed, deterministic evidence bundle from artifacts on disk.",
            "category": "bundle",
            "args_schema": [
                {"name": "artifacts", "type": "path", "required": True},
                {"name": "output", "type": "path", "required": True},
                {"name": "signing_algorithm", "type": "string", "required": False, "default": "hmac-sha256"},
            ],
            "requires_approval": True,
            "build_argv": _pack_bundle,
        },
        "verify-bundle": {
            "id": "verify-bundle",
            "display_name": "Verify evidence bundle",
            "description": "Verify the signature and manifest of an evidence bundle.",
            "category": "bundle",
            "args_schema": [
                {"name": "bundle", "type": "path", "required": True},
            ],
            "requires_approval": False,
            "build_argv": _verify_bundle,
        },
        "inspect-bundle": {
            "id": "inspect-bundle",
            "display_name": "Inspect evidence bundle",
            "description": "Print manifest summary of a bundle.",
            "category": "bundle",
            "args_schema": [
                {"name": "bundle", "type": "path", "required": True},
            ],
            "requires_approval": False,
            "build_argv": _inspect_bundle,
        },
        "check-readiness": {
            "id": "check-readiness",
            "display_name": "Check certification readiness",
            "description": "Run certification-readiness assessment.",
            "category": "diagnostic",
            "args_schema": [
                {"name": "output", "type": "path", "required": False},
            ],
            "requires_approval": False,
            "build_argv": _check_readiness,
        },
        "doctor": {
            "id": "doctor",
            "display_name": "Run doctor diagnostic",
            "description": "Sanity check plugins, PyYAML, and the consistency audit.",
            "category": "diagnostic",
            "args_schema": [],
            "requires_approval": False,
            "build_argv": _doctor,
        },
        "generate-demo": {
            "id": "generate-demo",
            "display_name": "Generate demo scenario",
            "description": "Run aigovops/examples/demo-scenario/run_demo.py end-to-end.",
            "category": "pipeline",
            "args_schema": [],
            "requires_approval": False,
            "build_argv": _generate_demo,
        },
        "export-bundle-zip": {
            "id": "export-bundle-zip",
            "display_name": "Export bundle as zip",
            "description": "Create a zip archive of an evidence bundle directory.",
            "category": "artifact",
            "args_schema": [
                {"name": "bundle", "type": "path", "required": True},
                {"name": "dest", "type": "path", "required": True},
            ],
            "requires_approval": True,
            "build_argv": _export_bundle_zip,
        },
        "regenerate-hub": {
            "id": "regenerate-hub",
            "display_name": "Regenerate Hub v2 HTML",
            "description": "Rebuild the single-file Hub v2 dashboard from the current evidence store.",
            "category": "agent",
            "args_schema": [
                {"name": "output", "type": "path", "required": False},
            ],
            "requires_approval": False,
            "build_argv": _regenerate_hub,
        },
        "action-execute": {
            "id": "action-execute",
            "display_name": "Execute governance action",
            "description": (
                "Dispatch an ActionRequest through the aigovclaw action-executor. "
                "The executor resolves authority mode, records audit entries, "
                "and either runs the handler or enqueues the request for approval."
            ),
            "category": "action",
            "args_schema": [
                {"name": "action_id", "type": "string", "required": True,
                 "help": "file-update | mcp-push | notification | re-run-plugin | trigger-downstream | git-commit-and-push"},
                {"name": "plugin", "type": "string", "required": False,
                 "help": "originating plugin name (defaults to hub-v2-operator)"},
                {"name": "target", "type": "string", "required": True},
                {"name": "action_args", "type": "json", "required": False,
                 "help": "per-action args object (serialized JSON)"},
                {"name": "rationale", "type": "string", "required": False},
                {"name": "dry_run", "type": "bool", "required": False, "default": False},
            ],
            "requires_approval": False,
            "build_argv": _action_executor_shim,
        },
        "action-approve": {
            "id": "action-approve",
            "display_name": "Approve pending action",
            "description": "Approve a queued ActionRequest and run it through the handler.",
            "category": "action",
            "args_schema": [
                {"name": "request_id", "type": "string", "required": True},
                {"name": "reason", "type": "string", "required": False},
            ],
            "requires_approval": False,
            "build_argv": _action_approve,
        },
        "action-reject": {
            "id": "action-reject",
            "display_name": "Reject pending action",
            "description": "Reject a queued ActionRequest with a recorded reason.",
            "category": "action",
            "args_schema": [
                {"name": "request_id", "type": "string", "required": True},
                {"name": "reason", "type": "string", "required": True},
            ],
            "requires_approval": False,
            "build_argv": _action_reject,
        },
    }
    return registry


def public_registry(registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a JSON-serializable view of the registry (omits build_argv)."""
    out = []
    for spec in registry.values():
        out.append({
            "id": spec["id"],
            "display_name": spec["display_name"],
            "description": spec["description"],
            "category": spec["category"],
            "args_schema": spec["args_schema"],
            "requires_approval": spec["requires_approval"],
        })
    return out
