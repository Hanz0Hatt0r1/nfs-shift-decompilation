from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase739_evidence_closes_only_selected_bmw_world_position() -> None:
    evidence = json.loads(
        _read("evidence/fun_00765c40_selected_bmw_world_position_join.json")
    )
    assert evidence["format"] == "SHIFT.Fun00765c40SelectedBMWWorldPosition/1"
    assert evidence["ready"] is True
    assert evidence["selected_body_domain"]["body_count"] == 11
    assert evidence["runtime_order"]["observer_runs_before_anchor_sequence"] is True
    assert evidence["runtime_order"]["pass1_reads_post_pass0_half_step_body"] is True
    assert evidence["external_fun_00765c40_remaining"]["world_position_selected_bmw"] is False
    assert evidence["external_fun_00765c40_remaining"]["load_terms"] is True
    assert evidence["external_fun_00765c40_remaining"]["cached_handle"] is True
    assert evidence["external_fun_00765c40_remaining"]["miss_fallback"] is True
    assert evidence["provider_frontier"]["external_provider_count_after"] == 7
    assert evidence["provider_frontier"]["provider_count_reduced"] is False


def test_phase739_composes_existing_proofs_without_rederiving_them() -> None:
    header = _read(
        "native_runtime/include/shift_fun_00765c40_selected_bmw_world_position.hpp"
    )
    assert "SHIFT.Fun00765c40SelectedBMWWorldPosition/1" in header
    assert "compose_fun_007618f0_input_from_current_bmw_wheel_bodies" in header
    assert "selected_bmw_m3_e36_fun_007618f0_source" in header
    assert "execute_fun_007618f0_local_sample_producer" in header
    assert "execute_fun_00765c40_world_position_transform" in header
    assert "kBmwM3E36RetailBodyCount * kBodyRecordSize" in header
    assert "rejected non-BMW BODY domain" in header


def test_phase739_reuses_pre_anchor_current_body_observer_order() -> None:
    composed = _read("native_runtime/src/fun_00770e80_composed_anchor_chain.cpp")
    observer_call = "callbacks.current_body_observer(result.final_body_bytes)"
    anchor_call = "execute_fun_0076d100_required_anchor_sequence"
    half_step_call = "execute_fun_00765470_machine_longitudinal_feedback_join"
    assert observer_call in composed
    assert anchor_call in composed
    assert half_step_call in composed
    assert composed.index(observer_call) < composed.index(anchor_call) < composed.index(half_step_call)

    motion_header = _read(
        "native_runtime/include/shift_fun_00770e80_motion_read_machine_input_provider_chain.hpp"
    )
    motion_source = _read(
        "native_runtime/src/fun_00770e80_motion_read_machine_input_provider_chain.cpp"
    )
    contact_header = _read(
        "native_runtime/include/shift_fun_00770e80_contact_outer_provider_chain.hpp"
    )
    contact_source = _read(
        "native_runtime/src/fun_00770e80_contact_outer_provider_chain.cpp"
    )
    assert "Fun0076d100CurrentBodyObserver current_body_observer" in motion_header
    assert "adapted.current_body_observer" in motion_source
    assert "Fun0076d100CurrentBodyObserver current_body_observer" in contact_header
    assert "upstream_body_observer" in contact_source
    assert "upstream_body_observer(current_body_bytes)" in contact_source


def test_phase739_selected_session_overwrites_only_world_position() -> None:
    session = _read("native_runtime/src/native_vehicle_provider_session.cpp")
    assert "fun_00765c40_selected_bmw_body_domain" in session
    assert "execute_fun_00765c40_selected_bmw_world_position" in session
    assert "result.query_input.world_position =" in session
    assert "world_position_state->world_position" in session
    assert "providers_.fun_00765c40(pass_index)" in session
    assert "result.load_terms" in session
    assert "generic fixtures" in session


def test_phase739_native_regression_and_cmake_are_wired() -> None:
    test_cpp = _read(
        "native_runtime/tests/fun_00765c40_selected_bmw_world_position_check.cpp"
    )
    assert "kBmwM3E36RetailBodyCount" in test_cpp
    assert "second-pass world position did not follow current BODY state" in test_cpp
    assert "non-BMW BODY domain failed open" in test_cpp

    phase738 = _read("native_runtime/cmake/phase738.cmake")
    phase739 = _read("native_runtime/cmake/phase739.cmake")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase739.cmake)" in phase738
    assert "shift_runtime_fun_00765c40_selected_bmw_world_position_check" in phase739
