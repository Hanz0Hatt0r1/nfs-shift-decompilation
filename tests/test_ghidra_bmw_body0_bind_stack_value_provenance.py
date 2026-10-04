from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_body0_bind_stack_value_provenance.py"


def _module():
    spec = importlib.util.spec_from_file_location("body0_bind_stack_value_provenance", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _ins(address, mnemonic, operands, fallthrough=None, flows=None, flow_type=None):
    if flow_type is None:
        flow_type = "UNCONDITIONAL_CALL" if mnemonic == "CALL" else "FALL_THROUGH"
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else flows,
        "flow_type": flow_type,
        "references": [],
        "pcode": [],
    }


def _row(address, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": "FUN_" + address[2:],
            "size": 100,
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _abi(m):
    stack = [
        {
            "stack_offset": offset,
            "stack_offset_hex": f"0x{offset:x}",
            "size": 4,
            "storage": f"Stack[0x{offset:x}]:4",
            "value_provenance_required_at_every_relevant_callsite": True,
        }
        for offset in (4, 8, 12, 16)
    ]
    callsites = []
    for caller, callsite in ((m.POSE_WRITER, "0x007b7d75"), ("0x007b8260", "0x007b82f4")):
        callsites.append(
            {
                "caller": caller,
                "caller_name": "FUN_" + caller[2:],
                "callsite": callsite,
                "target": m.POSE_WRITER,
                "candidate_class": "unjoined-direct-pose-writer-caller",
                "parameter_bindings": [],
                "parameter_storage_binding_ready": True,
                "register_parameter_value_provenance_ready": True,
                "stack_parameter_value_provenance_ready": False,
                "parameter_semantic_roles_ready": False,
            }
        )
    return {
        "format": m.ABI_FORMAT,
        "pose_writer": {
            "address": m.POSE_WRITER,
            "name": "FUN_007b7840",
            "calling_convention": "__thiscall",
            "parameter_count": 5,
            "register_parameter_count": 1,
            "stack_parameter_count": 4,
            "parameters": [],
        },
        "analysis": {
            "callsite_count": len(callsites),
            "callsites": callsites,
            "all_callsites_parameter_storage_bound": True,
            "all_register_parameter_values_ready": True,
            "stack_value_worklist": stack,
        },
        "handoff": {
            "pose_writer_parameter_storage_binding_ready": True,
            "pose_writer_register_argument_provenance_ready": True,
            "pose_writer_stack_argument_locations_ready": True,
            "pose_writer_stack_argument_values_ready": False,
            "pose_writer_ABI_semantic_roles_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "scope": {
            "stack_value_provenance_inferred": False,
            "BODY0_pointer_identity_proven": False,
        },
    }


def _self_row(m):
    return _row(
        m.POSE_WRITER,
        [
            _ins("0x007b7d5d", "MOV", ["EDI", "dword ptr [EBP + -0x24]"], "0x007b7d60"),
            _ins("0x007b7d60", "MOV", ["EAX", "dword ptr [EBP + -0x28]"], "0x007b7d63"),
            _ins("0x007b7d63", "MOV", ["ECX", "dword ptr [EBX + 0xc]"], "0x007b7d66"),
            _ins("0x007b7d66", "PUSH", ["EAX"], "0x007b7d67"),
            _ins("0x007b7d67", "MOV", ["EAX", "dword ptr [EBP + -0x20]"], "0x007b7d6a"),
            _ins("0x007b7d6a", "PUSH", ["EDI"], "0x007b7d6b"),
            _ins("0x007b7d6b", "PUSH", ["ECX"], "0x007b7d6c"),
            _ins("0x007b7d6c", "MOV", ["ECX", "dword ptr [EAX]"], "0x007b7d6e"),
            _ins("0x007b7d6e", "LEA", ["EDX", "[EBP + 0xfffffd50]"], "0x007b7d74"),
            _ins("0x007b7d74", "PUSH", ["EDX"], "0x007b7d75"),
            _ins("0x007b7d75", "CALL", [m.POSE_WRITER], "0x007b7d7a", [m.POSE_WRITER]),
            _ins("0x007b7d7a", "NOP", [], None),
        ],
    )


def _external_row(m):
    return _row(
        "0x007b8260",
        [
            _ins("0x007b82d3", "MOV", ["ECX", "dword ptr [EBX + 0xc]"], "0x007b82d6"),
            _ins("0x007b82d6", "FSTP", ["float ptr [EBP + -0x50]"], "0x007b82d9"),
            _ins("0x007b82d9", "FLD", ["float ptr [EAX + 0x4]"], "0x007b82dc"),
            _ins("0x007b82dc", "MOV", ["EDX", "dword ptr [EBX + 0x8]"], "0x007b82df"),
            _ins("0x007b82df", "PUSH", ["ECX"], "0x007b82e0"),
            _ins("0x007b82e0", "FSTP", ["float ptr [EBP + -0x4c]"], "0x007b82e3"),
            _ins("0x007b82e3", "FLD", ["float ptr [EAX + 0x8]"], "0x007b82e6"),
            _ins("0x007b82e6", "MOV", ["EAX", "dword ptr [ESI + 0x18]"], "0x007b82e9"),
            _ins("0x007b82e9", "PUSH", ["EDX"], "0x007b82ea"),
            _ins("0x007b82ea", "FSTP", ["float ptr [EBP + -0x48]"], "0x007b82ed"),
            _ins("0x007b82ed", "PUSH", ["EAX"], "0x007b82ee"),
            _ins("0x007b82ee", "LEA", ["ECX", "[EBP + -0x80]"], "0x007b82f1"),
            _ins("0x007b82f1", "PUSH", ["ECX"], "0x007b82f2"),
            _ins("0x007b82f2", "MOV", ["ECX", "ESI"], "0x007b82f4"),
            _ins("0x007b82f4", "CALL", [m.POSE_WRITER], "0x007b82f9", [m.POSE_WRITER]),
            _ins("0x007b82f9", "NOP", [], None),
        ],
    )


def _fixture(tmp_path: Path):
    m = _module()
    abi = _write(tmp_path / "abi.json", _abi(m))
    instructions = _write_rows(tmp_path / "instructions.jsonl", [_self_row(m), _external_row(m)])
    return m, abi, instructions


def _rows(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_resolves_all_four_stack_values_at_both_retail_shaped_callsites(tmp_path: Path):
    m, abi, instructions = _fixture(tmp_path)
    report = m.analyze_bmw_body0_bind_stack_value_provenance(abi, instructions)
    assert report["format"] == "SHIFT.BMWBody0BindStackValueProvenance/1"
    assert report["analysis"]["all_abi_callsites_analyzed"] is True
    assert report["analysis"]["all_stack_slots_resolved_at_every_callsite"] is True
    assert report["handoff"]["pose_writer_stack_argument_values_ready"] is True

    by_call = {row["callsite"]: row for row in report["analysis"]["callsites"]}
    self_slots = {row["stack_offset"]: row for row in by_call["0x007b7d75"]["resolved_stack_slots"]}
    assert self_slots[4]["push_instruction"] == "0x007b7d74"
    assert self_slots[4]["value_expression"] == "[EBP + 0XFFFFFD50]"
    assert self_slots[8]["value_expression"] == "DWORD PTR [EBX + 0XC]"
    assert self_slots[12]["value_expression"] == "DWORD PTR [EBP + -0X24]"
    assert self_slots[16]["value_expression"] == "DWORD PTR [EBP + -0X28]"

    external_slots = {row["stack_offset"]: row for row in by_call["0x007b82f4"]["resolved_stack_slots"]}
    assert external_slots[4]["value_expression"] == "[EBP + -0X80]"
    assert external_slots[8]["value_expression"] == "DWORD PTR [ESI + 0X18]"
    assert external_slots[12]["value_expression"] == "DWORD PTR [EBX + 0X8]"
    assert external_slots[16]["value_expression"] == "DWORD PTR [EBX + 0XC]"

    assert {row["id"] for row in report["blockers"]} == {
        "pose-writer-parameter-semantic-roles-unproven",
        "BODY0-pointer-at-bind-callsite-unproven",
        "bind-origin-basis-value-provenance-unproven",
    }


def test_second_cfg_predecessor_fails_closed(tmp_path: Path):
    m, abi, instructions = _fixture(tmp_path)
    rows = _rows(instructions)
    extra = _ins(
        "0x007b82d0",
        "JMP",
        ["0x007b82f1"],
        None,
        ["0x007b82f1"],
        "UNCONDITIONAL_JUMP",
    )
    rows[1]["instructions"].insert(0, extra)
    rows[1]["instruction_count"] += 1
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="predecessor count 2 blocks stack proof"):
        m.analyze_bmw_body0_bind_stack_value_provenance(abi, instructions)


def test_esp_mutation_between_pushes_fails_closed(tmp_path: Path):
    m, abi, instructions = _fixture(tmp_path)
    rows = _rows(instructions)
    for instruction in rows[1]["instructions"]:
        if instruction["address"] == "0x007b82e0":
            instruction["mnemonic"] = "ADD"
            instruction["operands"] = ["ESP", "0x4"]
            instruction["text"] = "ADD ESP,0x4"
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="unsupported ESP mutation"):
        m.analyze_bmw_body0_bind_stack_value_provenance(abi, instructions)


def test_transitive_register_source_fails_closed(tmp_path: Path):
    m, abi, instructions = _fixture(tmp_path)
    rows = _rows(instructions)
    for instruction in rows[1]["instructions"]:
        if instruction["address"] == "0x007b82d3":
            instruction["operands"] = ["ECX", "EDI"]
            instruction["text"] = "MOV ECX,EDI"
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="transitive register source EDI remains unresolved"):
        m.analyze_bmw_body0_bind_stack_value_provenance(abi, instructions)


def test_wrong_direct_target_fails_closed(tmp_path: Path):
    m, abi, instructions = _fixture(tmp_path)
    rows = _rows(instructions)
    for instruction in rows[1]["instructions"]:
        if instruction["address"] == "0x007b82f4":
            instruction["operands"] = ["0x007b0000"]
            instruction["flows"] = ["0x007b0000"]
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="direct target drift"):
        m.analyze_bmw_body0_bind_stack_value_provenance(abi, instructions)


def test_upstream_stack_value_preclaim_is_rejected(tmp_path: Path):
    m, abi, instructions = _fixture(tmp_path)
    value = json.loads(abi.read_text())
    value["handoff"]["pose_writer_stack_argument_values_ready"] = True
    _write(abi, value)
    with pytest.raises(ValueError, match="unexpectedly preclaims stack values"):
        m.analyze_bmw_body0_bind_stack_value_provenance(abi, instructions)


def test_success_preserves_semantic_negative_claims(tmp_path: Path):
    m, abi, instructions = _fixture(tmp_path)
    report = m.analyze_bmw_body0_bind_stack_value_provenance(abi, instructions)
    assert report["analysis"]["parameter_semantic_roles_ready"] is False
    assert report["analysis"]["BODY0_pointer_at_bind_callsite_ready"] is False
    assert report["analysis"]["BODY0_bind_origin_basis_values_ready"] is False
    assert report["analysis"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["parameter_ordinal_used_as_semantic_role"] is False
    assert report["scope"]["pose_writer_candidate_promoted_to_initializer"] is False
    assert report["scope"]["original_game_executed"] is False
    assert report["scope"]["new_runtime_capture_required"] is False
