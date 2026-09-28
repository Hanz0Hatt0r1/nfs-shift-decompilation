#!/usr/bin/env python3
"""Build the source-backed pre-PhysX/provider handoff contract from SDF JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prephysx_provider_handoff_runtime import build_prephysx_provider_handoff_contract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="parsed SHIFT.RigidBodySDFRuntime/1 JSON")
    parser.add_argument("-o", "--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = json.loads(args.input.read_text(encoding="utf-8"))
    contract = build_prephysx_provider_handoff_contract(report)
    payload = json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    print(json.dumps({
        "format": contract["format"],
        "status": contract["status"],
        "ready": contract["ready"],
        "solver_scalar_count": contract["selection"]["solver_scalar_count"],
        "same_dimension_candidates": contract["selection"]["same_dimension_candidates"],
        "generic_fallback_available": contract["selection"]["generic_fallback_available"],
        "errors": contract["errors"],
    }, ensure_ascii=False, indent=2))
    return 0 if contract["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
