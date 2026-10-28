#!/usr/bin/env python3
"""Regression checks for the source-1 guest/GPU dispatch crosswalk."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("join_linux_source1_gpu_dispatches_20261028.py")
SPEC = importlib.util.spec_from_file_location("source1_gpu_dispatch_join", SCRIPT)
assert SPEC and SPEC.loader
JOIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(JOIN)


def main() -> None:
    pm4_log = """
[2026-10-28 15:01:37.830] [info] shift-native: ring trace PM4_INTERRUPT #19 source=1 dispatch_id=0000000000005A17 generation=4 batch_rptr=128 batch_wptr=192 ring_guest=09752580 packet=117 packet_source=095D0120+1464 cpu_mask=0x04 dispatched_cpu_mask=0x04 callback_dispatches=[]
shift-native: ring trace PM4_INTERRUPT #20 source=1 dispatch_id=0000000000005A18 generation=4 batch_rptr=192 batch_wptr=224 ring_guest=09752580 packet=121 packet_source=095D0120+1512 cpu_mask=0x04 dispatched_cpu_mask=0x00 callback_dispatches=[]
"""
    interrupts = JOIN.parse_interrupt_rows(pm4_log)
    assert interrupts[0x5A17][0]["packet_source_guest"] == 0x095D0120
    assert interrupts[0x5A17][0]["packet_source_offset"] == 1464
    assert interrupts[0x5A18][0]["packet_ordinal"] == 121

    events = {
        "schema": "shift.xbox360.linux-gpu-backend-events.v1",
        "gpu_backend": "shift-native",
        "gpu_dispatch_id_trace": {"getter_available": True},
        "events": {
            "source1_callback_events": [
                {"gpu_dispatch_id": 0x5A17, "trace_sequence": 40,
                 "thread_name": "GPU interrupt worker"},
                {"gpu_dispatch_id": "0x5A19", "trace_sequence": 44},
            ],
            "producer_call_events": [
                {"parent_gpu_dispatch_id": 0x5A17, "producer_call": 8,
                 "delta": -1, "record_words": [1, 2, 3, 4]},
            ],
            "dequeue_events": [
                {"parent_gpu_dispatch_id": 0x5A17, "id": 21,
                 "slot_value": 0xC0000000, "phase": "entry"},
            ],
            "completion_events": [
                {"parent_gpu_dispatch_id": 0x5A17, "token": 0xC0000000,
                 "signed_delta": -1},
            ],
            "counter_write_events": [
                {"parent_gpu_dispatch_id": 0x5A17, "before": 1, "after": 0,
                 "signed_delta": -1, "parent_dequeue_id": 21},
            ],
            "queue_field_write_events": [
                {"parent_gpu_dispatch_id": 0x5A17, "guest_address": 0x17AF4000,
                 "before": 3381, "after": 3375},
            ],
            "event_call_events": [
                {"parent_gpu_dispatch_id": 0x5A18, "symbol": "KeSetEvent"},
            ],
        },
    }
    report = JOIN.join_dispatches(events, pm4_log, {
        "gpu_backend": "shift-native",
        "xex_sha256": "a" * 64,
        "plugin_sha256": "b" * 64,
    })
    assert report["summary"]["matched_dispatch_ids"] == 1
    assert report["summary"]["source1_dispatch_ids_without_pm4_row"] == [
        "0x0000000000005A19"
    ]
    assert report["summary"]["pm4_dispatch_ids_without_source1_callback"] == [
        "0x0000000000005A18"
    ]
    by_id = {row["dispatch_id"]: row for row in report["dispatches"]}
    linked = by_id["0x0000000000005A17"]
    assert linked["joined"]
    assert linked["source1_callback_count"] == 1
    assert linked["guest_worker_event_count"] == 5
    assert linked["pm4_interrupts"][0]["packet_ordinal"] == 117
    producer = next(
        row for row in linked["guest_worker_events"]
        if row["event_group"] == "producer_call_events"
    )
    assert producer["delta"] == -1
    counter = next(
        row for row in linked["guest_worker_events"]
        if row["event_group"] == "counter_write_events"
    )
    assert counter["signed_delta"] == -1
    assert "do not by themselves prove" in report["interpretation_limit"]
    assert report["capture_identity"]["plugin_sha256"] == "b" * 64

    no_getter = {**events, "gpu_dispatch_id_trace": {"getter_available": False}}
    try:
        JOIN.join_dispatches(no_getter, pm4_log)
    except ValueError as exc:
        assert "did not resolve" in str(exc)
    else:
        raise AssertionError("capture without getter was accepted")

    try:
        JOIN.join_dispatches(events, pm4_log, {"gpu_backend": "xenos"})
    except ValueError as exc:
        assert "backend does not match" in str(exc)
    else:
        raise AssertionError("mismatched run metadata was accepted")

    mismatched_plugin_events = {
        **events,
        "mapped_hashes": {"/capture/librexgpu-shift-native.so": "c" * 64},
    }
    try:
        JOIN.join_dispatches(mismatched_plugin_events, pm4_log, {
            "gpu_backend": "shift-native", "plugin_sha256": "b" * 64,
        })
    except ValueError as exc:
        assert "plugin hash" in str(exc)
    else:
        raise AssertionError("mismatched mapped plugin was accepted")

    print("source-1 callback IDs join to PM4 locations and worker events without causal overclaim")


if __name__ == "__main__":
    main()
