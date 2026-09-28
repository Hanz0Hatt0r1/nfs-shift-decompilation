#!/usr/bin/env python3
"""Verify one complete BMW M3 retail SDF runtime-probe bundle."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bmw_m3_runtime_probe_bundle_runtime import build_bundle_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shift", type=Path, required=True, help="SHIFT.exe or SHIFT.zip")
    parser.add_argument("--bff", type=Path, required=True, help="BMW_M3_E36.bff")
    parser.add_argument("--pre", type=Path, help="pre_solve_XXXXXX.json")
    parser.add_argument("--post", type=Path, help="post_solve_XXXXXX.json")
    parser.add_argument("--frame", type=Path, help="frame_entry_XXXXXX.json")
    parser.add_argument("--expected-session", type=Path)
    parser.add_argument("--abs-tol", type=float, default=0.0)
    parser.add_argument("--rel-tol", type=float, default=0.0)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("out/sdf-runtime-probe-bundle"),
    )
    parser.add_argument("-o", "--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_bundle_report(
        shift_input=args.shift,
        bff_path=args.bff,
        pre_path=args.pre,
        post_path=args.post,
        frame_path=args.frame,
        expected_session_path=args.expected_session,
        abs_tol=args.abs_tol,
        rel_tol=args.rel_tol,
        work_dir=args.work_dir,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "gates": report["gates"],
        "errors": report["errors"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
