from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "fun_007675f0_body_owned_scalars.json"
HEADER = ROOT / "native_runtime" / "include" / "shift_contact_outer_kernel.hpp"
DERIVER = ROOT / "native_runtime" / "include" / "shift_fun_007675f0_body_owned_scalars.hpp"
KERNEL = ROOT / "native_runtime" / "src" / "contact_outer_kernel.cpp"
CHAIN = ROOT / "native_runtime" / "src" / "fun_00770e80_contact_outer_provider_chain.cpp"


def _session_struct(text: str) -> str:
    return text.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]


def test_phase735_evidence_freezes_pc_authority_and_xbox_corroboration() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["phase"] == 735
    assert payload["pc_authority"]["sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["pc_authority"]["decompiler_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["pc_authority"]["function"] == "FUN_007675f0"
    assert payload["pc_authority"]["decompiler_line"] == 759784
    assert payload["pc_authority"]["machine_spans"][0]["sha256"] == (
        "82c0223f82e946c02948f997e46e1b9f729d43249cf1818c880a21e1b0bf9664"
    )
    xbox = payload["xbox_recomp_corroboration"]
    assert xbox["authoritative_for_pc"] is False
    assert xbox["function"] == "sub_825939F0"
    assert xbox["file"] == "nfs_shift_recomp.223.cpp"
    assert xbox["matching_hex_offsets"] == {
        "vehicle_body_pointer": "0x33a0",
        "vehicle_filtered_distance": "0x4080",
        "body_motion_x": "0x78",
        "body_motion_z": "0x88",
        "body_scalar": "0x120",
    }
    assert "sub_8259A978" in xbox["correction"]


def test_phase735_production_payload_drops_base_and_alignment_scalars() -> None:
    header = HEADER.read_text(encoding="utf-8")
    session = _session_struct(header)
    assert "const SurfaceProbeNode* surface_probe_node" in session
    assert "double base_scalar" not in session
    assert "double alignment_scalar" not in session
    assert "compatibility_base_scalar" in session
    assert "compatibility_alignment_scalar" in session
    assert "compatibility_body_owned_scalars_present" in session

    # Phase735 evidence is immutable history: at that phase projected_scalar was
    # still a production field. Later phases may narrow the live session further.
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["native_handoff"]
    assert handoff["production_base_scalar_field_present"] is False
    assert handoff["production_alignment_scalar_field_present"] is False
    assert handoff["production_projected_scalar_field_present"] is True
    assert handoff["top_level_external_provider_count"] == 7


def test_phase735_derivation_reuses_current_body_and_filtered_distance() -> None:
    deriver = DERIVER.read_text(encoding="utf-8")
    kernel = KERNEL.read_text(encoding="utf-8")
    chain = CHAIN.read_text(encoding="utf-8")

    assert "execute_fun_007675f0_body_owned_scalars(" in deriver
    assert "filtered_distance_state" in deriver
    assert "body_field_120" in deriver
    assert "perpendicular_motion" in deriver
    assert "alignment_scalar" in deriver
    assert "fun_007675f0_source_cross_f32" in deriver
    assert "fun_007675f0_source_normalize_f32" in deriver

    assert "if (result.gate_open)" in kernel
    assert "result.filtered_distance_state" in kernel
    assert "input.body_field_120" in kernel
    assert "result.body_owned_scalars_derived = true" in kernel

    assert "derive_fun_007675f0_body0_motion(current_body_bytes)" in chain
    assert "derive_fun_00769ef0_body0_field_120(current_body_bytes)" in chain
    assert "external.fun_007675f0_body_field_120 =" in chain
    assert "state->body_field_120" in chain


def test_phase735_records_projected_scalar_as_that_phase_next_blocker() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    provenance = payload["pc_recovered_provenance"]
    assert provenance["remaining_external_scalar"] == "projected_scalar"
    assert "FUN_00759c90" in provenance["projected_scalar_note"]
