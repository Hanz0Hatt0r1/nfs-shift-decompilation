#!/usr/bin/env python3
"""Build and validate the specialized-provider runtime capture handoff."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from specialized_provider_capture_handoff_runtime import (
    build_capture_handoff_contract,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="SHIFT.exe.c")
    parser.add_argument(
        "capture_directory",
        type=Path,
        help="provider capture directory",
    )
    parser.add_argument("--reset-events", type=Path)
    parser.add_argument(
        "--observed-provider-id",
        type=int,
        choices=(0, 1),
        help="provider id observed by the runtime capture",
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_capture_handoff_contract(
        args.source.read_text(encoding="utf-8"),
        args.capture_directory,
        reset_events_path=args.reset_events,
        observed_provider_id=args.observed_provider_id,
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

    validation = report.get("validation") or {}
    print(
        json.dumps(
            {
                "format": report["format"],
                "ready": report["ready"],
                "observed_provider_id": report["observed_provider_id"],
                "capture_ready": validation.get("capture_ready"),
                "attached_bundle_count": validation.get(
                    "attached_bundle_count"
                ),
                "observed_provider_attached": validation.get(
                    "observed_provider_attached"
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
