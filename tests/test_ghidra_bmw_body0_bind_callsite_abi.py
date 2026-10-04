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
    callers = [
        {
            "caller": m.POSE_WRITER,
            "caller_name": "FUN_007b7840",
            "callsite": m.SELF_CALL,
            "candidate_class": "unjoined-direct-pose-writer-caller",
            "from_BODY_builder": {"reachable": False},
            "from_SDF_loader": {"reachable": False},
            "BODY0_pointer_proven": False,
            "bind_initializer_semantics_proven": False,
            "origin_basis_value_provenance_proven": False,
        },
        {
            "caller": m.EXTERNAL_CALLER,
            "caller_name": "FUN_007b8260",
            "callsite": m.EXTERNAL_CALL,
            "candidate_class": "unjoined-direct-pose-writer-caller",
            "from_BODY_builder": {"reachable": False},
            "from_SDF_loader": {"reachable": False},
            "BODY0_pointer_proven": False,
            "bind_initializer_semantics_proven": False,
            "origin_basis_value_provenance_proven": False,
        },
    ]
    return {
        "format": m.FRONTIER_FORMAT,
        "anchors": {
            "pose_writer_candidate": {
                "address": m.POSE_WRITER,
                "name": "FUN_007b7840",
                "calling_convention": m.EXPECTED_CC,
                "signature": m.EXPECTED_SIGNATURE,
                "size": 1446,
                "external": False,
                "thunk": False,
            }
        },
        "pose_writer_candidate": {
            "function": m.POSE_WRITER,
            "direct_caller_count": len(callers),
            "direct_callers": callers,
            "bind_initializer_semantics_proven": False,
        },
        "targeted_proof_worklist": {
            "function_targets": [m.POSE_WRITER, m.EXTERNAL_CALLER],
        },
        "scope": {
            "pose_writer_candidate_promoted_to_initializer": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
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
            "size": 100,
            "calling_convention": cc,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _pose_row(m):
    instructions = [
        _ins(m.POSE_WRITER, "NOP", [], "0x007b7d5d"),
        _ins("0x007b7d5d", "MOV", ["EDI", "dword ptr [EBP + -0x24]"], "0x007b7d60"),
        _ins("0x007b7d60", "MOV", ["EAX", "dword ptr [EBP + -0x28]"], "0x007b7d63"),
        _ins("0x007b7d63", "MOV", ["ECX", "dword ptr [EBX + 0xc]"], "0x007b7d66"),
        _ins("0x007b7d66", "PUSH", ["EAX"], "0x007b7d67"),
        _ins("0x007b7d67", "MOV", ["EAX", "dword ptr [EBP + -0x20]"], "0x007b7d6a"),
        _ins("0x007b7d6a", "PUSH", ["EDI"], "0x007b7d6b"),
        _ins("0x007b7d6b", "PUSH", ["ECX"], "0x007b7d6c"),
        _ins("0x007b7d6c", "MOV", ["ECX", "dword ptr [EAX]"], "0x007b7d6e"),
        _ins("0x007b7d6e", "LEA", ["EDX", "[EBP + 0xfffffd50]"], "0x007b7d74"),
        _ins("0x007b7d74", "PUSH", ["EDX"], m.SELF_CALL),
        _ins(m.SELF_CALL, "CALL", [m.POSE_WRITER], "0x007b7d7a", [m.POSE_WRITER]),
    ]
    return _row(m.POSE_WRITER, instructions)


def _external_row(m):
    instructions = [
        _ins(m.EXTERNAL_CALLER, "NOP", [], m.EXTERNAL_ENTRY_THIS_COPY),
        _ins(m.EXTERNAL_ENTRY_THIS_COPY, "MOV", ["ESI", "ECX"], "0x007b8284"),
        _ins("0x007b8284", "NOP", [], "0x007b82d3"),
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
        _ins("0x007b82f2", "MOV", ["ECX", "ESI"], m.EXTERNAL_CALL),
        _ins(m.EXTERNAL_CALL, "CALL", [m.POSE_WRITER], "0x007b82f9", [m.POSE_WRITER]),
    ]
    return _row(m.EXTERNAL_CALLER, instructions)


def _fixture(tmp_path: Path):
    m = _module()
    frontier = _write(tmp_path / "frontier.json", _frontier(m))
    instructions = _write_rows(
        tmp_path / "instructions.jsonl",
        [_pose_row(m), _external_row(m)],
    )
    return m, frontier, instructions


def _read_instruction_rows(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_maps_both_retail_callsites_to_source_backed_formal_ordinals(tmp_path: Path):
    m, frontier, instructions = _fixture(tmp_path)
    report = m.analyze_bmw_body0_bind_callsite_abi(frontier, instructions)
    assert report["format"] == "SHIFT.BMWBody0BindCallsiteABI/1"
    analysis = report["analysis"]
    assert analysis["source_signature_to_physical_ABI_binding_proven"] is True
    assert analysis["stack_argument_value_provenance_modeled"] is True
    assert analysis["right_to_left_stack_order_proven"] is True
    assert analysis["stack_setup_linear_fallthrough_proven"] is True
    assert analysis["external_receiver_entry_ECX_continuity_proven"] is True

    by_call = {row["callsite"]: row for row in analysis["callsites"]}
    external = by_call[m.EXTERNAL_CALL]
    assert external["receiver_origins_before_call"] == ["entry:ECX"]
    ext_args = {row["formal"]: row for row in external["formal_argument_sources"]}
    assert ext_args["this"]["source_expression"] == "entry:ECX (all-path preserved as ESI)"
    assert ext_args["param_1"]["source_expression"] == "address [EBP - 0x80]"
    assert ext_args["param_2"]["source_expression"] == "dword ptr [entry:ECX + 0x18]"
    assert ext_args["param_3"]["source_expression"] == "dword ptr [EBX + 0x08]"
    assert ext_args["param_4"]["source_expression"] == "dword ptr [EBX + 0x0c]"

    self_call = by_call[m.SELF_CALL]
    self_args = {row["formal"]: row for row in self_call["formal_argument_sources"]}
    assert self_args["this"]["source_expression"] == "dword ptr [dword ptr [EBP - 0x20]]"
    assert self_args["param_1"]["source_expression"] == "address [EBP - 0x2b0]"
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert {row["id"] for row in report["blockers"]} == {
        "BODY0-pointer-at-bind-callsite-unproven",
        "bind-origin-basis-value-provenance-unproven",
        "pose-writer-candidate-bind-role-unproven",
    }


def test_real_ghidra_negative_offset_spelling_is_required(tmp_path: Path):
    m, frontier, instructions = _fixture(tmp_path)
    rows = _read_instruction_rows(instructions)
    for instruction in rows[0]["instructions"]:
        if instruction["address"] == "0x007b7d5d":
            instruction["operands"] = ["EDI", "dword ptr [EBP - 0x24]"]
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="0x007b7d5d: operands drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, instructions)


def test_x87_gap_cannot_hide_stack_or_control_flow_drift(tmp_path: Path):
    m, frontier, instructions = _fixture(tmp_path)
    rows = _read_instruction_rows(instructions)
    for instruction in rows[1]["instructions"]:
        if instruction["address"] == "0x007b82e0":
            instruction["mnemonic"] = "ADD"
            instruction["operands"] = ["ESP", "0x4"]
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="0x007b82e0: mnemonic drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, instructions)


def test_external_entry_receiver_continuity_drift_fails_closed(tmp_path: Path):
    m, frontier, instructions = _fixture(tmp_path)
    rows = _read_instruction_rows(instructions)
    for instruction in rows[1]["instructions"]:
        if instruction["address"] == m.EXTERNAL_ENTRY_THIS_COPY:
            instruction["operands"] = ["ESI", "EDI"]
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="external call receiver does not resolve to entry ECX|operands drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, instructions)


def test_signature_or_calling_convention_drift_fails_closed(tmp_path: Path):
    m, frontier, instructions = _fixture(tmp_path)
    value = json.loads(frontier.read_text())
    value["anchors"]["pose_writer_candidate"]["calling_convention"] = "__cdecl"
    _write(frontier, value)
    with pytest.raises(ValueError, match="calling convention drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, instructions)

    m, frontier, instructions = _fixture(tmp_path)
    value = json.loads(frontier.read_text())
    value["anchors"]["pose_writer_candidate"]["signature"] += " drift"
    _write(frontier, value)
    with pytest.raises(ValueError, match="signature drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, instructions)


def test_wrong_pose_writer_target_fails_closed(tmp_path: Path):
    m, frontier, instructions = _fixture(tmp_path)
    rows = _read_instruction_rows(instructions)
    for instruction in rows[1]["instructions"]:
        if instruction["address"] == m.EXTERNAL_CALL:
            instruction["operands"] = ["0x007b0000"]
            instruction["flows"] = ["0x007b0000"]
    _write_rows(instructions, rows)
    with pytest.raises(ValueError, match="expected direct target|direct target drift"):
        m.analyze_bmw_body0_bind_callsite_abi(frontier, instructions)


def test_success_still_does_not_promote_bind_semantics(tmp_path: Path):
    m, frontier, instructions = _fixture(tmp_path)
    report = m.analyze_bmw_body0_bind_callsite_abi(frontier, instructions)
    assert report["analysis"]["BODY0_pointer_at_bind_callsite_proven"] is False
    assert report["analysis"]["bind_origin_basis_value_semantics_proven"] is False
    assert report["analysis"]["bind_initializer_semantics_proven"] is False
    assert report["scope"]["param_1_promoted_to_bind_origin"] is False
    assert report["scope"]["param_2_promoted_to_bind_basis"] is False
    assert report["scope"]["pose_writer_candidate_promoted_to_initializer"] is False
    assert report["scope"]["original_game_executed"] is False
    assert report["scope"]["new_runtime_capture_required"] is False
