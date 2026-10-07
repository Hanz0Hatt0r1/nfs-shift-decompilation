from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/bmw_m3_e36_response_field_4054.json"
PROJECTION = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"
HELPER_H = ROOT / "native_runtime/include/shift_bmw_m3_e36_response_field_4054.hpp"
HELPER_CPP = ROOT / "native_runtime/src/bmw_m3_e36_response_field_4054.cpp"


def test_selected_bmw_vdf_to_pc_setup_writer_join_is_exact() -> None:
    proof = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert proof["format"] == "SHIFT.BMWM3E36ResponseField4054/1"
    assert proof["ready"] is True
    assert proof["platform_authority"] == "PC retail primary"
    resource = proof["resource"]
    assert resource["archive"] == "VehiclesGlobal.bff"
    assert resource["archive_sha256"] == "b186ae466e6cccb964c813c6f60bc060a4a8646c261f89270ef86e3ff5cdf953"
    assert resource["entry_index"] == 283
    assert resource["entry_path"] == "vehicles/physics/vehicles/bmw_m3_e36.vdf"
    assert resource["decoded_sha256"] == "f4c925bc6799439a12906d0aed9b73e22052cb46f7fbd4ea6f48409b9776a082"
    props = resource["car_physics_details"]
    assert props["Wheel FL Offset"] == "0.711;0.31;-1.35"
    assert props["Wheel RL Offset"] == "0.7225;0.31;1.35"
    assert resource["wheel_fl_z_f32_bits"] == "0xbfaccccd"
    assert resource["wheel_rl_z_f32_bits"] == "0x3faccccd"

    runtime = proof["pc_runtime_join"]
    assert runtime["writer_function"] == "FUN_0076b280"
    assert runtime["writer_source_line"] == 762154
    assert runtime["setup_call_source_line"] == 763779
    assert runtime["writer_is_setup_only"] is True
    assert proof["derived_value"]["f32_bits"] == "0x402ccccd"
    assert proof["derived_value"]["refresh_semantics"] == "vehicle setup fixed"

    spans = {row["role"]: row for row in proof["machine_spans"]}
    assert any(row["raw_byte_sha256"] == "4a066a9b9e6f5841b73b743a6293c710a6f1a03efb29377d3033949cdeea5fd1" for row in spans.values())
    assert any(row["raw_byte_sha256"] == "074120516d59c1d7cb786d4bc830a4e7b0ea9d7c13930595ed02e5747e4a2e36" for row in spans.values())
    assert any(row["raw_byte_sha256"] == "4298a38f967bfb2315f38989f6b05e1aa4837d0b781098b486b0771bdb3eee07" for row in spans.values())


def test_production_composition_owns_4054_without_raw_override() -> None:
    projection = PROJECTION.read_text(encoding="utf-8")
    helper_h = HELPER_H.read_text(encoding="utf-8")
    helper_cpp = HELPER_CPP.read_text(encoding="utf-8")

    assert "Fun007682c0ExternalMachineInput" not in projection
    assert "selected_bmw_m3_e36_response_field_4054()" in projection
    assert "input.response_field_4054" in projection
    assert "kBmwM3E36ResponseField4054Bits = 0x402ccccdu" in helper_h
    assert "static_cast<double>(fl_z) - static_cast<double>(rl_z)" in helper_cpp
    assert "std::fabs(difference)" in helper_cpp


def test_scope_keeps_phase721_historical_limits_immutable() -> None:
    proof = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = proof["limits"]
    assert limits["caller_gate_0xe0_internalized"] is False
    assert limits["four_load_terms_internalized"] is False
    assert limits["angle_mode_DAT_00c128cc_internalized"] is False
    assert limits["provider_count_reduced"] is False
    assert limits["active_external_provider_count"] == 8
    assert limits["sdf_wheelbase_substituted_for_vdf_setup_value"] is False
    assert limits["xbox_360_recomp_substituted_for_pc_authority"] is False
