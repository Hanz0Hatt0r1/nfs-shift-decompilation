from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_surface_probe_join.json"
HEADER = ROOT / "native_runtime/include/shift_contact_outer_kernel.hpp"
SOURCE = ROOT / "native_runtime/src/contact_outer_kernel.cpp"
CHAIN = ROOT / "native_runtime/src/fun_00770e80_contact_outer_provider_chain.cpp"
ORACLE = ROOT / "src/physics/physics_helper_675f0_runtime.py"


def test_pc_machine_mapping_and_node_ownership_are_explicit() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007675f0SurfaceProbeJoin/1"
    assert payload["ready"] is True
    assert payload["source"]["sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["fun_007675f0"] == "0x007675f0"
    assert payload["source"]["fun_00759210"] == "0x00759210"
    assert payload["caller_mapping"]["fun_00759210_call"] == "0x00767643"
    assert payload["caller_mapping"]["node_pointer_source"] == (
        "FUN_007675f0 first stack argument"
    )
    assert payload["caller_mapping"]["planar_delta"] == (
        "FUN_00759210 output point - BODY query point"
    )
    assert payload["caller_mapping"]["surface_scalar"] == (
        "FUN_00759210 output scalar"
    )
    assert payload["node_ownership"]["owner"] == "HDVehicle+0x120"
    assert payload["node_ownership"]["refresh_provider"] == "FUN_00717cd0"
    assert payload["node_ownership"]["refresh_provider_internalized"] is False


def test_production_payload_replaces_planar_and_surface_with_typed_node() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["remaining_external_field_count"] == 5
    assert payload["remaining_external_fun_007675f0_fields"] == [
        "surface_probe_node",
        "base_scalar",
        "projected_scalar",
        "alignment_scalar",
        "param_3",
    ]
    assert payload["scope"]["external_provider_count_before"] == 7
    assert payload["scope"]["external_provider_count_after"] == 7
    assert payload["scope"]["provider_count_reduced"] is False

    header = HEADER.read_text(encoding="utf-8")
    session_struct = header.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]
    assert "const SurfaceProbeNode* surface_probe_node" in session_struct
    assert "ContactOuterVector3d planar_delta{}" not in session_struct
    assert "double surface_scalar = 0.0" not in session_struct
    assert "compatibility_planar_delta" in session_struct
    assert "compatibility_surface_scalar" in session_struct

    historical_struct = header.split("struct ContactOuterExternalInput", 1)[1].split(
        "struct ContactOuterSessionInput", 1
    )[0]
    assert "ContactOuterVector3d planar_delta{}" in historical_struct
    assert "double surface_scalar = 0.0" in historical_struct


def test_native_join_uses_current_body_probe_and_existing_surface_probe() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    chain = CHAIN.read_text(encoding="utf-8")

    assert "derive_fun_007675f0_body0_probe_state" in source
    assert "kFun007675f0Body0PositionXOffset" in source
    assert "spill_f64_to_f32" in source
    assert "execute_fun_00759210_surface_probe" in source
    assert "probe.point" in source
    assert "probe.scalar" in source
    assert "resolve_fun_007675f0_surface_probe_input" in chain
    assert "derive_fun_007675f0_body0_probe_state" in chain


def test_active_gap_uses_filtered_state_not_raw_distance() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    gap = payload["gap_machine_correction"]
    assert gap["filtered_state_write_hdvehicle_0x4080"] == "0x00767700"
    assert gap["gap_use_span"] == "0x00767937..0x00767949"
    assert gap["gap_offset_constant"] == 1.5
    assert gap["correct_formula"] == (
        "filtered_distance_state - (surface_scalar - 1.5)"
    )
    assert gap["active_runtime_corrected"] is True

    source = SOURCE.read_text(encoding="utf-8")
    oracle = ORACLE.read_text(encoding="utf-8")
    assert "result.filtered_distance_state -" in source
    assert "filtered_distance_state-(surface_scalar-GAP_OFFSET)" in oracle
