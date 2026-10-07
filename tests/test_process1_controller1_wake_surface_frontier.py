from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_wake_surface_frontier.json"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_WAKE_SURFACE_FRONTIER.md"
PACING = ROOT / "evidence/process1_controller1_alertable_pacing.json"
CADENCE_JOIN = ROOT / "evidence/process1_controller1_retail_cadence_join.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wake_surface_frontier_is_pinned_pc_retail() -> None:
    payload = _load(EVIDENCE)
    assert payload["format"] == "SHIFT.Process1Controller1WakeSurfaceFrontier/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["xbox_recomp_required"] is False


def test_controller1_queue_is_poll_only_on_proven_init_path() -> None:
    payload = _load(EVIDENCE)
    queue = payload["controller_queue"]

    assert queue["base_controller_init"] == "FUN_006551b0"
    assert queue["base_event_mode_flag_offset"] == "0x50"
    assert queue["base_event_mode_flag_initial_value"] == 0
    assert queue["thread_entry"] == "FUN_00649b10"
    assert queue["thread_entry_mode_when_flag_zero"] == 1
    assert queue["queue_constructor"] == "FUN_0064ff40"
    assert queue["mode_1_queue_state_bits"] == "0x4"
    assert queue["queue_event_bit"] == "0x8"
    assert queue["mode_1_has_queue_event"] is False
    assert queue["enqueue_function"] == "FUN_00650350"
    assert queue["enqueue_signals_event_only_when_bit_0x8"] is True
    assert queue["worker"] == "FUN_00662880"
    assert queue["worker_dequeue"] == "FUN_006550a0"
    assert queue["worker_dequeue_is_nonblocking_poll"] is True
    assert queue["worker_uses_queue_event_wait"] is False
    assert queue["ordinary_message_enqueue_is_controller1_wake_signal"] is False


def test_alertable_completion_surface_stays_fail_closed() -> None:
    payload = _load(EVIDENCE)
    surface = payload["alertable_completion_surface"]

    assert surface["sleep_wrapper"] == "FUN_00649780"
    assert surface["sleep_api"] == "SleepEx"
    assert surface["requested_timeout_ms"] == 10
    assert surface["alertable"] is True
    assert surface["source_visible_QueueUserAPC_call_count"] == 0
    assert surface["source_visible_ReadFileEx_call_count"] == 2
    assert surface["source_visible_WriteFileEx_call_count"] == 2
    assert surface["generic_read_completion_routine"] == "lpCompletionRoutine_006553e0"
    assert surface["generic_write_completion_routine"] == "lpCompletionRoutine_00655410"
    assert surface["controller1_worker_direct_ReadFileEx_calls"] == 0
    assert surface["controller1_worker_direct_WriteFileEx_calls"] == 0
    assert surface["all_indirect_alertable_completion_sources_excluded"] is False


def test_frontier_joins_existing_pacing_and_cadence_without_frame_promotion() -> None:
    payload = _load(EVIDENCE)
    pacing = _load(PACING)
    cadence_join = _load(CADENCE_JOIN)

    assert payload["inputs"]["pacing_contract"] == pacing["format"]
    assert payload["inputs"]["cadence_join_contract"] == cadence_join["format"]
    assert pacing["worker_pacing"]["worker"] == payload["controller_queue"]["worker"]
    assert pacing["worker_pacing"]["requested_milliseconds"] == 10
    assert cadence_join["timing_domains"]["controller_worker"]["is_render_cadence"] is False

    render = payload["render_presentation_join"]
    assert render["ordinary_controller_message_queue_is_frame_wake"] is False
    assert render["direct_render_or_present_to_controller1_wake_proven"] is False
    assert render["render_frame_phase_lock_proven"] is False
    assert render["one_worker_iteration_per_rendered_frame_proven"] is False
    assert render["one_physics_dispatch_per_rendered_frame_proven"] is False


def test_documentation_keeps_queue_poll_and_alertable_completion_distinct() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "does not create an event-backed message queue" in text
    assert "ordinary enqueue" in text
    assert "SleepEx(10, TRUE)" in text
    assert "QueueUserAPC" in text
    assert "ReadFileEx" in text
    assert "WriteFileEx" in text
    assert "global alertable completion surface open" in text
    assert "render/presentation join remains fail-closed" in text
