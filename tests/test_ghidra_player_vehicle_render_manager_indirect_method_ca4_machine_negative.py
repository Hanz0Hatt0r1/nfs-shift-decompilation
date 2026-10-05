from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_player_vehicle_render_manager_indirect_method_ca4_machine_negative.py"
SPEC = importlib.util.spec_from_file_location("analyze_player_vehicle_render_manager_indirect_method_ca4_machine_negative", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

PEImage = m.PEImage
PESection = __import__("d3d9_pe_evidence").PESection


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _direct_negative(path: Path) -> Path:
    return _write_json(
        path,
        {
            "format": m._pcode._direct.FORMAT,
            "ready": False,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {
                "address": m._pcode.CANDIDATE_GLOBAL,
                "render_manager_class_identity_proven": True,
            },
            "constructor_layout_anchor": {
                "function": "0x0045ef50",
                "field_offset": "+0xca4",
                "allocation_label": "mPlayerVehicleRenderables",
                "source_backed": True,
            },
            "provenance": {
                "targeted_direct_callee_count": 17,
                "exact_entry_pointer_ca4_read_count": 0,
            },
        },
    )


def _indirect(path: Path, targets=("0x0045f620", "0x0045f630")) -> Path:
    calls = [
        {
            "resolved_target": targets[0],
            "manager_receiver_register_at_call": "ECX",
            "manager_receiver_identity_proven": True,
            "constructor_primary_table_identity_proven": True,
            "static_slot_target_proven": True,
            "straight_line_slot_load_proven": True,
        },
        {
            "resolved_target": targets[1],
            "manager_receiver_register_at_call": "ECX",
            "manager_receiver_identity_proven": True,
            "constructor_primary_table_identity_proven": True,
            "static_slot_target_proven": True,
            "straight_line_slot_load_proven": True,
        },
        {
            "resolved_target": targets[0],
            "manager_receiver_register_at_call": "ECX",
            "manager_receiver_identity_proven": True,
            "constructor_primary_table_identity_proven": True,
            "static_slot_target_proven": True,
            "straight_line_slot_load_proven": True,
        },
    ]
    return _write_json(
        path,
        {
            "format": m._pcode.INDIRECT_FORMAT,
            "ready": True,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "analysis": {"resolved_indirect_calls": calls},
            "provenance": {"resolved_indirect_call_count": 3},
            "targeted_instruction_worklist": {
                "functions": list(targets),
                "function_count": len(targets),
                "neighbors_added": False,
            },
            "handoff": {
                "candidate_global_manager_indirect_dispatch_resolved": True,
                "candidate_global_manager_indirect_method_worklist_ready": True,
            },
        },
    )


def _fake_image(*, getter_disp=m.OBSERVED_OFFSET, setter_disp=m.OBSERVED_OFFSET, getter_opcode=b"\x8b\x81") -> PEImage:
    section_va = 0x1000
    size = 0x70000
    data = bytearray(size)
    getter = getter_opcode + int(getter_disp).to_bytes(4, "little", signed=True) + b"\xc3"
    setter = bytes.fromhex("558bec8b45088981") + int(setter_disp).to_bytes(4, "little", signed=True) + bytes.fromhex("5dc20400")
    for address, payload in ((m.GETTER, getter), (m.SETTER, setter)):
        offset = (address - m.IMAGE_BASE) - section_va
        data[offset : offset + len(payload)] = payload
    return PEImage(
        data=bytes(data),
        image_base=m.IMAGE_BASE,
        machine=m.MACHINE_I386,
        optional_magic=0x10B,
        sections=(
            PESection(
                name=".text",
                virtual_address=section_va,
                virtual_size=size,
                raw_pointer=0,
                raw_size=size,
            ),
        ),
    )


def _machine(image: PEImage | None = None):
    return m.analyze_image(
        image or _fake_image(),
        executable_md5=m.PE_MD5,
        executable_sha256=m.PE_SHA256,
        require_retail_identity=True,
    )


def test_exact_retail_machine_shapes_close_indirect_ca4_branch():
    report = _machine()
    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["status"] == "proven"
    assert report["analysis"]["target_count"] == 2
    assert report["analysis"]["cfg_complete_target_count"] == 2
    assert report["analysis"]["ca4_access_count"] == 0
    assert report["analysis"]["observed_ecx_relative_offsets"] == [0xDAC]
    assert report["claim"]["indirect_manager_method_ca4_branch_negative"] is True
    assert report["claim"]["only_observed_ecx_relative_offset_is_dac"] is True
    getter, setter = report["analysis"]["targets"]
    assert getter["body_hex"] == "8b81ac0d0000c3"
    assert getter["memory_accesses"][0]["kind"] == "read"
    assert getter["memory_accesses"][0]["displacement"] == 0xDAC
    assert setter["body_hex"] == "558bec8b45088981ac0d00005dc20400"
    assert setter["memory_accesses"][1]["kind"] == "write"
    assert setter["memory_accesses"][1]["displacement"] == 0xDAC


def test_ca4_displacement_does_not_close_negative_branch():
    report = _machine(_fake_image(getter_disp=0xCA4))
    assert report["ready"] is False
    assert report["analysis"]["ca4_access_count"] == 1
    assert report["claim"]["indirect_manager_method_ca4_branch_negative"] is False


def test_opcode_drift_fails_closed():
    with pytest.raises(ValueError, match="0x0045f620 machine body drift"):
        _machine(_fake_image(getter_opcode=b"\x8b\x89"))


def test_retail_identity_drift_fails_closed():
    with pytest.raises(ValueError, match="md5"):
        m.analyze_image(
            _fake_image(),
            executable_md5="0" * 32,
            executable_sha256=m.PE_SHA256,
            require_retail_identity=True,
        )


def test_upstream_join_closes_complete_manager_method_hypothesis(tmp_path: Path):
    machine = _machine()
    report = m._validate_upstream_and_compose(
        _direct_negative(tmp_path / "direct.json"),
        _indirect(tmp_path / "indirect.json"),
        machine,
    )
    assert report["handoff"]["direct_manager_method_ca4_branch_negative"] is True
    assert report["handoff"]["indirect_manager_method_ca4_branch_negative"] is True
    assert report["handoff"]["manager_method_ca4_hypothesis_closed"] is True
    assert report["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] is False
    assert report["handoff"]["bmw_body0_bind_frame_proof_ready"] is False
    assert report["handoff"]["next_frontier"]["functions"] == [
        "0x007b3670",
        "0x007bba90",
        "0x007bbb10",
        "0x007bbb60",
    ]
    assert report["handoff"]["next_frontier"]["neighbors_added"] is False


def test_resolved_target_set_drift_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="target set drift"):
        m._validate_upstream_and_compose(
            _direct_negative(tmp_path / "direct.json"),
            _indirect(tmp_path / "indirect.json", targets=("0x0045f620", "0x0045f640")),
            _machine(),
        )


def test_cli_surface_requires_upstream_proofs_and_retail_executable():
    args = m.build_parser().parse_args(["direct.json", "indirect.json", "SHIFT.exe"])
    assert args.direct_negative == Path("direct.json")
    assert args.indirect_dispatch == Path("indirect.json")
    assert args.executable == Path("SHIFT.exe")
