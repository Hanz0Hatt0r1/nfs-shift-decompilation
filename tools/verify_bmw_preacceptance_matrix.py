#!/usr/bin/env python3
"""Verify the real BMW BFF pre-acceptance structural matrix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bmw_preacceptance_matrix_verifier_runtime import (
    summarize_verification,
    verify_bmw_preacceptance_matrix,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bff",
        type=Path,
        help="path to BMW_M3_E36.bff",
    )
    parser.add_argument(
        "--strict-sdf",
        action="store_true",
        help="fail SDF parsing on unknown/unparsed lines",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write full JSON report",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    report = verify_bmw_preacceptance_matrix(
        args.bff,
        strict_sdf=args.strict_sdf,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            summarize_verification(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
