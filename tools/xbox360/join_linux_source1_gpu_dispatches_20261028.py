#!/usr/bin/env python3
"""Join Native source-1 guest callbacks to Process 2 PM4 interrupt trace rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


PM4_INTERRUPT_RE = re.compile(
    r"ring trace PM4_INTERRUPT #(?P<event>\d+) source=1 "
    r"dispatch_id=(?P<dispatch_id>[0-9A-Fa-f]+) "
    r"generation=(?P<generation>\d+) batch_rptr=(?P<batch_rptr>\d+) "
    r"batch_wptr=(?P<batch_wptr>\d+) ring_guest=(?P<ring_guest>[0-9A-Fa-f]+) "
    r"packet=(?P<packet>\d+) packet_source=(?P<packet_source>[0-9A-Fa-f]+)\+(?P<source_offset>\d+)"
)
EVENT_GROUPS = (
    "enqueue_events", "dequeue_events", "completion_events", "producer_events",
    "producer_call_events", "submission_route_events", "counter_write_events",
    "queue_field_write_events", "event_call_events", "worker72_write_events",
    "ke_wait_return_events",
)
EVENT_FIELDS = (
    "kind", "trace_sequence", "elapsed_seconds", "thread", "thread_name",
    "id", "parent_dequeue_id", "parent_record", "record", "slot_value",
    "parent_producer_id", "producer_call", "write_index", "field",
    "memory_alias", "guest_function_candidate", "tag", "delta", "token", "counter_before",
    "counter_after", "signed_delta", "symbol", "event", "guest_signal_state",
    "return_status", "status_returned", "manager", "queue", "guest_address",
    "before", "after",
)


def normalize_dispatch_id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        value = value.strip()
        try:
            parsed = int(value, 16 if not value.lower().startswith("0x") else 0)
        except ValueError:
            return None
        return parsed if parsed > 0 else None
    return None


def format_dispatch_id(dispatch_id: int) -> str:
    return f"0x{dispatch_id:016X}"


def parse_interrupt_rows(log_text: str) -> dict[int, list[dict[str, Any]]]:
    rows: dict[int, list[dict[str, Any]]] = {}
    for line in log_text.splitlines():
        match = PM4_INTERRUPT_RE.search(line)
        if not match:
            continue
        raw = match.groupdict()
        dispatch_id = int(raw["dispatch_id"], 16)
        if not dispatch_id:
            continue
        row = {
            "trace_event": int(raw["event"]),
            "dispatch_id": format_dispatch_id(dispatch_id),
            "generation": int(raw["generation"]),
            "batch_rptr": int(raw["batch_rptr"]),
            "batch_wptr": int(raw["batch_wptr"]),
            "ring_guest": int(raw["ring_guest"], 16),
            "packet_ordinal": int(raw["packet"]),
            "packet_source_guest": int(raw["packet_source"], 16),
            "packet_source_offset": int(raw["source_offset"]),
        }
        rows.setdefault(dispatch_id, []).append(row)
    return rows


def _guest_event(event_group: str, event: dict[str, Any], dispatch_id: int) -> dict[str, Any]:
    row = {key: event[key] for key in EVENT_FIELDS if key in event}
    row["event_group"] = event_group
    row["dispatch_id"] = format_dispatch_id(dispatch_id)
    row["gpu_dispatch_id"] = event.get("gpu_dispatch_id")
    row["parent_gpu_dispatch_id"] = event.get("parent_gpu_dispatch_id")
    return row


def join_dispatches(
    events: dict[str, Any], log_text: str,
    metadata: dict[str, Any] | None = None,
    interrupt_log_sha256: str | None = None,
) -> dict[str, Any]:
    if events.get("schema") != "shift.xbox360.linux-gpu-backend-events.v1":
        raise ValueError("unsupported Process 1 events schema")
    if events.get("gpu_backend") != "shift-native":
        raise ValueError("dispatch-ID join requires a Native Vulkan capture")
    dispatch_trace = events.get("gpu_dispatch_id_trace")
    if not isinstance(dispatch_trace, dict) or dispatch_trace.get("getter_available") is not True:
        raise ValueError("capture did not resolve the GPU dispatch-ID getter")
    if metadata:
        if metadata.get("gpu_backend") != events.get("gpu_backend"):
            raise ValueError("run metadata backend does not match events.json")
        plugin_hash = metadata.get("plugin_sha256")
        mapped_plugin_hashes = [
            value for path, value in events.get("mapped_hashes", {}).items()
            if path.endswith("/librexgpu-shift-native.so")
        ]
        if plugin_hash and mapped_plugin_hashes and plugin_hash not in mapped_plugin_hashes:
            raise ValueError("run metadata plugin hash does not match mapped plugin hash")

    source1_callbacks: dict[int, list[dict[str, Any]]] = {}
    guest_events: dict[int, list[dict[str, Any]]] = {}
    event_rows = events.get("events", {})
    if not isinstance(event_rows, dict):
        raise ValueError("events.json has no event groups")
    for event in event_rows.get("source1_callback_events", []):
        if not isinstance(event, dict):
            continue
        dispatch_id = normalize_dispatch_id(event.get("gpu_dispatch_id"))
        if dispatch_id is not None:
            source1_callbacks.setdefault(dispatch_id, []).append(
                _guest_event("source1_callback_events", event, dispatch_id)
            )
    for group in EVENT_GROUPS:
        for event in event_rows.get(group, []):
            if not isinstance(event, dict):
                continue
            # A queued worker's parent ID is the GPU callback that produced its
            # record. Preserve the current ID in the row for nested callbacks.
            dispatch_id = normalize_dispatch_id(event.get("parent_gpu_dispatch_id"))
            if dispatch_id is None:
                dispatch_id = normalize_dispatch_id(event.get("gpu_dispatch_id"))
            if dispatch_id is not None:
                guest_events.setdefault(dispatch_id, []).append(
                    _guest_event(group, event, dispatch_id)
                )

    interrupts = parse_interrupt_rows(log_text)
    all_ids = sorted(set(source1_callbacks) | set(guest_events) | set(interrupts))
    dispatches = []
    for dispatch_id in all_ids:
        callbacks = source1_callbacks.get(dispatch_id, [])
        workers = guest_events.get(dispatch_id, [])
        gpu_rows = interrupts.get(dispatch_id, [])
        dispatches.append({
            "dispatch_id": format_dispatch_id(dispatch_id),
            "joined": bool(callbacks and gpu_rows),
            "source1_callback_count": len(callbacks),
            "guest_worker_event_count": len(workers),
            "pm4_interrupt_count": len(gpu_rows),
            "source1_callbacks": callbacks,
            "guest_worker_events": workers,
            "pm4_interrupts": gpu_rows,
        })

    unmatched_callback_ids = sorted(set(source1_callbacks) - set(interrupts))
    interrupt_ids_without_callback = sorted(set(interrupts) - set(source1_callbacks))
    return {
        "schema": "shift.xbox360.linux-source1-gpu-dispatch-join.v1",
        "capture_identity": {
            key: metadata.get(key)
            for key in (
                "gpu_backend", "xex_sha256", "host_sha256", "runtime_sha256",
                "plugin_sha256", "p2_plugin_build_id", "p2_source_commit",
            )
            if metadata and key in metadata
        },
        "summary": {
            "source1_callback_dispatch_ids": len(source1_callbacks),
            "dispatch_ids_with_worker_events": len(guest_events),
            "pm4_interrupt_dispatch_ids": len(interrupts),
            "matched_dispatch_ids": len(set(source1_callbacks) & set(interrupts)),
            "source1_dispatch_ids_without_pm4_row": [
                format_dispatch_id(value) for value in unmatched_callback_ids
            ],
            "pm4_dispatch_ids_without_source1_callback": [
                format_dispatch_id(value) for value in interrupt_ids_without_callback
            ],
            "guest_worker_events_without_dispatch_id": sum(
                1
                for group in EVENT_GROUPS
                for row in event_rows.get(group, [])
                if isinstance(row, dict)
                and normalize_dispatch_id(row.get("parent_gpu_dispatch_id")) is None
                and normalize_dispatch_id(row.get("gpu_dispatch_id")) is None
            ),
        },
        "interrupt_log_sha256": interrupt_log_sha256 or hashlib.sha256(
            log_text.encode("utf-8")
        ).hexdigest(),
        "dispatches": dispatches,
        "interpretation_limit": (
            "A matching ID ties the guest callback and worker records to the same "
            "Native PM4_INTERRUPT source=1 dispatch scope. Its packet coordinates "
            "locate the interrupt in the GPU trace; they do not by themselves prove "
            "which earlier EVENT_WRITE_SHD store caused a guest state change."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True, help="Process 1 events.json")
    parser.add_argument("--interrupt-log", type=Path, required=True,
                        help="same-run Native log containing PM4_INTERRUPT trace rows")
    parser.add_argument("--metadata", type=Path,
                        help="run_metadata.json (defaults to the events.json directory)")
    parser.add_argument("--output", type=Path, help="write JSON report to this path")
    args = parser.parse_args()
    metadata_path = args.metadata or args.events.with_name("run_metadata.json")
    try:
        events = json.loads(args.events.read_text(encoding="utf-8"))
        metadata = (
            json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata_path.is_file() else None
        )
        if metadata and metadata.get("schema") != "shift.xbox360.linux-gpu-backend-run.v1":
            raise ValueError("unsupported run metadata schema")
        log_bytes = args.interrupt_log.read_bytes()
        log_text = log_bytes.decode("utf-8", errors="replace")
        report = join_dispatches(
            events, log_text, metadata,
            interrupt_log_sha256=hashlib.sha256(log_bytes).hexdigest(),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"source1 GPU dispatch join failed: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
