from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007618f0_local_sample_producer.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007618f0_local_sample_producer.hpp"
SOURCE = ROOT / "native_runtime/src/fun_007618f0_local_sample_producer.cpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_retail_machine_spans_lock_local_sample_formula() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007618f0LocalSampleProducer/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    spans = {row["role"]: row for row in payload["machine_spans"]}
    assert spans["FUN_007618f0 entry saves HDVehicle this pointer"]["raw_byte_sha256"] == (
        "87c8427b3d324842f94c703c01a10c34320936118a53067e1afcd5c25ed21a5b"
    )
    assert spans["FUN_007618f0 restores HDVehicle and second source argument"]["raw_byte_sha256"] == (
        "c2baabcf13cc4a79c2138ee06d2d8ab002deb049419c93e4638572bac1ce2b76"
    )
    assert spans["pointer vec add, 0.5 scale, and Y override"]["raw_byte_sha256"] == (
        "78e59440901206946cfce162e739b29d13cc33ea9061a84ee3e398af055bcf88"
    )
    assert spans["FUN_007535f0 f64 vec3 scalar multiply"]["raw_byte_sha256"] == (
        "f99de4e31545a94fc20a3b4e7771569a19d5d6536faa08e04440079f8b380321"
    )
    assert spans["final source+0x918 add and HDVehicle+0x3938 stores"]["raw_byte_sha256"] == (
        "3c4b74dedbf14f6a6be5b91b732a49fbffed11d2d0ac67af68b3111b3cfb2a5d"
    )


def test_input_contract_preserves_exact_offsets_without_semantic_guessing() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    inputs = payload["input_contract"]
    assert "HDVehicle+0x820" in inputs["hdvehicle_pointer_vec_0820"]
    assert "HDVehicle+0x12a0" in inputs["hdvehicle_pointer_vec_12a0"]
    assert "+0x338" in inputs["source_scalar_0338"]
    assert "+0x918" in inputs["source_vec_0918"]
    assert payload["constant"]["address"] == "0x00aa9a20"
    assert payload["constant"]["f64_value"] == 0.5
    assert payload["constant"]["raw_le_hex"] == "000000000000e03f"

    formula = payload["formula"]
    assert "FUN_00753590" in formula["pointer_sum"]
    assert "0.5" in formula["pointer_midpoint"]
    assert formula["local_base_x"] == "pointer_midpoint.x"
    assert formula["local_base_y"] == "-source_scalar_0338"
    assert formula["local_base_z"] == "pointer_midpoint.z"
    assert "source_vec_0918" in formula["local_sample_3938"]
    assert formula["midpoint_y_not_used_in_local_base"] is True


def test_native_source_core_keeps_retail_store_boundaries() -> None:
    header = HEADER.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    assert "SHIFT.Fun007618f0LocalSampleProducer/1" in header
    assert "hdvehicle_pointer_vec_0820" in header
    assert "hdvehicle_pointer_vec_12a0" in header
    assert "source_scalar_0338" in header
    assert "source_vec_0918" in header
    assert "local_sample_3938" in header

    assert "retail_add_f64" in source
    assert "retail_mul_f64" in source
    assert "pointer_sum[index]" in source
    assert "result.pointer_midpoint[index]" in source
    assert "0.5" in source
    assert "-static_cast<long double>(input.source_scalar_0338)" in source
    assert "input.source_vec_0918[index]" in source


def test_phase728_does_not_claim_storage_owners_or_active_session_join() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    native = payload["native_consumption"]
    scope = payload["scope"]
    session = SESSION_SOURCE.read_text(encoding="utf-8")

    assert native["source_core_native"] is True
    assert native["active_session_joined"] is False
    assert scope["input_storage_owners_joined"] is False
    assert scope["pointer_target_lifetimes_proven"] is False
    assert scope["second_source_argument_semantic_name_claimed"] is False
    assert scope["HDVehicle_0x3938_formula_internalized"] is True
    assert scope["per_pass_BODY0_snapshot_joined"] is False
    assert scope["collision_provider_internalized"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False

    assert "execute_fun_007618f0_local_sample_producer" not in session
