from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_world_position_transform.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_world_position_transform.hpp"
SOURCE = ROOT / "native_runtime/src/fun_00765c40_world_position_transform.cpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_retail_machine_spans_lock_exact_two_stage_transform() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40WorldPositionTransform/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    spans = {row["role"]: row for row in payload["machine_spans"]}
    assert spans["FUN_00765c40 two-stage world-position producer call site"]["raw_byte_sha256"] == (
        "b040d039c8913e6c9f332159ee20dc393f6454a564f9da2f955c45be6fda5015"
    )
    assert spans["FUN_007aefb0 BODY0 basis times local f64 vec3"]["raw_byte_sha256"] == (
        "76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29"
    )
    assert spans["FUN_00753590 f64 vec3 addition"]["raw_byte_sha256"] == (
        "29ad42134f1176109058b222289fc03a1654034956d44d7f5dafadd20e1aa8e6"
    )
    assert spans["FUN_007618f0 local sample write to HDVehicle+0x3938"]["raw_byte_sha256"] == (
        "3c4b74dedbf14f6a6be5b91b732a49fbffed11d2d0ac67af68b3111b3cfb2a5d"
    )


def test_retail_dataflow_uses_body0_not_renderer_vhf_path() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    flow = payload["retail_dataflow"]
    assert flow["body_pointer"] == "HDVehicle+0x33a0 (selected BMW chassis BODY0)"
    assert flow["body_origin"] == ["BODY0+0x00 f64", "BODY0+0x08 f64", "BODY0+0x10 f64"]
    assert flow["body_basis"] == "BODY0+0xd4..+0xf4, 9 contiguous f32 values"
    assert flow["local_sample"] == "HDVehicle+0x3938/+0x3940/+0x3948 f64 vec3"
    assert flow["rotated_scratch"] == "HDVehicle+0x38f0/+0x38f8/+0x3900 f64 vec3"
    assert flow["rotation_helper"] == "FUN_007aefb0"
    assert flow["origin_add_helper"] == "FUN_00753590"
    assert flow["world_position_formula"] == (
        "BODY0.origin + BODY0.basis * HDVehicle.local_sample_0x3938"
    )
    assert payload["scope"]["renderer_BODY0_VHF_transform_used"] is False


def test_native_transform_preserves_retail_instruction_grouping() -> None:
    header = HEADER.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    assert "SHIFT.Fun00765c40WorldPositionTransform/1" in header
    assert "execute_fun_00765c40_world_position_transform" in header
    assert "BodyRecordBytes" in header
    assert "CollisionQueryVector3d" in header

    assert "body_record_offset::kBasis" in source
    assert "body_record_offset::kOrigin" in source
    assert "mul(basis[1], local_sample_position[1])" in source
    assert "mul(basis[0], local_sample_position[0])" in source
    assert "mul(basis[2], local_sample_position[2])" in source
    assert "retail_store_f64(row0)" in source
    assert "result.body_rotated_local[0]" in source


def test_phase727_keeps_local_sample_and_per_pass_runtime_join_external() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    local = payload["local_sample_producer"]
    native = payload["native_consumption"]
    scope = payload["scope"]
    session = SESSION_SOURCE.read_text(encoding="utf-8")

    assert local["writer_function"] == "FUN_007618f0"
    assert local["complete_semantics_internalized"] is False
    assert native["final_transform_native"] is True
    assert native["active_session_joined"] is False
    assert scope["final_world_position_transform_internalized"] is True
    assert scope["HDVehicle_0x3938_local_sample_producer_internalized"] is False
    assert scope["FUN_007618f0_complete_semantics_claimed"] is False
    assert scope["per_pass_BODY0_snapshot_joined_to_FUN_00765c40"] is False
    assert scope["collision_provider_internalized"] is False
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False

    assert "execute_fun_00765c40_world_position_transform" not in session
