from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_early_response_native.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_early_response_branch.hpp"
TEST = ROOT / "native_runtime/tests/fun_00766510_early_response_branch_check.cpp"
PHASE749 = ROOT / "native_runtime/cmake/phase749.cmake"
PHASE750 = ROOT / "native_runtime/cmake/phase750.cmake"
PROCESS1 = ROOT / "evidence/fun_00766510_early_response_branch_ownership.json"


def test_phase750_consumes_positive_process1_contract() -> None:
    native = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    owner = json.loads(PROCESS1.read_text(encoding="utf-8"))
    assert native["format"] == "SHIFT.Fun00766510EarlyResponseBranch/1"
    assert native["ready"] is True
    assert native["authority"]["ownership_contract"] == owner["format"]
    assert owner["ready"] is True
    assert owner["adjudication"]["early_response_branch_owner_closed"] is True
    assert owner["adjudication"]["contact_response_provider_removable_now"] is False


def test_phase750_preserves_dynamic_sixth_table_entry() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    contract = payload["native_contract"]
    runtime = payload["runtime_materialization"]
    assert contract["table_base"] == "+0x3b20"
    assert contract["table_entry_count"] == 6
    assert contract["table_entry_stride"] == "0x18"
    assert contract["sixth_entry"] == ["+0x3b98", "+0x3ba0", "+0x3ba8"]
    assert runtime["third_lane_rewritten_each_evaluation"] is True
    assert runtime["setup_table_snapshot_mutated_in_place"] is False


def test_phase750_keeps_unproven_clamp_semantics_external() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    runtime = payload["runtime_materialization"]
    assert runtime["formula"] == (
        "+0x3af0 * 0.5 * clamped_pair_sum + +0x3ae8 + "
        "abs(pair_delta) * +0x3af8"
    )
    assert runtime["clamp_algorithm_internalized"] is False
    assert runtime["clamped_pair_sum_is_explicit_input"] is True
    assert runtime["pair_delta_is_explicit_input"] is True

    header = HEADER.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")
    assert "refresh_fun_00756b60_early_response_state" in header
    assert "inputs.base_coefficient * 0.5 * inputs.clamped_pair_sum" in header
    assert "std::abs(inputs.pair_delta) * inputs.delta_coefficient" in header
    assert "state.table[5][2] = state.runtime_lane" in header
    assert "abs(delta) must be used" in test


def test_phase750_remains_fail_closed_for_provider_removal() -> None:
    scope = json.loads(EVIDENCE.read_text(encoding="utf-8"))["scope"]
    assert scope["early_branch_state_consumed_by_process2"] is True
    assert scope["table_evaluator_internalized"] is False
    assert scope["body_apply_internalized"] is False
    assert scope["caller_accumulator_internalized"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7


def test_phase750_cmake_is_chained_after_phase749() -> None:
    phase749 = PHASE749.read_text(encoding="utf-8")
    phase750 = PHASE750.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase750.cmake)" in phase749
    assert "shift_runtime_fun_00766510_early_response_branch_check" in phase750
