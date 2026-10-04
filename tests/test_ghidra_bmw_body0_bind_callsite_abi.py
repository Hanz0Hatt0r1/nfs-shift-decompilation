from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_body0_bind_callsite_abi.py"


def _module():
    spec = importlib.util.spec_from_file_location("bmw_body0_bind_callsite_abi", TOOL)
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


def _frontier(m):
    return {
        "format": m.FRONTIER_FORMAT,
        "anchors": {
            "pose_writer_candidate": {
                "address": m.POSE_WRITER,
                "calling_convention": m.EXPECTED_CC,
                "signature": m.EXPECTED_SIGNATURE,
            }
        },
        "pose_writer_candidate": {
            "function": m.POSE_WRITER,
            "direct_caller_count": 2,
            "bind_initializer_semantics_proven": False,
            "direct_callers": [
                {
                    "caller": m.POSE_WRITER,
                    "callsite": m.SELF_CALL,
                    "BODY0_pointer_proven": False,
                    "bind_initializer_semantics_proven": False,
                },
                {
                    "caller": m.EXTERNAL_CALLER,
                    "callsite": m.EXTERNAL_CALL,
                    "BODY0_pointer_proven": False,
                    "bind_initializer_semantics_proven": False,
                },
            ],
        },
    }


def _register_report(m):
    rows = []
    for caller, callsite in [(m.POSE_WRITER, m.SELF_CALL), (m.EXTERNAL_CALLER, m.EXTERNAL_CALL)]:
        rows.append(
            {
                "caller": caller,
                "callsite": callsite,
                "physical_register_provenance_ready": True,
                "BODY0_pointer_proven": False,
                "bind_initializer_semantics_proven": False,
            }
        )
    return {
        "format": m.REGISTER_FORMAT,
        "analysis": {
            "all_frontier_callsites_analyzed": True,
            "callsites": rows,
        },
    }


def _ins(address, mnemonic, operands, fallthrough=None, flows=None):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else flows,
        "flow_type": "UNCONDITIONAL_CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "references": [],
        "pcode": [],
    }


def _row(address, instructions, *, cc="__thiscall"):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": "FUN_" + address[2:],
            "calling_convention": cc,
            "size": 100,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _pose_row(m):
    a = [
        _ins(m.POSE_WRITER, "NOP", [], "0x007b7d5d"),
        _ins("0x007b7d5d", "MOV", ["EDI", "dword ptr [EBP - 0x24]"], "0x007b7d60"),
        _ins("0x007b7d60", "MOV", ["EAX", "dword ptr [EBP - 0x28]"], "0x007b7d63"),
        _ins("0x007b7d63", "MOV", ["ECX", "dword ptr [EBX + 0xc]"], "0x007b7d66"),
        _ins("0x007b7d66", "PUSH", ["EAX"], "0x007b7d67"),
        _ins("0x007b7d67", "MOV", ["EAX", "dword ptr [EBP - 0x20]"], "0x007b7d6a"),
        _ins("0x007b7d6a", "PUSH", ["EDI"], "0x007b7d6b"),
        _ins("0x007b7d6b", "PUSH", ["ECX"], "0x007b7d6c"),
        _ins("0x007b7d6c", "MOV", ["ECX", "dword ptr [EAX]"], "0x007b7d6e"),
        _ins("0x007b7d6e", "LEA", ["EDX", "[EBP - 0x2b0]"], "0x007b7d74"),
        _ins("0x007b7d74", "PUSH", ["EDX"], m.SELF_CALL),
        _ins(m.SELF_CALL, "CALL", [m.POSE_WRITER], "0x007b7d7a", [m.POSE_WRITER]),
    ]
    return _row(m.POSE_WRITER, a)


def _external_row(m):
    a = [
        _ins(m.EXTERNAL_CALLER, "NOP", [], "0x007b827d"),
        _ins("0x007b827d", "MOV", ["ESI", "ECX"], "0x007b827f"),
        _ins("0x007b827f", "NOP", [], "0x007b82d3"),
        _ins("0x007b82d3", "MOV", ["ECX", "dword ptr [EBX + 0xc]"], "0x007b82d6"),
        _ins("0x007b82d6", "NOP", [], "0x007b82dc"),
        _ins("0x007b82dc", "MOV", ["EDX", "dword ptr [EBX + 0x8]"], "0x007b82df"),
        _ins("0x007b82df", "PUSH", ["ECX"], "0x007b82e0"),
        _ins("0x007b82e0", "NOP", [], "0x007b82e6"),
        _ins("0x007b82e6", "MOV", ["EAX", "dword ptr [ESI + 0x18]"], "0x007b82e9"),
        _ins("0x007b82e9", "PUSH", ["EDX"], "0x007b82ea"),
        _ins("0x007b82ea", "NOP", [], "0x007b82ed"),
        _ins("0x007b82ed", "PUSH", ["EAX"], "0x007b82ee"),
        _ins("0x007b82ee", "LEA", ["ECX", "[EBP - 0x80]"], "0x007b82f1"),
        _ins("0x007b82f1", "PUSH", ["ECX"], "0x007b82f2"),
        _ins("0x007b82f2", "MOV", ["ECX", "ESI"], m.EXTERNAL_CALL),
        _ins(m.EXTERNAL_CALL, "CALL", [m.POSE_WRITER], "0x007b82f9", [m.POSE_WRITER]),
    ]
    return _row(m.EXTERNAL_CALLER, a)


def _fixture(tmp_path: Path):
    m = _module()
    frontier = _write(tmp_path / "frontier.json", _frontier(m))
    registers = _write(tmp_path / "registers.json", _register_report(m))
    instructions = _write_rows(tmp_path / "instructions.jsonl", [_pose_row(m), _external_row(m)])
    return m, frontier, registers, instructions


def test_maps_both_retail_callsites_to_source_backed_formal_ordinals(tmp_path: Path):
    m, frontier, registers, instructions = _fixture(tmp_path)
    report = m.analyze_bmw_body0_bind_callsite_abi(frontier, registers, instructions)
    assert report["format"] == "SHIFT.BMWBody0BindCallsiteABI/1"
    assert report["analysis"]["physical_ABI_semantic_binding_proven"] is True
    assert report["analysis"]["stack_argument_value_provenance_modeled"] is True
    assert report["analysis"]["right_to_left_stack_order_proven"] is True
    by_call = {row["callsite"]: row for row in report["analysis"]["callsites"]}
    ext = by_call[m.EXTERNAL_CALL]
    assert ext["physical_to_formal"] == {
        "this": "entry:ECX (preserved as ESI)",
        "param_1": "address [EBP - 0x80]",
        "param_2": "dword ptr [entry:ECX + 0x18]",
        "param_3": "dword ptr [EBX + 0x08]",
        "param_4": "dword ptr [EBX + 0x0c]",
    }
    self_call = by_call[m.SELF_CALL]
    assert self_call["physical_to_formal"]["this"] == "dword ptr [dword ptr [EBP - 0x20]]"
    assert self_call["physical_to_formal"]["param_1"] == "address [EBP - 0x2b0]"
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert {row["id"] for row in report["blockers"]} == {
        "BODY0-pointer-at-bind-callsite-unproven",
        "bind-origin-basis-value-provenance-unproven",
        "pose-writer-candidate-bind-role-unproven",
    }


def test_swapped_external_push_fails_closed(tmp_path: Path):
    m, frontier, registers, instructions = _fixture(tmp_path)
    rows = [json.loads(x) for x in instructions.read_text().splitlines() if x.strip()]
    for ins in rows[1]["instructions"]:
        if ins["address"] == "0x007b82ed":
            ins["operands"] = ["EDX"]
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="0x007b82ed: operands drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, registers, instructions)


def test_external_receiver_restore_drift_fails_closed(tmp_path: Path):
    m, frontier, registers, instructions = _fixture(tmp_path)
    rows = [json.loads(x) for x in instructions.read_text().splitlines() if x.strip()]
    for ins in rows[1]["instructions"]:
        if ins["address"] == "0x007b82f2":
            ins["operands"] = ["ECX", "EDI"]
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="0x007b82f2: operands drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, registers, instructions)


def test_signature_or_calling_convention_drift_fails_closed(tmp_path: Path):
    m, frontier, registers, instructions = _fixture(tmp_path)
    value = json.loads(frontier.read_text())
    value["anchors"]["pose_writer_candidate"]["calling_convention"] = "__cdecl"
    _write(frontier, value)
    with pytest.raises(ValueError, match="calling convention drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, registers, instructions)

    m, frontier, registers, instructions = _fixture(tmp_path)
    value = json.loads(frontier.read_text())
    value["anchors"]["pose_writer_candidate"]["signature"] += " drift"
    _write(frontier, value)
    with pytest.raises(ValueError, match="signature drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, registers, instructions)


def test_register_report_semantic_preclaim_is_rejected(tmp_path: Path):
    m, frontier, registers, instructions = _fixture(tmp_path)
    value = json.loads(registers.read_text())
    value["analysis"]["callsites"][0]["BODY0_pointer_proven"] = True
    _write(registers, value)
    with pytest.raises(ValueError, match="preclaims BODY0"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, registers, instructions)


def test_success_still_does_not_promote_bind_semantics(tmp_path: Path):
    m, frontier, registers, instructions = _fixture(tmp_path)
    report = m.analyze_bmw_body0_bind_callsite_abi(frontier, registers, instructions)
    assert report["analysis"]["BODY0_pointer_at_bind_callsite_proven"] is False
    assert report["analysis"]["bind_origin_basis_value_semantics_proven"] is False
    assert report["analysis"]["bind_initializer_semantics_proven"] is False
    assert report["scope"]["pose_writer_candidate_promoted_to_initializer"] is False
    assert report["scope"]["original_game_executed"] is False
    assert report["scope"]["new_runtime_capture_required"] is False
