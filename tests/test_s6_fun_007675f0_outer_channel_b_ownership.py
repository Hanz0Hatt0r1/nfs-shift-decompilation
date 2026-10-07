from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_outer_channel_b_ownership.json"
KERNEL_HEADER = ROOT / "native_runtime/include/shift_contact_outer_kernel.hpp"
KERNEL_SOURCE = ROOT / "native_runtime/src/contact_outer_kernel.cpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
ORACLE = ROOT / "src/physics/physics_helper_675f0_runtime.py"
OUTER_STATIC = ROOT / "evidence/outer_update_callsite_static.md"


def test_machine_evidence_is_hash_locked_and_distinguishes_hdvehicle_from_body() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007675f0OuterChannelBOwnership/1"
    assert payload["ready"] is True
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    owner = payload["outer_channel_b"]
    assert owner["producer_function"] == "FUN_00770e80"
    assert owner["parameter"] == "param_2"
    assert owner["receiver"] == "HDVehicle"
    assert owner["receiver_offset"] == "0xa0"
    assert owner["shared_by_both_physics_passes"] is True
    contact = payload["contact_filter_join"]
    assert contact["load_address"] == "0x007676d8"
    assert contact["narrowing"] == "f64 -> f32 store/reload before FUN_00783a30"
    assert contact["body_pointer_offset"] == "0x33a0"
    assert contact["body_offset_claimed"] is False

    for window in payload["machine_windows"].values():
        blob = bytes.fromhex(window["bytes"])
        assert hashlib.sha256(blob).hexdigest() == window["sha256"]


def test_outer_channel_b_is_the_existing_fun00770e80_outer_timestep_owner() -> None:
    outer_static = OUTER_STATIC.read_text(encoding="utf-8")
    session = SESSION_SOURCE.read_text(encoding="utf-8")
    assert "param_2 -> receiver +0xa0" in outer_static
    assert "outer_timestep" in session
    assert "outer_timestep);" in session
    assert "HDVehicle+0xa0" in session
    assert "same f64 value for each 0.5x" in session
    assert "compose_fun_007675f0_external_input" in session


def test_production_session_payload_excludes_distance_filter_cap() -> None:
    header = KERNEL_HEADER.read_text(encoding="utf-8")
    session_struct = header.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]
    assert "double distance_filter_cap =" not in session_struct
    assert "compatibility_distance_filter_cap_present" in session_struct
    assert "compatibility_distance_filter_cap" in session_struct
    assert "double previous_distance_state" not in session_struct

    source = KERNEL_SOURCE.read_text(encoding="utf-8")
    assert "static_cast<float>(outer_channel_b)" in source
    assert "external.distance_filter_cap = static_cast<double>(narrowed_channel_b)" in source
    assert "PC 0x007676d8 loads HDVehicle+0xa0 as f64" in source


def test_phase379_oracle_no_longer_mislabels_receiver_a0_as_body_field() -> None:
    oracle = ORACLE.read_text(encoding="utf-8")
    assert "body_field+0xa0" not in oracle
    assert "f32(HDVehicle+0xa0)" in oracle


def test_scope_keeps_provider_count_and_reduces_normal_fields_to_six() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    narrowing = payload["provider_narrowing"]
    assert narrowing["removed_field"] == "distance_filter_cap"
    assert narrowing["production_session_remaining_field_count"] == 6
    assert narrowing["external_provider_count_before"] == 7
    assert narrowing["external_provider_count_after"] == 7
    assert narrowing["provider_count_reduced"] is False
    assert payload["scope"]["new_provider_boundary_added"] is False
