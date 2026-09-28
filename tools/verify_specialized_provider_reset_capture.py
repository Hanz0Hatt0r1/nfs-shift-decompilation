#!/usr/bin/env python3
"""Build a specialized-provider scalar-reset evidence manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from specialized_provider_reset_evidence_manifest_runtime import (
    build_reset_evidence_contract,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--events",
        type=Path,
        required=True,
        help="scalar_reset_events.jsonl from the GDB probe",
    )
    parser.add_argument(
        "--provider-pre",
        action="append",
        type=Path,
        default=[],
        help="provider_pre_<id>_<hit>.json; may be repeated",
    )
    parser.add_argument(
        "--provider-post",
        action="append",
        type=Path,
        default=[],
        help="provider_post_<id>_<hit>.json; may be repeated",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="optional output manifest path",
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(
                f"{path}:{line_number}: expected JSON object"
            )
        events.append(value)
    return events


def _validate_capture_lists(
    pre_paths: list[Path],
    post_paths: list[Path],
) -> None:
    if post_paths and len(pre_paths) != len(post_paths):
        raise ValueError(
            "--provider-pre and --provider-post must have equal counts"
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _validate_capture_lists(
        args.provider_pre,
        args.provider_post,
    )

    events = _load_events(args.events)
    provider_captures: list[dict[str, Any]] = []

    if args.provider_post:
        for pre_path, post_path in zip(
            args.provider_pre,
            args.provider_post,
        ):
            provider_captures.append(_load_json(pre_path))
            provider_captures.append(_load_json(post_path))
    else:
        provider_captures.extend(
            _load_json(path)
            for path in args.provider_pre
        )

    report = build_reset_evidence_contract(
        events,
        provider_captures=provider_captures,
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
                "event_count": report.get("event_count"),
                "frame_count": report.get("frame_count"),
                "provider_event_counts": summary.get(
                    "provider_event_counts"
                ),
                "group_event_counts": summary.get(
                    "group_event_counts"
                ),
                "provider_solve_checks": summary.get(
                    "provider_solve_checks"
                ),
                "provider_solve_ready": summary.get(
                    "provider_solve_ready"
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
