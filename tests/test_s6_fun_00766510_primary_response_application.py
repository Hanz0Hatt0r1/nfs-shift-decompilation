from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_primary_response_application.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00766510_primary_response_application.hpp"
PHASE741_CMAKE = ROOT / "native_runtime/cmake/phase741.cmake"
PHASE742_CMAKE = ROOT / "native_runtime/cmake/phase742.cmake"


def test_phase742_evidence_freezes_exact_primary_application_only() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510PrimaryResponseApplication/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"

    source = payload["source"]
    assert source["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert source["decompiler_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert source["consumer_function"] == "FUN_00766510"
    assert source["decompiler_lines"] == [759686, 759695]
    assert source["machine_span"]["start"] == "0x00766f9f"
    assert source["machine_span"]["end_exclusive"] == "0x00767046"
    assert source["machine_span"]["raw_byte_sha256"] == (
        "ea0d7c2fb2f33101808f9ad997867c724476fea62bc0ed60f6af0023471f1546"
    )

    assert payload["offsets"]["primary_point_or_lever_arm"] == (
        "HDVehicle+0x38f0/+0x38f8/+0x3900"
    )
    assert payload["offsets"]["primary_response_table"] == "HDVehicle+0x3950"
    assert payload["offsets"]["caller_cross_accumulator"] == (
        "HDVehicle+0x40a0/+0x40a8/+0x40b0"
    )

    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["primary_response_vector_application_frozen"] is True
    assert scope["complete_FUN_00766510_internalized"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["caller_state_producers_internalized"] is False
    assert scope["physical_semantics_invented"] is False


def test_phase742_header_composes_existing_native_primitives() -> None:
    header = HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00766510PrimaryResponseApplication/1" in header
    assert "kFun00766510PrimaryLeverArmOffset = 0x38f0u" in header
    assert "kFun00766510PrimaryResponseTableOffset = 0x3950u" in header
    assert "kFun00766510CallerCrossAccumulatorOffset = 0x40a0u" in header
    assert "transform_fun_007aefb0_refresh" in header
    assert "apply_fun_007baa70_body_accumulator" in header
    assert "fun_00753650_cross" in header
    assert "result.caller_cross_accumulator[component] +=" in header
    assert "result.auxiliary_accumulator[component] +=" in header


def test_phase742_cmake_chains_after_phase741() -> None:
    phase741 = PHASE741_CMAKE.read_text(encoding="utf-8")
    phase742 = PHASE742_CMAKE.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase742.cmake)" in phase741
    assert "shift_runtime_fun_00766510_primary_response_application_check" in phase742
