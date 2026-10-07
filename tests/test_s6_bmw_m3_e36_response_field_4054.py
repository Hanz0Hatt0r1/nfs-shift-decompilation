from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/bmw_m3_e36_response_field_4054.json"
UPSTREAM = ROOT / "evidence/bmw_offset33b_selector_geometry_inputs.json"
HEADER = ROOT / "native_runtime/include/shift_bmw_m3_e36_response_field_4054.hpp"
SOURCE = ROOT / "native_runtime/src/bmw_m3_e36_response_field_4054.cpp"
PROJECTION = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_selected_bmw_vdf_provenance_and_numeric_inputs_match_upstream() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    source = payload["selected_bmw_resource"]

    assert payload["format"] == "SHIFT.BMWM3E36ResponseField4054/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert source["archive_sha256"] == upstream["sources"]["vehicle_vdf"]["archive"]["sha256"]
    assert source["decoded_sha256"] == upstream["sources"]["vehicle_vdf"]["entry"]["decoded_sha256"]
    assert source["path"] == "vehicles/physics/vehicles/bmw_m3_e36.vdf"
    assert source["wheel_fl_offset"] == upstream["vdf"]["wheel_offsets"]["fl"]
    assert source["wheel_rl_offset"] == upstream["vdf"]["wheel_offsets"]["rl"]
    assert upstream["retail_layout"]["VDF.Wheel FL Offset"] == "record+0x34"
    assert upstream["retail_layout"]["VDF.Wheel RL Offset"] == "record+0x4c"


def test_pc_machine_spans_are_hash_locked() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    spans = {row["function"]: row for row in payload["machine_spans"]}
    assert spans["FUN_00703f10 Wheel FL Offset reflection registration"]["raw_byte_sha256"] == (
        "8989952a105bf348dcab1289fa3c5c375e98378d96d796f1a2da002b0ee20aa9"
    )
    assert spans["FUN_00703f10 Wheel RL Offset reflection registration"]["raw_byte_sha256"] == (
        "06f97c52059f60c7f7d745397ee64aba2b5546eab06c515ff715c92b7098d802"
    )
    assert spans["FUN_007047f0 selected CarPhysicsDetails copy"]["raw_byte_sha256"] == (
        "901d47e93a92ab8910ab9717dcc66321c04df9e6428851b0613b0b68c3d2a92c"
    )
    assert spans["FUN_0076b280 wheel-offset load and setup writer path"]["raw_byte_sha256"] == (
        "68c1c35f20dd8d3621732c46455634f0520f5a14ffdffc8f5cc33f55ef969860"
    )
    assert spans["FUN_0076b280 HDVehicle+0x4054 writer"]["raw_byte_sha256"] == (
        "074120516d59c1d7cb786d4bc830a4e7b0ea9d7c13930595ed02e5747e4a2e36"
    )


def test_retail_formula_and_native_bit_checkpoint_are_exact() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    formula = payload["formula"]
    assert formula["wheel_fl_z_f32_bits"] == "0xbfaccccd"
    assert formula["wheel_rl_z_f32_bits"] == "0x3faccccd"
    assert formula["response_field_4054_f32_bits"] == "0x402ccccd"
    assert formula["x87_control_word"] == "0x027f"

    source = SOURCE.read_text(encoding="utf-8")
    assert "0xbfaccccdu" in source
    assert "0x3faccccdu" in source
    assert "fabs" in source
    assert "fstps" in source
    assert "0x027fu" in source
    assert "std::fabs" not in source
    assert "derive_bmw_m3_e36_response_field_4054" in HEADER.read_text(encoding="utf-8")


def test_response_4054_is_no_longer_external_and_session_owns_it_once() -> None:
    projection = PROJECTION.read_text(encoding="utf-8")
    external_struct = projection.split(
        "struct Fun007682c0ExternalMachineInput", 1
    )[1].split("struct Fun007682c0DerivedProjectionState", 1)[0]
    assert "response_field_4054" not in external_struct
    assert "float response_field_4054" in projection.split(
        "compose_fun_007682c0_machine_input", 1
    )[1]

    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")
    assert "float response_field_4054_ = 0.0f" in session_header
    assert "float response_field_4054() const" in session_header
    constructor = session_source.split(
        "NativeVehicleProviderSession::NativeVehicleProviderSession", 1
    )[1].split("NativeVehicleProviderSessionResult", 1)[0]
    assert "derive_bmw_m3_e36_response_field_4054().value" in constructor
    assert "providers_.motion_read_input" not in constructor
    assert "response_field_4054_" in session_source.split(
        "compose_fun_007682c0_machine_input", 1
    )[1]

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["ownership"]["setup_fixed"] is True
    assert payload["ownership"]["per_pass_refresh"] is False
    assert payload["ownership"]["per_outer_refresh"] is False
    assert payload["native_consumption"]["computed_once_at_session_construction"] is True
    assert payload["native_consumption"]["Fun007682c0ExternalMachineInput_field_required"] is False
    assert "+0x4054" not in " ".join(payload["remaining_raw_input_blockers"])
