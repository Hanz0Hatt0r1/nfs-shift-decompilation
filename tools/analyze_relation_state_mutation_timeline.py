#!/usr/bin/env python3
"""Correlate captured FUN_00757d2c events with the retail solver timeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
PHYSICS_SRC = ROOT / "src" / "physics"
if str(PHYSICS_SRC) not in sys.path:
    sys.path.insert(0, str(PHYSICS_SRC))

from relation_state_mutation_timeline_correlation_runtime import (  # noqa: E402
    analyze_relation_state_mutation_capture_directory,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "capture_directory",
        type=Path,
        help="full-mode sdf-probe capture directory",
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = analyze_relation_state_mutation_capture_directory(
        args.capture_directory
    )
    payload = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "format": report["format"],
                "ready": report["ready"],
                "mutation_event_count": report["mutation_event_count"],
                "timeline_anchor_count": report["timeline_anchor_count"],
                "summary": report["summary"],
                "errors": report["errors"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
