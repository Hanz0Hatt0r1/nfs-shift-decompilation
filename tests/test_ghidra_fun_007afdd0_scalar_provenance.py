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
        / "analyze_fun_007afdd0_scalar_provenance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "analyze_fun_007afdd0_scalar_provenance", path
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


def _pcode(opcode, text, *, output=None, inputs=None):
    return {
        "opcode": opcode,
        "text": text,
        "output": output,
        "inputs": [] if inputs is None else inputs,
    }


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


def _fixture():
    ram = _varnode("ram", space="const", offset="0x1", constant=True, register=False)
    ebp = _varnode("EBP", offset="0x30")
    ecx = _varnode("ECX", offset="0x20")
    st0 = _varnode("ST0", offset="0x100", size=10)
    unique = _varnode("unique:100", space="unique", offset="0x100", register=False)
    sine_target = _varnode(
        "0x00900c40", space="const", offset="0x900c40", size=4,
        constant=True, register=False
    )
    sqrt_target = _varnode(
        "0x00909990", space="const", offset="0x909990", size=4,
        constant=True, register=False
    )
    cosine_target = _varnode(
        "0x00900b10", space="const", offset="0x900b10", size=4,
        constant=True, register=False
    )
    return [
        _instruction(
            "0x007afdd0", "d901", "FLD", "FLD dword ptr [ECX]",
            ["dword ptr [ECX]"],
            [
                _pcode("LOAD", "unique:100 = LOAD ram, ECX", output=unique, inputs=[ram, ecx]),
                _pcode("COPY", "ST0 = COPY unique:100", output=st0, inputs=[unique]),
            ],
            fallthrough="0x007afdd2",
        ),
        _instruction(
            "0x007afdd2", "d95df0", "FSTP", "FSTP dword ptr [EBP-0x10]",
            ["dword ptr [EBP-0x10]"],
            [_pcode("STORE", "STORE ram, EBP, ST0", inputs=[ram, ebp, st0])],
            fallthrough="0x007afdd5",
        ),
        _instruction(
            "0x007afdd5", "e800000000", "CALL", "CALL 0x00909990",
            ["0x00909990"],
            [_pcode("CALL", "CALL 0x00909990", inputs=[sqrt_target])],
            flows=["0x00909990"],
            references=[{"to": "0x00909990", "type": "UNCONDITIONAL_CALL"}],
            flow_type="UNCONDITIONAL_CALL",
            fallthrough="0x007afdda",
        ),
        _instruction(
            "0x007afdda", "e800000000", "CALL", "CALL 0x00900c40",
            ["0x00900c40"],
            [_pcode("CALL", "CALL 0x00900c40", inputs=[sine_target])],
            flows=["0x00900c40"],
            references=[{"to": "0x00900c40", "type": "UNCONDITIONAL_CALL"}],
            flow_type="UNCONDITIONAL_CALL",
            fallthrough="0x007afddf",
        ),
        _instruction(
            "0x007afddf", "d95dec", "FSTP", "FSTP dword ptr [EBP-0x14]",
            ["dword ptr [EBP-0x14]"],
            [_pcode("STORE", "STORE ram, EBP, ST0", inputs=[ram, ebp, st0])],
            fallthrough="0x007afde2",
        ),
        _instruction(
            "0x007afde2", "e800000000", "CALL", "CALL 0x00900b10",
            ["0x00900b10"],
            [_pcode("CALL", "CALL 0x00900b10", inputs=[cosine_target])],
            flows=["0x00900b10"],
            references=[{"to": "0x00900b10", "type": "UNCONDITIONAL_CALL"}],
            flow_type="UNCONDITIONAL_CALL",
            fallthrough="0x007afde7",
        ),
        _instruction(
            "0x007afde7", "d95de8", "FSTP", "FSTP dword ptr [EBP-0x18]",
            ["dword ptr [EBP-0x18]"],
            [_pcode("STORE", "STORE ram, EBP, ST0", inputs=[ram, ebp, st0])],
            fallthrough="0x007afdea",
        ),
        _instruction(
            "0x007afdea", "c3", "RET", "RET", [],
            [_pcode("RETURN", "RETURN [ESP]")],
            flow_type="TERMINATOR",
        ),
    ]


def _row(instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "program": "SHIFT.exe",
        "requested": "0x007afdd0",
        "found": True,
        "function": {
            "address": "0x007afdd0",
            "name": "FUN_007afdd0",
            "size": sum(len(bytes.fromhex(item["bytes"])) for item in instructions),
            "calling_convention": "__cdecl",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_inputs(tmp_path, instructions, **static_overrides):
    export = tmp_path / "fun.jsonl"
    export.write_text(json.dumps(_row(instructions)) + "\n", encoding="utf-8")
    machine = b"".join(bytes.fromhex(item["bytes"]) for item in instructions)
    static = {
        "format": "SHIFT.Fun007afdd0BasisRotationStatic/1",
        "target": "FUN_007afdd0",
        "target_address": "0x007afdd0",
        "instruction_freeze_ready": True,
        "machine_byte_count": len(machine),
        "machine_sha256": hashlib.sha256(machine).hexdigest(),
        "pcode_summary": {"structured_varnodes_complete": True},
    }
    static.update(static_overrides)
    report = tmp_path / "phase680.json"
    report.write_text(json.dumps(static), encoding="utf-8")
    return export, report


def test_freezes_helper_calls_and_store_candidates_without_assigning_roles(tmp_path):
    module = _load_module()
    export, static = _write_inputs(tmp_path, _fixture())

    report = module.analyze_scalar_provenance(export, static)

    assert report["format"] == "SHIFT.Fun007afdd0ScalarProvenance/1"
    assert report["scalar_provenance_frontier_ready"] is True
    assert report["machine_scalar_production_ready"] is False
    assert report["host_libm_substitution_allowed"] is False
    assert len(report["helper_calls"]["sine"]["calls"]) == 1
    assert report["helper_calls"]["sine"]["calls"][0]["direct_target"] == "0x00900c40"
    assert len(report["helper_calls"]["cosine"]["calls"]) == 1
    assert report["helper_calls"]["cosine"]["calls"][0]["direct_target"] == "0x00900b10"
    assert [item["direct_target"] for item in report["helper_calls"]["other"]] == [
        "0x00909990"
    ]
    assert len(report["f32_store_candidates"]) == 3
    assert all(item["source_role"] is None for item in report["f32_store_candidates"])
    assert all(
        item["assigned_store_candidate"] is None
        for item in report["source_scalar_boundaries"]
    )
    blocker_ids = {item["id"] for item in report["blockers"]}
    assert "scalar-store-role-mapping-unproven" in blocker_ids
    assert "sqrt-helper-identity-unresolved" in blocker_ids
    assert "call-return-floating-register-provenance-unresolved" in blocker_ids
    assert report["scope"]["source_role_assignment_by_address_assumed"] is False
    assert report["scope"]["sqrt_callee_identity_assumed"] is False
    assert report["scope"]["original_game_executed"] is False
    assert report["scope"]["runtime_capture_required"] is False


def test_duplicate_trig_helper_call_blocks_frontier(tmp_path):
    module = _load_module()
    instructions = _fixture()
    duplicate = dict(instructions[3])
    duplicate["address"] = "0x007afddc"
    instructions.insert(4, duplicate)
    export, static = _write_inputs(tmp_path, instructions)

    report = module.analyze_scalar_provenance(export, static)
    assert report["scalar_provenance_frontier_ready"] is False
    blocker = next(
        item for item in report["blockers"]
        if item["id"] == "sine-helper-callsite-not-unique"
    )
    assert blocker["call_count"] == 2


def test_phase680_machine_identity_mismatch_is_rejected(tmp_path):
    module = _load_module()
    export, static = _write_inputs(tmp_path, _fixture(), machine_sha256="0" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        module.analyze_scalar_provenance(export, static)


def test_incomplete_structured_pcode_is_rejected(tmp_path):
    module = _load_module()
    instructions = _fixture()
    instructions[0]["pcode"][0].pop("inputs")
    export, static = _write_inputs(tmp_path, instructions)
    with pytest.raises(ValueError, match="structured p-code varnodes required"):
        module.analyze_scalar_provenance(export, static)


def test_phase680_incomplete_structured_pcode_gate_is_rejected(tmp_path):
    module = _load_module()
    export, static = _write_inputs(
        tmp_path,
        _fixture(),
        pcode_summary={"structured_varnodes_complete": False},
    )
    with pytest.raises(ValueError, match="structured p-code varnodes are incomplete"):
        module.analyze_scalar_provenance(export, static)
