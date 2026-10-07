from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_distance_filter_cap_ownership.json"
PHASE730_EVIDENCE = ROOT / "evidence/fun_007675f0_distance_state_ownership.json"
SETUP_HEADER = ROOT / "native_runtime/include/shift_fun_007675f0_distance_filter_cap_setup.hpp"
KERNEL_HEADER = ROOT / "native_runtime/include/shift_contact_outer_kernel.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
PC_ORACLE = ROOT / "src/physics/physics_helper_675f0_runtime.py"


def test_phase731_pc_owner_and_xbox_crosscheck_are_exact() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007675f0DistanceFilterCapOwnership/1"
    assert payload["ready"] is True

    pc = payload["pc_retail"]
    assert pc["program"] == "SHIFT.exe"
    assert pc["function"] == "FUN_007675f0"
    assert pc["source_line"] == 759784
    assert pc["owner"] == "HDVehicle"
    assert pc["offset"] == "0xa0"
    assert pc["consumer"] == "FUN_00783a30"
    assert pc["production_per_pass_provider_field"] is False

    xbox = payload["xbox360_retail_crosscheck"]
    assert xbox["xex_sha256"] == (
        "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
    )
    assert xbox["extracted_pe_sha256"] == (
        "23844dbba0cf72bc11512821b90008ea5d2b06ee886d921f416ca6caae43a628"
    )
    assert xbox["fun_007675f0_analog_start"] == "0x8259a9f0"
    assert xbox["distance_filter_cap_offset"] == "HDVehicle+0xa0"
    assert xbox["cap_load_instruction"] == "0x8259aaa8: lfd 0, 160(31)"
    assert xbox["cross_platform_support_only"] is True
    assert xbox["used_to_infer_pc_initializer_or_value"] is False


def test_existing_pc_oracle_already_names_body_field_a0() -> None:
    oracle = PC_ORACLE.read_text(encoding="utf-8")
    assert "body_field+0xa0" in oracle
    assert "FUN_00783a30(previous, distance, body_field+0xa0, 0.5)" in oracle


def test_production_session_payload_no_longer_contains_per_pass_cap() -> None:
    header = KERNEL_HEADER.read_text(encoding="utf-8")
    session_struct = header.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]
    assert "double distance_filter_cap" not in session_struct
    assert "compatibility_distance_filter_cap_seed_present" in session_struct
    assert "compatibility_distance_filter_cap_seed" in session_struct

    setup = SETUP_HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun007675f0DistanceFilterCapSetup/1" in setup
    assert "kFun007675f0DistanceFilterCapOffset = 0xa0u" in setup
    assert "validate_fun_007675f0_distance_filter_cap_setup" in setup

    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    assert "Fun007675f0DistanceFilterCapSetup contact_outer_distance_filter_cap_setup" in session_header

    source = SESSION_SOURCE.read_text(encoding="utf-8")
    assert "distance filter cap used before explicit setup seed" in source
    assert "compatibility_distance_filter_cap_seed" in source
    assert "contact_outer_distance_filter_cap_setup.distance_filter_cap" in source
    assert source.count("contact_outer_distance_filter_cap_setup =") >= 3


def test_phase731_narrows_field_count_without_rewriting_phase730_history() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["contact_outer_external_field_count_before"] == 7
    assert scope["contact_outer_external_field_count_after"] == 6
    assert scope["remaining_external_fun_007675f0_fields"] == [
        "planar_delta",
        "surface_scalar",
        "base_scalar",
        "projected_scalar",
        "alignment_scalar",
        "param_3",
    ]

    phase730 = json.loads(PHASE730_EVIDENCE.read_text(encoding="utf-8"))
    assert phase730["format"] == "SHIFT.Fun007675f0DistanceStateOwnership/1"
    assert phase730["remaining_external_field_count"] == 7
