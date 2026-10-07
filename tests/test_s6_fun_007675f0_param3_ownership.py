from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007675f0_param3_ownership.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00769ef0_param3.hpp"
KERNEL_HEADER = ROOT / "native_runtime/include/shift_contact_outer_kernel.hpp"
CHAIN = ROOT / "native_runtime/src/fun_00770e80_contact_outer_provider_chain.cpp"
SESSION = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
PHASE732 = ROOT / "evidence/fun_007675f0_surface_probe_join.json"


def test_pc_machine_contract_and_exact_constant_are_frozen() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007675f0Param3Ownership/1"
    assert payload["ready"] is True
    assert payload["source"]["executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    machine = payload["machine_evidence"]
    assert machine["producer_span"]["sha256"] == (
        "bc51cb790747aeb9eed889678a7b72e508c0e9991c6854820493a46fe2d87a22"
    )
    assert machine["call_span"]["sha256"] == (
        "8158017874872b7e9e0081b19dbaef498aae92521bbeb67fd635e149c200f090"
    )
    assert machine["consumer_span"]["sha256"] == (
        "0a1f66073dedfa1b95222d46cdc99d413c39528ca0119c66a649102b12e3236d"
    )
    assert machine["scale_constant"]["f64_bits"] == "0x40239eb851eb851f"
    assert machine["scale_constant"]["sha256"] == (
        "3043fd6ddec9a67a13d1e668dee87697720daf8c3fe8a217d15e3b86b1f12501"
    )
    assert machine["zero_constant"]["sha256"] == (
        "af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc"
    )


def test_native_deriver_preserves_source_boundaries() -> None:
    header = HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00769ef0Param3/1" in header
    assert "kFun00769ef0Body0Field120Offset = 0x120u" in header
    assert "0x1.39eb851eb851fp+3" in header
    assert "validate_fun_00765c40_load_terms" in header
    assert "load_terms[0]" in header
    assert "fun_00769ef0_add64(load_sum, 0.0)" in header
    assert "fun_00769ef0_retail_f32_spill" in header
    assert "fun_00769ef0_clamp01_f32" in header
    assert "BODY0 +0x120 cannot be zero" in header


def test_production_payload_no_longer_accepts_param3() -> None:
    header = KERNEL_HEADER.read_text(encoding="utf-8")
    session_struct = header.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]
    production = session_struct.split(
        "bool compatibility_surface_probe_outputs_present", 1
    )[0]
    assert "double param_3" not in production
    assert "compatibility_param_3_present" in session_struct
    assert "compatibility_param_3" in session_struct

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["scope"]["production_contact_outer_fields_before"] == 5
    assert payload["scope"]["production_contact_outer_fields_after"] == 4
    assert payload["scope"]["remaining_production_fields"] == [
        "surface_probe_node",
        "base_scalar",
        "projected_scalar",
        "alignment_scalar",
    ]
    assert payload["scope"]["external_provider_count_after"] == 7


def test_same_pass_load_terms_and_current_body_feed_param3() -> None:
    chain = CHAIN.read_text(encoding="utf-8")
    session = SESSION.read_text(encoding="utf-8")

    assert "derive_fun_00769ef0_body0_field_120(current_body_bytes)" in chain
    assert "external.fun_00769ef0_param_3_load_terms_present" in chain
    assert "execute_fun_00769ef0_param_3" in chain
    assert "state->body_field_120" in chain

    assert "FUN_007675f0 param_3 requested before FUN_00765c40 load terms" in session
    assert "external.fun_00769ef0_param_3_load_terms = load_state->terms" in session
    assert "external.fun_00769ef0_param_3_load_terms_present = true" in session

    contact_factor = session.index("callbacks.contact_factor")
    contact_outer = session.index("callbacks.contact_outer_input_provider")
    assert contact_factor < contact_outer


def test_phase732_evidence_remains_immutable_history() -> None:
    phase732 = json.loads(PHASE732.read_text(encoding="utf-8"))
    assert phase732["format"] == "SHIFT.Fun007675f0SurfaceProbeJoin/1"
    assert phase732["scope"]["remaining_production_fun_007675f0_fields"][-1] == "param_3"
