from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_distance_filter_cap_ownership.json"
XBOX = ROOT / "evidence/xbox360_fun_007675f0_crosscheck.json"
SETUP = ROOT / "native_runtime/include/shift_fun_007675f0_distance_filter_cap_setup.hpp"
KERNEL_HEADER = ROOT / "native_runtime/include/shift_contact_outer_kernel.hpp"
KERNEL_SOURCE = ROOT / "native_runtime/src/contact_outer_kernel.cpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_pc_contract_and_xbox_crosscheck_agree_on_object_offset() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    xbox = json.loads(XBOX.read_text(encoding="utf-8"))

    assert payload["format"] == "SHIFT.Fun007675f0DistanceFilterCapOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["function"] == "FUN_007675f0"
    assert payload["source"]["source_line"] == 759784
    assert "body_field+0xa0" in payload["source"]["pc_recovered_expression"]
    assert payload["retail_state"]["offset"] == "0xa0"
    assert payload["retail_state"]["per_pass_call_argument"] is False
    assert payload["retail_state"]["upstream_initializer_proven"] is False
    assert payload["retail_state"]["selected_value_promoted"] is False

    assert xbox["format"] == "SHIFT.Xbox360Fun007675f0Crosscheck/1"
    assert xbox["source"]["xex_sha256"] == (
        "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
    )
    assert xbox["source"]["extracted_pe_sha256"] == (
        "23844dbba0cf72bc11512821b90008ea5d2b06ee886d921f416ca6caae43a628"
    )
    assert xbox["counterpart"]["xbox_function_start"] == "0x8259a9f0"
    assert xbox["distance_filter_cap"]["xbox_load"] == "lfd 0,160(r31)"
    assert xbox["distance_filter_cap"]["xbox_offset_hex"] == "0xa0"
    assert xbox["distance_filter_cap"]["same_object_as_0x4080_state"] is True
    assert xbox["policy"]["pc_retail_source_remains_authoritative_for_native_contract"] is True


def test_production_session_payload_removes_per_pass_filter_cap() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["remaining_external_field_count"] == 6
    assert payload["remaining_external_fun_007675f0_fields"] == [
        "planar_delta",
        "surface_scalar",
        "base_scalar",
        "projected_scalar",
        "alignment_scalar",
        "param_3",
    ]
    assert payload["scope"]["external_provider_count_before"] == 7
    assert payload["scope"]["external_provider_count_after"] == 7
    assert payload["scope"]["provider_count_reduced"] is False

    header = KERNEL_HEADER.read_text(encoding="utf-8")
    session_struct = header.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]
    assert "double distance_filter_cap =" not in session_struct
    assert "compatibility_distance_filter_cap_seed_present" in session_struct
    assert "compatibility_distance_filter_cap_seed" in session_struct
    assert "legacy.distance_filter_cap" in session_struct

    kernel_source = KERNEL_SOURCE.read_text(encoding="utf-8")
    assert "external.distance_filter_cap = distance_filter_cap" in kernel_source
    assert "session_input.distance_filter_cap" not in kernel_source


def test_filter_cap_is_one_time_setup_and_transactional() -> None:
    setup = SETUP.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")

    assert "SHIFT.Fun007675f0DistanceFilterCapSetup/1" in setup
    assert "kFun007675f0DistanceFilterCapOffset = 0xa0u" in setup
    assert "validate_fun_007675f0_distance_filter_cap_setup" in setup
    assert "selected session" in setup

    assert "Fun007675f0DistanceFilterCapSetup contact_outer_filter_cap_setup" in session_header
    assert "contact_outer_distance_filter_cap() const" in session_header
    assert "distance filter cap used before explicit setup seed" in session_source
    assert "compatibility_distance_filter_cap_seed_present" in session_source
    assert "contact_outer_filter_cap_setup.distance_filter_cap" in session_source
    assert session_source.count(
        "providers_.contact_outer_filter_cap_setup = filter_cap_setup_before"
    ) >= 3
