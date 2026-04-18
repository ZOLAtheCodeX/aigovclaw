"""Bridge from the aigovops demo-scenario flat-output layout to the
nested evidence-store layout the hub generator expects.

Demo outputs (aigovops/examples/demo-scenario/outputs/) are written flat:

    outputs/
      audit-log-entry.json
      risk-register.json
      soa.json
      aisia.json
      ...

Hub expects nested:

    <evidence>/risk-register/<anything>.json
    <evidence>/soa/<anything>.json
    ...

This module maps filenames to hub artifact-type directories and copies
them. No transformation of payload content; the plugin output dicts are
the contract the hub reads from.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


DEMO_FILE_TO_HUB_DIR = {
    "risk-register.json": "risk-register",
    "soa.json": "soa",
    "aisia.json": "aisia",
    "nonconformity-register.json": "nonconformity",
    "metrics-report.json": "metrics",
    "gap-assessment.json": "gap-assessment",
    # audit-log-entry, role-matrix, management-review-package are not
    # currently rendered as hub panels; skipped deliberately.
}


def import_demo_outputs(demo_outputs: Path, dst_evidence: Path) -> list[Path]:
    """Copy demo outputs into the hub-expected nested layout.

    Returns the list of destination files written.
    """
    if not demo_outputs.is_dir():
        raise FileNotFoundError(f"demo outputs directory not found: {demo_outputs}")
    dst_evidence.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for filename, hub_subdir in DEMO_FILE_TO_HUB_DIR.items():
        src = demo_outputs / filename
        if not src.is_file():
            continue
        dst_dir = dst_evidence / hub_subdir
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / filename
        shutil.copy2(src, dst)
        written.append(dst)
    return written


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="aigovclaw.hub.import_demo",
        description="Reshape the aigovops demo-scenario outputs directory into the "
        "nested layout the hub generator expects.",
    )
    ap.add_argument("--demo-dir", required=True, type=Path, help="path to aigovops/examples/demo-scenario/outputs/")
    ap.add_argument("--evidence", required=True, type=Path, help="destination evidence directory for the hub")
    args = ap.parse_args(argv)

    written = import_demo_outputs(args.demo_dir, args.evidence)
    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
