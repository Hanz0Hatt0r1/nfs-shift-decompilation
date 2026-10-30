#!/usr/bin/env python3
"""Export same-run P1 callbacks and Native PM4 interrupts as ordered JSONL.gz."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path


CAPTURE_PATH = Path(__file__).with_name(
    "capture_linux_post_bink_worker_route_v45_ordered_route_20261027.py"
)
SPEC = importlib.util.spec_from_file_location("worker_route_capture", CAPTURE_PATH)
assert SPEC and SPEC.loader
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


def join_input_rows(events: dict, interrupts: list[dict]) -> list[dict]:
    rows = []
    for event in events.get("events", {}).get("source1_callback_events", []):
        if event.get("source") == 1 and isinstance(event.get("wall_clock_epoch_ms"), int):
            rows.append({
                "record_type": "p1_guest_source1_callback",
                "timestamp_epoch_ms": event["wall_clock_epoch_ms"],
                "event": event,
            })
    for event in interrupts:
        if event.get("source") == 1 and isinstance(event.get("timestamp_epoch_ms"), int):
            rows.append({
                "record_type": "p2_source1_pm4_interrupt",
                "timestamp_epoch_ms": event["timestamp_epoch_ms"],
                "event": event,
            })
    return sorted(rows, key=lambda row: (
        row["timestamp_epoch_ms"], row["record_type"],
        row["event"].get("entry_ordinal", row["event"].get("ordinal", 0)),
    ))


def write_archive(rows: list[dict], output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                for row in rows:
                    text.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-json", type=Path, required=True)
    parser.add_argument("--renderer-log", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    events = json.loads(args.events_json.read_text(encoding="utf-8"))
    interrupts = []
    malformed = 0
    for log_path in args.renderer_log:
        records, bad = CAPTURE.parse_ring_interrupt_log(log_path)
        interrupts.extend(records)
        malformed += bad
    if malformed:
        raise SystemExit(f"refusing incomplete ring trace: malformed records={malformed}")
    rows = join_input_rows(events, interrupts)
    callbacks = sum(row["record_type"] == "p1_guest_source1_callback" for row in rows)
    pm4 = sum(row["record_type"] == "p2_source1_pm4_interrupt" for row in rows)
    if not callbacks or not pm4:
        raise SystemExit(f"refusing empty join input: callbacks={callbacks} source1_pm4={pm4}")
    digest = write_archive(rows, args.output)
    print(json.dumps({
        "output": str(args.output),
        "sha256": digest,
        "records": len(rows),
        "p1_source1_callbacks": callbacks,
        "p2_source1_pm4_interrupts": pm4,
        "malformed_ring_records": malformed,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
