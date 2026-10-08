from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_later_response_native.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_later_response_branch.hpp"
TEST = ROOT / "native_runtime/tests/fun_00766510_later_response_branch_check.cpp"
PHASE748 = ROOT / "native_runtime/cmake/phase748.cmake"
PHASE749 = ROOT / "native_runtime/cmake/phase749.cmake"
PROCESS1 = ROOT / "evidence/fun_00766510_later_response_branch_ownership.json"


def test_phase749_consumes_positive_process1_contract() -> None:
    native = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    owner = json.loads(PROCESS1.read_text(encoding="utf-8"))
    assert native["format"] == "SHIFT.Fun00766510LaterResponseBranch/1"
    assert native["ready"] is True
    assert native["authority"]["ownership_contract"] == owner["format"]
    assert owner["ready"] is True
    assert owner["adjudication"]["later_response_branch_owner_closed"] is True
    assert owner["adjudication"]["contact_response_provider_removable_now"] is False


def test_phase749_preserves_dynamic_sixth_table_entry() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    contract = payload["native_contract"]
    runtime = payload["runtime_materialization"]
    assert contract["table_base"] == "+0x3a40"
    assert contract["table_entry_count"] == 6
    assert contract["table_entry_stride"] == "0x18"
    assert contract["runtime_lane_offset"] == "+0x3ac0"
    assert contract["persistent_lane_offset"] == "+0x3ac8"
    assert runtime["sixth_entry"] == ["+0x3ab8", "+0x3ac0", "+0x3ac8"]
    assert runtime["second_lane_rewritten_each_evaluation"] is True
    assert runtime["third_lane_from_persistent_refresh"] is True
    assert runtime["setup_table_snapshot_mutated_in_place"] is False


def test_phase749_keeps_persistent_refresh_and_mutable_bases_explicit() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    refresh = payload["persistent_refresh"]
    assert refresh["function"] == "FUN_00756b10"
    assert refresh["derived_scale_formula"] == (
        "+0x3780*s^2 + +0x3778*s + +0x3770"
    )
    assert refresh["persistent_lane_formula"] == (
        "+0x3798*s^2 + +0x3790*s + +0x3788"
    )
    assert refresh["mutable_bases_preserved"] is True
    assert refresh["baseline_restore_modeled"] is True

    header = HEADER.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")
    assert "refresh_fun_00756b10_later_response_state" in header
    assert "restore_fun_00766510_later_response_mutable_bases" in header
    assert "state.table[5][1] = state.runtime_lane" in header
    assert "state.table[5][2] = persistent.persistent_lane" in header
    assert "mutable coefficient bases were incorrectly frozen" in test


def test_phase749_remains_fail_closed_for_provider_removal() -> None:
    scope = json.loads(EVIDENCE.read_text(encoding="utf-8"))["scope"]
    assert scope["p1_1b_consumed_by_process2"] is True
    assert scope["full_later_branch_body_apply_internalized"] is False
    assert scope["caller_accumulator_internalized"] is False
    assert scope["diagnostic_tail_internalized"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7


def test_phase749_cmake_is_chained_after_phase748() -> None:
    phase748 = PHASE748.read_text(encoding="utf-8")
    phase749 = PHASE749.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase749.cmake)" in phase748
    assert "shift_runtime_fun_00766510_later_response_branch_check" in phase749
