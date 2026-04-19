"""AIGovClaw Hub v2 CLI.

Usage:
  python3 -m aigovclaw.hub.v2.cli generate --output <path> [--evidence <path>] [--aigovops-root <path>]
  python3 -m aigovclaw.hub.v2.cli serve    [--port 8080] [--host 127.0.0.1] [--evidence <path>]

v2 is the practitioner-facing dashboard that ports the AIGovOS information
architecture onto the AIGovOps plugin data model. v0 and v1 remain unchanged.

Stdlib only.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import webbrowser
from pathlib import Path

from ..import_demo import import_demo_outputs
from .generator import (
    DEFAULT_AIGOVOPS_ROOT,
    VendorMissingError,
    generate,
    resolve_evidence_path,
)


def _cmd_generate(args: argparse.Namespace) -> int:
    evidence = args.evidence
    if getattr(args, "demo_dir", None):
        demo = Path(args.demo_dir)
        dst = Path(evidence) if evidence else Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v2-demo-"))
        written = import_demo_outputs(demo, dst)
        print(f"Imported {len(written)} demo artifacts into {dst}")
        evidence = dst
    root = args.aigovops_root or None
    try:
        out = generate(args.output, evidence_path=evidence, aigovops_root=root)
    except VendorMissingError as err:
        print(str(err), file=sys.stderr)
        return 2
    print(f"Wrote {out}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Start the command-center HTTP server.

    Serves the Hub v2 HTML at GET / and the full command-center JSON API
    under /api/*. See hub/v2_server/server.py for the endpoint list.
    """
    evidence = resolve_evidence_path(args.evidence)
    if getattr(args, "demo_dir", None):
        demo = Path(args.demo_dir)
        dst = Path(args.evidence) if args.evidence else Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v2-demo-"))
        written = import_demo_outputs(demo, dst)
        print(f"Imported {len(written)} demo artifacts into {dst}")
        evidence = dst

    # Pre-flight vendor check so the CLI fails fast with the maintainer message
    # rather than waiting for the first browser hit.
    tmp_root = Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v2-"))
    try:
        generate(tmp_root / "preflight.html", evidence_path=evidence, aigovops_root=args.aigovops_root)
    except VendorMissingError as err:
        print(str(err), file=sys.stderr)
        return 2

    # Lazy import to keep the generate path free of server deps.
    from ..v2_server.server import serve as cc_serve

    if args.open:
        try:
            webbrowser.open(f"http://{args.host}:{args.port}/")
        except Exception:
            pass

    cc_serve(
        host=args.host,
        port=args.port,
        evidence_path=evidence,
        aigovops_root=args.aigovops_root,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aigovclaw.hub.v2",
        description="Generate and serve the AIGovClaw hub v2 (practitioner dashboard).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Write the v2 single-file HTML dashboard.")
    g.add_argument("--output", "-o", required=True, help="Output HTML file path.")
    g.add_argument("--evidence", default=None, help="Override evidence store path.")
    g.add_argument(
        "--aigovops-root",
        default=str(DEFAULT_AIGOVOPS_ROOT) if DEFAULT_AIGOVOPS_ROOT.exists() else None,
        help="Path to the aigovops repo (for crosswalk data). Defaults to sibling checkout.",
    )
    g.add_argument(
        "--demo-dir",
        default=None,
        help="Path to aigovops/examples/demo-scenario/outputs/. Reshape into hub layout before rendering.",
    )
    g.set_defaults(func=_cmd_generate)

    s = sub.add_parser("serve", help="Serve the v2 dashboard over stdlib http.server.")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--evidence", default=None, help="Override evidence store path.")
    s.add_argument(
        "--aigovops-root",
        default=str(DEFAULT_AIGOVOPS_ROOT) if DEFAULT_AIGOVOPS_ROOT.exists() else None,
        help="Path to the aigovops repo (for crosswalk data).",
    )
    s.add_argument(
        "--demo-dir",
        default=None,
        help="Reshape aigovops demo-scenario outputs before serving.",
    )
    s.add_argument("--open", action="store_true", help="Open a browser window.")
    s.set_defaults(func=_cmd_serve)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
