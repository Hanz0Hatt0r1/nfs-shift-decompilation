#!/usr/bin/env python3
"""Preflight an authentic SHIFT provider capture environment."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sdf_runtime_probe_preflight_runtime import (
    preflight_provider_capture,
    validate_probe_script,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, help="SHIFT.exe or SHIFT.zip")
    parser.add_argument("output", type=Path)
    parser.add_argument("--probe-script", type=Path, required=True)
    parser.add_argument("--wine", default="wine")
    parser.add_argument("--gdb", default="gdb")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = preflight_provider_capture(
        args.executable,
        args.output,
        probe_script=args.probe_script,
        wine_command=args.wine,
        gdb_command=args.gdb,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "executable_valid": report["artifacts"]["ready"],
        "probe_script_exists": report["probe_script"]["exists"],
        "probe_script_valid": report["probe_script"]["validation"]["ready"],
        "wine": report["runtime_tools"]["wine"],
        "gdb": report["runtime_tools"]["gdb"],
        "gdb_python_ready": report["gdb_python"]["ready"],
        "errors": report["errors"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
