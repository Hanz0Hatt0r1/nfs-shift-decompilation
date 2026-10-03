import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vtable_xref_instructions.py"
    )
    spec = importlib.util.spec_from_file_location("analyze_vtable_xref_instructions", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _op(opcode, text):
    return {"opcode": opcode, "text": text}


def _instruction(address, text, operands, refs, pcode):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": text.split()[0],
        "text": text,
        "operands": operands,
        "flow_type": "FALL_THROUGH",
        "fallthrough": None,
        "flows": [],
        "references": refs,
        "pcode": pcode,
    }


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _frontier(path):
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT.GhidraConstructionFrontier/1",
                "frontier_candidates": [
                    {
                        "function": "0x00003000",
                        "name": "FUN_00003000",
                        "referenced_vtable_addresses": ["0x00005000"],
                        "status": "vtable-xref-direct-proven-slice-frontier",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _export(path, instructions, *, version=2, function="0x00003000"):
    _write_jsonl(
        path,
        [
            {
                "format": f"SHIFT.GhidraFunctionInstructions/{version}",
                "program": "SHIFT.exe",
                "requested": function,
                "found": True,
                "function": {
                    "address": function,
                    "name": "FUN_00003000",
                    "size": 64,
                    "calling_convention": "__thiscall",
                },
                "instruction_count": len(instructions),
                "instructions": instructions,
            }
        ],
    )


def test_exact_vtable_reference_plus_store_is_kept_as_unpromoted_candidate(tmp_path):
    module = _load_module()
    frontier = tmp_path / "frontier.json"
    export = tmp_path / "instructions.jsonl"
    _frontier(frontier)
    _export(
        export,
        [
            _instruction(
                "0x00003000",
                "MOV dword ptr [ECX],0x00005000",
                ["dword ptr [ECX]", "0x00005000"],
                [{"to": "0x00005000", "type": "DATA"}],
                [_op("STORE", "STORE ram, ECX, 0x5000")],
            ),
            _instruction(
                "0x00003004",
                "CMP EAX,0x00005000",
                ["EAX", "0x00005000"],
                [{"to": "0x00005000", "type": "DATA"}],
                [_op("INT_EQUAL", "unique:1 = INT_EQUAL EAX, 0x5000")],
            ),
            _instruction(
                "0x00003008",
                "MOV dword ptr [ESI + 0x4],0x00006000",
                ["dword ptr [ESI + 0x4]", "0x00006000"],
                [{"to": "0x00006000", "type": "DATA"}],
                [_op("STORE", "STORE ram, ESI, 0x6000")],
            ),
        ],
    )

    report = module.audit_vtable_xref_instructions(export, frontier)
    assert report["format"] == "SHIFT.GhidraVtableXrefInstructionAudit/1"
    assert report["vtable_reference_instruction_count"] == 2
    assert report["store_candidate_count"] == 1
    assert report["non_memory_reference_count"] == 1
    assert report["blocker_count"] == 0

    store = report["store_candidates"][0]
    assert store["instruction"] == "0x00003000"
    assert store["matching_vtable_references"] == [{"to": "0x00005000", "type": "DATA"}]
    assert store["simple_memory_operands"][0]["base_register"] == "ECX"
    assert store["simple_memory_operands"][0]["displacement_hex"] == "0x0"
    assert store["promoted"] is False
    assert report["store_shape_groups"][0]["heuristic_vtable"] == "0x00005000"
    assert report["scope"]["store_candidate_is_vptr_store_proof"] is False
    assert report["scope"]["constructor_identity_proven"] is False


def test_store_with_complex_destination_remains_blocker(tmp_path):
    module = _load_module()
    frontier = tmp_path / "frontier.json"
    export = tmp_path / "instructions.jsonl"
    _frontier(frontier)
    _export(
        export,
        [
            _instruction(
                "0x00003000",
                "MOV dword ptr [ECX + EDX*4],0x00005000",
                ["dword ptr [ECX + EDX*4]", "0x00005000"],
                [{"to": "0x00005000", "type": "DATA"}],
                [_op("STORE", "STORE ram, unique:1, 0x5000")],
            )
        ],
    )
    report = module.audit_vtable_xref_instructions(export, frontier)
    assert report["store_candidate_count"] == 1
    assert report["blocker_count"] == 1
    assert report["store_shape_group_count"] == 0
    assert report["blockers"][0]["status"] == (
        "vtable-address-store-without-simple-register-relative-memory-operand"
    )


def test_v1_instruction_export_fails_closed(tmp_path):
    module = _load_module()
    frontier = tmp_path / "frontier.json"
    export = tmp_path / "instructions.jsonl"
    _frontier(frontier)
    _export(export, [], version=1)
    with pytest.raises(ValueError, match="requires SHIFT.GhidraFunctionInstructions/2"):
        module.audit_vtable_xref_instructions(export, frontier)


def test_function_outside_construction_frontier_fails_closed(tmp_path):
    module = _load_module()
    frontier = tmp_path / "frontier.json"
    export = tmp_path / "instructions.jsonl"
    _frontier(frontier)
    _export(
        export,
        [
            _instruction(
                "0x00004000",
                "NOP",
                [],
                [],
                [_op("COPY", "EAX = COPY EAX")],
            )
        ],
        function="0x00004000",
    )
    with pytest.raises(ValueError, match="absent from construction frontier"):
        module.audit_vtable_xref_instructions(export, frontier)


def test_bad_frontier_format_fails_closed(tmp_path):
    module = _load_module()
    frontier = tmp_path / "frontier.json"
    export = tmp_path / "instructions.jsonl"
    frontier.write_text(json.dumps({"format": "wrong", "frontier_candidates": []}), encoding="utf-8")
    _export(export, [])
    with pytest.raises(ValueError, match="expected SHIFT.GhidraConstructionFrontier/1"):
        module.audit_vtable_xref_instructions(export, frontier)
