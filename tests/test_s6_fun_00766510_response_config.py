from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_response_config_native.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_response_config.hpp"
TEST = ROOT / "native_runtime/tests/fun_00766510_response_config_check.cpp"
PHASE751 = ROOT / "native_runtime/cmake/phase751.cmake"
PHASE752 = ROOT / "native_runtime/cmake/phase752.cmake"
PROCESS1 = ROOT / "evidence/fun_00766510_response_config_ownership.json"


def test_phase752_consumes_positive_process1_contract() -> None:
    native = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    owner = json.loads(PROCESS1.read_text(encoding="utf-8"))
    assert native["format"] == "SHIFT.Fun00766510ResponseConfig/1"
    assert native["ready"] is True
    assert native["authority"]["ownership_contract"] == owner["format"]
    assert owner["ready"] is True
    assert owner["adjudication"]["response_config_owner_closed"] is True
    assert owner["adjudication"]["contact_response_provider_removable_now"] is False


def test_phase752_pins_setup_owned_response_config() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    contract = payload["native_contract"]
    setup = payload["setup_owned"]
    assert contract["setup_scale_offset"] == "+0x3910"
    assert contract["curve_offset"] == "+0x3918"
    assert contract["table_base"] == "+0x3950"
    assert contract["table_entry_count"] == 6
    assert contract["table_entry_stride"] == "0x18"
    assert setup["plus_3910_per_pass_provider_required"] is False
    assert setup["plus_3918_per_pass_provider_required"] is False
    assert setup["plus_3950_per_pass_provider_required"] is False


def test_phase752_models_exact_mutable_3908_refresh() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    refresh = payload["persistent_refresh"]
    assert refresh["function"] == "FUN_00756ac0"
    assert refresh["formula"] == "+0x3750*s^2 + +0x3748*s + +0x3740"
    assert refresh["setup_constant"] is False
    assert refresh["refresh_after_fun_00757e60"] is True
    assert refresh["refresh_after_fun_00758210"] is True
    assert refresh["refresh_after_fun_00769d60"] is True

    header = HEADER.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")
    assert "refresh_fun_00756ac0_response_config_state" in header
    assert "coefficients.quadratic * selector_squared" in header
    assert "response-config mutable base was incorrectly frozen" in test


def test_phase752_remains_fail_closed_for_runtime_response_and_provider() -> None:
    scope = json.loads(EVIDENCE.read_text(encoding="utf-8"))["scope"]
    assert scope["response_config_consumed_by_process2"] is True
    assert scope["runtime_curve_scale_table_chain_internalized"] is False
    assert scope["caller_accumulator_internalized"] is False
    assert scope["diagnostic_tail_internalized"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7


def test_phase752_cmake_is_chained_after_phase751() -> None:
    phase751 = PHASE751.read_text(encoding="utf-8")
    phase752 = PHASE752.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase752.cmake)" in phase751
    assert "shift_runtime_fun_00766510_response_config_check" in phase752
