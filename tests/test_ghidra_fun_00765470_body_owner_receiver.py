import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools" / "ghidra" / "analyze_fun_00765470_body_owner_receiver.py"
    )
    spec = importlib.util.spec_from_file_location(
        "analyze_fun_00765470_body_owner_receiver", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _varnode(text, *, register=True):
    return {
        "text": text,
        "space": "register" if register else "unique",
        "offset": "0x0",
        "size": 4,
        "constant": False,
        "register": register,
        "unique": not register,
    }


def _pcode(opcode, text, *, output=None, inputs=None):
    return {
        "opcode": opcode,
        "text": text,
        "output": output,
        "inputs": [] if inputs is None else inputs,
    }


def _ins(
    address,
    mnemonic,
    operands,
    *,
    fallthrough=None,
    flows=None,
    flow_type="FALL_THROUGH",
    outputs=(),
):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": f"{mnemonic} {' '.join(operands)}".strip(),
        "operands": list(operands),
        "flow_type": flow_type,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else list(flows),
        "references": [],
        "pcode": [
            _pcode(
                "COPY",
                f"{register} = COPY unknown",
                output=_varnode(register),
            )
            for register in outputs
        ],
    }


def _row(instructions, *, version=2, address="0x00765470"):
    return {
        "format": f"SHIFT.GhidraFunctionInstructions/{version}",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": "FUN_00765470",
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write(path, row):
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def _linear_receiver_fixture(m):
    return [
        _ins(
            "0x00765470", "MOV", ["ESI", "ECX"],
            fallthrough="0x00765472", outputs=("ESI",),
        ),
        _ins(
            "0x00765472", "CALL", ["0x00760000"],
            fallthrough="0x00765477", flows=["0x00760000"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            "0x00765477", "MOV", ["ECX", "ESI"],
            fallthrough=m.BODY_LOOP_CALL, outputs=("ECX",),
        ),
        _ins(
            m.BODY_LOOP_CALL, "CALL", [m.BODY_LOOP_TARGET],
            fallthrough="0x0076582f", flows=[m.BODY_LOOP_TARGET],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            "0x0076582f", "RET", [], flow_type="TERMINATOR",
        ),
    ]


def test_proves_entry_ecx_through_preserved_register_across_calls(tmp_path):
    m = _module()
    export = tmp_path / "fun.jsonl"
    _write(export, _row(_linear_receiver_fixture(m)))

    report = m.analyze_fun_00765470_body_owner_receiver(export)
    assert report["format"] == "SHIFT.Fun00765470BodyOwnerReceiverProvenance/1"
    assert report["analysis"]["receiver_origins_before_body_loop_call"] == ["entry:ECX"]
    assert report["analysis"]["receiver_origin_cardinality"] == 1
    assert report["analysis"]["receiver_equals_half_step_entry_ECX_on_all_reachable_paths"] is True
    assert report["analysis"]["receiver_provenance_ambiguous"] is False
    assert report["handoff"]["half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven"] is True
    assert report["handoff"]["global_vehicle_to_BODY_owner_composition_ready"] is True
    assert report["handoff"]["phase703_gate_rewrite_ready"] is True
    assert report["handoff"]["phase698_positive_selection_admissible_by_this_artifact_alone"] is False
    assert report["blockers"] == []


def test_all_branch_paths_must_resolve_to_entry_ecx(tmp_path):
    m = _module()
    export = tmp_path / "fun.jsonl"
    instructions = [
        _ins(
            "0x00765470", "MOV", ["ESI", "ECX"],
            fallthrough="0x00765472", outputs=("ESI",),
        ),
        _ins(
            "0x00765472", "JNZ", ["0x00765478"],
            fallthrough="0x00765474", flows=["0x00765478"],
            flow_type="CONDITIONAL_JUMP",
        ),
        _ins(
            "0x00765474", "MOV", ["ECX", "ESI"],
            fallthrough="0x00765476", outputs=("ECX",),
        ),
        _ins(
            "0x00765476", "JMP", [m.BODY_LOOP_CALL],
            flows=[m.BODY_LOOP_CALL], flow_type="UNCONDITIONAL_JUMP",
        ),
        _ins(
            "0x00765478", "LEA", ["ECX", "[ESI]"],
            fallthrough=m.BODY_LOOP_CALL, outputs=("ECX",),
        ),
        _ins(
            m.BODY_LOOP_CALL, "CALL", [m.BODY_LOOP_TARGET],
            fallthrough="0x0076582f", flows=[m.BODY_LOOP_TARGET],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0076582f", "RET", [], flow_type="TERMINATOR"),
    ]
    _write(export, _row(instructions))
    report = m.analyze_fun_00765470_body_owner_receiver(export)
    assert report["analysis"]["receiver_origins_before_body_loop_call"] == ["entry:ECX"]
    assert report["analysis"]["receiver_equals_half_step_entry_ECX_on_all_reachable_paths"] is True


def test_one_divergent_branch_keeps_receiver_proof_ambiguous(tmp_path):
    m = _module()
    export = tmp_path / "fun.jsonl"
    instructions = [
        _ins(
            "0x00765470", "MOV", ["ESI", "ECX"],
            fallthrough="0x00765472", outputs=("ESI",),
        ),
        _ins(
            "0x00765472", "JNZ", ["0x00765478"],
            fallthrough="0x00765474", flows=["0x00765478"],
            flow_type="CONDITIONAL_JUMP",
        ),
        _ins(
            "0x00765474", "MOV", ["ECX", "ESI"],
            fallthrough="0x00765476", outputs=("ECX",),
        ),
        _ins(
            "0x00765476", "JMP", [m.BODY_LOOP_CALL],
            flows=[m.BODY_LOOP_CALL], flow_type="UNCONDITIONAL_JUMP",
        ),
        _ins(
            "0x00765478", "MOV", ["ECX", "EDI"],
            fallthrough=m.BODY_LOOP_CALL, outputs=("ECX",),
        ),
        _ins(
            m.BODY_LOOP_CALL, "CALL", [m.BODY_LOOP_TARGET],
            fallthrough="0x0076582f", flows=[m.BODY_LOOP_TARGET],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0076582f", "RET", [], flow_type="TERMINATOR"),
    ]
    _write(export, _row(instructions))
    report = m.analyze_fun_00765470_body_owner_receiver(export)
    assert report["analysis"]["receiver_origins_before_body_loop_call"] == [
        "entry:ECX", "entry:EDI"
    ]
    assert report["analysis"]["receiver_equals_half_step_entry_ECX_on_all_reachable_paths"] is False
    assert report["analysis"]["receiver_provenance_ambiguous"] is True
    assert report["handoff"]["phase703_gate_rewrite_ready"] is False
    assert report["blockers"][0]["id"] == "body-loop-ECX-not-proven-as-half-step-entry-ECX"


def test_intervening_call_clobbers_ecx_without_reload(tmp_path):
    m = _module()
    export = tmp_path / "fun.jsonl"
    instructions = [
        _ins(
            "0x00765470", "MOV", ["ECX", "ESI"],
            fallthrough="0x00765472", outputs=("ECX",),
        ),
        _ins(
            "0x00765472", "CALL", ["0x00760000"],
            fallthrough=m.BODY_LOOP_CALL, flows=["0x00760000"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins(
            m.BODY_LOOP_CALL, "CALL", [m.BODY_LOOP_TARGET],
            fallthrough="0x0076582f", flows=[m.BODY_LOOP_TARGET],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0076582f", "RET", [], flow_type="TERMINATOR"),
    ]
    _write(export, _row(instructions))
    report = m.analyze_fun_00765470_body_owner_receiver(export)
    origins = report["analysis"]["receiver_origins_before_body_loop_call"]
    assert len(origins) == 1
    assert origins[0].startswith("unknown:ECX@0x00765472:call-clobber")
    assert report["analysis"]["receiver_equals_half_step_entry_ECX_on_all_reachable_paths"] is False


def test_unmodelled_pcode_write_invalidates_ecx(tmp_path):
    m = _module()
    export = tmp_path / "fun.jsonl"
    instructions = [
        _ins(
            "0x00765470", "NOP", [],
            fallthrough=m.BODY_LOOP_CALL, outputs=("ECX",),
        ),
        _ins(
            m.BODY_LOOP_CALL, "CALL", [m.BODY_LOOP_TARGET],
            fallthrough="0x0076582f", flows=[m.BODY_LOOP_TARGET],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0076582f", "RET", [], flow_type="TERMINATOR"),
    ]
    _write(export, _row(instructions))
    report = m.analyze_fun_00765470_body_owner_receiver(export)
    origins = report["analysis"]["receiver_origins_before_body_loop_call"]
    assert origins[0].startswith("unknown:ECX@0x00765470:unmodelled-pcode-write")
    assert report["handoff"]["global_vehicle_to_BODY_owner_composition_ready"] is False


def test_rejects_wrong_export_version(tmp_path):
    m = _module()
    export = tmp_path / "fun.jsonl"
    _write(export, _row(_linear_receiver_fixture(m), version=1))
    with pytest.raises(ValueError, match="requires SHIFT.GhidraFunctionInstructions/2"):
        m.analyze_fun_00765470_body_owner_receiver(export)


def test_rejects_wrong_call_target(tmp_path):
    m = _module()
    export = tmp_path / "fun.jsonl"
    instructions = _linear_receiver_fixture(m)
    for instruction in instructions:
        if instruction["address"] == m.BODY_LOOP_CALL:
            instruction["operands"] = ["0x007b2280"]
            instruction["flows"] = ["0x007b2280"]
    _write(export, _row(instructions))
    with pytest.raises(ValueError, match="expected direct target"):
        m.analyze_fun_00765470_body_owner_receiver(export)
