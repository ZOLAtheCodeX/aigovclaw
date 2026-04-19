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
import http.server
import socketserver
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
    evidence = resolve_evidence_path(args.evidence)
    if getattr(args, "demo_dir", None):
        demo = Path(args.demo_dir)
        dst = Path(args.evidence) if args.evidence else Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v2-demo-"))
        written = import_demo_outputs(demo, dst)
        print(f"Imported {len(written)} demo artifacts into {dst}")
        evidence = dst
    tmp_root = Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v2-"))
    out_html = tmp_root / "index.html"
    try:
        generate(out_html, evidence_path=evidence, aigovops_root=args.aigovops_root)
    except VendorMissingError as err:
        print(str(err), file=sys.stderr)
        return 2

    try:
        link = tmp_root / evidence.name
        if evidence.exists() and not link.exists():
            link.symlink_to(evidence, target_is_directory=True)
    except OSError:
        pass

    host = args.host
    port = args.port

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(tmp_root), **kw)

        def log_message(self, fmt, *a):
            sys.stderr.write("[hub-v2] " + (fmt % a) + "\n")

    with socketserver.TCPServer((host, port), Handler) as httpd:
        url = f"http://{host}:{port}/index.html"
        print(f"Serving AIGovClaw hub v2 at {url}")
        print(f"Evidence: {evidence}")
        print("Ctrl-C to stop.")
        if args.open:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
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
