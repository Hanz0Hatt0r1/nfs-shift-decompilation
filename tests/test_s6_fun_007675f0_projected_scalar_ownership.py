from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "fun_007675f0_projected_scalar_ownership.json"
CONTACT_HEADER = ROOT / "native_runtime" / "include" / "shift_contact_outer_kernel.hpp"
AGGREGATE_HEADER = ROOT / "native_runtime" / "include" / "shift_wheel_force_aggregate.hpp"
AGGREGATE_SOURCE = ROOT / "native_runtime" / "src" / "wheel_force_aggregate.cpp"
KERNEL = ROOT / "native_runtime" / "src" / "contact_outer_kernel.cpp"


def _session_struct(text: str) -> str:
    return text.split("struct ContactOuterSessionInput", 1)[1].split(
        "struct Fun007675f0BodyMotion", 1
    )[0]


def test_phase736_freezes_pc_machine_evidence() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["phase"] == 736
    pc = payload["pc_authority"]
    assert pc["sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert pc["caller_projection_span"] == {
        "start": "0x0076779f",
        "end_exclusive": "0x007677e2",
        "sha256": "35176a6a1a6f96546fa3da56aac56c585d4724da9aa5e32850cadbe001ee4aaf",
    }
    assert pc["aggregate_function_span"] == {
        "start": "0x00759c90",
        "end_exclusive": "0x00759dab",
        "sha256": "a32046ea002f8e570a093148ba08ed242d1e47e2d810cc0ad7c916e0697e989a",
    }


def test_phase736_locks_three_record_source_geometry() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    contract = payload["aggregate_contract"]
    assert contract["record_base"] == "HDVehicle+0x7f0"
    assert contract["record_count"] == 3
    assert contract["pointer_increment_double_elements"] == "0x150"
    assert contract["record_stride_bytes"] == "0xa80"
    assert contract["per_record_fields"] == {
        "scalar_a": "+0x00",
        "vector_a": "+0xb0",
        "scalar_b": "-0x08",
        "vector_b": "+0x98",
        "point_for_second_output_only": "+0xf8",
    }


def test_phase736_production_payload_moves_from_scalar_to_records() -> None:
    header = CONTACT_HEADER.read_text(encoding="utf-8")
    session = _session_struct(header)
    assert "Fun00759c90RecordSet fun_00759c90_records" in session
    assert "double projected_scalar" not in session
    assert "compatibility_projected_scalar" in session

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["native_handoff"]
    assert handoff["production_projected_scalar_field_present"] is False
    assert handoff["production_fun_00759c90_record_set_present"] is True
    assert handoff["compatibility_projected_scalar_preserved"] is True
    assert handoff["top_level_external_provider_count"] == 7


def test_phase736_reuses_phase660_weighted_total_and_source_projection_order() -> None:
    aggregate_header = AGGREGATE_HEADER.read_text(encoding="utf-8")
    aggregate_source = AGGREGATE_SOURCE.read_text(encoding="utf-8")
    kernel = KERNEL.read_text(encoding="utf-8")

    assert "execute_fun_00759c90_weighted_total" in aggregate_header
    assert "result.total = execute_fun_00759c90_weighted_total(records);" in aggregate_source
    assert "execute_fun_007675f0_projected_scalar(" in kernel
    assert "execute_fun_00759c90_weighted_total(records)" in kernel
    assert "static_cast<double>(total_x) * direction_x + 0.0 +" in kernel
    assert "static_cast<double>(total_z) * direction_z" in kernel
    assert "result.projected_scalar_derived = true" in kernel


def test_phase736_keeps_xbox_as_non_authoritative_corroboration() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    xbox = payload["xbox_recomp_corroboration"]
    assert xbox["authoritative_for_pc"] is False
    assert xbox["file"] == "nfs_shift_recomp.223.cpp"
    assert xbox["sha256"] == (
        "5bb094f6125c6611f39ecd9fb759907004115c7ffc1d33d99173506479eba5dd"
    )
    assert xbox["caller"] == "sub_825939F0"
    assert xbox["aggregate"] == "sub_825899C0"
