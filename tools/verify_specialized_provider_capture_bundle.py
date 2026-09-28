#!/usr/bin/env python3
"""Analyze all specialized-provider snapshots in a capture directory."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from specialized_provider_capture_bundle_runtime import (
    build_capture_bundle_contract,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        type=Path,
        help="directory containing provider_pre/provider_post captures",
    )
    parser.add_argument(
        "--reset-events",
        type=Path,
        help="optional scalar_reset_events.jsonl",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="optional output manifest path",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    report = build_capture_bundle_contract(
        args.directory,
        reset_events_path=args.reset_events,
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

    summary = report.get("summary") or {}
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "directory": report["directory"],
                "bundle_count": report["bundle_count"],
                "provider_bundle_counts": summary.get(
                    "provider_bundle_counts"
                ),
                "bundles_with_post": summary.get("bundles_with_post"),
                "reset_event_count_total": summary.get(
                    "reset_event_count_total"
                ),
                "reset_events_reconciled": summary.get(
                    "reset_events_reconciled"
                ),
                "ready_bundle_count": summary.get(
                    "ready_bundle_count"
                ),
                "errors": report.get("errors", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
