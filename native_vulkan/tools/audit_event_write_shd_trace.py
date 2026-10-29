#!/usr/bin/env python3
"""Validate Native EVENT_WRITE_SHD provenance and summarize software-head writes."""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


EVENT_RE = re.compile(
    r"ring trace EVENT_WRITE_SHD event=(?P<event>\d+) "
    r"monotonic_ns=(?P<time>\d+) batch=(?P<batch>\d+) "
    r"generation=(?P<generation>\d+) batch_rptr=(?P<rptr>\d+) "
    r"batch_wptr=(?P<wptr>\d+) ring_guest=(?P<ring>[0-9a-fA-F]+) "
    r"packet=(?P<ordinal>\d+) source_ib=(?P<source>[0-9a-fA-F]+) "
    r"source_offset=(?P<offset>\d+) depth=(?P<depth>\d+) "
    r"raw_words=\[(?P<raw>[0-9a-fA-F,]*)\] "
    r"expanded_words=\[(?P<expanded>[0-9a-fA-F,]*)\] "
    r"source_bytes_match=(?P<source_match>true|false) "
    r"initiator=(?P<initiator>[0-9a-fA-F]+) "
    r"encoded_address=(?P<encoded>[0-9a-fA-F]+) "
    r"guest_physical=(?P<guest>[0-9a-fA-F]+) "
    r"destination_host=(?P<host>\S+) endian=(?P<endian>\d+) "
    r"value_mode=(?P<mode>literal|swap_counter) "
    r"packet_value=(?P<packet_value>[0-9a-fA-F]+) "
    r"swap_counter=(?P<counter>\d+) "
    r"decoded_value=(?P<decoded>[0-9a-fA-F]+) "
    r"raw_store=(?P<raw_store>[0-9a-fA-F]+) "
    r"guest_value=(?P<old>[0-9a-fA-F]+)->(?P<new>[0-9a-fA-F]+)"
)


def _hex_words(value):
    return [int(word, 16) for word in value.split(",") if word]


def parse_line(line):
    match = EVENT_RE.search(line)
    if not match:
        return None
    raw = match.groupdict()
    row = {
        "event": int(raw["event"]),
        "monotonic_ns": int(raw["time"]),
        "batch": int(raw["batch"]),
        "generation": int(raw["generation"]),
        "batch_rptr": int(raw["rptr"]),
        "batch_wptr": int(raw["wptr"]),
        "ring_guest": int(raw["ring"], 16),
        "packet_ordinal": int(raw["ordinal"]),
        "source_ib": int(raw["source"], 16),
        "source_offset": int(raw["offset"]),
        "nesting_depth": int(raw["depth"]),
        "raw_words": _hex_words(raw["raw"]),
        "expanded_words": _hex_words(raw["expanded"]),
        "source_bytes_match": raw["source_match"] == "true",
        "initiator": int(raw["initiator"], 16),
        "encoded_address": int(raw["encoded"], 16),
        "guest_physical": int(raw["guest"], 16),
        "destination_host": raw["host"],
        "endian": int(raw["endian"]),
        "value_mode": raw["mode"],
        "packet_value": int(raw["packet_value"], 16),
        "swap_counter": int(raw["counter"]),
        "decoded_value": int(raw["decoded"], 16),
        "raw_store": int(raw["raw_store"], 16),
        "guest_value_before": int(raw["old"], 16),
        "guest_value_after": int(raw["new"], 16),
    }
    if len(row["raw_words"]) != 4:
        raise ValueError(f"EVENT_WRITE_SHD event {row['event']} has malformed raw words")
    if row["raw_words"][1] != row["initiator"]:
        raise ValueError(f"EVENT_WRITE_SHD event {row['event']} initiator disagrees with raw packet")
    if row["raw_words"][2] != row["encoded_address"]:
        raise ValueError(f"EVENT_WRITE_SHD event {row['event']} address disagrees with raw packet")
    if row["raw_words"][3] != row["packet_value"]:
        raise ValueError(f"EVENT_WRITE_SHD event {row['event']} value disagrees with raw packet")
    if row["encoded_address"] & ~3 != row["guest_physical"]:
        raise ValueError(f"EVENT_WRITE_SHD event {row['event']} guest address decode mismatch")
    if row["encoded_address"] & 3 != row["endian"]:
        raise ValueError(f"EVENT_WRITE_SHD event {row['event']} endian decode mismatch")
    expected_value = (
        row["swap_counter"]
        if row["initiator"] & 0x80000000
        else row["packet_value"]
    )
    if row["decoded_value"] != expected_value:
        raise ValueError(f"EVENT_WRITE_SHD event {row['event']} value semantics mismatch")
    return row


def audit(log_paths, target):
    rows = []
    for path in log_paths:
        with Path(path).open(errors="replace") as stream:
            rows.extend(row for line in stream if (row := parse_line(line)))
    rows.sort(key=lambda row: row["event"])
    if not rows:
        raise ValueError("no EVENT_WRITE_SHD trace records found")
    event_ids = [row["event"] for row in rows]
    missing_ids = [
        value
        for left, right in zip(event_ids, event_ids[1:])
        for value in range(left + 1, right)
    ]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("duplicate EVENT_WRITE_SHD event sequence number")

    target_rows = [row for row in rows if row["guest_physical"] == target]
    if not target_rows:
        raise ValueError(f"no EVENT_WRITE_SHD writes target 0x{target:08X}")
    regressions = [
        row for row in target_rows
        if row["guest_value_after"] < row["guest_value_before"]
    ]
    source_mismatches = [row for row in rows if not row["source_bytes_match"]]
    prior_value_mismatches = [
        {"event": previous["event"], "next_event": current["event"],
         "previous_after": previous["guest_value_after"],
         "current_before": current["guest_value_before"]}
        for previous, current in zip(target_rows, target_rows[1:])
        if previous["guest_value_after"] != current["guest_value_before"]
    ]
    transitions = Counter(
        row["guest_value_after"] - row["guest_value_before"]
        for row in target_rows
    )
    return {
        "schema": "shift.process2.event_write_shd_trace_audit.v1",
        "target_guest_physical": f"0x{target:08X}",
        "summary": {
            "event_write_records": len(rows),
            "event_sequence_range": [event_ids[0], event_ids[-1]],
            "missing_event_sequence_ids": missing_ids,
            "target_write_count": len(target_rows),
            "target_transition_delta_counts": dict(sorted(transitions.items())),
            "target_regression_count": len(regressions),
            "expanded_to_execution_byte_mismatches": len(source_mismatches),
            "target_previous_after_mismatches": len(prior_value_mismatches),
        },
        "regressions": regressions,
        "source_byte_mismatches": source_mismatches,
        "target_previous_after_mismatches": prior_value_mismatches,
        "target_writes": target_rows,
        "interpretation_limit": (
            "A complete trace attributes each store to its executed packet and its "
            "expanded-byte snapshot. A packet with an explicit stale value is not "
            "by itself proof of a Native bug; compare its original guest command and "
            "the paired run before classifying the behavior."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", action="append", required=True)
    parser.add_argument("--target", type=lambda value: int(value, 0), default=0x17AF4000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.log, args.target)
    except (OSError, ValueError) as exc:
        print(f"EVENT_WRITE_SHD audit failed: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
