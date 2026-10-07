from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_load_term_ownership.json"
LOAD_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_load_terms.hpp"
PROJECTION_HEADER = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_pc_load_term_ownership_is_hash_locked_and_ordered() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40LoadTerms/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    layout = payload["wheel_layout"]
    assert layout["array_base"] == "HDVehicle+0x400"
    assert layout["count"] == 4
    assert layout["stride"] == "0xa80"
    assert layout["per_wheel_load_field"] == "+0x738 f64"
    assert layout["hdvehicle_offsets"] == ["0xb38", "0x15b8", "0x2038", "0x2ab8"]
    order = payload["pass_order"]
    assert order["order"] == ["FUN_00765c40", "FUN_00758b50", "FUN_00766510", "FUN_00769ef0"]
    assert order["load_terms_available_before_FUN_00769ef0"] is True


def test_native_api_moves_load_terms_to_fun_00765c40_owner() -> None:
    load_header = LOAD_HEADER.read_text(encoding="utf-8")
    projection = PROJECTION_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")
    assert "kFun00765c40WheelStride = 0xa80u" in load_header
    assert "kFun00765c40WheelLoadFieldOffset = 0x738u" in load_header
    for offset in ("0xb38u", "0x15b8u", "0x2038u", "0x2ab8u"):
        assert offset in load_header
    external_struct = projection.split("struct Fun007682c0ExternalMachineInput", 1)[1].split("};", 1)[0]
    assert "load_terms" not in external_struct
    compose = projection.split("compose_fun_007682c0_machine_input", 1)[1]
    assert "const Fun00765c40LoadTerms& load_terms" in compose
    assert "input.load_terms = load_terms" in compose
    assert "using NativeVehicleContactFactorProvider" in session_header
    assert "NativeVehicleContactFactorProvider contact_factor" in session_header
    assert "Fun00765c40PassLoadState" in session_source
    contact_store = session_source.index("load_state->terms = providers_.contact_factor(pass_index)")
    ready_store = session_source.index("load_state->ready = true")
    compose_call = session_source.index("compose_fun_007682c0_machine_input")
    assert contact_store < ready_store < compose_call
    assert "providers_.motion_read_input" not in session_source
    assert "if (!load_state->ready)" in session_source


def test_phase722_artifact_remains_historical_contact_boundary_evidence() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["native_handoff"]
    limits = payload["limits"]
    assert handoff["owner_boundary"] == "NativeVehicleExternalProviderBundle.contact_factor"
    assert handoff["new_provider_type"] == "NativeVehicleContactFactorProvider"
    assert handoff["payload_type"] == "Fun00765c40LoadTerms"
    assert handoff["motion_read_provider_must_not_supply_load_terms"] is True
    assert handoff["active_external_provider_count"] == 8
    assert handoff["provider_count_reduced"] is False
    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["collision_provider_internalized"] is False
    assert limits["runtime_capture_required"] is False
