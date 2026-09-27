#!/usr/bin/env python3
"""Compare two retail-style SDF solver snapshots."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sdf_solver_snapshot_parity_runtime import compare_solver_snapshot


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: root must be an object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument(
        "--abs-tolerance",
        type=float,
        default=0.0,
        help="absolute tolerance for matrix/RHS floating-point comparisons",
    )
    parser.add_argument(
        "--max-diffs",
        type=int,
        default=20,
        help="maximum number of matrix/RHS differences retained",
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = compare_solver_snapshot(
        load(args.expected),
        load(args.actual),
        abs_tolerance=args.abs_tolerance,
        max_diffs=args.max_diffs,
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
                "structural_match": report["structural_match"],
                "numeric_match": report["numeric_match"],
                "matrix_diff_count": report["matrix"]["diff_count"],
                "rhs_diff_count": report["rhs"]["diff_count"],
                "structural_errors": report["structural_errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["status"] == "match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
