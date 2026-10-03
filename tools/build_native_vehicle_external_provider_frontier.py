#!/usr/bin/env python3
"""Emit the Phase 699 external-provider frontier for Process 1 handoff."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHYSICS = ROOT / "src" / "physics"
if str(PHYSICS) not in sys.path:
    sys.path.insert(0, str(PHYSICS))

from native_vehicle_external_provider_frontier import build_frontier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)

    report = build_frontier()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"format: {report['format']}")
    print(f"external providers: {report['external_provider_count']}")
    print(f"implement now: {len(report['implement_now'])}")
    print(f"Process 1 handoffs: {len(report['process1_handoff_requests'])}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
