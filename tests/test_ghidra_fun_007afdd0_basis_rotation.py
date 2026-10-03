import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_fun_007afdd0_basis_rotation.py"
    )
    spec = importlib.util.spec_from_file_location(
        "analyze_fun_007afdd0_basis_rotation", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _varnode(text, space="register", offset="0x0", size=4, **flags):
    return {
        "text": text,
        "space": space,
        "offset": offset,
        "size": size,
        "constant": flags.get("constant", False),
        "register": flags.get("register", space == "register"),
        "unique": flags.get("unique", space == "unique"),
    }


def _pcode(opcode, text, *, output=None, inputs=None, structured=True):
    row = {"opcode": opcode, "text": text}
    if structured:
        row["output"] = output
        row["inputs"] = [] if inputs is None else inputs
    return row


def _instruction(
    address,
    payload,
    mnemonic,
    text,
    operands,
    pcode,
    *,
    flows=None,
    references=None,
    flow_type="FALL_THROUGH",
    fallthrough=None,
):
    return {
        "address": address,
        "bytes": payload,
        "mnemonic": mnemonic,
        "text": text,
        "operands": operands,
        "flow_type": flow_type,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else flows,
        "references": [] if references is None else references,
        "pcode": pcode,
    }


def _row(instructions, *, version=2, address="0x007afdd0"):
    return {
        "format": f"SHIFT.GhidraFunctionInstructions/{version}",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": "FUN_007afdd0",
            "size": sum(len(bytes.fromhex(item["bytes"])) for item in instructions),
            "calling_convention": "__cdecl",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write(path, row):
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def _structured_fixture():
    ecx = _varnode("ECX", offset="0x20")
    edx = _varnode("EDX", offset="0x24")
    st0 = _varnode("ST0", offset="0x100", size=10)
    unique = _varnode("unique:100", space="unique", offset="0x100")
    ram = _varnode("ram", space="const", offset="0x1", constant=True)
    return [
        _instruction(
            "0x007afdd0",
            "d901",
            "FLD",
            "FLD dword ptr [ECX]",
            ["dword ptr [ECX]"],
            [
                _pcode("LOAD", "unique:100 = LOAD ram, ECX", output=unique, inputs=[ram, ecx]),
                _pcode("COPY", "ST0 = COPY unique:100", output=st0, inputs=[unique]),
            ],
            fallthrough="0x007afdd2",
        ),
        _instruction(
            "0x007afdd2",
            "d80a",
            "FMUL",
            "FMUL dword ptr [EDX]",
            ["dword ptr [EDX]"],
            [
                _pcode("LOAD", "unique:104 = LOAD ram, EDX", output=unique, inputs=[ram, edx]),
                _pcode("FLOAT_MULT", "ST0 = FLOAT_MULT ST0, unique:104", output=st0, inputs=[st0, unique]),
            ],
            fallthrough="0x007afdd4",
        ),
        _instruction(
            "0x007afdd4",
            "d95904",
            "FSTP",
            "FSTP dword ptr [ECX + 0x4]",
            ["dword ptr [ECX + 0x4]"],
            [
                _pcode("STORE", "STORE ram, ECX+4, ST0", output=None, inputs=[ram, ecx, st0]),
            ],
            fallthrough="0x007afdd7",
        ),
        _instruction(
            "0x007afdd7",
            "c3",
            "RET",
            "RET",
            [],
            [
                _pcode("RETURN", "RETURN [ESP]", output=None, inputs=[]),
            ],
            flow_type="TERMINATOR",
            fallthrough=None,
        ),
    ]


def test_freezes_machine_order_and_reports_precision_blockers(tmp_path):
    module = _load_module()
    export = tmp_path / "fun.jsonl"
    instructions = _structured_fixture()
    _write(export, _row(instructions))

    report = module.analyze_fun_007afdd0(export)

    assert report["format"] == "SHIFT.Fun007afdd0BasisRotationStatic/1"
    assert report["target"] == "FUN_007afdd0"
    assert report["instruction_freeze_ready"] is True
    assert report["native_port_ready"] is False
    assert report["instruction_count"] == 4
    assert report["machine_byte_count"] == 8
    assert report["machine_sha256"] == hashlib.sha256(
        bytes.fromhex("d901d80ad95904c3")
    ).hexdigest()
    assert report["floating_summary"]["x87_instruction_count"] == 3
    assert report["floating_summary"]["sse_scalar_instruction_count"] == 0
    assert report["pcode_summary"]["structured_varnodes_complete"] is True
    assert [item["width"] for item in report["memory_trace"]] == [
        "dword",
        "dword",
        "dword",
    ]
    blocker_ids = {item["id"] for item in report["blockers"]}
    assert "x87-stack-dataflow-unreconstructed" in blocker_ids
    assert "ambient-x87-control-word-unfrozen" in blocker_ids
    assert "memory-aliasing-and-field-identity-unresolved" in blocker_ids
    assert "structured-pcode-varnodes-missing" not in blocker_ids
    assert report["scope"]["rodrigues_semantics_assumed"] is False
    assert report["scope"]["normalization_assumed"] is False


def test_reports_calls_branches_and_missing_structured_varnodes(tmp_path):
    module = _load_module()
    export = tmp_path / "fun.jsonl"
    instructions = [
        _instruction(
            "0x007afdd0",
            "d901",
            "FLD",
            "FLD dword ptr [ECX]",
            ["dword ptr [ECX]"],
            [_pcode("LOAD", "unique:100 = LOAD ram, ECX", structured=False)],
            fallthrough="0x007afdd2",
        ),
        _instruction(
            "0x007afdd2",
            "7505",
            "JNZ",
            "JNZ 0x007afdd9",
            ["0x007afdd9"],
            [_pcode("CBRANCH", "CBRANCH 0x007afdd9, ZF", structured=False)],
            flows=["0x007afdd9"],
            flow_type="CONDITIONAL_JUMP",
            fallthrough="0x007afdd4",
        ),
        _instruction(
            "0x007afdd4",
            "e800000000",
            "CALL",
            "CALL 0x007b0000",
            ["0x007b0000"],
            [_pcode("CALL", "CALL 0x007b0000", structured=False)],
            flows=["0x007b0000"],
            references=[{"to": "0x007b0000", "type": "UNCONDITIONAL_CALL"}],
            flow_type="UNCONDITIONAL_CALL",
            fallthrough="0x007afdd9",
        ),
    ]
    _write(export, _row(instructions))

    report = module.analyze_fun_007afdd0(export)
    blocker_ids = {item["id"] for item in report["blockers"]}
    assert report["control_flow_summary"]["call_count"] == 1
    assert report["control_flow_summary"]["conditional_branch_count"] == 1
    assert report["pcode_summary"]["structured_varnodes_complete"] is False
    assert "callee-semantics-unfrozen" in blocker_ids
    assert "floating-control-flow-paths-unproven" in blocker_ids
    assert "structured-pcode-varnodes-missing" in blocker_ids


def test_rejects_version_one_export(tmp_path):
    module = _load_module()
    export = tmp_path / "fun.jsonl"
    instructions = _structured_fixture()
    _write(export, _row(instructions, version=1))
    with pytest.raises(ValueError, match="requires SHIFT.GhidraFunctionInstructions/2"):
        module.analyze_fun_007afdd0(export)


def test_rejects_wrong_target(tmp_path):
    module = _load_module()
    export = tmp_path / "fun.jsonl"
    instructions = _structured_fixture()
    instructions[0]["address"] = "0x007afdc0"
    _write(export, _row(instructions, address="0x007afdc0"))
    with pytest.raises(ValueError, match="expected FUN_007afdd0"):
        module.analyze_fun_007afdd0(export)


def test_rejects_non_increasing_instruction_addresses(tmp_path):
    module = _load_module()
    export = tmp_path / "fun.jsonl"
    instructions = _structured_fixture()
    instructions[1]["address"] = "0x007afdd0"
    _write(export, _row(instructions))
    with pytest.raises(ValueError, match="not strictly increasing"):
        module.analyze_fun_007afdd0(export)
