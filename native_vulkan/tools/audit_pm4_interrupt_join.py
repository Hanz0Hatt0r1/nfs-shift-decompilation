#!/usr/bin/env python3
"""Audit P1 source-1 callback events against Process 2 PM4 interrupt logs.

The timestamp/order join is evidence of correspondence only. Process 2 logs the
outer guest callback invoked for a PM4 interrupt; Process 1 may observe nested
callbacks run by that wrapper.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


P2_RE = re.compile(
    r"^\[(?P<time>[^]]+)\].*?ring trace PM4_INTERRUPT #(?P<id>\d+) "
    r"source=1 generation=(?P<generation>\d+) "
    r"batch_rptr=(?P<rptr>\d+) batch_wptr=(?P<wptr>\d+) "
    r"ring_guest=(?P<ring>[0-9a-fA-F]+) packet=(?P<ordinal>\d+) "
    r"packet_source=(?P<source>[0-9a-fA-F]+)\+(?P<offset>\d+) "
    r"cpu_mask=0x(?P<mask>[0-9a-fA-F]+) "
    r"dispatched_cpu_mask=0x(?P<dispatched>[0-9a-fA-F]+) "
    r"callback_dispatches=\[(?P<callbacks>.*)\]$"
)
CALLBACK_RE = re.compile(
    r"cpu(?P<cpu>\d+):callback=0x(?P<callback>[0-9a-fA-F]+),"
    r"data=0x(?P<data>[0-9a-fA-F]+),status=(?P<status>[a-z_]+)"
)


def parse_p2_line(line):
    match = P2_RE.search(line.rstrip())
    if not match:
        return None
    row = match.groupdict()
    timestamp = datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S.%f")
    callback_matches = list(CALLBACK_RE.finditer(row.pop("callbacks")))
    row.update(
        timestamp_ms=round(timestamp.astimezone().timestamp() * 1000),
        id=int(row["id"]),
        generation=int(row["generation"]),
        rptr=int(row["rptr"]),
        wptr=int(row["wptr"]),
        ring=int(row["ring"], 16),
        ordinal=int(row["ordinal"]),
        packet_source=int(row["source"], 16),
        packet_offset=int(row["offset"]),
        mask=int(row["mask"], 16),
        dispatched=int(row["dispatched"], 16),
        callbacks=[
            {
                "cpu": int(cb["cpu"]),
                "callback": int(cb["callback"], 16),
                "data": int(cb["data"], 16),
                "status": cb["status"],
            }
            for cb in callback_matches
        ],
    )
    return row


def audit(events_path, log_paths, max_delta_ms):
    events = json.loads(Path(events_path).read_text())
    p1 = events["events"]["source1_callback_events"]
    if not p1:
        raise ValueError("P1 capture contains no source-1 callback events")
    p2 = []
    for path in log_paths:
        with Path(path).open(errors="replace") as stream:
            p2.extend(row for line in stream if (row := parse_p2_line(line)))
    p2.sort(key=lambda row: (row["timestamp_ms"], row["id"]))

    joins = []
    p2_index = 0
    for p1_index, event in enumerate(p1):
        stamp = int(event["wall_clock_epoch_ms"])
        while p2_index + 1 < len(p2) and abs(
            p2[p2_index + 1]["timestamp_ms"] - stamp
        ) < abs(p2[p2_index]["timestamp_ms"] - stamp):
            p2_index += 1
        if p2_index >= len(p2):
            raise ValueError(f"no P2 event available for P1 callback {p1_index}")
        match = p2[p2_index]
        delta = match["timestamp_ms"] - stamp
        if abs(delta) > max_delta_ms:
            raise ValueError(
                f"P1 callback {p1_index} has no P2 event within {max_delta_ms} ms"
            )
        if int(event["callback_mask"]) != match["mask"]:
            raise ValueError(f"CPU mask differs at P1 callback {p1_index}")
        if match["dispatched"] & match["mask"] != match["mask"]:
            raise ValueError(f"CPU dispatch mask is incomplete at P2 event {match['id']}")
        if not match["callbacks"] or any(
            callback["status"] != "invoked" for callback in match["callbacks"]
        ):
            raise ValueError(f"guest callback did not complete at P2 event {match['id']}")
        callback = next(
            (cb for cb in match["callbacks"] if match["mask"] & (1 << cb["cpu"])),
            None,
        )
        if callback is None:
            raise ValueError(f"no dispatched CPU callback at P2 event {match['id']}")
        joins.append(
            {
                "p1_callback_index": p1_index,
                "p1_wall_clock_epoch_ms": stamp,
                "p1_registered_callback_function": f"0x{int(event['callback_function']):08x}",
                "p1_callback_object": f"0x{int(event['callback_object']):08x}",
                "p1_callback_data": f"0x{int(event['callback_data']):08x}",
                "p1_cpu_mask": f"0x{int(event['callback_mask']):02x}",
                "p2_pm4_interrupt_id": match["id"],
                "p2_wall_clock_epoch_ms": match["timestamp_ms"],
                "timestamp_delta_ms_p2_minus_p1": delta,
                "source": 1,
                "ring_generation": match["generation"],
                "batch_rptr": match["rptr"],
                "batch_wptr": match["wptr"],
                "ring_guest": f"0x{match['ring']:08x}",
                "pm4_packet_ordinal": match["ordinal"],
                "packet_source": f"{match['packet_source']:08X}+{match['packet_offset']}",
                "cpu_mask": f"0x{match['mask']:02x}",
                "dispatched_cpu_mask": f"0x{match['dispatched']:02x}",
                "dispatch_cpu": callback["cpu"],
                "outer_callback_wrapper": f"0x{callback['callback']:08x}",
                "outer_callback_data": f"0x{callback['data']:08x}",
                "dispatch_status": callback["status"],
            }
        )
        p2_index += 1

    ids = [row["p2_pm4_interrupt_id"] for row in joins]
    if any(right != left + 1 for left, right in zip(ids, ids[1:])):
        raise ValueError("joined Process 2 interrupt IDs are not continuous")
    deltas = sorted(abs(row["timestamp_delta_ms_p2_minus_p1"]) for row in joins)
    return {
        "schema": "shift.process2.pm4_interrupt_timestamp_order_audit.v1",
        "join_method": "one-to-one monotonic nearest timestamp match",
        "max_absolute_timestamp_delta_ms": max_delta_ms,
        "summary": {
            "joined_rows": len(joins),
            "p2_interrupt_id_range": [ids[0], ids[-1]],
            "p2_ids_contiguous": True,
            "absolute_timestamp_delta_ms": {
                "min": deltas[0],
                "median": deltas[len(deltas) // 2],
                "max": deltas[-1],
            },
            "p1_registered_callback_targets": dict(
                sorted(
                    (
                        f"0x{address:08X}",
                        sum(int(event["callback_function"]) == address for event in p1),
                    )
                    for address in {int(event["callback_function"]) for event in p1}
                )
            ),
            "p2_outer_callback_wrappers": dict(
                sorted(
                    (
                        f"0x{address:08X}",
                        sum(int(row["outer_callback_wrapper"], 16) == address for row in joins),
                    )
                    for address in {int(row["outer_callback_wrapper"], 16) for row in joins}
                )
            ),
        },
        "interpretation": (
            "This is a timestamp/order join. Process 1 records callbacks observed "
            "inside the guest wrapper; Process 2 records the outer guest callback "
            "and data passed to ExecuteInterrupt. This does not prove callback "
            "payload or guest semantic equivalence."
        ),
        "rows": joins,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p1-events", required=True)
    parser.add_argument("--p2-log", action="append", required=True)
    parser.add_argument("--max-delta-ms", type=int, default=120)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.p1_events, args.p2_log, args.max_delta_ms)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"interrupt audit failed: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
