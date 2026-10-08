from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_control_timing_frontier.json"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_CONTROL_TIMING_FRONTIER.md"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_authority_and_inputs_are_pinned() -> None:
    payload = _load()
    assert payload["format"] == "SHIFT.Process1Controller1ControlTimingFrontier/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"
    assert payload["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert payload["authority"]["retail_source_sha256"] == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert payload["authority"]["new_machine_or_source_claims_in_this_join"] is False
    assert "SHIFT.Process1Controller1BManagerQueueWake/1" in payload["inputs"]
    assert "SHIFT.Process1Controller1ApcSourceInventory/1" in payload["inputs"]
    assert "SHIFT.Process1Fun006333f0LayoutExclusion/1" in payload["inputs"]


def test_direct_controller_timing_surface_is_closed() -> None:
    payload = _load()
    closed = payload["closed_surface"]
    assert closed["controller1_worker"] == "FUN_00662880"
    assert closed["worker_model"] == "poll queue -> manager dispatch -> SleepEx(10, TRUE) -> repeat"
    assert closed["bmanager_messages"] == [3, 4, 5, 6, 7]
    assert closed["normal_queue_init_argument"] == 1
    assert closed["normal_queue_flags_after_init"] == 7
    assert closed["msgqueue_event_bit"] == 8
    assert closed["normal_message_enqueue_interrupts_sleep_via_queue_event"] is False
    assert closed["known_readfileex_writefileex_targets_controller1"] is False
    assert closed["waitable_timer_completion_targets_controller1"] is False
    assert closed["winsock_completion_targets_controller1"] is False
    assert closed["direct_named_controller1_manager_path_to_readfileex_or_writefileex"] is False
    assert closed["known_imported_completion_source_targets_controller1"] is False
    assert closed["source_visible_generic_queue_alias_frontier_closed"] is True


def test_remaining_frontier_stays_fail_closed() -> None:
    payload = _load()
    residual = payload["remaining_timing_frontier"]
    assert residual["indirect_virtual_or_function_pointer_apc_path_ruled_out"] is False
    assert residual["indirect_or_native_apc_injection_ruled_out"] is False
    assert residual["render_or_present_phase_lock_proven"] is False
    assert residual["render_phase_lock_required_to_continue_p1_3_control_provenance"] is False
    adjudication = payload["adjudication"]
    assert adjudication["controller1_direct_control_timing_surface_ready"] is True
    assert adjudication["controller1_control_timing_complete"] is False
    assert adjudication["p1_3_complete"] is False
    assert adjudication["retail_control_chain_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_documentation_preserves_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "SleepEx(10, TRUE)",
        "Base File: Async Thread",
        "indirect/native APC injection",
        "render-frame phase locking",
        "P1.3 complete: **false**",
        "external-provider count: **7**",
        "NEXT_STEP",
    ):
        assert token in text
