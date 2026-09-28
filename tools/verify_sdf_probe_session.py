#!/usr/bin/env python3
"""Verify a paired pre/post SDF runtime probe session."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdf_runtime_probe_session_runtime import (
    compare_probe_session,
    load_probe_json,
    normalize_probe_session,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pre", type=Path, required=True, help="pre_solve_XXXXXX.json")
    parser.add_argument("--post", type=Path, help="post_solve_XXXXXX.json")
    parser.add_argument("--frame", type=Path, help="optional frame_entry_XXXXXX.json")
    parser.add_argument("--expected-pre", type=Path)
    parser.add_argument("--expected-post", type=Path)
    parser.add_argument("--abs-tol", type=float, default=0.0)
    parser.add_argument("--rel-tol", type=float, default=0.0)
    parser.add_argument("-o", "--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    observed = {
        "pre_solve": load_probe_json(args.pre),
    }
    if args.post is not None:
        observed["post_solve"] = load_probe_json(args.post)
    if args.frame is not None:
        observed["frame_entry"] = load_probe_json(args.frame)

    if args.expected_pre is None and args.expected_post is None:
        report = normalize_probe_session(
            observed["pre_solve"],
            observed.get("post_solve"),
        )
    else:
        if args.expected_pre is None:
            raise ValueError("--expected-pre is required when using expected captures")
        expected = {
            "pre_solve": load_probe_json(args.expected_pre),
        }
        if args.expected_post is not None:
            expected["post_solve"] = load_probe_json(args.expected_post)
        report = compare_probe_session(
            observed,
            expected,
            abs_tol=args.abs_tol,
            rel_tol=args.rel_tol,
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
                "frame": report.get("frame"),
                "errors": report.get("errors", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
