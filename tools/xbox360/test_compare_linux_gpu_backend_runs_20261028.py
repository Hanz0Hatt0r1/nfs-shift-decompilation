#!/usr/bin/env python3
"""Regression tests for event-aligned Xenos/Native Vulkan comparisons."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("compare_linux_gpu_backend_runs_20261028.py")
SPEC = importlib.util.spec_from_file_location("gpu_backend_compare", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CAPTURE_SCRIPT = Path(__file__).with_name("capture_linux_post_bink_worker_route_v45_ordered_route_20261027.py")
CAPTURE_SPEC = importlib.util.spec_from_file_location("gpu_backend_capture", CAPTURE_SCRIPT)
assert CAPTURE_SPEC and CAPTURE_SPEC.loader
CAPTURE = importlib.util.module_from_spec(CAPTURE_SPEC)
CAPTURE_SPEC.loader.exec_module(CAPTURE)


def make_run(root: Path, backend: str, rows: list[dict], *, elapsed_shift: float = 0.0,
             gate: bool = True, host_masks: list[int] | None = None,
             bink: bool = True, mapped: bool = True):
    run_dir = root / backend
    run_dir.mkdir()
    plugin_name = f"librexgpu-{backend}.so"
    plugin_hash = "a" * 64 if backend == "xenos" else "b" * 64
    runtime_hash = "c" * 64
    host_hash = "d" * 64
    xex_hash = "e" * 64
    resource_hash = "f" * 64
    metadata = {
        "schema": "shift.xbox360.linux-gpu-backend-run.v1",
        "gpu_backend": backend,
        "plugin_sha256": plugin_hash,
        "staged_plugin_sha256": plugin_hash,
        "host_sha256": host_hash,
        "staged_host_sha256": host_hash,
        "runtime_sha256": runtime_hash,
        "xex_sha256": xex_hash,
        "resource_manifest_sha256": resource_hash,
        "controller_input": {
            "enabled": True,
            "gate_observed": gate,
            "pulses": ([
                {"button": "Start", "expected_mask": "0x0010"},
                {"button": "A", "expected_mask": "0x1000"},
                {"button": "Start", "expected_mask": "0x0010"},
            ] if gate else []),
        },
    }
    events = {
        "schema": "shift.xbox360.linux-gpu-backend-events.v1",
        "gpu_backend": backend,
        "mapped_hashes": ({
            "/tmp/bin/librexruntime.so": runtime_hash,
            f"/tmp/bin/{plugin_name}": plugin_hash,
        } if mapped else {}),
        "bink_target": ({"target": 281, "progress": 281} if bink else None),
        "input_gate_emitted": gate,
        "xam_input_calls": 12,
        "controller_update_call_counts": {"sub_82308E60": 12},
        "events": {
            "trace_events": [],
            "host_input_events": [
                {"kind": "host_input", "trace_sequence": 99 + index, "buttons": mask}
                for index, mask in enumerate(host_masks or [])
            ],
        },
    }
    for row in rows:
        item = dict(row)
        item["elapsed_seconds"] = item.get("elapsed_seconds", 1.0) + elapsed_shift
        events["events"]["trace_events"].append(item)
    (run_dir / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (run_dir / "events.json").write_text(json.dumps(events), encoding="utf-8")
    return run_dir


def main():
    baseline = [
        {"kind": "bink_complete", "trace_sequence": 1, "target": 281, "progress": 281},
        {"kind": "scene_state", "trace_sequence": 2, "state_348": 1, "update_count_356": 1},
        {"kind": "counter_write", "trace_sequence": 3, "old": 1, "new": 0},
    ]
    with tempfile.TemporaryDirectory() as temp:
        shared_dir = Path(temp)
        preexisting = shared_dir / "xenia_memory_100"
        preexisting.write_bytes(b"keep")
        before = CAPTURE.xenia_memory_names(shared_dir)
        orphan = shared_dir / "xenia_memory_200"
        orphan.write_bytes(b"runtime backing")
        fd = os.open(orphan, os.O_RDONLY)
        try:
            cleanup = CAPTURE.cleanup_orphaned_xenia_memory(
                before, shared_dir=shared_dir, proc_root=Path("/proc"),
            )
            assert cleanup["removed"] == []
            assert cleanup["retained_open_or_unlink_failed"] == [orphan.name]
        finally:
            os.close(fd)
        cleanup = CAPTURE.cleanup_orphaned_xenia_memory(
            before, shared_dir=shared_dir, proc_root=Path("/proc"),
        )
        assert cleanup["removed"] == [orphan.name]
        assert preexisting.exists() and not orphan.exists()

    input_result = MODULE.button_path(
        {"controller_input": {"enabled": True, "gate_observed": True}},
        {
            "xam_input_calls": 3,
            "events": {
                "xam_input_return_events": [
                    {"status": 0, "buttons": 0},
                    {"status": 0, "buttons": 0x0010},
                    {"status": 0xC0000001, "buttons": None},
                ],
            },
        },
    )
    assert input_result["xam_input_return_count"] == 3
    assert input_result["xam_input_return_statuses"] == {"0x00000000": 2, "0xC0000001": 1}
    assert input_result["xam_input_button_masks"] == ["0x0000", "0x0010"]

    with tempfile.TemporaryDirectory() as temp:
        trace_log = Path(temp) / "runner.log"
        trace_log.write_text(
            "WORKER_RING_MAPPED path=/tmp/librexruntime.so sha256=" + "c" * 64 + "\n"
            "WORKER_RING_WORKER_LOOP queue=0xB7368BE0 event=0xB7368C00\n"
            "WORKER_RING {\"kind\":\"bink_complete\",\"progress\":281,\"target\":281,\"trace_sequence\":1}\n"
            "WORKER_RING {\"kind\":\"counter_write\",\"before\":1,\"after\":0,\"trace_sequence\":2}\n"
            "WORKER_RING {\"kind\":\"scene_function_return\",\"function\":\"sub_82F38158\",\"return_value\":0,\"trace_sequence\":3}\n"
            "WORKER_RING {\"kind\":\"retail_queue_wait\",\"call\":1,\"head\":3,\"tail\":21,\"predicate_byte\":20,\"trace_sequence\":4}\n"
            "WORKER_RING {\"kind\":\"retail_queue_wait_return\",\"call\":1,\"return_r3\":0,\"trace_sequence\":5}\n"
            "WORKER_RING {\"kind\":\"ke_wait_return\",\"wait_call\":7,\"return_status\":0,\"trace_sequence\":6}\n"
            "WORKER_RING {\"kind\":\"queue_field_write\",\"field\":\"software_tail\",\"before\":21,\"after\":22,\"trace_sequence\":7}\n"
            "WORKER_RING_EVENT_WRITE_SHD {\"index\":3,\"guest_address\":\"0x17af4000\",\"packet_value\":\"0x00000009\",\"head_before\":7,\"packet_bytes\":\"c00258000000000317af400200000009\"}\n"
            "WORKER_RING_STOP_DIAGNOSTICS {\"software_gpu_queue\":{\"head\":19,\"tail\":21,\"predicate_byte\":20},\"guest_main_thread\":{\"current_guest_pc_context_slot\":2211449680}}\n",
            encoding="utf-8",
        )
        recovered = CAPTURE.recover_trace_events_from_log(trace_log, "shift-native")
        assert recovered and recovered["partial_capture"]
        assert recovered["bink_target"]["progress"] == 281
        assert recovered["events"]["counter_write_events"][0]["after"] == 0
        assert recovered["events"]["scene_function_return_events"][0]["return_value"] == 0
        assert recovered["events"]["retail_queue_wait_events"][0]["head"] == 3
        assert recovered["events"]["retail_queue_wait_return_events"][0]["call"] == 1
        assert recovered["events"]["ke_wait_return_events"][0]["wait_call"] == 7
        assert recovered["events"]["queue_field_write_events"][0]["after"] == 22
        assert recovered["counts"]["event_write_shd_packet_events"] == 1
        assert recovered["event_write_shd_packet_events"][0]["packet_value"] == "0x00000009"
        assert recovered["worker_queues"] == [0xB7368BE0]
        assert recovered["stop_context"]["diagnostics"]["software_gpu_queue"] == {
            "head": 19, "tail": 21, "predicate_byte": 20,
        }
        assert recovered["stop_context"]["diagnostics"]["guest_main_thread"][
            "current_guest_pc_context_slot"
        ] == 2211449680
        bink_log = 'WORKER_RING_BINK {"elapsed_seconds":42.125,"target":281,"progress":281}\n'
        assert CAPTURE.bink_complete_elapsed(bink_log) == 42.125
        assert not CAPTURE.input_trigger_ready(bink_log, "bink_complete", 42.624, 0.5)
        assert CAPTURE.input_trigger_ready(bink_log, "bink_complete", 42.625, 0.5)
        wall_clock_bink_log = (
            'WORKER_RING {"kind":"bink_complete","elapsed_seconds":42.125,'
            '"wall_clock_epoch_ms":100000}\n'
        )
        assert CAPTURE.bink_complete_wall_clock_epoch_ms(wall_clock_bink_log) == 100000
        assert not CAPTURE.input_trigger_ready(
            wall_clock_bink_log, "bink_complete", 42.625, 0, 99999,
        )
        assert CAPTURE.input_trigger_ready(
            wall_clock_bink_log, "bink_complete", 42.625, 0, 100000,
        )
        assert not CAPTURE.input_trigger_ready(
            wall_clock_bink_log, "bink_complete", 42.625, 1, 100999,
        )
        assert CAPTURE.input_trigger_ready(
            wall_clock_bink_log, "bink_complete", 42.625, 1, 101000,
        )
        assert not CAPTURE.input_trigger_ready(bink_log, "scene_gate", 43.0, 0)
        assert CAPTURE.input_trigger_ready(
            bink_log + "GPU_COMPARE_INPUT_GATE\n", "scene_gate", 43.0, 0,
        )
        trace_source = Path(__file__).with_name(
            "trace_linux_post_bink_worker_route_v45_ordered_route_20261027.gdb"
        ).read_text(encoding="utf-8")
        assert 'SceneFunction("sub_82DDC6F0")' in trace_source
        assert 'maybe_emit_input_gate(self.symbol, manager_snapshot)' in trace_source
        assert 'RetailQueueWait()' in trace_source
        assert 'class RetailQueueWaitReturn(gdb.FinishBreakpoint)' in trace_source
        assert 'class KeWaitReturn(gdb.FinishBreakpoint)' in trace_source
        assert 'RetailQueueWaitReturn(' in trace_source
        assert 'KeWaitReturn(' in trace_source
        assert 'capture_stop_diagnostics()' in trace_source
        assert 'WORKER_RING_STOP_DIAGNOSTICS ' in trace_source
        assert 'class QueueFieldWrite(gdb.Breakpoint)' in trace_source
        assert 'arm_queue_field_watches(' in trace_source
        assert '"completion_predicate"' in trace_source
        assert 'guest_queue_field_aliases(base, head_pointer)' in trace_source
        assert 'alias_probe == "software_head"' in trace_source
        assert 'alias_probe == "physical_head_counter"' in trace_source
        assert 'watch_keys = ("counter_watch", "worker72_watch") if alias_probe == "software_head" else ("worker72_watch",)' in trace_source
        assert 'state["counter_watch"].enabled = True' in trace_source
        assert 'or (32 <= queue_depth <= 64 and not snapshot["completion_mask_set"])' in trace_source
        assert '"virtual_a"' in trace_source and '"virtual_c"' in trace_source
        assert '"virtual_e"' in trace_source and '"physical"' in trace_source
        assert '"software_queue": {' in trace_source
        assert 'and all(snapshot["child_words_264"])' in trace_source

    wait_summary = MODULE.retail_queue_wait_summary({"events": {
        "retail_queue_wait_events": [
            {"call": 1, "elapsed_seconds": 4.0, "head": 3, "tail": 21,
             "predicate_byte": 0x14, "completion_mask_set": False},
            {"call": 2, "elapsed_seconds": 5.0, "head": 3, "tail": 21,
             "predicate_byte": 0x14, "completion_mask_set": False},
            {"call": 3, "elapsed_seconds": 6.0, "head": 4, "tail": 21,
             "predicate_byte": 0x16, "completion_mask_set": True},
        ],
    }})
    assert wait_summary["sample_count"] == 3
    assert wait_summary["first"]["head"] == 3
    assert wait_summary["last"]["completion_mask_set"] is True
    assert len(wait_summary["distinct_conditions"]) == 2

    lifecycle = MODULE.retail_queue_wait_lifecycle({"events": {
        "retail_queue_wait_events": [
            {"call": 1, "thread_name": "Core 0/0: Main ", "head": 3},
            {"call": 2, "thread_name": "Core 0/0: Main ", "head": 4},
        ],
        "retail_queue_wait_return_events": [
            {"call": 1, "thread_name": "Core 0/0: Main ", "return_r3": 0},
        ],
    }})
    assert lifecycle["entry_count"] == 2
    assert lifecycle["return_count"] == 1
    assert lifecycle["first_unreturned_entry"]["call"] == 2

    ke_lifecycle = MODULE.ke_wait_lifecycle({"events": {
        "event_call_events": [
            {"symbol": "KeWaitForSingleObject", "wait_call": 7,
             "thread_name": "Core 0/0: Main ", "event": 0xB7368C00},
            {"symbol": "KeSetEvent", "thread_name": "Core 0/0: Main "},
        ],
        "ke_wait_return_events": [
            {"wait_call": 7, "thread_name": "XThreadWorker", "return_status": 0x102,
             "duration_seconds": 0.025},
        ],
    }})
    assert ke_lifecycle["entry_count"] == 1
    assert ke_lifecycle["return_count"] == 1
    assert ke_lifecycle["unreturned_entry_count"] == 0
    assert ke_lifecycle["return_status_counts"] == {"0x00000102": 1}
    assert ke_lifecycle["return_duration_seconds"] == {"min": 0.025, "max": 0.025}

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        pulse_masks = [0, 0x0010, 0, 0x1000, 0, 0x0010, 0]
        left = make_run(root, "xenos", baseline, host_masks=pulse_masks)
        right = make_run(root, "shift-native", baseline, elapsed_shift=15.0, host_masks=pulse_masks)
        result = MODULE.compare(left, right)
        assert result["first_post_bink_divergence"] is None
        assert result["first_trace_order_difference"] is None
        assert result["input_comparability"]["same_three_pulse_profile_delivered"]

    # Same producer call shape with differing words is a GPU-submission
    # candidate, not a claim that the unknown tag payload is semantically wrong.
    submission_common = {
        "kind": "producer_call", "trace_sequence": 2,
        "producer_call": 1, "id": 1, "tag": 11,
        "delta": 0, "caller_lr": 0x823B2EAC,
        "routes": [{"symbol": "sub_823B2AF0", "caller_lr": 0x823B2CD0}],
        "record_words": [0, 0, 0, 0],
    }
    submission_left = [baseline[0], submission_common]
    submission_right = [baseline[0], {**submission_common, "record_words": [1, 2, 3, 4]}]
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", submission_left)
        right = make_run(root, "shift-native", submission_right)
        candidate = MODULE.compare(left, right)["first_submission_record_difference_candidate"]
        assert candidate["kind"] == "producer_record_words_mismatch_candidate"
        assert candidate["producer_call_ordinal"] == 1
        assert candidate["tag"] == 11
        assert candidate["route"] == ["sub_823B2AF0"]
        assert candidate["xenos_record_words"] == [0, 0, 0, 0]
        assert candidate["shift_native_record_words"] == [1, 2, 3, 4]
        assert "not established" in candidate["interpretation"]

    # A declared/gated input profile is not evidence that XInput received it.
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline, host_masks=[0, 0x0010, 0, 0x1000, 0, 0x0010, 0])
        right = make_run(root, "shift-native", baseline, host_masks=[0])
        result = MODULE.compare(left, right)
        assert not result["input_comparability"]["same_three_pulse_profile_delivered"]
        assert result["input_comparability"]["delivered_profiles"]["shift_native"] == []

    changed = [dict(row) for row in baseline]
    changed[1]["state_348"] = 0
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline)
        right = make_run(root, "shift-native", changed)
        comparison = MODULE.compare(left, right)
        diff = comparison["first_post_bink_divergence"]
        assert diff is not None and diff["kind"] in ("replace", "delete", "insert")
        assert diff["xenos_events"][0]["kind"] == "scene_state"
        assert diff["shift_native_events"][0]["state_348"] == 0
        assert comparison["first_semantic_divergence"] == diff

    # Compare original scene-transition return values while normalizing
    # relocated guest object pointers and scene-manager cadence counters.
    transition_return = {
        "kind": "scene_function_return", "trace_sequence": 4,
        "function": "sub_82FD5658", "call": 1,
        "arguments_r3_r8": [0x831E6184, 0, 0, 0, 0, 0],
        "return_value": 0,
        "function_state_at_return": {"state_word_plus4": 2},
        "scene_manager_at_return": {
            "object": 0x831E6184, "list_count_36": 2,
            "state_348": 0, "update_count_356": 0,
            "child_words_264": [0x81234000, 0, 0, 0],
        },
    }
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline)
        right = make_run(root, "shift-native", baseline)
        for run_dir, event in (
            (left, transition_return),
            (right, {**transition_return, "return_value": 1,
                     "scene_manager_at_return": {
                         **transition_return["scene_manager_at_return"],
                         "object": 0x831F7000,
                         "child_words_264": [0x82001000, 0, 0, 0],
                         "update_count_356": 99,
                     }}),
        ):
            events_path = run_dir / "events.json"
            events = json.loads(events_path.read_text(encoding="utf-8"))
            events["events"]["scene_function_return_events"] = [event]
            events_path.write_text(json.dumps(events), encoding="utf-8")
        comparison = MODULE.compare(left, right)
        candidate = comparison["frontend_transition_return_divergence_candidate"]
        assert candidate is not None
        assert candidate["xenos_events"][0]["function"] == "sub_82FD5658"
        assert candidate["xenos_events"][0]["return_value"] == 0
        assert candidate["shift_native_events"][0]["return_value"] == 1
        assert candidate["shift_native_events"][0]["scene_manager"]["child_slots_populated"] == [True, False, False, False]
        assert "first_semantic_divergence" in comparison  # transition result remains a candidate

    void_return_rows = {
        "schema": "shift.xbox360.linux-gpu-backend-events.v1",
        "events": {
            "bink_complete_events": [{"kind": "bink_complete", "trace_sequence": 1}],
            "scene_function_return_events": [{
                **transition_return,
                "trace_sequence": 2,
                "function": "sub_82F38158",
                "return_value": 0,  # undefined r3 from a void PPC function
            }],
        },
    }
    void_sequence = MODULE.frontend_transition_return_sequence(void_return_rows)
    assert void_sequence[0]["return_value"] is None
    assert MODULE.frontend_transition_function_counts(void_return_rows) == {
        "sub_82F33810": 0, "sub_82F38158": 0, "sub_82FD5658": 0,
    }

    transition_trace = CAPTURE_SCRIPT.with_name(
        "trace_linux_post_bink_worker_route_v45_ordered_route_20261027.gdb"
    ).read_text(encoding="utf-8")
    for symbol in ("sub_82F38158", "sub_82FD5658", "sub_82F33810"):
        assert f'SceneFunction("{symbol}")' in transition_trace
    assert '"scene_function_return_events"' in transition_trace

    missing = [baseline[0], baseline[2]]
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline)
        right = make_run(root, "shift-native", missing)
        diff = MODULE.compare(left, right)["first_post_bink_divergence"]
        assert diff is not None and diff["kind"] in ("delete", "insert")
        assert diff["xenos_event_range"] != diff["shift_native_event_range"]

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline)
        right = make_run(root, "shift-native", baseline)
        metadata_path = right / "run_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["xex_sha256"] = "0" * 64
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        try:
            MODULE.compare(left, right)
        except ValueError as exc:
            assert "required input identity" in str(exc)
        else:
            raise AssertionError("different XEX hashes were accepted as a pair")

    # Guest pointer relocation and callback interleaving must not masquerade
    # as a scene-state change. Keep the global ordering mismatch visible as a
    # candidate while reporting no semantic scene divergence.
    left_rows = [
        {"kind": "bink_complete", "trace_sequence": 1, "target": 281, "progress": 281},
        {"kind": "event_call", "trace_sequence": 2, "symbol": "KeWaitForSingleObject"},
        {"kind": "scene_state", "trace_sequence": 3, "state_348": 1, "list_count_36": 1,
         "child_words_264": [0x80001000, 0, 0, 1], "object": 0x80002000},
    ]
    right_rows = [
        {"kind": "bink_complete", "trace_sequence": 1, "target": 281, "progress": 281},
        {"kind": "scene_state", "trace_sequence": 2, "state_348": 1, "list_count_36": 1,
         "child_words_264": [0x90001000, 0, 0, 1], "object": 0x90002000},
        {"kind": "event_call", "trace_sequence": 3, "symbol": "KeSetEvent"},
    ]
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", left_rows)
        right = make_run(root, "shift-native", right_rows)
        result = MODULE.compare(left, right)
        assert result["first_game_state_divergence"] is None
        assert result["first_semantic_divergence"] is None
        assert result["first_trace_order_difference"] is not None

    # Counter changes are compared as a serialized guest-field operation
    # sequence, independent of their wall-clock spacing.
    counter_prefix = [1, -1, 1, -1, 1]
    xenos_counter_rows = [
        {"kind": "bink_complete", "trace_sequence": 1, "target": 281, "progress": 281},
        *[
            {"kind": "counter_write", "trace_sequence": index + 2,
             "before": 0, "after": 0, "signed_delta": delta,
             "guest_address": 0xB7368A04,
             "host_stack": ["sub_823B31A0"] if delta > 0 else ["sub_823B85D0"]}
            for index, delta in enumerate([*counter_prefix, 1, -1])
        ],
    ]
    native_counter_rows = [
        {"kind": "bink_complete", "trace_sequence": 1, "target": 281, "progress": 281},
        *[
            {"kind": "counter_write", "trace_sequence": index + 2,
             "before": 0, "after": 0, "signed_delta": delta,
             "guest_address": 0xB7368A04,
             "host_stack": ["sub_823B31A0"] if delta > 0 else ["sub_823B85D0"]}
            for index, delta in enumerate([*counter_prefix, -1, -1])
        ],
    ]
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", xenos_counter_rows)
        right = make_run(root, "shift-native", native_counter_rows)
        result = MODULE.compare(left, right)
        diff = result["first_manager_counter_divergence"]
        assert diff["guest_field"] == "manager+11012"
        assert diff["common_prefix_writes"] == 5
        assert diff["xenos"]["delta"] == 1
        assert diff["shift_native"]["delta"] == -1
        assert result["first_semantic_divergence"] == diff

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", [baseline[0]])
        right = make_run(root, "shift-native", [
            baseline[0],
            {"kind": "counter_write", "trace_sequence": 2,
             "before": 0, "after": 0xFFFFFFFF, "signed_delta": -1,
             "guest_address": 0xB7368A04, "host_stack": ["sub_823B85D0"]},
        ])
        diff = MODULE.compare(left, right)["first_manager_counter_divergence"]
        assert diff["kind"] == "manager_counter_length_mismatch"
        assert diff["xenos"] is None
        assert diff["shift_native"]["delta"] == -1

    # Link a counter decrement to its exact worker completion and parent
    # dequeue, then retain only a pointer-and-trace-window match for the
    # nested source-1 callback. This is not a PM4 interrupt causal join.
    parent_record = 0xC95F4200
    context = MODULE.counter_operation_context({"events": {
        "completion_events": [{
            "kind": "completion", "phase": "return", "trace_sequence": 2158,
            "counter_before": 1, "counter_after": 0, "token": 0xC0000000,
            "signed_delta": -1, "parent_dequeue_id": 816,
            "parent_record": parent_record, "ring_queue": 0xB7368BE0,
        }],
        "dequeue_events": [{
            "kind": "dequeue", "id": 816, "queue": 0xB7368BE0,
            "phase": "return", "consumer_before": 1, "consumer_after": 2,
            "producer_before": 2, "producer_after": 4, "slot_value": parent_record,
        }],
        "source1_callback_events": [{
            "kind": "source1_callback", "trace_sequence": 2155,
            "entry_ordinal": 170, "callback_function": 0x823B8C60,
            "callback_data": parent_record, "thread": 11,
            "thread_name": "SHIFT Native GP",
        }],
    }}, {
        "trace_sequence": 2159, "before": 1, "after": 0,
        "host_stack": ["#0 sub_823B85D0"],
    })
    assert context is not None
    assert context["parent_dequeue"]["id"] == 816
    assert context["parent_dequeue"]["slot_value"] == parent_record
    assert context["nearby_source1_callbacks_matching_parent_record"][0]["callback_data"] == parent_record
    assert "does not join the callback to a particular PM4 interrupt" in context["join_scope"]

    with tempfile.TemporaryDirectory() as temp:
        ring_log = Path(temp) / "ring.log"
        ring_log.write_text(
            "[2026-10-28 03:36:57.391] [info] shift-native: ring trace PM4_INTERRUPT #0 source=1 generation=1 "
            "batch_rptr=2 batch_wptr=9 ring_guest=B7365F00 packet=10 "
            "packet_source=12345678+64 cpu_mask=0x04 dispatched_cpu_mask=0x04 "
            "callback_dispatches=[cpu2:callback=0x823B37B8,data=0xB7365F00,status=returned]\n",
            encoding="utf-8",
        )
        records, malformed = CAPTURE.parse_ring_interrupt_log(ring_log)
        assert malformed == 0 and len(records) == 1
        assert records[0]["packet_ordinal"] == 10
        assert records[0]["source_ib_byte_offset"] == 64
        assert records[0]["callbacks"] == [
            {"cpu": 2, "callback": 0x823B37B8, "data": 0xB7365F00, "status": "returned"}
        ]
        summary = MODULE.gpu_ring_trace_summary({"gpu_ring_interrupt_events": records})
        assert summary["record_count"] == 1
        assert summary["callback_dispatches"][0]["callback"] == "0x823B37B8"
        nearby = MODULE.nearby_gpu_ring_interrupts(
            {"gpu_ring_interrupt_events": [{**records[0], "timestamp_epoch_ms": 1012}]},
            {"wall_clock_epoch_ms": 1000},
        )
        assert nearby[0]["delta_ms_from_counter_write"] == 12
        assert nearby[0]["packet_ordinal"] == 10

        guest_entry = {
            "kind": "source1_callback",
            "trace_sequence": 21,
            "wall_clock_epoch_ms": 1004,
            "entry_ordinal": 7,
            "thread": 2,
            "thread_name": "XThreadGpu",
            "guest_lr": 0x823B34A0,
            "arguments_r3_to_r10": [1, 0xB7365B00, 0, 0, 0, 0, 0, 0],
            "callback_function": 0x823A4758,
            "callback_data": 0x208,
            "callback_bit_index": 2,
            "callback_bit_mask": 4,
            "manager_flags_before": 4,
            "manager_flag_bit_set_before": True,
            "manager_counter_before": 1,
            "manager_words_10904_to_1091c": [4, 0, 1, 0, 0, 0, 0],
        }
        nearby_callbacks = MODULE.nearby_source1_guest_callbacks(
            {"events": {"source1_callback_events": [guest_entry]}},
            {"wall_clock_epoch_ms": 1000},
        )
        assert nearby_callbacks[0]["entry_ordinal"] == 7
        assert nearby_callbacks[0]["delta_ms_from_counter_write"] == 4
        assert nearby_callbacks[0]["manager_flag_bit_set_before"]

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline)
        right = make_run(root, "shift-native", baseline, gate=False)
        result = MODULE.compare(left, right)
        assert not result["input_comparability"]["gates_match"]
        assert not result["input_comparability"]["same_three_pulse_profile_delivered"]

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline, host_masks=[0x1010])
        right = make_run(root, "shift-native", baseline, host_masks=[0x1010])
        observed = MODULE.compare(left, right)["input_path"]["xenos"]["observed_buttons"]
        assert observed["Start"]["host_xinput_mask_seen"]
        assert observed["A"]["host_xinput_mask_seen"]

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline)
        right = make_run(root, "shift-native", [], gate=False, bink=False, mapped=False)
        result = MODULE.compare(left, right)
        assert result["mapped_artifact_verification"]["shift-native"]["runtime"] == \
            "not_captured_before_bink_or_fault"
        assert not result["milestones"]["shift_native"]["bink_281_of_281"]
        assert result["first_semantic_divergence"]["kind"] == "milestone_mismatch"
        assert result["first_semantic_divergence"]["milestone"] == "bink_281_of_281"

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        left = make_run(root, "xenos", baseline)
        right = make_run(root, "shift-native", baseline)
        log_dir = right / "bin" / "logs"
        log_dir.mkdir(parents=True)
        draws = []
        for packet in range(14):
            draws.append(
                f"draw(packet={packet},index={packet},draw_registers={{valid_mask=0x1ffff,"
                "surface=0x100,color=0x200,depth=0x300,mode=0x4,depth_control=0x1,"
                "color_mask=0xf,stencil_refmask=0xff,screen_scissor=[0x0,0x20002000],"
                "window_scissor=[0x0,0x20002000]},"
                "raster={color_base=0x0,depth_base=0x2d0,guest_format=1,color_format=1,"
                "depth_format=0,extent=1280x720,pitch=640,samples=4,depth_only=0,"
                "color_mask=0xf,depth_test=1,depth_write=1,stencil_test=1,depth_control=0x8777,"
                "stencil_refmask=0xff0000,scissor=1[0,0..1280,720]})"
            )
        operations = ";".join([
            *draws,
            "copy(packet=72,source=2560x1440,source_regs=0x100/0x200/0x300/0x4,"
            "destination=0x975e000,1280x720,format=26/2,endian=1,exp_bias=11,samples=6,"
            "clear=1/1,source_target={ready:1,extent=2560x1440,samples=4},"
            "swap_rb=0,shaders=prepared,source_geometry=captured,topology=2,indices=3,"
            "auto_index=1,vertex_bytes=24,index_bytes=0)",
            "copy(packet=86,source=1280x720,source_regs=0x100/0x200/0x300/0x4,"
            "destination=0x975e000,1280x720,format=6/0,endian=0,exp_bias=0,samples=0,"
            "clear=0/0,source_target={ready:1,extent=1280x720,samples=1},"
            "swap_rb=1,shaders=prepared,source_geometry=captured,topology=2,indices=3,"
            "auto_index=1,vertex_bytes=24,index_bytes=0)",
        ])
        (log_dir / "nfs_shift_001.log").write_text(
            "[2026-10-28 04:16:12.386] [info] shift-native: captured ordered PM4 operations: "
            + operations + "\n"
            + "[2026-10-28 04:16:12.387] [info] shift-native: captured ordered PM4 operations: "
            + "draw(packet=26,index=26,raster={color_base=0x0,depth_base=0x2d0,"
              "guest_format=1,color_format=1,depth_format=0,extent=1280x720,pitch=640,"
              "samples=4,depth_only=0,color_mask=0xf,depth_test=1,depth_write=1,"
              "stencil_test=1,scissor=1[0,0..1280,720]});"
              "draw(packet=27,index=27,raster={color_base=0x0,depth_base=0x2d0,"
              "guest_format=0,color_format=0,depth_format=0,extent=1280x720,pitch=1280,"
              "samples=1,depth_only=0,color_mask=0xf,depth_test=0,depth_write=0,"
              "stencil_test=0,scissor=1[0,0..1280,720]});"
              "copy(packet=52,source=1280x720,source_regs=0x14000500/0x0/0x2d0/0x6,"
              "destination=0x975e000,1280x720,format=6/0,endian=0,exp_bias=0,samples=0,"
              "clear=0/0,source_target={ready:1,extent=1280x720,samples=1,color_base=0x0,"
              "depth_base=0x2d0,guest_format=0},swap_rb=1,shaders=prepared,"
              "source_geometry=captured,topology=2,indices=0,auto_index=1,"
              "vertex_bytes=24,index_bytes=0)\n"
            + "shift-native: captured Copy/Convert PM4 geometry packet #72 topology=2\n"
            + "shift-native: captured Copy/Convert PM4 geometry packet #86 topology=2\n"
            + "[2026-10-28 04:16:12.400] [info] shift-native: resolved captured retail draw #6202 "
            "(Vulkan readback target frame 322) elapsed_ms=37765\n"
            "  topology=2 autoindex=1 index_count=3 index_guest=0x0 raster=1280x720 "
            "scissor=[0,0,1280,720] depth={test:1,write:1,stencil:1}\n"
            "  vertex fetch: guest=0x96ea938 descriptor={0x96ea93b,0x10000056} endian=2 "
            "stride=28 payload_bytes=84 attributes=2\n"
            "  normalized_vertex_payload_fnv1a=0xc6201a9b785f89c7\n"
            "  raw_vertices_dump=/tmp/native-draw.frame322.draw6202.vertices.bin bytes=84 "
            "fnv1a=0xc6201a9b785f89c7\n"
            "  raw_indices_dump=/tmp/native-draw.frame322.draw6202.indices.bin bytes=0 "
            "fnv1a=0xcbf29ce484222325\n"
            "[2026-10-28 04:16:13.000] [info] shift-native: unresolved captured draw #10 "
            "topology=2 autoindex=true count=24 raster=true inputs=true translated=true: "
            "glslang parse failed: ERROR: 0:61: 'sampled_0' : redefinition\n"
            "[2026-10-28 04:16:14.000] [info] shift-native: unresolved captured draw #10 "
            "topology=2 autoindex=true count=24 raster=true inputs=true translated=true: "
            "glslang parse failed: ERROR: 0:61: 'sampled_0' : redefinition\n"
            "[2026-10-28 04:16:15.000] [info] shift-native: unresolved captured draw #12 "
            "topology=2 autoindex=true count=24 raster=true inputs=false translated=false: "
            "unsupported control-flow opcode 7 at instruction 1\n",
            encoding="utf-8",
        )
        result = MODULE.compare(left, right)
        summary = result["native_renderer_logs"]["shift_native"]
        assert summary["copy_convert_geometry_packet_72_record_count"] == 1
        assert summary["max_copy_convert_geometry_packet"] == 86
        progression = summary["packet_72_progression"]
        assert progression["packet_72_geometry_captured"]
        assert progression["highest_ordered_copy_convert_packet"] == 86
        assert progression["same_snapshot_contains_packet_72_and_a_later_packet"]
        refresh = summary["packet_0_fourteen_draw_refreshes"]
        assert len(refresh) == 1
        assert [item["packet"] for item in refresh[0]["draws"]] == list(range(14))
        assert refresh[0]["draws"][0]["raster"]["extent"] == [1280, 720]
        assert refresh[0]["draws"][0]["raster"]["scissor"] == "0,0..1280,720"
        assert [item["packet"] for item in refresh[0]["copy_converts"]] == [72, 86]
        alias_candidates = summary["captured_p2_packet27_alias_candidates"]
        assert summary["captured_p2_packet27_alias_candidate_count"] == 1
        assert len(alias_candidates) == 1
        assert alias_candidates[0]["observable_capture_tuple_matches_p2_packet27_contract"]
        assert not alias_candidates[0]["edram_tile_alias_mapping_verified_by_p1"]
        selected = summary["selected_frame_draw_captures"]
        assert len(selected) == 1 and selected[0]["frame"] == 322
        assert selected[0]["draw_count"] == 1
        assert selected[0]["draws"][0]["vertex_payload_bytes"] == 84
        assert selected[0]["draws"][0]["raw_index_dump"]["size_bytes"] == 0
        unresolved = summary["unresolved_draw_rejections"]
        assert [row["draw_ordinal"] for row in unresolved] == [10, 12]
        assert unresolved[0]["occurrences"] == 2
        assert unresolved[0]["raster_ready"] and unresolved[0]["inputs_ready"]
        assert unresolved[0]["translated"]
        assert "sampled_0" in unresolved[0]["rejection_reason"]
        assert unresolved[1]["rejection_reason"] == "unsupported control-flow opcode 7 at instruction 1"

    print("GPU backend comparator aligns submission payloads, manager counters and scene state separately from trace interleaving")


if __name__ == "__main__":
    main()
