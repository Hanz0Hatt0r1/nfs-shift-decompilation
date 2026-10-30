#!/usr/bin/env python3
"""Compare state-aligned retail Menu Setup traces from v112 on both backends."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PULSES = [("Start", 5, 17), ("A", 21, 33), ("Start", 37, 49)]
INPUT_FIELDS = ("buttons", "host_buttons", "previous", "start_edge", "a_edge", "active")
ACTION_FUNCTIONS = ("sub_822EF7B0", "sub_822F7EC8")


class ComparisonError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _records(path: Path) -> list[tuple[str, dict[str, Any]]]:
    result = []
    for line_no, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if not line.startswith("P1_") or " {" not in line:
            continue
        marker, raw = line.split(" ", 1)
        try:
            result.append((marker, json.loads(raw)))
        except json.JSONDecodeError as exc:
            raise ComparisonError(f"{path}:{line_no}: malformed event JSON") from exc
    return result


def _pulse_schedule(metadata: dict[str, Any]) -> list[tuple[Any, Any, Any]]:
    return [(row.get("button"), row.get("observed_down_state2_index"),
             row.get("observed_up_state2_index"))
            for row in metadata.get("controller_pulses", [])]


def _semantic_input(row: dict[str, Any]) -> dict[str, Any]:
    inp = row.get("input") or {}
    return {field: inp.get(field) for field in INPUT_FIELDS}


def _return_signature(function: str | None, value: str | None) -> str:
    if function == "sub_822F7EC8":
        return "null" if value in (None, "0x0", "0") else "non-null guest pointer"
    return str(value)


def _zero_nonzero(value: str | None) -> str:
    if value is None:
        return "missing"
    return "zero" if value in ("0x0", "0") else "non-zero"


def _event_scalar_words(words: list[int]) -> list[int]:
    return [words[index] for index in (1, 4, 6, 7, 13) if len(words) > index]


def _symbol_name(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r" in section \.ltext of .+$", "", value).strip()


def _capture(run_dir: Path, backend: str) -> dict[str, Any]:
    metadata_path = run_dir / "run_metadata.json"
    if not metadata_path.is_file():
        raise ComparisonError(f"{run_dir}: missing run_metadata.json")
    metadata = json.loads(metadata_path.read_text())
    if (metadata.get("backend") != backend or metadata.get("gdb_exit") != 0
            or metadata.get("guest_memory_modified_by_probe") is not False):
        raise ComparisonError(f"{run_dir}: wrong backend, failed capture, or mutating probe")
    if _pulse_schedule(metadata) != PULSES:
        raise ComparisonError(f"{run_dir}: Start/A/Start did not land at 5/17, 21/33, 37/49")
    if (metadata.get("post_pulse_settle_updates_requested") != 16
            or metadata.get("post_pulse_settle_updates_observed") != 16
            or metadata.get("post_pulse_settle_stop_reason") != "settle_updates_observed"):
        raise ComparisonError(f"{run_dir}: missing all 16 post-input settle updates")

    log_path = Path(metadata.get("events_log", ""))
    if not log_path.is_file() or metadata.get("events_log_sha256") != _sha256(log_path):
        raise ComparisonError(f"{run_dir}: missing or hash-mismatched event log")
    records = _records(log_path)
    by_marker: dict[str, list[dict[str, Any]]] = {}
    for marker, row in records:
        by_marker.setdefault(marker, []).append(row)

    updates = by_marker.get("P1_STATE2_UPDATE", [])
    if ([row.get("state2_index") for row in updates] != list(range(1, 66))
            or any(row.get("state") != 2 for row in updates)):
        raise ComparisonError(f"{run_dir}: did not remain in state 2 through update 65")

    input_rows = by_marker.get("P1_RETAIL_INPUT_TRUE_HANDLER", [])
    input_edges = []
    for row in input_rows:
        event_fields = row.get("event_fields") or []
        inp = row.get("input") or {}
        input_edges.append({
            "button": row.get("button"),
            "state2_index": row.get("state2_index"),
            "event_code": f"0x{event_fields[2]:08x}" if len(event_fields) > 2 else None,
            "event_object_raw": row.get("event_object"),
            "event_fields": event_fields,
            "event_vtable_slots": row.get("event_vtable_slots"),
            "predicate_object_raw": row.get("predicate_object"),
            "predicate_fields": row.get("predicate_fields"),
            "predicate_vtable": row.get("predicate_vtable"),
            "predicate_vtable_slots": row.get("predicate_vtable_slots"),
            "caller_lr": row.get("caller_lr"),
            "guest_context_r3_r10": row.get("guest_context_r3_r10"),
            "guest_context_r30_r31": row.get("guest_context_r30_r31"),
            "thread": row.get("thread"),
            "buttons": inp.get("buttons"),
            "host_buttons": inp.get("host_buttons"),
            "start_edge": inp.get("start_edge"),
            "a_edge": inp.get("a_edge"),
            "event_vtable": row.get("event_vtable"),
        })
    expected_edges = [("Start", 5), ("A", 21), ("Start", 37)]
    if [(row["button"], row["state2_index"]) for row in input_edges] != expected_edges:
        raise ComparisonError(f"{run_dir}: original true input handlers did not see all three edges")
    if any(row["event_code"] is None for row in input_edges):
        raise ComparisonError(f"{run_dir}: input event code is unavailable")
    action_event_field_writes = [{
        key: row.get(key) for key in (
            "button", "state2_index", "event_code", "event_object", "guest_field",
            "guest_lr", "before", "after", "guest_r26_candidate",
            "guest_r31_matches_event_object", "guest_memory_modified_by_probe", "thread",
        )
    } for row in by_marker.get("P1_ACTION_EVENT_FIELD_WRITE", [])]

    calls: dict[tuple[str, int], dict[str, Any]] = {}
    returns: dict[tuple[str, int], dict[str, Any]] = {}
    for row in by_marker.get("P1_ACTION_CONSUMER_CALL", []):
        key = (row.get("function"), row.get("call_index"))
        if key in calls:
            raise ComparisonError(f"{run_dir}: duplicate action consumer call {key}")
        calls[key] = row
    for row in by_marker.get("P1_ACTION_CONSUMER_RETURN", []):
        key = (row.get("function"), row.get("call_index"))
        if key in returns:
            raise ComparisonError(f"{run_dir}: duplicate action consumer return {key}")
        returns[key] = row
    if set(calls) != set(returns):
        raise ComparisonError(f"{run_dir}: sampled action calls and returns do not pair")
    consumer_summary = by_marker.get("P1_ACTION_CONSUMER_SUMMARY", [])
    if len(consumer_summary) != 1 or consumer_summary[0].get("guest_memory_modified_by_probe") is not False:
        raise ComparisonError(f"{run_dir}: missing read-only action consumer summary")
    consumer_outcomes = []
    for key, call in calls.items():
        returned = returns[key]
        if (returned.get("args_r3_r10_at_entry") != call.get("args_r3_r10")
                or returned.get("caller_lr") != call.get("caller_lr")):
            raise ComparisonError(f"{run_dir}: call/return evidence disagrees for {key}")
        consumer_outcomes.append({
            "function": call.get("function"), "button": call.get("button"),
            "state2_index": call.get("last_state2_index_seen"),
            "input": _semantic_input(call), "caller_lr": call.get("caller_lr"),
            "return_r3": returned.get("return_r3"),
            "args_r3_r10_raw": call.get("args_r3_r10"),
            "return_r3_r10_raw": returned.get("return_r3_r10"),
            "return_signature": _return_signature(call.get("function"),
                                                   returned.get("return_r3")),
            "receiver_raw": call.get("receiver"),
        })

    dequeue_rows = [row for row in by_marker.get("P1_DEQUEUE_RETURN_CONTEXT", [])
                    if row.get("source_function") == "sub_822E1910"]
    if not dequeue_rows:
        raise ComparisonError(f"{run_dir}: no live sub_822E1910 return contexts")
    worker_events = []
    for row in dequeue_rows:
        words = row.get("dequeued_output_words") or []
        object_words = row.get("dequeued_event_object_words") or []
        if row.get("return_r3") == "0x1" and (len(words) < 4 or len(object_words) < 14):
            raise ComparisonError(f"{run_dir}: successful dequeue lacks event payload fields")
        worker_events.append({
            "source_call_index": row.get("source_call_index"),
            "state2_index": row.get("state2_index"),
            "return_r3": row.get("return_r3"),
            "event_type": words[1] if len(words) > 1 else None,
            "event_scalar_words": _event_scalar_words(object_words),
            "event_object_words_raw": object_words,
            "event_object_raw": row.get("dequeued_event_object"),
            "queue_receiver_raw": row.get("queue_receiver"),
            "guest_context_r3_r10_raw": row.get("guest_context_r3_r10"),
            "guest_r1_raw": row.get("guest_r1"),
            "guest_lr_raw": row.get("source_caller_lr"),
            "r28_plus_0x10": row.get("guest_r28_plus_0x10"),
        })
    context_writes = [{
        "before": row.get("context_r3_before"),
        "after": row.get("context_r3_after"),
        "guest_lr": row.get("context_guest_lr"),
        "guest_memory_modified_by_probe": row.get("guest_memory_modified_by_probe"),
        "r28_plus_0x10": (row.get("dequeue_return_snapshot") or {}).get("guest_r28_plus_0x10"),
    } for row in by_marker.get("P1_CONTEXT_R3_WRITE_WATCH", [])]
    handlers = by_marker.get("P1_DEQUEUE_EVENT_HANDLER_CALL", [])
    nested_calls = by_marker.get("P1_NESTED_EVENT_DISPATCH_CALL", [])
    nested_returns = by_marker.get("P1_NESTED_EVENT_DISPATCH_RETURN", [])
    if (not handlers or len(handlers) != len(nested_calls)
            or len(nested_calls) != len(nested_returns)):
        raise ComparisonError(f"{run_dir}: downstream event-handler/callback evidence is incomplete")
    callback_outcomes = []
    for row in nested_calls:
        object_words = row.get("callback_event_object_words") or []
        callback_outcomes.append({
            "source_call_index": row.get("source_call_index"),
            "state2_index": row.get("source_state2_index"),
            "event_type": row.get("event_type"),
            "event_scalar_words": _event_scalar_words(object_words),
            "callback_symbol": _symbol_name(row.get("host_target_symbol")),
            "event_object_words_raw": object_words,
            "event_object_raw": row.get("callback_event_object"),
            "guest_r3_r10_at_call_raw": row.get("guest_r3_r10_at_call"),
            "guest_lr_at_call": row.get("guest_lr_at_call"),
        })
    callback_return_values = [
        (row.get("guest_r3_r10_after_call") or [None])[0]
        for row in nested_returns
    ]
    callback_semantics = sorted(
        ((row["event_type"], tuple(row["event_scalar_words"]), row["callback_symbol"])
         for row in callback_outcomes), key=repr)

    scene_writes = by_marker.get("P1_SCENE_GATE_FIELD_WRITE", [])
    if len(scene_writes) != 1:
        raise ComparisonError(f"{run_dir}: expected the one-time scene-gate initialization write")
    gate = scene_writes[0]
    if gate.get("before") != 0 or gate.get("after") != 1:
        raise ComparisonError(f"{run_dir}: unexpected scene-gate initialization transition")
    gui_summary = by_marker.get("P1_MAIN_MENU_EVENT_QUEUE_SUMMARY", [])
    if len(gui_summary) != 1:
        raise ComparisonError(f"{run_dir}: missing GUI event-queue summary")
    raw_gui_summary = gui_summary[0]
    gui_semantics = {
        key: raw_gui_summary.get(key) for key in (
            "constructor_calls", "open_calls", "enqueue_calls", "enqueue_returns",
            "direct_append_calls", "direct_append_returns",
        )
    }
    gui_processing_counts = {
        key: raw_gui_summary.get(key) for key in (
            "process_event_queue_calls", "process_parent_calls", "process_parent_returns",
        )
    }

    hashes = metadata.get("hashes", {})
    return {
        "backend": backend,
        "run_dir": str(run_dir),
        "duration_seconds": metadata.get("duration_seconds"),
        "event_log_sha256": metadata["events_log_sha256"],
        "xex_sha256": hashes.get("xex"), "host_sha256": hashes.get("host"),
        "runtime_sha256": hashes.get("runtime"), "plugin_sha256": hashes.get("plugin"),
        "runner_sha256": metadata.get("runner_sha256"),
        "trace_sha256": metadata.get("trace_sha256"),
        "game_data_root": metadata.get("game_data_root"),
        "input_pulses": _pulse_schedule(metadata),
        "state2_update_count": len(updates), "state2_last_index": updates[-1]["state2_index"],
        "post_pulse_settle_updates": metadata.get("post_pulse_settle_updates_observed"),
        "input_edges": input_edges,
        "action_event_field_writes": action_event_field_writes,
        "action_consumer_outcomes": consumer_outcomes,
        "action_consumer_signatures": sorted([
            {key: row[key] for key in ("function", "button", "state2_index", "input",
                                       "caller_lr", "return_signature")}
            for row in consumer_outcomes
        ], key=repr),
        "action_consumer_summary": consumer_summary[0],
        "successful_dequeue_events": [row for row in worker_events if row["return_r3"] == "0x1"],
        "successful_dequeue_signatures": sorted([
            {key: row[key] for key in ("return_r3", "event_type", "event_scalar_words",
                                       "r28_plus_0x10")}
            for row in worker_events if row["return_r3"] == "0x1"
        ], key=repr),
        "dequeue_context_r3_writes": sorted(context_writes, key=repr),
        "event_handler_call_count": len(handlers),
        "nested_callback_signatures": callback_outcomes,
        "nested_callback_semantics": callback_semantics,
        "nested_callback_return_r3_raw": callback_return_values,
        "nested_callback_return_signatures": sorted(_zero_nonzero(value)
                                                    for value in callback_return_values),
        "scene_gate_initialization": {
            "before": gate.get("before"), "after": gate.get("after"),
        },
        "scene_gate_initialization_raw": gate,
        "gui_event_queue_summary": gui_semantics,
        "gui_event_queue_processing_counts": gui_processing_counts,
        "gui_event_queue_summary_raw": raw_gui_summary,
        "guest_memory_modified_by_probe": False,
    }


def _counter(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    counts = Counter(tuple(row.get(field) for field in fields) for row in rows)
    return [
        {"key": list(key), "count": count}
        for key, count in sorted(counts.items(), key=lambda item: repr(item[0]))
    ]


def compare_runs(xenos_dir: Path, native_dir: Path) -> dict[str, Any]:
    xenos = _capture(xenos_dir, "xenos")
    native = _capture(native_dir, "shift-native")
    for field in ("xex_sha256", "host_sha256", "runtime_sha256", "runner_sha256",
                  "trace_sha256", "game_data_root", "input_pulses"):
        if xenos[field] != native[field]:
            raise ComparisonError(f"runs do not share {field}")
    if xenos["plugin_sha256"] == native["plugin_sha256"]:
        raise ComparisonError("GPU plugin hashes unexpectedly match")

    compare_fields = (
        "input_edges", "action_consumer_signatures", "successful_dequeue_signatures",
        "dequeue_context_r3_writes", "event_handler_call_count",
        "nested_callback_semantics", "nested_callback_return_signatures",
        "scene_gate_initialization", "gui_event_queue_summary",
    )
    differences = [field for field in compare_fields if xenos[field] != native[field]]
    return {
        "schema": "shift.xbox360.linux-menu-setup-worker-gate-pair.v112",
        "result": {
            "same_xex_host_runtime_and_capture": True,
            "same_state_aligned_input_schedule": True,
            "both_remained_in_state_2_through_update_65": True,
            "both_observed_16_post_input_settle_updates": True,
            "semantic_trace_fields_match": not differences,
            "semantic_difference_fields": differences,
            "backend_specific_cause_established": False,
            "difference_requires_repeat_before_attribution": bool(differences),
            "worker_dequeue_count_match": len(xenos["successful_dequeue_events"]) == len(
                native["successful_dequeue_events"]),
            "nested_callback_count_match": len(xenos["nested_callback_signatures"]) == len(
                native["nested_callback_signatures"]),
            "gui_queue_structure_match": xenos["gui_event_queue_summary"] == native[
                "gui_event_queue_summary"],
            "probe_modified_guest_memory": False,
        },
        "runs": {"xenos": xenos, "shift-native": native},
        "comparison": {
            "input_edge_counts": {
                backend: len(run["input_edges"]) for backend, run in
                (("xenos", xenos), ("shift-native", native))
            },
            "action_outcome_counts_by_button_and_function": {
                backend: _counter(run["action_consumer_signatures"],
                                  ("button", "function", "return_signature"))
                for backend, run in (("xenos", xenos), ("shift-native", native))
            },
            "successful_dequeue_count": {
                backend: len(run["successful_dequeue_events"])
                for backend, run in (("xenos", xenos), ("shift-native", native))
            },
            "nested_callback_count": {
                backend: len(run["nested_callback_signatures"])
                for backend, run in (("xenos", xenos), ("shift-native", native))
            },
            "nested_callback_semantics": {
                backend: run["nested_callback_semantics"]
                for backend, run in (("xenos", xenos), ("shift-native", native))
            },
            "gui_event_queue_processing_counts": {
                backend: run["gui_event_queue_processing_counts"]
                for backend, run in (("xenos", xenos), ("shift-native", native))
            },
            "semantic_difference_fields": differences,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xenos_run", type=Path)
    parser.add_argument("native_run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(compare_runs(args.xenos_run, args.native_run), indent=2,
                           sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
