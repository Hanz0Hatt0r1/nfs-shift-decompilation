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
    r"source=1(?: dispatch_id=(?P<dispatch_id_prefix>[0-9a-fA-F]+))? "
    r"generation=(?P<generation>\d+) "
    r"batch_rptr=(?P<rptr>\d+) batch_wptr=(?P<wptr>\d+) "
    r"ring_guest=(?P<ring>[0-9a-fA-F]+) packet=(?P<ordinal>\d+) "
    r"packet_source=(?P<source>[0-9a-fA-F]+)\+(?P<offset>\d+) "
    r"cpu_mask=0x(?P<mask>[0-9a-fA-F]+) "
    r"dispatched_cpu_mask=0x(?P<dispatched>[0-9a-fA-F]+) "
    r"callback_dispatches=\[(?P<callbacks>.*)\]"
    r"(?: dispatch_id=(?P<dispatch_id_suffix>[0-9a-fA-F]+))?$"
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
        dispatch_id=(
            int(row["dispatch_id_prefix"] or row["dispatch_id_suffix"], 16)
            if row["dispatch_id_prefix"] or row["dispatch_id_suffix"]
            else None
        ),
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


def join_callbacks(p1, p2, max_delta_ms):
    """Join by dispatch ID when captured; otherwise use the legacy time/order audit."""
    if not p1:
        raise ValueError("P1 capture contains no source-1 callback events")

    if any("gpu_dispatch_id" in event for event in p1):
        if not all("gpu_dispatch_id" in event for event in p1):
            raise ValueError("P1 callback capture has incomplete gpu_dispatch_id fields")
        by_dispatch_id = {}
        for interrupt in p2:
            dispatch_id = interrupt.get("dispatch_id")
            if dispatch_id is None:
                continue
            if dispatch_id in by_dispatch_id:
                raise ValueError(f"duplicate P2 gpu_dispatch_id {dispatch_id}")
            by_dispatch_id[dispatch_id] = interrupt
        joins = []
        for p1_index, event in enumerate(p1):
            dispatch_id = int(event["gpu_dispatch_id"])
            interrupt = by_dispatch_id.get(dispatch_id)
            if interrupt is None:
                raise ValueError(f"no P2 PM4 interrupt for gpu_dispatch_id {dispatch_id}")
            if (
                int(event["callback_mask"]) != interrupt["mask"]
                or interrupt["dispatched"] & interrupt["mask"]
                != interrupt["mask"]
            ):
                raise ValueError(
                    f"P1/P2 callback mask mismatch for gpu_dispatch_id {dispatch_id}"
                )
            callbacks = interrupt["callbacks"]
            callback = next(
                (cb for cb in callbacks if interrupt["mask"] & (1 << cb["cpu"])),
                None,
            )
            if not callback or callback["status"] != "invoked":
                raise ValueError(
                    f"P2 callback was not invoked for gpu_dispatch_id {dispatch_id}"
                )
            joins.append(_join_row(p1_index, event, interrupt, callback))
        return joins

    if len(p2) < len(p1):
        raise ValueError("P2 capture has fewer source-1 interrupts than P1 callbacks")

    candidates = []
    for start in range(len(p2) - len(p1) + 1):
        segment = p2[start : start + len(p1)]
        if any(
            right["id"] != left["id"] + 1
            for left, right in zip(segment, segment[1:])
        ):
            continue

        deltas = []
        valid = True
        for event, interrupt in zip(p1, segment):
            stamp = int(event["wall_clock_epoch_ms"])
            delta = interrupt["timestamp_ms"] - stamp
            if (
                abs(delta) > max_delta_ms
                or int(event["callback_mask"]) != interrupt["mask"]
                or interrupt["dispatched"] & interrupt["mask"]
                != interrupt["mask"]
            ):
                valid = False
                break
            callbacks = interrupt["callbacks"]
            if not callbacks or any(cb["status"] != "invoked" for cb in callbacks):
                valid = False
                break
            if not any(
                interrupt["mask"] & (1 << callback["cpu"])
                for callback in callbacks
            ):
                valid = False
                break
            deltas.append(delta)
        if valid:
            candidates.append((segment, deltas))

    if not candidates:
        raise ValueError(
            f"no continuous P2 interrupt window matches all P1 callbacks "
            f"within {max_delta_ms} ms"
        )
    if len(candidates) != 1:
        raise ValueError(
            f"P1 callbacks ambiguously match {len(candidates)} P2 interrupt windows"
        )

    segment, deltas = candidates[0]
    joins = []
    for p1_index, (event, match, delta) in enumerate(zip(p1, segment, deltas)):
        callback = next(
            cb for cb in match["callbacks"]
            if match["mask"] & (1 << cb["cpu"])
        )
        joins.append(_join_row(p1_index, event, match, callback, delta))
    return joins


def _join_row(p1_index, event, interrupt, callback, delta=None):
    if delta is None:
        delta = interrupt["timestamp_ms"] - int(event["wall_clock_epoch_ms"])
    row = {
        "p1_callback_index": p1_index,
        "p1_wall_clock_epoch_ms": int(event["wall_clock_epoch_ms"]),
        "p1_registered_callback_function": f"0x{int(event['callback_function']):08x}",
        "p1_callback_object": f"0x{int(event['callback_object']):08x}",
        "p1_callback_data": f"0x{int(event['callback_data']):08x}",
        "p1_cpu_mask": f"0x{int(event['callback_mask']):02x}",
        "p2_pm4_interrupt_id": interrupt["id"],
        "p2_wall_clock_epoch_ms": interrupt["timestamp_ms"],
        "timestamp_delta_ms_p2_minus_p1": delta,
        "source": 1,
        "ring_generation": interrupt["generation"],
        "batch_rptr": interrupt["rptr"],
        "batch_wptr": interrupt["wptr"],
        "ring_guest": f"0x{interrupt['ring']:08x}",
        "pm4_packet_ordinal": interrupt["ordinal"],
        "packet_source": f"{interrupt['packet_source']:08X}+{interrupt['packet_offset']}",
        "cpu_mask": f"0x{interrupt['mask']:02x}",
        "dispatched_cpu_mask": f"0x{interrupt['dispatched']:02x}",
        "dispatch_cpu": callback["cpu"],
        "outer_callback_wrapper": f"0x{callback['callback']:08x}",
        "outer_callback_data": f"0x{callback['data']:08x}",
        "dispatch_status": callback["status"],
    }
    if interrupt.get("dispatch_id") is not None:
        row["gpu_dispatch_id"] = interrupt["dispatch_id"]
    return row


def audit(events_path, log_paths, max_delta_ms):
    events = json.loads(Path(events_path).read_text())
    p1 = events["events"]["source1_callback_events"]
    p2 = []
    for path in log_paths:
        with Path(path).open(errors="replace") as stream:
            p2.extend(row for line in stream if (row := parse_p2_line(line)))
    p2.sort(key=lambda row: (row["timestamp_ms"], row["id"]))
    joins = join_callbacks(p1, p2, max_delta_ms)

    direct_id_join = all("gpu_dispatch_id" in event for event in p1)
    ids = [row["p2_pm4_interrupt_id"] for row in joins]
    if not direct_id_join and any(right != left + 1 for left, right in zip(ids, ids[1:])):
        raise ValueError("joined Process 2 interrupt IDs are not continuous")
    deltas = sorted(abs(row["timestamp_delta_ms_p2_minus_p1"]) for row in joins)
    return {
        "schema": "shift.process2.pm4_interrupt_join_audit.v2",
        "join_method": (
            "exact gpu_dispatch_id; one P2 interrupt may own multiple nested P1 callbacks"
            if direct_id_join else
            "unique one-to-one continuous interrupt-ID window with bounded timestamp error"
        ),
        "max_absolute_timestamp_delta_ms": max_delta_ms,
        "summary": {
            "joined_rows": len(joins),
            "p2_source1_events_considered": len(p2),
            "p2_events_outside_joined_window": len(p2) - len(joins),
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
            "This is a timestamp/order join to a unique continuous PM4 interrupt "
            "window. Process 1 records callbacks observed inside the guest wrapper; "
            "Process 2 records the outer guest callback and data passed to "
            "ExecuteInterrupt. This does not prove callback payload or guest "
            "semantic equivalence."
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
