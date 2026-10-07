from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_load_term_ownership.json"
LOAD_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_load_terms.hpp"
PASS_RESULT_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
PROJECTION_HEADER = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_pc_load_term_ownership_is_hash_locked_and_ordered() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40LoadTerms/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )

    layout = payload["wheel_layout"]
    assert layout["array_base"] == "HDVehicle+0x400"
    assert layout["count"] == 4
    assert layout["stride"] == "0xa80"
    assert layout["per_wheel_load_field"] == "+0x738 f64"
    assert layout["hdvehicle_offsets"] == [
        "0xb38",
        "0x15b8",
        "0x2038",
        "0x2ab8",
    ]

    construction = payload["construction_and_job_registration"]
    assert construction["wheel_array_constructor_machine_span"]["raw_byte_sha256"] == (
        "562dad4f26444d7ea1e78c8e8a5696d99f4e15ec805348b462768588981c1b80"
    )
    assert construction["wheel_constructor_vtable_machine_span"]["raw_byte_sha256"] == (
        "c632989647d85ed40526d7b2a8f46f0a06ec1f7d1e9919e033ec728695078098"
    )
    assert construction["vtable_first_two_entries"]["raw_byte_sha256"] == (
        "a0a7ee6292a11c8c7e582fc654bda7bd4663b43b730a9e848ce8f8d6bb089dff"
    )
    assert construction["scheduler_virtual_dispatch_machine_span"]["raw_byte_sha256"] == (
        "da532461abd479e4d7b6d3bfd50d42f1836f15c27d8b4994b8e682a51c776554"
    )
    assert construction["registration_machine_span"]["raw_byte_sha256"] == (
        "b5e2cca8b47984afd0132ede72d829644646c13e839e39541b36e6a64852bd2a"
    )

    writes = payload["wheel_job_writes"]
    assert writes["entry"] == "0x0075cfb0"
    assert writes["entry_zero_and_initialization_span"]["raw_byte_sha256"] == (
        "e6b7338dce366057c26f610d7ab9c01f5c816113ac2d1cf4ad13699c66ee528d"
    )
    assert writes["runtime_load_store_span"]["raw_byte_sha256"] == (
        "2dc553aa0c28f4317ab2978d18cca6c465a0a700cb14633440f54784754a046b"
    )

    order = payload["pass_order"]
    assert order["FUN_00765c40_machine_span"]["raw_byte_sha256"] == (
        "e667e132f5185960e299fdd089e66af9dd65e7773dc970c8f47ee2893c411a4c"
    )
    assert order["order"] == [
        "FUN_00765c40",
        "FUN_00758b50",
        "FUN_00766510",
        "FUN_00769ef0",
    ]
    assert order["load_terms_available_before_FUN_00769ef0"] is True


def test_active_session_names_exact_fun_00765c40_boundary() -> None:
    load_header = LOAD_HEADER.read_text(encoding="utf-8")
    pass_result_header = PASS_RESULT_HEADER.read_text(encoding="utf-8")
    projection = PROJECTION_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")

    assert "kFun00765c40WheelStride = 0xa80u" in load_header
    assert "kFun00765c40WheelLoadFieldOffset = 0x738u" in load_header
    for offset in ("0xb38u", "0x15b8u", "0x2038u", "0x2ab8u"):
        assert offset in load_header

    assert "Fun00765c40ExternalPassResult" in pass_result_header
    assert "Fun00765c40LoadTerms load_terms" in pass_result_header
    assert "validate_fun_00765c40_external_pass_result" in pass_result_header

    assert "Fun007682c0ExternalMachineInput" not in projection
    compose = projection.split("compose_fun_007682c0_machine_input", 1)[1]
    assert "const Fun00765c40LoadTerms& load_terms" in compose
    assert "input.load_terms = load_terms" in compose

    assert "using NativeVehicleFun00765c40Provider" in session_header
    assert "NativeVehicleFun00765c40Provider fun_00765c40" in session_header
    assert "NativeVehicleContactFactorProvider" not in session_header
    assert "NativeVehicleMotionReadInputProvider" not in session_header
    assert "Fun00765c40PassLoadState" in session_source
    provider_call = session_source.index("providers_.fun_00765c40(pass_index, external_input)")
    validate_call = session_source.index("validate_fun_00765c40_external_pass_result")
    load_store = session_source.index("load_state->terms = result.load_terms")
    ready_store = session_source.index("load_state->ready = true")
    compose_call = session_source.index("compose_fun_007682c0_machine_input")
    assert provider_call < validate_call < load_store < ready_store < compose_call
    assert "providers_.contact_factor" not in session_source
    assert "providers_.motion_read_input" not in session_source
    assert "if (!load_state->ready)" in session_source


def test_phase722_historical_scope_remains_immutable() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["native_handoff"]
    limits = payload["limits"]

    assert handoff["owner_boundary"] == "NativeVehicleExternalProviderBundle.contact_factor"
    assert handoff["new_provider_type"] == "NativeVehicleContactFactorProvider"
    assert handoff["payload_type"] == "Fun00765c40LoadTerms"
    assert handoff["motion_read_provider_must_not_supply_load_terms"] is True
    assert handoff["active_external_provider_count"] == 8
    assert handoff["provider_count_reduced"] is False
    assert handoff["ownership_narrowed"] is True

    assert limits["complete_FUN_00765c40_internalized"] is False
    assert limits["wheel_contact_formula_internalized"] is False
    assert limits["collision_provider_internalized"] is False
    assert limits["HDVehicle_0xe0_internalized"] is False
    assert limits["DAT_00c128cc_internalized"] is False
    assert limits["xbox_360_recomp_substituted_for_pc_authority"] is False
    assert limits["runtime_capture_required"] is False
    assert limits["original_game_execution_required"] is False
