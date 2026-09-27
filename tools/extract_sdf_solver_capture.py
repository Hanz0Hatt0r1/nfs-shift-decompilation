#!/usr/bin/env python3
"""Extract a normalized SHIFT SDF solver frame from a raw binary capture."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sdf_solver_capture_binary_runtime import (
    capture_to_json,
    read_flat_solver_capture_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract a normalized SDF solver frame from an explicit-offset raw binary dump"
    )
    parser.add_argument("input", type=Path, help="raw binary capture blob")
    parser.add_argument("output", type=Path, help="normalized solver-frame JSON")
    parser.add_argument("--scalar-count", type=int, required=True)
    parser.add_argument("--rhs-offset", type=int, required=True, help="RHS byte offset")
    parser.add_argument("--matrix-offset", type=int, required=True, help="matrix byte offset")
    parser.add_argument("--frame", type=int)
    parser.add_argument("--source")
    parser.add_argument(
        "--identity-node",
        type=int,
        action="append",
        default=[],
        help="runtime identity scalar node; repeatable",
    )
    parser.add_argument(
        "--row-index",
        type=int,
        action="append",
        default=None,
        help="logical row offset; repeatable",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    capture = read_flat_solver_capture_file(
        args.input,
        scalar_count=args.scalar_count,
        rhs_offset=args.rhs_offset,
        matrix_offset=args.matrix_offset,
        row_indices=args.row_index,
        runtime_identity_nodes=args.identity_node,
        frame=args.frame,
    )
    result = capture_to_json(capture, args.output)
    print(
        json.dumps(
            {
                "format": result["format"],
                "status": "written",
                "ready": result["ready"],
                "output": result["output"],
                "scalar_count": result["scalar_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
