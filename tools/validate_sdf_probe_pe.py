#!/usr/bin/env python3
"""Validate retail SHIFT.exe against the source-backed SDF probe targets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdf_runtime_probe_pe_validation import (
    EXPECTED_EXECUTABLE_SHA256,
    validate_probe_executable_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, help="retail SHIFT.exe")
    parser.add_argument(
        "--allow-other-sha256",
        action="store_true",
        help="validate PE/prologues without enforcing the known supplied-executable SHA",
    )
    parser.add_argument("-o", "--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    expected_sha = None if args.allow_other_sha256 else EXPECTED_EXECUTABLE_SHA256
    report = validate_probe_executable_file(
        args.executable,
        expected_sha256=expected_sha,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "sha256": report["sha256"],
                "image_base": f"0x{report['image_base']:08x}",
                "target_count": len(report["targets"]),
                "errors": report["errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
