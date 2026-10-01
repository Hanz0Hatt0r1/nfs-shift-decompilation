#!/usr/bin/env python3
"""Correlate Phase 635 FUN_00757d2c events with full-probe solver anchors."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relation_state_mutation_evidence_runtime import (
    FORMAT,
    build_relation_state_mutation_evidence,
)


_ANCHOR_GLOBS = (
    "frame_entry_*.json",
    "pre_solve_*.json",
    "provider_pre_*.json",
    "provider_post_*.json",
    "post_solve_*.json",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "capture_dir",
        type=Path,
        help="full sdf-probe capture directory",
    )
    parser.add_argument(
        "--events",
        type=Path,
        help="override relation_state_mutation_events.jsonl",
    )
    parser.add_argument(
        "--reset-events",
        type=Path,
        help="override scalar_reset_events.jsonl; optional",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="optional evidence manifest path",
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
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
        values.append(value)
    return values


def _anchor_paths(capture_dir: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in _ANCHOR_GLOBS:
        for path in sorted(capture_dir.glob(pattern)):
            resolved = path.resolve()
            if resolved not in seen:
                paths.append(path)
                seen.add(resolved)
    return paths


def _blocked_report(error: str) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "event_count": 0,
        "anchor_count": 0,
        "correlated_event_count": 0,
        "placements": [],
        "summary": {},
        "scheduler_admission": {
            "ready": False,
            "scope": "retail-event-evidence-only",
            "native_scheduler_integrated": False,
            "requires_explicit_native_mapping": True,
        },
        "errors": [error],
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    capture_dir = args.capture_dir.resolve()
    events_path = (
        args.events.resolve()
        if args.events is not None
        else capture_dir / "relation_state_mutation_events.jsonl"
    )
    reset_events_path = (
        args.reset_events.resolve()
        if args.reset_events is not None
        else capture_dir / "scalar_reset_events.jsonl"
    )

    if not capture_dir.is_dir():
        report = _blocked_report(
            f"missing-capture-directory:{capture_dir}"
        )
    elif not events_path.is_file():
        report = _blocked_report(
            f"missing-mutation-events:{events_path}"
        )
    else:
        try:
            events = _load_jsonl(events_path)
            anchor_paths = _anchor_paths(capture_dir)
            anchors = [_load_json(path) for path in anchor_paths]
            reset_events = (
                _load_jsonl(reset_events_path)
                if reset_events_path.is_file()
                else []
            )
            anchors.extend(reset_events)
            report = build_relation_state_mutation_evidence(
                events,
                anchors=anchors,
            )
            report["inputs"] = {
                "capture_dir": str(capture_dir),
                "mutation_events": str(events_path),
                "timeline_anchor_files": [
                    str(path.resolve())
                    for path in anchor_paths
                ],
                "scalar_reset_events": (
                    str(reset_events_path)
                    if reset_events_path.is_file()
                    else None
                ),
                "scalar_reset_event_count": len(reset_events),
            }
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            report = _blocked_report(
                f"capture-read-failed:{type(exc).__name__}:{exc}"
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
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    summary = report.get("summary") or {}
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "event_count": report.get("event_count", 0),
        "anchor_count": report.get("anchor_count", 0),
        "correlated_event_count": report.get(
            "correlated_event_count",
            0,
        ),
        "timing_class_counts": summary.get(
            "timing_class_counts",
            {},
        ),
        "timeline_window_counts": summary.get(
            "timeline_window_counts",
            {},
        ),
        "scheduler_admission": report.get(
            "scheduler_admission",
            {},
        ),
        "errors": report.get("errors", []),
    }, ensure_ascii=False, indent=2))

    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
