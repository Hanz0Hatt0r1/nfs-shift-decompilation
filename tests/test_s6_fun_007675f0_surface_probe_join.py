from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_surface_probe_join.json"
PHASE731 = ROOT / "evidence/fun_007675f0_distance_filter_cap_ownership.json"
KERNEL_HEADER = ROOT / "native_runtime/include/shift_contact_outer_kernel.hpp"
KERNEL_SOURCE = ROOT / "native_runtime/src/contact_outer_kernel.cpp"
CHAIN_SOURCE = ROOT / "native_runtime/src/fun_00770e80_contact_outer_provider_chain.cpp"
SURFACE_PROBE_HEADER = ROOT / "native_runtime/include/shift_surface_probe.hpp"


def test_pc_caller_join_and_xbox_corroboration_are_frozen() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007675f0SurfaceProbeJoin/1"
    assert payload["ready"] is True

    pc = payload["pc_retail"]
    assert pc["sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert pc["caller"] == "FUN_007675f0"
    assert pc["caller_address"] == "0x007675f0"
    assert pc["probe"] == "FUN_00759210"
    assert pc["probe_address"] == "0x00759210"
    assert pc["node_pointer_input"]["instruction"] == "0x0076760c: mov edx,[ebx+0x8]"
    assert pc["node_pointer_input"]["producer_proven"] is False
    assert pc["body_query_position"]["source_offsets"] == [
        "BODY0+0x00",
        "BODY0+0x08",
        "BODY0+0x10",
    ]
    assert pc["body_query_position"]["caller_spill_storage"] == "f32"
    assert pc["probe_call"]["call_instruction"] == "0x00767643: call 0x00759210"
    assert pc["delta_join"]["helper"] == "0x004a7870"
    assert pc["delta_join"]["operation"] == "float32 lane-wise left - right"
    assert pc["scalar_join"]["native_field"] == "surface_scalar"

    xbox = payload["xbox360_retail_crosscheck"]
    assert xbox["xex_sha256"] == (
        "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
    )
    assert xbox["probe_counterpart"] == "0x8258ffb8"
    assert xbox["probe_call_instruction"] == "0x8259aa44: bl 0x8258ffb8"
    assert xbox["cross_platform_support_only"] is True
    assert xbox["authoritative_for_pc_layout"] is False


def test_active_session_payload_exposes_node_not_derived_probe_outputs() -> None:
    header = KERNEL_HEADER.read_text(encoding="utf-8")
    session_struct = header.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]
    production_prefix = session_struct.split(
        "bool compatibility_surface_probe_outputs_present", 1
    )[0]

    assert "const SurfaceProbeNode* surface_probe_node" in production_prefix
    assert "planar_delta" not in production_prefix
    assert "surface_scalar" not in production_prefix
    assert "double projected_scalar" in production_prefix
    # Later source-backed closures may remove fields that were still external at
    # the immutable Phase 732 frontier. They must not reintroduce the probe outputs.
    assert "double base_scalar" not in production_prefix
    assert "double alignment_scalar" not in production_prefix
    assert "double param_3" not in production_prefix
    assert "compatibility_base_scalar" in session_struct
    assert "compatibility_alignment_scalar" in session_struct
    assert "compatibility_param_3_present" in session_struct
    assert "compatibility_param_3" in session_struct

    assert "compatibility_planar_delta" in session_struct
    assert "compatibility_surface_scalar" in session_struct
    assert "compatibility_surface_probe_outputs_present" in session_struct

    surface_probe_header = SURFACE_PROBE_HEADER.read_text(encoding="utf-8")
    assert "SHIFT.NativeSurfaceProbe/1" in surface_probe_header
    assert "execute_fun_00759210_surface_probe" in surface_probe_header


def test_native_chain_derives_current_body_query_and_probe_outputs_before_kernel() -> None:
    kernel = KERNEL_SOURCE.read_text(encoding="utf-8")
    chain = CHAIN_SOURCE.read_text(encoding="utf-8")

    assert "derive_fun_007675f0_body0_probe_query_position" in kernel
    assert "execute_fun_007675f0_surface_probe_join" in kernel
    assert "execute_fun_00759210_surface_probe" in kernel
    assert "resolve_fun_007675f0_surface_probe_outputs" in kernel
    assert "surface-probe node boundary" in kernel

    body_observer = chain.index("adapted.current_body_observer")
    query_derive = chain.index("derive_fun_007675f0_body0_probe_query_position")
    contact_outer = chain.index("adapted.contact_outer")
    resolver = chain.index("resolve_fun_007675f0_surface_probe_outputs")
    compose = chain.index("compose_fun_007675f0_input")
    assert body_observer < query_derive < contact_outer < resolver < compose


def test_phase732_narrows_active_fields_but_preserves_phase731_history() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["contact_outer_production_field_count_before"] == 6
    assert scope["contact_outer_production_field_count_after"] == 5
    assert scope["derived_fields_internalized"] == ["planar_delta", "surface_scalar"]
    assert scope["new_earlier_boundary"] == "surface_probe_node"
    assert scope["remaining_production_fun_007675f0_fields"] == [
        "surface_probe_node",
        "base_scalar",
        "projected_scalar",
        "alignment_scalar",
        "param_3",
    ]

    phase731 = json.loads(PHASE731.read_text(encoding="utf-8"))
    assert phase731["format"] == "SHIFT.Fun007675f0DistanceFilterCapOwnership/1"
    assert phase731["remaining_external_field_count"] == 6
