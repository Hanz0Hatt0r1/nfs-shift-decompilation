from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007560c0_motion_read_gate_setup.json"
SETUP_HEADER = ROOT / "native_runtime/include/shift_fun_007560c0_motion_read_gate_setup.hpp"
PROJECTION_HEADER = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_pc_setup_gate_evidence_is_hash_locked() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007560c0MotionReadGateSetup/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    writer = payload["setup_writer"]
    assert writer["setup_call_machine_span"]["raw_byte_sha256"] == (
        "77c8f47343e25ecb4d867397346092533ad49e3b024f08527d16123771a2fd22"
    )
    assert writer["table_derived_store_span"]["raw_byte_sha256"] == (
        "a16b138c0c49e920477882ee6b1a9921cc80f28acc49dd6c21886f36a96d5a00"
    )
    assert writer["vehicle_override_store_span"]["raw_byte_sha256"] == (
        "45b36e0f76117c958aac13ac2b79de6a7880214943ba99ace954055ead6f1962"
    )
    assert writer["disabled_zero_store_span"]["raw_byte_sha256"] == (
        "86f904aae08a05624c3fd5df0f86afca538e5eead82dd4aeff424c2e10d6af14"
    )
    assert payload["late_consumer"]["machine_span"]["raw_byte_sha256"] == (
        "17635fa58a0dc3fa049a33525d4516d607ddd344900d39ff7f2411182c030b8a"
    )


def test_gate_is_setup_owned_and_no_late_provider_struct_remains() -> None:
    setup_header = SETUP_HEADER.read_text(encoding="utf-8")
    projection = PROJECTION_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")

    assert "Fun007682c0ExternalMachineInput" not in projection
    assert "Fun007560c0MotionReadGateSetup" in setup_header
    assert "bool caller_gate_open" in setup_header
    assert "Fun007560c0MotionReadGateSetup& setup_gate" in projection
    assert "input.caller_gate_open = setup_gate.caller_gate_open" in projection
    assert "selected_bmw_native_session_player_difficulty()" in projection

    assert "Fun007560c0MotionReadGateSetup motion_read_setup" in session_header
    assert "NativeVehicleMotionReadInputProvider" not in session_header
    assert "motion_read_setup" in session_source
    assert "providers_.motion_read_setup" in session_source
    assert "providers_.motion_read_input" not in session_source


def test_phase723_scope_keeps_selected_gate_value_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["native_handoff"]
    limits = payload["limits"]
    defaults = payload["settings_defaults"]

    assert handoff["session_owned_setup_state"] is True
    assert handoff["late_motion_read_provider_must_not_supply_gate"] is True
    assert handoff["active_external_provider_count"] == 8
    assert handoff["provider_count_reduced"] is False
    assert limits["selected_setup_gate_value_derived_natively"] is False
    assert limits["DAT_00c128cc_internalized"] is False
    assert defaults["selected_runtime_values_proven_equal_to_defaults"] is False
    assert limits["xbox_360_recomp_substituted_for_pc_authority"] is False
