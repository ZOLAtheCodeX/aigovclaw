"""AIGovClaw Hub CLI.

Usage:
  python3 -m aigovclaw.hub.cli generate --output <path> [--evidence <path>]
  python3 -m aigovclaw.hub.cli serve [--port 8080] [--host 127.0.0.1] [--evidence <path>]

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

from .generator import generate, resolve_evidence_path


def _cmd_generate(args: argparse.Namespace) -> int:
    out = generate(args.output, evidence_path=args.evidence)
    print(f"Wrote {out}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    evidence = resolve_evidence_path(args.evidence)
    tmp_root = Path(tempfile.mkdtemp(prefix="aigovclaw-hub-"))
    out_html = tmp_root / "index.html"
    generate(out_html, evidence_path=evidence)

    # Mirror evidence files under /evidence/ for drill-down links. Symlink when
    # possible, otherwise fall back to serving absolute paths with a custom
    # handler. We use a working-tree layout where index.html sits alongside the
    # evidence tree, so relative drill-down hrefs resolve correctly.
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
            sys.stderr.write("[hub] " + (fmt % a) + "\n")

    with socketserver.TCPServer((host, port), Handler) as httpd:
        url = f"http://{host}:{port}/index.html"
        print(f"Serving AIGovClaw hub at {url}")
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
        prog="aigovclaw.hub",
        description="Generate and serve the AIGovClaw composite AIMS hub.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Write a single-file HTML dashboard.")
    g.add_argument("--output", "-o", required=True, help="Output HTML file path.")
    g.add_argument("--evidence", default=None, help="Override evidence store path.")
    g.set_defaults(func=_cmd_generate)

    s = sub.add_parser("serve", help="Serve the dashboard over stdlib http.server.")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--evidence", default=None, help="Override evidence store path.")
    s.add_argument("--open", action="store_true", help="Open a browser window.")
    s.set_defaults(func=_cmd_serve)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
