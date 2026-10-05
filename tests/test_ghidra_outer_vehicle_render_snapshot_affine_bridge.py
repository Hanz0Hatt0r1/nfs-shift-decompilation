from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_outer_vehicle_render_snapshot_affine_bridge.py"
SPEC = importlib.util.spec_from_file_location("outer_bridge", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_report_keeps_vhf_gate_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(m, "_validate_database", lambda path: None)
    monkeypatch.setattr(m, "_validate_source", lambda path: "a" * 64)
    monkeypatch.setattr(
        m,
        "_validate_pe",
        lambda path: [{"address": "0x0047f9fb", "bytes": "00"}],
    )

    report = m.analyze(tmp_path, tmp_path / "SHIFT.exe.c", tmp_path / "SHIFT.exe")

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["slot_identity"]["physical_slot_producer_consumer_bridge_ready"] is True
    assert report["snapshot_relation"]["translation_formula"] == (
        "P_snapshot = P_outer + R_outer * delta_local"
    )
    assert report["handoff"]["outer_vehicle_to_render_root_symbolic_affine_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["next_proof"]["new_runtime_capture_required"] is False


def test_source_fact_drift_rejected(tmp_path):
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        "void FUN_007839a0(void *this, int param_1) "
        "{ *(int *)((int)this + 0x84c) = param_1; }",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        m._validate_source(source)


def test_extract_function_handles_nested_body():
    text = "void FUN_X(int a) { if (a) { a++; } }\nvoid FUN_Y(void) { }\n"
    body = m._extract_function(text, "FUN_X")
    assert "a++" in body
    assert "FUN_Y" not in body


def test_machine_signature_map_contains_hidden_abi_edges():
    assert 0x0047F9FB in m.PE_SIGNATURES
    assert 0x0070DCDB in m.PE_SIGNATURES
    assert 0x007839A3 in m.PE_SIGNATURES
    assert m.SLOT_ARRAY - m.SLOT_MANAGER == 0x140
