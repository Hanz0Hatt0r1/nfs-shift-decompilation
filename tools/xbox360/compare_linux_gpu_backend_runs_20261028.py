#!/usr/bin/env python3
"""Compare event-aligned retail captures from the Xenos and Native Vulkan backends."""

from __future__ import annotations

import argparse
from collections import Counter
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


VOLATILE_FIELDS = {
    "elapsed_seconds", "wall_clock_epoch_ms", "trace_sequence", "id",
    "parent_id", "dequeue_id", "producer_id", "thread", "thread_name",
}
BUTTONS = {"Start": 0x0010, "A": 0x1000}
GUEST_ADDRESS_FIELDS = {
    "manager", "worker", "queue", "record", "payload", "stream", "event",
    "callback_object", "object", "state_pointer", "base", "context",
    "slot_value", "slot_value_after", "queue_address", "guest_address",
}


def load_run(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata_path = run_dir / "run_metadata.json"
    events_path = run_dir / "events.json"
    if not metadata_path.is_file() or not events_path.is_file():
        raise ValueError(f"capture directory is incomplete: {run_dir}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    events = json.loads(events_path.read_text(encoding="utf-8"))
    if metadata.get("schema") != "shift.xbox360.linux-gpu-backend-run.v1":
        raise ValueError(f"unsupported run metadata schema in {metadata_path}")
    if events.get("schema") != "shift.xbox360.linux-gpu-backend-events.v1":
        raise ValueError(f"unsupported event schema in {events_path}")
    if metadata.get("gpu_backend") != events.get("gpu_backend"):
        raise ValueError(f"backend identity differs between metadata and events in {run_dir}")
    if metadata.get("plugin_sha256") != metadata.get("staged_plugin_sha256"):
        raise ValueError(f"staged GPU plugin hash mismatch in {run_dir}")
    if metadata.get("host_sha256") != metadata.get("staged_host_sha256"):
        raise ValueError(f"staged host hash mismatch in {run_dir}")
    return metadata, events


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in sorted(value.items()):
            if key in VOLATILE_FIELDS or key in GUEST_ADDRESS_FIELDS:
                continue
            if key in ("arguments_r3_to_r8", "arguments_r3_r8") and isinstance(item, list) and len(item) >= 6:
                result[key] = [None, None, *canonical(item[2:5]), None]
            elif key == "child_words_264" and isinstance(item, list):
                result[key] = [bool(word) for word in item]
            elif key == "slots" and isinstance(item, list):
                result[key] = [bool(word) for word in item]
            else:
                result[key] = canonical(item)
        return result
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def canonical_event(event: dict[str, Any]) -> Any:
    result = canonical(event)
    # The scene manager's update counter is a cadence metric, not a scene identity.
    if event.get("kind") == "scene_state":
        result.pop("update_count_356", None)
    return result


def timeline(events: dict[str, Any], *, after_bink: bool = False) -> list[dict[str, Any]]:
    items = [
        item
        for group in events.get("events", {}).values()
        for item in group
        if isinstance(item, dict) and isinstance(item.get("trace_sequence"), int)
    ]
    items.sort(key=lambda item: item["trace_sequence"])
    if after_bink:
        bink_index = next(
            (index for index, item in enumerate(items) if item.get("kind") == "bink_complete"),
            None,
        )
        if bink_index is None:
            return []
        items = items[bink_index:]
    return items


def first_divergence(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, Any] | None:
    left_signatures = [json.dumps(canonical_event(item), sort_keys=True, separators=(",", ":")) for item in left]
    right_signatures = [json.dumps(canonical_event(item), sort_keys=True, separators=(",", ":")) for item in right]
    matcher = difflib.SequenceMatcher(a=left_signatures, b=right_signatures, autojunk=False)
    opcodes = matcher.get_opcodes()
    for index, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag == "equal":
            continue
        previous_equal = None
        for prior_tag, _, pi2, _, pj2 in reversed(opcodes[:index]):
            if prior_tag == "equal":
                previous_equal = {"xenos_end": pi2, "shift_native_end": pj2}
                break
        return {
            "kind": tag,
            "xenos_event_range": [i1, i2],
            "shift_native_event_range": [j1, j2],
            "previous_common_anchor": previous_equal,
            "xenos_events": left[i1:min(i2, i1 + 4)],
            "shift_native_events": right[j1:min(j2, j1 + 4)],
        }
    return None


def first_submission_record_difference(
    xenos_events: dict[str, Any], shift_native_events: dict[str, Any],
) -> dict[str, Any] | None:
    """Find a same-ordinal producer record whose payload words differ.

    This is an early GPU-submission candidate only. The tag's record layout
    is not known here, so differing words do not establish a renderer defect.
    """
    def calls(events: dict[str, Any]) -> dict[int, dict[str, Any]]:
        result = {}
        for event in timeline(events, after_bink=True):
            if event.get("kind") != "producer_call":
                continue
            ordinal = event.get("producer_call", event.get("id"))
            if isinstance(ordinal, int):
                result[ordinal] = event
        return result

    def route_signature(event: dict[str, Any]) -> list[tuple[Any, Any]]:
        return [
            (route.get("symbol"), route.get("caller_lr"))
            for route in event.get("routes", [])
            if isinstance(route, dict)
        ]

    left = calls(xenos_events)
    right = calls(shift_native_events)
    for ordinal in sorted(left.keys() & right.keys()):
        a, b = left[ordinal], right[ordinal]
        # Do not label unrelated records as a payload mismatch if the call
        # site or route already differs.
        if (
            a.get("tag") != b.get("tag")
            or a.get("delta") != b.get("delta")
            or a.get("caller_lr") != b.get("caller_lr")
            or route_signature(a) != route_signature(b)
        ):
            continue
        left_words = a.get("record_words")
        right_words = b.get("record_words")
        if left_words is None or right_words is None or left_words == right_words:
            continue
        caller_lr = a.get("caller_lr")
        return {
            "kind": "producer_record_words_mismatch_candidate",
            "producer_call_ordinal": ordinal,
            "tag": a.get("tag"),
            "delta": a.get("delta"),
            "caller_lr": f"0x{caller_lr:08X}" if isinstance(caller_lr, int) else caller_lr,
            "route": [symbol for symbol, _ in route_signature(a)],
            "xenos_record_words": left_words,
            "shift_native_record_words": right_words,
            "interpretation": (
                "The same producer call ordinal, tag, caller and route carry different captured words. "
                "The tag's record layout and causal relation to later guest/GPU state are not established."
            ),
        }
    return None


def event_counts(events: dict[str, Any]) -> dict[str, int]:
    return {key.removesuffix("_events"): len(value) for key, value in sorted(events.get("events", {}).items())}


def scene_transitions(events: dict[str, Any]) -> list[dict[str, Any]]:
    transitions = []
    for event in events.get("events", {}).get("scene_state_events", []):
        row = {
            "state_348": event.get("state_348"),
            "list_count_36": event.get("list_count_36"),
            # These are guest pointers/flags. Preserve whether each slot is
            # populated, but don't mistake backend-specific guest addresses
            # for different scene contents.
            "child_slots_populated": [bool(word) for word in event.get("child_words_264", [])],
        }
        if transitions and all(transitions[-1].get(key) == value for key, value in row.items()):
            transitions[-1]["last_update_count_356"] = event.get("update_count_356")
            transitions[-1]["last_elapsed_seconds"] = event.get("elapsed_seconds")
            transitions[-1]["samples"] += 1
            continue
        transitions.append({
            **row,
            "first_update_count_356": event.get("update_count_356"),
            "last_update_count_356": event.get("update_count_356"),
            "first_elapsed_seconds": event.get("elapsed_seconds"),
            "last_elapsed_seconds": event.get("elapsed_seconds"),
            "samples": 1,
        })
    return transitions


def retail_queue_wait_summary(events: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "call", "elapsed_seconds", "thread_name", "manager", "head_pointer",
        "head", "tail", "wait_target_r30", "predicate_byte", "completion_mask_set",
    )
    rows = [
        {field: row.get(field) for field in fields}
        for row in events.get("events", {}).get("retail_queue_wait_events", [])
        if isinstance(row, dict)
    ]
    return {
        "sample_count": len(rows),
        "first": rows[0] if rows else None,
        "last": rows[-1] if rows else None,
        "distinct_conditions": list(dict.fromkeys(
            tuple(row.get(field) for field in fields if field not in ("call", "elapsed_seconds", "thread_name"))
            for row in rows
        )),
    }


def wait_lifecycle_summary(
    entries: list[dict[str, Any]], returns: list[dict[str, Any]], id_field: str,
    main_thread_only: bool = True,
) -> dict[str, Any]:
    if main_thread_only:
        entries = [row for row in entries if str(row.get("thread_name") or "").startswith("Core 0/0: Main")]
        returns = [row for row in returns if str(row.get("thread_name") or "").startswith("Core 0/0: Main")]
    returned_ids = {row.get(id_field) for row in returns}
    unreturned = [row for row in entries if row.get(id_field) not in returned_ids]
    return {
        "entry_count": len(entries),
        "return_count": len(returns),
        "unreturned_entry_count": len(unreturned),
        "first_entry": entries[0] if entries else None,
        "last_entry": entries[-1] if entries else None,
        "last_return": returns[-1] if returns else None,
        "first_unreturned_entry": unreturned[0] if unreturned else None,
        "last_unreturned_entry": unreturned[-1] if unreturned else None,
    }


def retail_queue_wait_lifecycle(events: dict[str, Any]) -> dict[str, Any]:
    rows = events.get("events", {})
    return wait_lifecycle_summary(
        rows.get("retail_queue_wait_events", []),
        rows.get("retail_queue_wait_return_events", []),
        "call",
    )


def ke_wait_lifecycle(events: dict[str, Any]) -> dict[str, Any]:
    rows = events.get("events", {})
    entries = [
        row for row in rows.get("event_call_events", [])
        if row.get("symbol") == "KeWaitForSingleObject" and row.get("wait_call") is not None
    ]
    summary = wait_lifecycle_summary(
        entries, rows.get("ke_wait_return_events", []), "wait_call",
        main_thread_only=False,
    )
    returned = rows.get("ke_wait_return_events", [])
    statuses: dict[str, int] = {}
    durations = []
    for row in returned:
        if row.get("return_status") is not None:
            status = f"0x{int(row['return_status']) & 0xFFFFFFFF:08X}"
            statuses[status] = statuses.get(status, 0) + 1
        if row.get("duration_seconds") is not None:
            durations.append(float(row["duration_seconds"]))
    summary["return_status_counts"] = statuses
    summary["return_duration_seconds"] = {
        "min": min(durations) if durations else None,
        "max": max(durations) if durations else None,
    }
    return summary


def scene_state_sequence(events: dict[str, Any]) -> list[dict[str, Any]]:
    """Return scene identity changes, collapsing repeated manager updates."""
    ordered = timeline(events, after_bink=True)
    bink_sequence = next(
        (item.get("trace_sequence") for item in ordered if item.get("kind") == "bink_complete"),
        None,
    )
    if bink_sequence is None:
        return []
    rows = [
        item
        for group in events.get("events", {}).values()
        for item in group
        if isinstance(item, dict)
        and item.get("kind") == "scene_state"
        and item.get("trace_sequence", -1) >= bink_sequence
    ]
    rows.sort(key=lambda item: item.get("trace_sequence", -1))
    result: list[dict[str, Any]] = []
    previous_signature = None
    for row in rows:
        identity = {
            "kind": "scene_state",
            "state_348": row.get("state_348"),
            "list_count_36": row.get("list_count_36"),
            "child_words_264": [bool(word) for word in row.get("child_words_264", [])],
        }
        signature = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        if signature != previous_signature:
            result.append(row)
            previous_signature = signature
    return result


FRONTEND_TRANSITION_FUNCTIONS = {
    "sub_82F38158", "sub_82FD5658", "sub_82F33810",
}


def frontend_transition_return_sequence(events: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare return values at the retail scene-transition call sites.

    The return payload keeps guest object pointers out of the comparison while
    retaining the observed state writes and the resulting scene-manager state.
    """
    ordered = timeline(events, after_bink=True)
    bink_sequence = next(
        (item.get("trace_sequence") for item in ordered if item.get("kind") == "bink_complete"),
        None,
    )
    if bink_sequence is None:
        return []

    rows = []
    for row in events.get("events", {}).get("scene_function_return_events", []):
        if (
            not isinstance(row, dict)
            or row.get("trace_sequence", -1) < bink_sequence
            or row.get("function") not in FRONTEND_TRANSITION_FUNCTIONS
        ):
            continue
        scene = row.get("scene_manager_at_return", {})
        rows.append({
            "function": row.get("function"),
            "call": row.get("call"),
            # The two orchestration helpers are void; their r3 value is
            # undefined, so compare their observed state writes instead.
            "return_value": row.get("return_value") if row.get("function") == "sub_82FD5658" else None,
            "function_state_at_return": row.get("function_state_at_return"),
            "scene_manager": {
                "state_348": scene.get("state_348"),
                "list_count_36": scene.get("list_count_36"),
                "child_slots_populated": [bool(value) for value in scene.get("child_words_264", [])],
            },
        })
    return rows


def frontend_transition_function_counts(events: dict[str, Any]) -> dict[str, int]:
    ordered = timeline(events, after_bink=True)
    bink_sequence = next(
        (item.get("trace_sequence") for item in ordered if item.get("kind") == "bink_complete"),
        None,
    )
    counts = Counter()
    if bink_sequence is None:
        return {function: 0 for function in sorted(FRONTEND_TRANSITION_FUNCTIONS)}
    for row in events.get("events", {}).get("scene_function_events", []):
        if (
            isinstance(row, dict)
            and row.get("trace_sequence", -1) >= bink_sequence
            and row.get("function") in FRONTEND_TRANSITION_FUNCTIONS
        ):
            counts[row["function"]] += 1
    return {function: counts[function] for function in sorted(FRONTEND_TRANSITION_FUNCTIONS)}


def manager_counter_sequence(events: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ordered writes to the instrumented manager+11012 word."""
    ordered = timeline(events, after_bink=True)
    bink_sequence = next(
        (item.get("trace_sequence") for item in ordered if item.get("kind") == "bink_complete"),
        None,
    )
    if bink_sequence is None:
        return []
    writes = [
        item for item in ordered
        if item.get("kind") == "counter_write"
        and item.get("trace_sequence", -1) >= bink_sequence
        and isinstance(item.get("after", item.get("new")), int)
    ]
    return writes


def signed32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def counter_delta(event: dict[str, Any]) -> int:
    if isinstance(event.get("signed_delta"), int):
        return event["signed_delta"]
    before = event.get("before", event.get("old", 0))
    after = event.get("after", event.get("new", 0))
    return signed32(after - before)


def counter_progression(events: dict[str, Any]) -> dict[str, Any]:
    writes = manager_counter_sequence(events)
    first_negative = next((
        {
            "write_ordinal": index,
            "trace_sequence": row.get("trace_sequence"),
            "signed_value": signed32(row.get("after", row.get("new", 0))),
        }
        for index, row in enumerate(writes, 1)
        if signed32(row.get("after", row.get("new", 0))) < 0
    ), None)
    return {
        "write_count": len(writes),
        "delta_sequence": [counter_delta(row) for row in writes],
        "final_signed_value": (
            signed32(writes[-1].get("after", writes[-1].get("new", 0))) if writes else None
        ),
        "first_negative_write": first_negative,
    }


def first_counter_divergence(
    xenos: list[dict[str, Any]], shift_native: list[dict[str, Any]],
) -> dict[str, Any] | None:
    xenos_deltas = [counter_delta(row) for row in xenos]
    native_deltas = [counter_delta(row) for row in shift_native]
    common = 0
    while common < min(len(xenos_deltas), len(native_deltas)) and xenos_deltas[common] == native_deltas[common]:
        common += 1
    if common == len(xenos_deltas) == len(native_deltas):
        return None

    def describe(rows: list[dict[str, Any]], deltas: list[int]) -> dict[str, Any] | None:
        if common >= len(rows):
            return None
        row = rows[common]
        stack = row.get("host_stack")
        return {
            "write_index": row.get("write_index"),
            "trace_sequence": row.get("trace_sequence"),
            "elapsed_seconds": row.get("elapsed_seconds"),
            "delta": deltas[common],
            "before": row.get("before", row.get("old")),
            "after": row.get("after", row.get("new")),
            "guest_address": row.get("guest_address"),
            "guest_caller": stack[0] if isinstance(stack, list) and stack else None,
        }

    return {
        "kind": "manager_counter_operation_mismatch" if common < min(len(xenos_deltas), len(native_deltas)) else "manager_counter_length_mismatch",
        "guest_field": "manager+11012",
        "common_prefix_writes": common,
        "write_ordinal": common + 1,
        "xenos": describe(xenos, xenos_deltas),
        "shift_native": describe(shift_native, native_deltas),
        "xenos_following_deltas": xenos_deltas[common:common + 8],
        "shift_native_following_deltas": native_deltas[common:common + 8],
    }


def counter_operation_context(events: dict[str, Any], write: dict[str, Any] | None) -> dict[str, Any] | None:
    if write is None:
        return None
    stack = write.get("host_stack", [])
    wanted_kind = "producer" if any("sub_823B31A0" in frame for frame in stack) else "completion"
    rows = events.get("events", {}).get(f"{wanted_kind}_events", [])
    sequence = write.get("trace_sequence", -1)
    near = [
        row for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("trace_sequence"), int)
        and abs(row["trace_sequence"] - sequence) <= 16
        and row.get("kind") == wanted_kind
        and row.get("counter_before") == write.get("before", write.get("old"))
        and row.get("counter_after") == write.get("after", write.get("new"))
    ]
    if not near:
        return None
    row = min(near, key=lambda item: abs(item["trace_sequence"] - sequence))
    keys = (
        ("token", "expected_delta", "signed_delta", "parent_dequeue_id", "parent_record",
         "ring_queue", "ring_consumer", "ring_producer", "worker", "worker76", "phase")
        if wanted_kind == "completion"
        else ("caller_lr", "tag", "delta", "producer_call", "record", "record_words")
    )
    context = {"kind": wanted_kind, **{key: row.get(key) for key in keys}}
    if wanted_kind == "completion":
        dequeue = next((
            item for item in events.get("events", {}).get("dequeue_events", [])
            if item.get("id") == row.get("parent_dequeue_id")
        ), None)
        if dequeue is not None:
            context["parent_dequeue"] = {
                key: dequeue.get(key)
                for key in (
                    "id", "queue", "phase", "consumer_before", "consumer_after",
                    "producer_before", "producer_after", "slot_value",
                )
            }
        parent_record = row.get("parent_record")
        if isinstance(parent_record, int):
            matching_callbacks = [
                item for item in events.get("events", {}).get("source1_callback_events", [])
                if item.get("callback_function") == 0x823B8C60
                and item.get("callback_data") == parent_record
                and isinstance(item.get("trace_sequence"), int)
                and abs(item["trace_sequence"] - row["trace_sequence"]) <= 16
            ]
            context["nearby_source1_callbacks_matching_parent_record"] = [
                {
                    key: item.get(key)
                    for key in (
                        "trace_sequence", "entry_ordinal", "callback_function",
                        "callback_data", "thread", "thread_name",
                    )
                }
                for item in sorted(
                    matching_callbacks,
                    key=lambda item: abs(item["trace_sequence"] - row["trace_sequence"]),
                )[:8]
            ]
        context["join_scope"] = (
            "completion is linked to its dequeued record by parent_dequeue_id; "
            "callback records match the same guest pointer within a local trace window; "
            "this does not join the callback to a particular PM4 interrupt"
        )
    return context


def source1_callback_summary(events: dict[str, Any]) -> list[dict[str, Any]]:
    counts: Counter[tuple[Any, ...]] = Counter()
    for row in events.get("events", {}).get("source1_callback_events", []):
        data = row.get("callback_data")
        if isinstance(data, int) and data >= 0x80000000:
            data_key = "guest_pointer"
        elif isinstance(data, int):
            data_key = f"literal:0x{data:X}"
        else:
            data_key = "unknown"
        counts[(row.get("source"), row.get("callback_function"), row.get("callback_mask"), data_key)] += 1
    return [
        {
            "source": key[0],
            "callback_function": f"0x{key[1]:08X}" if isinstance(key[1], int) else key[1],
            "callback_mask": key[2],
            "callback_data_class": key[3],
            "count": count,
        }
        for key, count in sorted(counts.items(), key=lambda item: (str(item[0]), item[1]))
    ]


def nearby_source1_guest_callbacks(
    events: dict[str, Any], write: dict[str, Any] | None, *, window_ms: int = 100,
) -> list[dict[str, Any]]:
    """Return entry snapshots near a guest counter write; this is temporal correlation only."""
    if not write or not isinstance(write.get("wall_clock_epoch_ms"), int):
        return []
    target = write["wall_clock_epoch_ms"]
    nearby = []
    for row in events.get("events", {}).get("source1_callback_events", []):
        timestamp = row.get("wall_clock_epoch_ms")
        if not isinstance(timestamp, int) or abs(timestamp - target) > window_ms:
            continue
        nearby.append((abs(timestamp - target), timestamp - target, row))
    nearby.sort(key=lambda item: item[0])
    return [
        {
            "delta_ms_from_counter_write": delta,
            "entry_ordinal": row.get("entry_ordinal"),
            "trace_sequence": row.get("trace_sequence"),
            "thread": row.get("thread"),
            "thread_name": row.get("thread_name"),
            "guest_lr": row.get("guest_lr"),
            "arguments_r3_to_r10": row.get("arguments_r3_to_r10"),
            "callback_function": row.get("callback_function"),
            "callback_data": row.get("callback_data"),
            "callback_bit_index": row.get("callback_bit_index"),
            "callback_bit_mask": row.get("callback_bit_mask"),
            "manager_flags_before": row.get("manager_flags_before"),
            "manager_flag_bit_set_before": row.get("manager_flag_bit_set_before"),
            "manager_counter_before": row.get("manager_counter_before"),
            "manager_words_10904_to_1091c": row.get("manager_words_10904_to_1091c"),
        }
        for _, delta, row in nearby[:8]
    ]


def completion_token_summary(events: dict[str, Any]) -> list[dict[str, Any]]:
    counts: Counter[tuple[Any, ...]] = Counter(
        (row.get("token"), row.get("expected_delta"), row.get("signed_delta"))
        for row in events.get("events", {}).get("completion_events", [])
    )
    return [
        {
            "token": f"0x{key[0]:08X}" if isinstance(key[0], int) else key[0],
            "expected_delta": key[1],
            "signed_delta": key[2],
            "count": count,
        }
        for key, count in sorted(counts.items(), key=lambda item: (str(item[0]), item[1]))
    ]


def final_queue_snapshots(events: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for row in events.get("final_queue_snapshots", []):
        producer, consumer = row.get("producer"), row.get("consumer")
        result.append({
            "queue": f"0x{row['queue']:08X}" if isinstance(row.get("queue"), int) else row.get("queue"),
            "producer": producer,
            "consumer": consumer,
            "observed_backlog": producer - consumer if isinstance(producer, int) and isinstance(consumer, int) else None,
            "slots_populated": [bool(value) for value in row.get("slots", [])],
        })
    return result


def gpu_ring_trace_summary(events: dict[str, Any]) -> dict[str, Any]:
    rows = events.get("gpu_ring_interrupt_events", [])
    dispatches: Counter[tuple[Any, ...]] = Counter()
    read_wraps = write_wraps = 0
    for previous, current in zip(rows, rows[1:]):
        read_wraps += current.get("batch_rptr", 0) < previous.get("batch_rptr", 0)
        write_wraps += current.get("batch_wptr", 0) < previous.get("batch_wptr", 0)
    for row in rows:
        for callback in row.get("callbacks", []):
            dispatches[(
                callback.get("cpu"), callback.get("callback"),
                callback.get("status"),
            )] += 1
    return {
        "record_count": len(rows),
        "source_counts": dict(sorted(Counter(str(row.get("source")) for row in rows).items())),
        "cpu_masks": dict(sorted(Counter(f"0x{row.get('cpu_mask', 0):02X}" for row in rows).items())),
        "dispatched_cpu_masks": dict(sorted(Counter(
            f"0x{row.get('dispatched_cpu_mask', 0):02X}" for row in rows
        ).items())),
        "first_packet_ordinal": rows[0].get("packet_ordinal") if rows else None,
        "last_packet_ordinal": rows[-1].get("packet_ordinal") if rows else None,
        "first_batch_rptr_wptr": [rows[0].get("batch_rptr"), rows[0].get("batch_wptr")] if rows else None,
        "last_batch_rptr_wptr": [rows[-1].get("batch_rptr"), rows[-1].get("batch_wptr")] if rows else None,
        "batch_rptr_wraps": read_wraps,
        "batch_wptr_wraps": write_wraps,
        "generations": sorted({row.get("generation") for row in rows}),
        "callback_dispatches": [
            {
                "cpu": key[0],
                "callback": f"0x{key[1]:08X}" if isinstance(key[1], int) else key[1],
                "status": key[2],
                "count": count,
            }
            for key, count in sorted(dispatches.items(), key=lambda item: (str(item[0]), item[1]))
        ],
    }


def _split_ordered_renderer_operations(text: str) -> list[str]:
    """Split a renderer operation summary on top-level semicolons."""
    result: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(text):
        if character in "({[":
            depth += 1
        elif character in ")}]":
            depth = max(0, depth - 1)
        elif character == ";" and depth == 0:
            item = text[start:index].strip()
            if item:
                result.append(item)
            start = index + 1
    final = text[start:].strip()
    if final:
        result.append(final)
    return result


def _operation_group(text: str, key: str) -> str | None:
    marker = f"{key}={{"
    start = text.find(marker)
    if start < 0:
        return None
    start += len(marker)
    depth = 1
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index]
    return None


def _operation_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?:^|[,{{]){re.escape(key)}=([^,}})]+)", text)
    return match.group(1).strip() if match else None


def _operation_number(text: str, key: str) -> int | None:
    value = _operation_scalar(text, key)
    if value is None:
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def _parse_renderer_operation(text: str) -> dict[str, Any] | None:
    match = re.match(r"([A-Za-z_]+)\((.*)\)$", text)
    if not match:
        return None
    kind, body = match.groups()
    packet = _operation_number(body, "packet")
    if packet is None:
        return None
    result: dict[str, Any] = {"kind": kind, "packet": packet}
    index = _operation_number(body, "index")
    if index is not None:
        result["index"] = index

    if kind == "draw":
        raster = _operation_group(body, "raster")
        if raster is not None:
            extent = re.search(r"\bextent=(\d+)x(\d+)", raster)
            scissor = re.search(r"\bscissor=(\d+)\[([^]]+)\]", raster)
            result["raster"] = {
                "extent": [int(extent.group(1)), int(extent.group(2))] if extent else None,
                "pitch": _operation_number(raster, "pitch"),
                "samples": _operation_number(raster, "samples"),
                "color_base": _operation_number(raster, "color_base"),
                "depth_base": _operation_number(raster, "depth_base"),
                "guest_format": _operation_number(raster, "guest_format"),
                "color_format": _operation_number(raster, "color_format"),
                "depth_format": _operation_number(raster, "depth_format"),
                "depth_only": _operation_number(raster, "depth_only"),
                "color_mask": _operation_number(raster, "color_mask"),
                "depth_test": _operation_number(raster, "depth_test"),
                "depth_write": _operation_number(raster, "depth_write"),
                "stencil_test": _operation_number(raster, "stencil_test"),
                "scissor_enabled": int(scissor.group(1)) if scissor else None,
                "scissor": scissor.group(2) if scissor else None,
            }
        registers = _operation_group(body, "draw_registers")
        if registers is not None:
            result["draw_registers"] = {
                key: _operation_scalar(registers, key)
                for key in ("valid_mask", "surface", "color", "depth", "mode",
                            "depth_control", "color_mask", "stencil_refmask",
                            "screen_scissor", "window_scissor")
                if _operation_scalar(registers, key) is not None
            }
    elif kind in ("copy", "convert"):
        source = re.search(r"\bsource=(\d+x\d+)", body)
        destination = re.search(r"\bdestination=(0x[0-9a-fA-F]+),(\d+x\d+)", body)
        result.update({
            "source_extent": source.group(1) if source else None,
            "source_registers": _operation_scalar(body, "source_regs"),
            "destination_base": int(destination.group(1), 16) if destination else None,
            "destination_extent": destination.group(2) if destination else None,
            "format": _operation_scalar(body, "format"),
            "endian": _operation_number(body, "endian"),
            "exp_bias": _operation_number(body, "exp_bias"),
            "samples": _operation_number(body, "samples"),
            "clear": _operation_scalar(body, "clear"),
            "source_target": _operation_group(body, "source_target"),
            "swap_rb": _operation_number(body, "swap_rb"),
            "source_geometry": _operation_scalar(body, "source_geometry"),
            "topology": _operation_number(body, "topology"),
            "indices": _operation_number(body, "indices"),
            "auto_index": _operation_number(body, "auto_index"),
            "vertex_bytes": _operation_number(body, "vertex_bytes"),
            "index_bytes": _operation_number(body, "index_bytes"),
        })
    return result


def _captured_p2_packet27_alias_candidate(
    previous_draw: dict[str, Any], draw: dict[str, Any], copy: dict[str, Any],
) -> dict[str, Any]:
    source = previous_draw.get("raster", {})
    destination = draw.get("raster", {})
    copy_source = copy.get("source_target") or ""
    source_ready = re.search(
        r"ready:1,extent=(\d+)x(\d+),samples=(\d+),color_base=(0x[0-9a-fA-F]+),"
        r"depth_base=(0x[0-9a-fA-F]+),guest_format=(\d+)",
        copy_source,
    )
    source_target_matches = bool(source_ready) and (
        (int(source_ready.group(1)), int(source_ready.group(2)), int(source_ready.group(3)),
         int(source_ready.group(4), 16), int(source_ready.group(5), 16), int(source_ready.group(6)))
        == (1280, 720, 1, 0, 0x2D0, 0)
    )
    previous_matches = all((
        source.get("extent") == [1280, 720], source.get("pitch") == 640,
        source.get("samples") == 4, source.get("guest_format") == 1,
        source.get("color_format") == 1, source.get("depth_format") == 0,
        source.get("color_base") == 0, source.get("depth_base") == 0x2D0,
    ))
    next_matches = all((
        destination.get("extent") == [1280, 720], destination.get("pitch") == 1280,
        destination.get("samples") == 1, destination.get("guest_format") == 0,
        destination.get("color_format") == 0, destination.get("depth_format") == 0,
        destination.get("color_base") == 0, destination.get("depth_base") == 0x2D0,
        destination.get("depth_test") == 0, destination.get("depth_write") == 0,
        destination.get("stencil_test") == 0,
    ))
    copy_matches = all((
        copy.get("source_extent") == "1280x720",
        (copy.get("source_registers") or "").lower() == "0x14000500/0x0/0x2d0/0x6",
        copy.get("destination_base") == 0x0975E000,
        copy.get("destination_extent") == "1280x720",
        copy.get("format") == "6/0", copy.get("endian") == 0,
        copy.get("samples") == 0, copy.get("clear") == "0/0",
        copy.get("swap_rb") == 1, copy.get("source_geometry") == "captured",
        copy.get("topology") == 2, copy.get("auto_index") == 1,
        copy.get("vertex_bytes") == 24, copy.get("index_bytes") == 0,
        source_target_matches,
    ))
    return {
        "previous_draw_packet": previous_draw.get("packet"),
        "alias_draw_packet": draw.get("packet"),
        "immediate_copy_packet": copy.get("packet"),
        "previous_raster": source,
        "alias_raster": destination,
        "copy": copy,
        "observable_capture_tuple_matches_p2_packet27_contract": bool(
            previous_matches and next_matches and copy_matches
        ),
        "edram_tile_alias_mapping_verified_by_p1": False,
        "interpretation": (
            "The captured operation fields match the observable P2 packet-27 to packet-52 tuple. "
            "This log does not expose Vulkan submission success or independently validate EDRAM tile mapping."
        ),
    }


def renderer_log_diagnostics(run_dir: Path) -> dict[str, Any]:
    """Summarize structured Native renderer logs without copying raw traces."""
    log_paths = sorted((run_dir / "bin" / "logs").glob("nfs_shift*.log"))
    log_manifest = []
    snapshots: list[dict[str, Any]] = []
    p2_packet27_alias_candidates: list[dict[str, Any]] = []
    unresolved_draw_rejections: dict[tuple[Any, ...], dict[str, Any]] = {}
    geometry_packet_indices: list[int] = []
    geometry_packet_records: list[dict[str, Any]] = []
    selected_draws: dict[int, list[dict[str, Any]]] = {}
    geometry_packet_72_count = 0
    for path in log_paths:
        contents = path.read_bytes()
        log_manifest.append({
            "name": path.name,
            "size_bytes": len(contents),
            "sha256": hashlib.sha256(contents).hexdigest(),
        })
        text = contents.decode("utf-8", errors="replace")
        lines = text.splitlines()
        for line_number, line in enumerate(lines, 1):
            unresolved_match = re.search(
                r"unresolved captured draw #(\d+) topology=(\d+) autoindex=(true|false) "
                r"count=(\d+) raster=(true|false) inputs=(true|false) translated=(true|false): (.*)$",
                line,
            )
            if unresolved_match:
                ordinal, topology, autoindex, count, raster, inputs, translated, reason = unresolved_match.groups()
                signature = (
                    int(ordinal), int(topology), autoindex == "true", int(count),
                    raster == "true", inputs == "true", translated == "true", reason.rstrip(),
                )
                timestamp_match = re.match(r"\[([^]]+)\]", line)
                observation = {
                    "log": path.name,
                    "line": line_number,
                    "timestamp": timestamp_match.group(1) if timestamp_match else None,
                    "line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                }
                record = unresolved_draw_rejections.get(signature)
                if record is None:
                    unresolved_draw_rejections[signature] = {
                        "draw_ordinal": signature[0],
                        "topology": signature[1],
                        "autoindex": signature[2],
                        "count": signature[3],
                        "raster_ready": signature[4],
                        "inputs_ready": signature[5],
                        "translated": signature[6],
                        "rejection_reason": signature[7],
                        "occurrences": 1,
                        "first_observation": observation,
                        "last_observation": observation,
                    }
                else:
                    record["occurrences"] += 1
                    record["last_observation"] = observation
            draw_match = re.search(
                r"resolved captured retail draw #(\d+).*?Vulkan readback target frame (\d+)",
                line,
            )
            if draw_match:
                block_lines = [line]
                for following in lines[line_number:line_number + 32]:
                    if re.search(r"resolved captured retail draw #\d+", following):
                        break
                    if following.startswith("["):
                        break
                    block_lines.append(following)
                block = "\n".join(block_lines)
                raster_match = re.search(
                    r"raster=(\d+x\d+).*?scissor=\[([^]]+)\]",
                    block,
                )
                depth_match = re.search(
                    r"depth=\{test:(\d+),write:(\d+),stencil:(\d+)\}",
                    block,
                )
                vertex_match = re.search(
                    r"vertex fetch: guest=(0x[0-9a-fA-F]+).*?descriptor=\{(0x[0-9a-fA-F]+),(0x[0-9a-fA-F]+)\}"
                    r" endian=(\d+) stride=(\d+) payload_bytes=(\d+) attributes=(\d+)",
                    block,
                    re.S,
                )
                payload_match = re.search(
                    r"normalized_vertex_payload_fnv1a=0x([0-9a-fA-F]+)", block
                )
                raw_vertex_match = re.search(
                    r"raw_vertices_dump=(\S+) bytes=(\d+) fnv1a=0x([0-9a-fA-F]+)", block
                )
                raw_index_match = re.search(
                    r"raw_indices_dump=(\S+) bytes=(\d+) fnv1a=0x([0-9a-fA-F]+)", block
                )
                topology_match = re.search(
                    r"topology=(\d+) autoindex=(\d+) index_count=(\d+) index_guest=(0x[0-9a-fA-F]+)",
                    block,
                )
                elapsed_match = re.search(r"\belapsed_ms=(\d+)", line)
                frame = int(draw_match.group(2))
                selected_draws.setdefault(frame, []).append({
                    "dump_index": int(draw_match.group(1)),
                    "elapsed_ms": int(elapsed_match.group(1)) if elapsed_match else None,
                    "topology": int(topology_match.group(1)) if topology_match else None,
                    "autoindex": bool(int(topology_match.group(2))) if topology_match else None,
                    "index_count": int(topology_match.group(3)) if topology_match else None,
                    "index_guest_address": int(topology_match.group(4), 16) if topology_match else None,
                    "raster_extent": raster_match.group(1) if raster_match else None,
                    "scissor": raster_match.group(2) if raster_match else None,
                    "depth": {
                        "test": int(depth_match.group(1)),
                        "write": int(depth_match.group(2)),
                        "stencil": int(depth_match.group(3)),
                    } if depth_match else None,
                    "vertex_fetch_guest_address": int(vertex_match.group(1), 16) if vertex_match else None,
                    "vertex_descriptor": [
                        int(vertex_match.group(2), 16), int(vertex_match.group(3), 16),
                    ] if vertex_match else None,
                    "vertex_endian": int(vertex_match.group(4)) if vertex_match else None,
                    "vertex_stride": int(vertex_match.group(5)) if vertex_match else None,
                    "vertex_payload_bytes": int(vertex_match.group(6)) if vertex_match else None,
                    "vertex_attribute_count": int(vertex_match.group(7)) if vertex_match else None,
                    "vertex_payload_fnv1a": payload_match.group(1).lower() if payload_match else None,
                    "raw_vertex_dump": {
                        "name": Path(raw_vertex_match.group(1)).name,
                        "size_bytes": int(raw_vertex_match.group(2)),
                        "fnv1a": raw_vertex_match.group(3).lower(),
                    } if raw_vertex_match else None,
                    "raw_index_dump": {
                        "name": Path(raw_index_match.group(1)).name,
                        "size_bytes": int(raw_index_match.group(2)),
                        "fnv1a": raw_index_match.group(3).lower(),
                    } if raw_index_match else None,
                })
            geometry_match = re.search(
                r"captured Copy/Convert PM4 geometry packet #(\d+)", line
            )
            if geometry_match:
                packet = int(geometry_match.group(1))
                geometry_packet_indices.append(packet)
                geometry_packet_72_count += packet == 72
                timestamp_match = re.match(r"\[([^]]+)\]", line)
                geometry_packet_records.append({
                    "packet": packet,
                    "log": path.name,
                    "line": line_number,
                    "timestamp": timestamp_match.group(1) if timestamp_match else None,
                })
            marker = "captured ordered PM4 operations:"
            marker_at = line.find(marker)
            if marker_at < 0:
                continue
            parsed = [
                operation for operation in (
                    _parse_renderer_operation(item)
                    for item in _split_ordered_renderer_operations(line[marker_at + len(marker):])
                ) if operation is not None
            ]
            if not parsed:
                continue
            draws = [item for item in parsed if item["kind"] == "draw"]
            copies = [item for item in parsed if item["kind"] in ("copy", "convert")]
            packet_ids = [item["packet"] for item in copies]
            timestamp = line[:line.find("]") + 1].strip("[]") if "]" in line else None
            for index in range(1, len(parsed) - 1):
                previous_draw, alias_draw, immediate_copy = parsed[index - 1:index + 2]
                if (previous_draw["kind"] != "draw" or previous_draw["packet"] != 26
                        or alias_draw["kind"] != "draw" or alias_draw["packet"] != 27
                        or immediate_copy["kind"] not in ("copy", "convert")
                        or immediate_copy["packet"] != 52):
                    continue
                p2_packet27_alias_candidates.append({
                    "log": path.name,
                    "line": line_number,
                    "timestamp": timestamp,
                    "line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                    **_captured_p2_packet27_alias_candidate(
                        previous_draw, alias_draw, immediate_copy
                    ),
                })
            snapshots.append({
                "log": path.name,
                "line": line_number,
                "timestamp": timestamp,
                "line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                "operation_count": len(parsed),
                "draw_count": len(draws),
                "copy_convert_count": len(copies),
                "draws": draws,
                "copy_converts": copies,
                "includes_copy_packet_72": 72 in packet_ids,
                "progressed_past_copy_packet_72": any(packet > 72 for packet in packet_ids),
                "max_copy_convert_packet": max(packet_ids, default=None),
            })
    packet_0_refreshes = [
        snapshot for snapshot in snapshots
        if len(snapshot["draws"]) == 14
        and [item["packet"] for item in snapshot["draws"]] == list(range(14))
    ]
    packet_72_streams = [
        snapshot for snapshot in snapshots
        if snapshot["includes_copy_packet_72"] and snapshot["progressed_past_copy_packet_72"]
    ]
    ordered_geometry = sorted(
        geometry_packet_records,
        key=lambda row: (row["timestamp"] or "", row["log"], row["line"]),
    )
    first_packet_72 = next((row for row in ordered_geometry if row["packet"] == 72), None)
    first_later_geometry = next((
        row for row in ordered_geometry
        if first_packet_72 and row["timestamp"] and first_packet_72["timestamp"]
        and row["timestamp"] > first_packet_72["timestamp"] and row["packet"] > 72
    ), None)
    ordered_later_packet_snapshots = [
        snapshot for snapshot in snapshots
        if any(operation["packet"] > 72 for operation in snapshot["copy_converts"])
    ]
    raw_draw_artifacts = []
    for path in sorted(run_dir.glob("native-draw.frame*.draw*.bin")):
        contents = path.read_bytes()
        raw_draw_artifacts.append({
            "name": path.name,
            "size_bytes": len(contents),
            "sha256": hashlib.sha256(contents).hexdigest(),
        })
    return {
        "log_files": log_manifest,
        "unresolved_draw_rejections": list(unresolved_draw_rejections.values()),
        "selected_frame_draw_captures": [
            {"frame": frame, "draw_count": len(draws), "draws": draws}
            for frame, draws in sorted(selected_draws.items())
        ],
        "raw_draw_artifacts": raw_draw_artifacts,
        "ordered_operation_snapshot_count": len(snapshots),
        "copy_convert_geometry_record_count": len(geometry_packet_indices),
        "copy_convert_geometry_packet_72_record_count": geometry_packet_72_count,
        "max_copy_convert_geometry_packet": max(geometry_packet_indices, default=None),
        "packet_72_progression": {
            "packet_72_geometry_captured": first_packet_72 is not None,
            "packet_72_geometry_capture_count": geometry_packet_72_count,
            "first_packet_72_geometry_record": first_packet_72,
            "first_later_higher_packet_geometry_record": first_later_geometry,
            "highest_ordered_copy_convert_packet": max(
                (operation["packet"] for snapshot in snapshots
                 for operation in snapshot["copy_converts"]),
                default=None,
            ),
            "ordered_snapshots_with_packet_above_72": ordered_later_packet_snapshots,
            "same_snapshot_contains_packet_72_and_a_later_packet": bool(packet_72_streams),
            "interpretation": (
                "Higher packet indices are present later in the captured renderer logs; the logs "
                "do not identify a shared stream ID linking those records to packet 72."
            ),
        },
        "packet_0_fourteen_draw_refreshes": packet_0_refreshes,
        "captured_p2_packet27_alias_candidate_count": len(p2_packet27_alias_candidates),
        "captured_p2_packet27_alias_candidates": p2_packet27_alias_candidates,
    }


def nearby_gpu_ring_interrupts(
    events: dict[str, Any], write: dict[str, Any] | None, *, window_ms: int = 100,
) -> list[dict[str, Any]]:
    if not write or not isinstance(write.get("wall_clock_epoch_ms"), int):
        return []
    target = write["wall_clock_epoch_ms"]
    nearby = []
    for row in events.get("gpu_ring_interrupt_events", []):
        timestamp = row.get("timestamp_epoch_ms")
        if not isinstance(timestamp, int) or abs(timestamp - target) > window_ms:
            continue
        nearby.append((abs(timestamp - target), timestamp - target, row))
    nearby.sort(key=lambda item: item[0])
    return [
        {
            "delta_ms_from_counter_write": delta,
            "ordinal": row.get("ordinal"),
            "source": row.get("source"),
            "generation": row.get("generation"),
            "batch_rptr": row.get("batch_rptr"),
            "batch_wptr": row.get("batch_wptr"),
            "ring_guest": row.get("ring_guest"),
            "packet_ordinal": row.get("packet_ordinal"),
            "source_ib": row.get("source_ib"),
            "source_ib_byte_offset": row.get("source_ib_byte_offset"),
            "cpu_mask": row.get("cpu_mask"),
            "dispatched_cpu_mask": row.get("dispatched_cpu_mask"),
            "callbacks": row.get("callbacks", []),
        }
        for _, delta, row in nearby[:5]
    ]


def button_path(metadata: dict[str, Any], events: dict[str, Any]) -> dict[str, Any]:
    rows = events.get("events", {})
    host_masks = [row.get("buttons") for row in rows.get("host_input_events", [])]
    host_button_rising_edges = []
    previous_mask = 0
    for mask in host_masks:
        if not isinstance(mask, int):
            continue
        rising = mask & ~previous_mask
        for name, expected_mask in BUTTONS.items():
            if rising & expected_mask:
                host_button_rising_edges.append((name, f"0x{expected_mask:04X}"))
        previous_mask = mask
    guest_edges = []
    for group_name in ("controller_update_events", "controller_return_events"):
        guest_edges.extend(row.get("edge", 0) for row in rows.get(group_name, []))
    xam_returns = rows.get("xam_input_return_events", [])
    observed = {}
    for name, mask in BUTTONS.items():
        observed[name] = {
            "expected_xinput_mask": f"0x{mask:04X}",
            "host_xinput_mask_seen": any(
                isinstance(value, int) and (value & mask) == mask for value in host_masks
            ),
        }
    return {
        "input_enabled": metadata.get("controller_input", {}).get("enabled"),
        "gate_observed": metadata.get("controller_input", {}).get("gate_observed"),
        "xam_input_calls": events.get("xam_input_calls", 0),
        "xam_input_return_count": len(xam_returns),
        "xam_input_return_statuses": dict(sorted(Counter(
            f"0x{row.get('status', 0):08X}" for row in xam_returns
            if isinstance(row.get("status"), int)
        ).items())),
        "xam_input_button_masks": sorted({
            f"0x{row['buttons']:04X}" for row in xam_returns
            if isinstance(row.get("buttons"), int)
        }),
        "observed_buttons": observed,
        "host_button_rising_edges": [list(edge) for edge in host_button_rising_edges],
        "retail_controller_edge_values": sorted({
            f"0x{value:08X}" for value in guest_edges if isinstance(value, int)
        }),
        "retail_edge_mapping_confirmed": False,
        "retail_action_dispatch_proven": False,
    }


def compare(left_dir: Path, right_dir: Path) -> dict[str, Any]:
    left_meta, left_events = load_run(left_dir)
    right_meta, right_events = load_run(right_dir)
    if left_meta["gpu_backend"] != "xenos" or right_meta["gpu_backend"] != "shift-native":
        raise ValueError("compare expects Xenos on the left and shift-native on the right")
    identity_fields = (
        "xex_sha256", "host_sha256", "runtime_sha256", "resource_manifest_sha256",
    )
    identity = {}
    for field in identity_fields:
        left_value, right_value = left_meta.get(field), right_meta.get(field)
        identity[field] = {"xenos": left_value, "shift_native": right_value, "match": left_value == right_value}
    if not all(item["match"] and item["xenos"] is not None for item in identity.values()):
        raise ValueError(f"paired captures do not share the required input identity: {identity}")

    left_input = left_meta.get("controller_input", {})
    right_input = right_meta.get("controller_input", {})
    left_profile = [(pulse.get("button"), pulse.get("expected_mask")) for pulse in left_input.get("pulses", [])]
    right_profile = [(pulse.get("button"), pulse.get("expected_mask")) for pulse in right_input.get("pulses", [])]
    declared_profiles_match = left_profile == right_profile
    gates_match = bool(left_input.get("gate_observed")) == bool(right_input.get("gate_observed"))
    left_host_profile = [tuple(edge) for edge in button_path(left_meta, left_events)["host_button_rising_edges"]]
    right_host_profile = [tuple(edge) for edge in button_path(right_meta, right_events)["host_button_rising_edges"]]
    same_profile_delivered = (
        declared_profiles_match
        and gates_match
        and bool(left_input.get("gate_observed"))
        and left_host_profile == left_profile
        and right_host_profile == right_profile
    )

    mapped_verification = {}
    for meta, event_data in ((left_meta, left_events), (right_meta, right_events)):
        mapped = event_data.get("mapped_hashes", {})
        plugin_suffix = f"/librexgpu-{meta['gpu_backend']}.so"
        runtime_hashes = [value for path, value in mapped.items() if path.endswith("/librexruntime.so")]
        plugin_hashes = [value for path, value in mapped.items() if path.endswith(plugin_suffix)]
        if runtime_hashes and meta["runtime_sha256"] not in runtime_hashes:
            raise ValueError(f"mapped runtime hash mismatch in {meta['gpu_backend']} capture")
        if plugin_hashes and meta["plugin_sha256"] not in plugin_hashes:
            raise ValueError(f"mapped GPU plugin hash mismatch in {meta['gpu_backend']} capture")
        if event_data.get("bink_target") and (not runtime_hashes or not plugin_hashes):
            raise ValueError(f"mapped artifact hashes were not captured after Bink in {meta['gpu_backend']} run")
        mapped_verification[meta["gpu_backend"]] = {
            "runtime": "matched" if runtime_hashes else "not_captured_before_bink_or_fault",
            "plugin": "matched" if plugin_hashes else "not_captured_before_bink_or_fault",
        }

    left_timeline, right_timeline = timeline(left_events, after_bink=True), timeline(right_events, after_bink=True)
    left_bink = bool(left_events.get("bink_target"))
    right_bink = bool(right_events.get("bink_target"))
    bink_divergence = None
    if left_bink != right_bink:
        bink_divergence = {
            "kind": "milestone_mismatch",
            "milestone": "bink_281_of_281",
            "xenos_reached": left_bink,
            "shift_native_reached": right_bink,
            "xenos_bink": left_events.get("bink_target"),
            "shift_native_bink": right_events.get("bink_target"),
        }
    trace_order_difference = (
        first_divergence(left_timeline, right_timeline) if left_bink and right_bink else None
    )
    submission_record_difference = (
        first_submission_record_difference(left_events, right_events)
        if left_bink and right_bink else None
    )
    scene_divergence = None
    frontend_transition_return_divergence = None
    frontend_transition_returns = {"xenos": [], "shift_native": []}
    frontend_transition_call_counts = {"xenos": {}, "shift_native": {}}
    counter_divergence = None
    counter_sequences = {"xenos": [], "shift_native": []}
    if left_bink and right_bink:
        scene_divergence = first_divergence(
            scene_state_sequence(left_events), scene_state_sequence(right_events),
        )
        frontend_transition_returns = {
            "xenos": frontend_transition_return_sequence(left_events),
            "shift_native": frontend_transition_return_sequence(right_events),
        }
        frontend_transition_call_counts = {
            "xenos": frontend_transition_function_counts(left_events),
            "shift_native": frontend_transition_function_counts(right_events),
        }
        frontend_transition_return_divergence = first_divergence(
            frontend_transition_returns["xenos"],
            frontend_transition_returns["shift_native"],
        )
        counter_sequences = {
            "xenos": manager_counter_sequence(left_events),
            "shift_native": manager_counter_sequence(right_events),
        }
        counter_divergence = first_counter_divergence(
            counter_sequences["xenos"], counter_sequences["shift_native"],
        )
        if counter_divergence:
            for backend, event_data, event_key in (
                ("xenos", left_events, "xenos"),
                ("shift_native", right_events, "shift_native"),
            ):
                if counter_divergence[event_key] is None:
                    continue
                ordinal = counter_divergence["common_prefix_writes"]
                write = counter_sequences[backend][ordinal] if ordinal < len(counter_sequences[backend]) else None
                counter_divergence[event_key]["related_operation"] = counter_operation_context(event_data, write)
                counter_divergence[event_key]["nearby_gpu_ring_interrupts"] = nearby_gpu_ring_interrupts(
                    event_data, write,
                )
                counter_divergence[event_key]["nearby_source1_guest_callback_entries"] = (
                    nearby_source1_guest_callbacks(event_data, write)
                )
    semantic_divergence = bink_divergence or counter_divergence or scene_divergence
    post_bink_event_counts = {
        "xenos": dict(sorted(Counter(item.get("kind", "unknown") for item in left_timeline).items())),
        "shift_native": dict(sorted(Counter(item.get("kind", "unknown") for item in right_timeline).items())),
    }
    left_milestones = {
        "bink_281_of_281": bool(left_events.get("bink_target")),
        "controller_input_gate": bool(left_events.get("input_gate_emitted")),
    }
    right_milestones = {
        "bink_281_of_281": bool(right_events.get("bink_target")),
        "controller_input_gate": bool(right_events.get("input_gate_emitted")),
    }
    return {
        "schema": "shift.xbox360.linux-gpu-backend-comparison.v3",
        "xenos_run": str(left_dir),
        "shift_native_run": str(right_dir),
        "required_identity": identity,
        "mapped_artifact_verification": mapped_verification,
        "milestones": {
            "xenos": {**left_milestones, "scene_transitions": scene_transitions(left_events)},
            "shift_native": {**right_milestones, "scene_transitions": scene_transitions(right_events)},
        },
        "event_counts": {"xenos": event_counts(left_events), "shift_native": event_counts(right_events)},
        "retail_queue_waits": {
            "xenos": retail_queue_wait_summary(left_events),
            "shift_native": retail_queue_wait_summary(right_events),
        },
        "retail_queue_wait_lifecycle": {
            "xenos": retail_queue_wait_lifecycle(left_events),
            "shift_native": retail_queue_wait_lifecycle(right_events),
        },
        "ke_wait_lifecycle": {
            "xenos": ke_wait_lifecycle(left_events),
            "shift_native": ke_wait_lifecycle(right_events),
        },
        "post_bink_event_counts": post_bink_event_counts,
        # A global trace order interleaves independent host threads. Keep its
        # first mismatch as a candidate only; scene identity is the stable
        # cross-thread gameplay checkpoint used for the semantic conclusion.
        "first_semantic_divergence": semantic_divergence,
        "first_manager_counter_divergence": counter_divergence,
        "manager_counter_progression": {
            "xenos": counter_progression(left_events),
            "shift_native": counter_progression(right_events),
        },
        "source1_guest_callback_summary": {
            "xenos": source1_callback_summary(left_events),
            "shift_native": source1_callback_summary(right_events),
        },
        "completion_token_summary": {
            "xenos": completion_token_summary(left_events),
            "shift_native": completion_token_summary(right_events),
        },
        "final_worker_queue_snapshots": {
            "xenos": final_queue_snapshots(left_events),
            "shift_native": final_queue_snapshots(right_events),
        },
        "gpu_ring_trace": {
            "xenos": gpu_ring_trace_summary(left_events),
            "shift_native": gpu_ring_trace_summary(right_events),
        },
        "native_renderer_logs": {
            "xenos": renderer_log_diagnostics(left_dir),
            "shift_native": renderer_log_diagnostics(right_dir),
        },
        "first_game_state_divergence": scene_divergence,
        "frontend_transition_return_divergence_candidate": frontend_transition_return_divergence,
        "frontend_transition_return_sequences": frontend_transition_returns,
        "frontend_transition_call_counts": frontend_transition_call_counts,
        "first_trace_order_difference": trace_order_difference,
        "first_submission_record_difference_candidate": submission_record_difference,
        "first_post_bink_divergence": semantic_divergence,
        "controller_update_call_counts": {
            "xenos": left_events.get("controller_update_call_counts", {}),
            "shift_native": right_events.get("controller_update_call_counts", {}),
        },
        "input_path": {
            "xenos": button_path(left_meta, left_events),
            "shift_native": button_path(right_meta, right_events),
        },
        "input_comparability": {
            "declared_profiles_match": declared_profiles_match,
            "gates_match": gates_match,
            "same_three_pulse_profile_delivered": same_profile_delivered,
            "delivered_profiles": {
                "xenos": [list(edge) for edge in left_host_profile],
                "shift_native": [list(edge) for edge in right_host_profile],
            },
        },
        "stop_context": {
            "xenos": left_events.get("stop_context", {}),
            "shift_native": right_events.get("stop_context", {}),
        },
        "run_outcome": {
            "xenos": {
                "duration_seconds": left_meta.get("duration_seconds"),
                "gdb_exit": left_meta.get("gdb_exit"),
                "bink_reached": left_bink,
            },
            "shift_native": {
                "duration_seconds": right_meta.get("duration_seconds"),
                "gdb_exit": right_meta.get("gdb_exit"),
                "bink_reached": right_bink,
            },
        },
        "capture_integrity": {
            "xenos": {
                "event_trace": "partial" if left_events.get("partial_capture") else "finalized",
                "gdb_exit": left_meta.get("gdb_exit"),
                "resource_manifest_verified_after_capture": left_meta.get("resource_manifest_verified_after_capture"),
            },
            "shift_native": {
                "event_trace": "partial" if right_events.get("partial_capture") else "finalized",
                "gdb_exit": right_meta.get("gdb_exit"),
                "resource_manifest_verified_after_capture": right_meta.get("resource_manifest_verified_after_capture"),
            },
        },
        "interpretation": (
            "Manager-counter writes compare producer and completion effects in their serialized watchpoint "
            "order; scene state is a stable gameplay checkpoint. Global trace order can reflect independent-"
            "thread interleaving. Neither backend is assumed correct; confirm across repeated captures and "
            "correlate GPU packets before assigning cause."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compare_parser = subparsers.add_parser("compare", help="compare two completed captures")
    compare_parser.add_argument("xenos_run", type=Path)
    compare_parser.add_argument("shift_native_run", type=Path)
    compare_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.xenos_run, args.shift_native_run)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"comparison failed: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
