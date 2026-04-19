"""AIGovClaw Hub CLI.

Usage:
  python3 -m aigovclaw.hub.cli generate    --output <path> [--evidence <path>]
  python3 -m aigovclaw.hub.cli serve       [--port 8080] [--host 127.0.0.1] [--evidence <path>]
  python3 -m aigovclaw.hub.cli generate-v1 --output <path> [--evidence <path>]
  python3 -m aigovclaw.hub.cli generate-v2 --output <path> [--evidence <path>]

The `generate` and `serve` subcommands produce v0 (zero-dependency single-file
HTML). `generate-v1` delegates to hub.v1.cli and produces the React editorial
artifact. `generate-v2` delegates to hub.v2.cli and produces the practitioner
dashboard (AIGovOS IA ported onto AIGovOps plugin data).

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
from .import_demo import import_demo_outputs


def _cmd_generate(args: argparse.Namespace) -> int:
    evidence = args.evidence
    if args.demo_dir:
        demo = Path(args.demo_dir)
        dst = Path(evidence) if evidence else Path(tempfile.mkdtemp(prefix="aigovclaw-hub-demo-"))
        written = import_demo_outputs(demo, dst)
        print(f"Imported {len(written)} demo artifacts into {dst}")
        evidence = dst
    out = generate(args.output, evidence_path=evidence)
    print(f"Wrote {out}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    evidence = resolve_evidence_path(args.evidence)
    if getattr(args, "demo_dir", None):
        demo = Path(args.demo_dir)
        dst = Path(args.evidence) if args.evidence else Path(tempfile.mkdtemp(prefix="aigovclaw-hub-demo-"))
        written = import_demo_outputs(demo, dst)
        print(f"Imported {len(written)} demo artifacts into {dst}")
        evidence = dst
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
        print(f"Serving AIGovClaw Command Centre at {url}")
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
        description="Generate and serve the AIGovClaw composite AIMS Command Centre.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Write a single-file HTML dashboard.")
    g.add_argument("--output", "-o", required=True, help="Output HTML file path.")
    g.add_argument("--evidence", default=None, help="Override evidence store path.")
    g.add_argument(
        "--demo-dir",
        default=None,
        help=(
            "Path to aigovops/examples/demo-scenario/outputs/. When set, the flat "
            "demo outputs are reshaped into the hub layout (into --evidence if "
            "provided, else a tmp dir) before rendering."
        ),
    )
    g.set_defaults(func=_cmd_generate)

    s = sub.add_parser("serve", help="Serve the dashboard over stdlib http.server.")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--evidence", default=None, help="Override evidence store path.")
    s.add_argument(
        "--demo-dir",
        default=None,
        help=(
            "Path to aigovops/examples/demo-scenario/outputs/. When set, the "
            "flat demo outputs are reshaped into the hub layout before serving."
        ),
    )
    s.add_argument("--open", action="store_true", help="Open a browser window.")
    s.set_defaults(func=_cmd_serve)

    # v1: delegate to hub.v1.cli. Keep the v0 commands untouched.
    g1 = sub.add_parser(
        "generate-v1",
        help="Write the v1 React + shadcn-shaped single-file artifact.",
    )
    g1.add_argument("--output", "-o", required=True, help="Output HTML file path.")
    g1.add_argument("--evidence", default=None, help="Override evidence store path.")
    g1.add_argument(
        "--demo-dir",
        default=None,
        help="Reshape aigovops demo-scenario outputs before rendering.",
    )
    g1.set_defaults(func=_cmd_generate_v1)

    # v2: practitioner dashboard with CASCADE / DISCOVERY / ASSURANCE / GOVERNANCE IA.
    g2 = sub.add_parser(
        "generate-v2",
        help="Write the v2 practitioner dashboard single-file artifact.",
    )
    g2.add_argument("--output", "-o", required=True, help="Output HTML file path.")
    g2.add_argument("--evidence", default=None, help="Override evidence store path.")
    g2.add_argument(
        "--aigovops-root",
        default=None,
        help="Path to the aigovops repo (for crosswalk data). Defaults to sibling checkout.",
    )
    g2.add_argument(
        "--demo-dir",
        default=None,
        help="Reshape aigovops demo-scenario outputs before rendering.",
    )
    g2.set_defaults(func=_cmd_generate_v2)

    # hub-v2-serve: start the Hub v2 command-center HTTP server. Serves the
    # Hub v2 HTML at / and the JSON API under /api/*. Binds 127.0.0.1 by
    # default. See hub/v2_server/server.py for the endpoint list.
    sv2 = sub.add_parser(
        "hub-v2-serve",
        help="Start the Command Centre v2 server (HTML + JSON API).",
    )
    sv2.add_argument("--port", type=int, default=8080)
    sv2.add_argument("--host", default="127.0.0.1")
    sv2.add_argument("--evidence", default=None, help="Override evidence store path.")
    sv2.add_argument("--aigovops-root", default=None, help="Path to aigovops repo.")
    sv2.add_argument("--demo-dir", default=None,
                     help="Reshape aigovops demo-scenario outputs before serving.")
    sv2.add_argument("--open", action="store_true", help="Open a browser window.")
    sv2.set_defaults(func=_cmd_hub_v2_serve)

    return p


def _cmd_hub_v2_serve(args: argparse.Namespace) -> int:
    # Lazy import to avoid forcing server deps on generate-only paths.
    from .v2.cli import _cmd_serve as v2_serve  # noqa: WPS433
    return v2_serve(args)


def _cmd_generate_v1(args: argparse.Namespace) -> int:
    # Import lazily so the v0 CLI keeps working if hub.v1 is absent.
    from .v1.cli import _cmd_generate as v1_generate  # noqa: WPS433
    return v1_generate(args)


def _cmd_generate_v2(args: argparse.Namespace) -> int:
    from .v2.cli import _cmd_generate as v2_generate  # noqa: WPS433
    return v2_generate(args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
