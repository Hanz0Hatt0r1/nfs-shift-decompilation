from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_player_vehicle_render_manager_indirect_method_ca4_access.py"
SPEC = importlib.util.spec_from_file_location("analyze_player_vehicle_render_manager_indirect_method_ca4_access", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _direct_negative(path: Path):
    return _write_json(
        path,
        {
            "format": m._direct.FORMAT,
            "ready": False,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {
                "address": m.CANDIDATE_GLOBAL,
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


def _indirect(path: Path, targets=("0x0045f620", "0x0045f630")):
    calls = [
        {
            "function": "0x0056bcd0",
            "call_instruction": "0x0056bcf2",
            "resolved_target": targets[0],
            "manager_receiver_register_at_call": "ECX",
            "manager_receiver_identity_proven": True,
            "constructor_primary_table_identity_proven": True,
            "static_slot_target_proven": True,
            "straight_line_slot_load_proven": True,
        },
        {
            "function": "0x0056bcd0",
            "call_instruction": "0x0056bd09",
            "resolved_target": targets[1],
            "manager_receiver_register_at_call": "ECX",
            "manager_receiver_identity_proven": True,
            "constructor_primary_table_identity_proven": True,
            "static_slot_target_proven": True,
            "straight_line_slot_load_proven": True,
        },
        {
            "function": "0x0056bd30",
            "call_instruction": "0x0056bd59",
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
            "format": m.INDIRECT_FORMAT,
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


def _ins(address, mnemonic, operands=None, *, fallthrough=None, flows=None, pcode=None):
    operands = [] if operands is None else operands
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else flows,
        "flow_type": "TERMINATOR" if mnemonic == "RET" else "FALL_THROUGH",
        "references": [],
        "pcode": [] if pcode is None else pcode,
    }


def _slice(start: str, instructions, *, length=0x40):
    return {
        "format": m.SLICE_FORMAT,
        "program": m.PROGRAM,
        "requested": start,
        "start": start,
        "length": length,
        "exact_instruction_at_start": True,
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _positive_lane(start="0x0045f620"):
    return [
        _ins(start, "MOV", ["ESI", "ECX"], fallthrough="0x0045f622"),
        _ins(
            "0x0045f622",
            "MOV",
            ["EAX", "dword ptr [ESI + 0xca4]"],
            fallthrough="0x0045f628",
            pcode=[{"opcode": "LOAD", "text": "LOAD ca4"}],
        ),
        _ins("0x0045f628", "RET"),
    ]


def _inputs(tmp_path: Path, first, second=None):
    if second is None:
        second = [_ins("0x0045f630", "RET")]
    direct = _direct_negative(tmp_path / "direct.json")
    indirect = _indirect(tmp_path / "indirect.json")
    slices = _write_jsonl(
        tmp_path / "slices.jsonl",
        [_slice("0x0045f620", first), _slice("0x0045f630", second)],
    )
    return direct, indirect, slices


def test_proves_resolved_indirect_entry_ecx_ca4_read(tmp_path):
    report = m.analyze(*_inputs(tmp_path, _positive_lane()))
    assert report["ready"] is True
    assert report["status"] == "indirect-manager-method-ca4-read-ready"
    assert report["provenance"]["exact_entry_ecx_ca4_read_count"] == 1
    proof = report["analysis"]["proven_ca4_reads"][0]
    assert proof["entry"] == "0x0045f620"
    assert proof["base_origins_before_access"] == ["entry:ECX"]
    assert report["owner_trace_worklist"]["entries"] == ["0x0045f620"]
    assert report["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] is True
    assert report["handoff"]["player_vehicle_renderables_owner_join_ready"] is False


def test_complete_negative_closes_indirect_method_branch(tmp_path):
    first = [_ins("0x0045f620", "RET")]
    report = m.analyze(*_inputs(tmp_path, first))
    assert report["ready"] is False
    assert report["status"] == "indirect-manager-method-ca4-access-not-found"
    assert report["provenance"]["cfg_complete_target_count"] == 2
    assert report["provenance"]["negative_branch_closed"] is True


def test_incomplete_slice_cannot_be_negative_proof(tmp_path):
    first = [_ins("0x0045f620", "MOV", ["EAX", "ECX"], fallthrough="0x0045f622")]
    report = m.analyze(*_inputs(tmp_path, first))
    assert report["ready"] is False
    assert report["status"] == "indirect-manager-method-ca4-acquisition-incomplete"
    assert report["provenance"]["negative_branch_closed"] is False
    assert report["analysis"]["targets"][0]["cfg_completeness_issues"]


def test_wrong_entry_origin_does_not_promote_ca4(tmp_path):
    first = [
        _ins("0x0045f620", "MOV", ["ESI", "EDX"], fallthrough="0x0045f622"),
        _ins(
            "0x0045f622",
            "MOV",
            ["EAX", "dword ptr [ESI + 0xca4]"],
            fallthrough="0x0045f628",
            pcode=[{"opcode": "LOAD", "text": "LOAD ca4"}],
        ),
        _ins("0x0045f628", "RET"),
    ]
    report = m.analyze(*_inputs(tmp_path, first))
    assert report["ready"] is False
    assert report["provenance"]["ca4_candidate_count"] == 1
    assert report["provenance"]["exact_entry_ecx_ca4_read_count"] == 0


def test_rejects_slice_target_set_drift(tmp_path):
    direct = _direct_negative(tmp_path / "direct.json")
    indirect = _indirect(tmp_path / "indirect.json")
    slices = _write_jsonl(
        tmp_path / "slices.jsonl",
        [_slice("0x0045f620", [_ins("0x0045f620", "RET")])],
    )
    with pytest.raises(ValueError, match="slice target set drift"):
        m.analyze(direct, indirect, slices)


def test_rejects_non_ecx_manager_receiver(tmp_path):
    direct = _direct_negative(tmp_path / "direct.json")
    indirect_path = _indirect(tmp_path / "indirect.json")
    indirect = json.loads(indirect_path.read_text(encoding="utf-8"))
    indirect["analysis"]["resolved_indirect_calls"][0]["manager_receiver_register_at_call"] = "EDX"
    indirect_path.write_text(json.dumps(indirect) + "\n", encoding="utf-8")
    slices = _write_jsonl(
        tmp_path / "slices.jsonl",
        [
            _slice("0x0045f620", [_ins("0x0045f620", "RET")]),
            _slice("0x0045f630", [_ins("0x0045f630", "RET")]),
        ],
    )
    with pytest.raises(ValueError, match="receiver is not ECX"):
        m.analyze(direct, indirect_path, slices)


def test_slice_exporter_is_exact_address_based():
    source = (ROOT / "tools" / "ghidra" / "ShiftInstructionSliceExporter.java").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "ghidra" / "run_shift_instruction_slices.sh").read_text(encoding="utf-8")
    assert "listing.getInstructionAt(start)" in source
    assert "new AddressSet(start, end)" in source
    assert "getFunctionAt" not in source
    assert "ShiftInstructionSliceExporter.java" in runner
