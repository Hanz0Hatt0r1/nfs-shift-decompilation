#!/usr/bin/env python3
"""Build an end-to-end vehicle BFF to pre-PhysX/provider handoff manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from vehicle_physics_handoff_runtime import build_vehicle_physics_handoff


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bff", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_vehicle_physics_handoff(
        args.bff,
        args.output,
        strict=args.strict,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "solver_scalar_count": report["summary"]["solver_scalar_count"],
        "same_dimension_provider_candidates": report["summary"]["same_dimension_provider_candidates"],
        "errors": report["errors"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
