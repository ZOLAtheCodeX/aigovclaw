"""AIGovClaw Hub v1 CLI.

Usage:
  python3 -m aigovclaw.hub.v1.cli generate --output <path> [--evidence <path>]
  python3 -m aigovclaw.hub.v1.cli serve [--port 8080] [--host 127.0.0.1] [--evidence <path>]

v1 is an optional richer interactive view. v0 remains the default via
`python3 -m aigovclaw.hub.cli generate`.

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
from .generator import VendorMissingError, generate, resolve_evidence_path


def _cmd_generate(args: argparse.Namespace) -> int:
    evidence = args.evidence
    if args.demo_dir:
        demo = Path(args.demo_dir)
        dst = Path(evidence) if evidence else Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v1-demo-"))
        written = import_demo_outputs(demo, dst)
        print(f"Imported {len(written)} demo artifacts into {dst}")
        evidence = dst
    try:
        out = generate(args.output, evidence_path=evidence)
    except VendorMissingError as err:
        print(str(err), file=sys.stderr)
        return 2
    print(f"Wrote {out}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    evidence = resolve_evidence_path(args.evidence)
    if getattr(args, "demo_dir", None):
        demo = Path(args.demo_dir)
        dst = Path(args.evidence) if args.evidence else Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v1-demo-"))
        written = import_demo_outputs(demo, dst)
        print(f"Imported {len(written)} demo artifacts into {dst}")
        evidence = dst
    tmp_root = Path(tempfile.mkdtemp(prefix="aigovclaw-hub-v1-"))
    out_html = tmp_root / "index.html"
    try:
        generate(out_html, evidence_path=evidence)
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
            sys.stderr.write("[hub-v1] " + (fmt % a) + "\n")

    with socketserver.TCPServer((host, port), Handler) as httpd:
        url = f"http://{host}:{port}/index.html"
        print(f"Serving AIGovClaw hub v1 at {url}")
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
        prog="aigovclaw.hub.v1",
        description="Generate and serve the AIGovClaw hub v1 (React artifact).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Write a single-file React HTML artifact.")
    g.add_argument("--output", "-o", required=True, help="Output HTML file path.")
    g.add_argument("--evidence", default=None, help="Override evidence store path.")
    g.add_argument(
        "--demo-dir",
        default=None,
        help=(
            "Path to aigovops/examples/demo-scenario/outputs/. When set, the "
            "flat demo outputs are reshaped into the hub layout before rendering."
        ),
    )
    g.set_defaults(func=_cmd_generate)

    s = sub.add_parser("serve", help="Serve the v1 artifact over stdlib http.server.")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--evidence", default=None, help="Override evidence store path.")
    s.add_argument(
        "--demo-dir",
        default=None,
        help="Reshape aigovops/examples/demo-scenario/outputs/ into hub layout before serving.",
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
