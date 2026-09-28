#!/usr/bin/env python3
"""Compare a specialized-provider pre/post capture with source-derived factor edges."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from specialized_provider_capture_source_mutation_runtime import (
    build_source_mutation_correlation_contract,
)
from specialized_provider_factor_pattern_runtime import extract_factor_pattern


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pre", type=Path, required=True)
    parser.add_argument("--post", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--provider",
        type=int,
        choices=(0, 1),
        required=True,
    )
    parser.add_argument(
        "--abs-tol",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--rel-tol",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
    )
    return parser


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    source_pattern = extract_factor_pattern(
        args.source.read_text(encoding="utf-8"),
        provider_id=args.provider,
    )
    report = build_source_mutation_correlation_contract(
        _load_json(args.pre),
        _load_json(args.post),
        source_pattern,
        abs_tol=args.abs_tol,
        rel_tol=args.rel_tol,
    )

    payload = (
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    summary = report["summary"]
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "provider_id": report["provider_id"],
                "source_edge_count": summary["source_edge_count"],
                "source_address_count": summary["source_address_count"],
                "observed_workspace_address_count": summary[
                    "observed_workspace_address_count"
                ],
                "observed_addresses_covered": summary[
                    "observed_addresses_covered"
                ],
                "observed_addresses_uncovered": summary[
                    "observed_addresses_uncovered"
                ],
                "alias_address_count": summary["alias_address_count"],
                "errors": report["errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
