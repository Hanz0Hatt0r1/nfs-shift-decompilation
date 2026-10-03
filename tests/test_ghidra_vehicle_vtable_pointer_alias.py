import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_vtable_pointer_alias.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_vtable_pointer_alias", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _p(opcode, text=None):
    return {"opcode": opcode, "text": text or opcode}


def _ins(address, mnemonic, operands=None, *, pcode=None, flows=None):
    operands = operands or []
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + ((" " + ",".join(operands)) if operands else ""),
        "operands": operands,
        "flow_type": "CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": None,
        "flows": flows or [],
        "references": [],
        "pcode": pcode or [],
    }


def _row(module, function, instructions):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": function,
        "found": True,
        "function": {
            "address": function,
            "name": f"FUN_{function[2:]}",
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(
    tmp_path,
    *,
    between=None,
    store_destination="dword ptr [ESI]",
    store_source="0x00b10000",
    overlap=True,
):
    module = _load_module()
    function = "0x00715700"
    store_instruction = "0x00715710"
    source_instruction = "0x00715730"
    table = "0x00b10000"
    between = list(between or [])

    instructions = [
        _ins(
            store_instruction,
            "MOV",
            [store_destination, store_source],
            pcode=[_p("STORE")],
        ),
        *between,
        _ins(
            source_instruction,
            "MOV",
            ["ECX", "dword ptr [ESI + 0x40]"],
            pcode=[_p("LOAD")],
        ),
    ]
    instruction_export = tmp_path / "instructions.jsonl"
    _write_jsonl(instruction_export, [_row(module, function, instructions)])

    overlaps = []
    if overlap:
        overlaps.append(
            {
                "function": function,
                "vtable_store_instruction": store_instruction,
                "vtable_store_instruction_text": f"MOV {store_destination},{store_source}",
                "base_register": "ESI",
                "store_displacement": 0,
                "store_displacement_hex": "0x0",
                "matching_vtable_references": [{"to": table, "type": "DATA"}],
                "evidence_state": "ambiguous",
                "pointer_alias_proven": False,
                "vptr_store_proven": False,
            }
        )
    pointer = {
        "format": module.POINTER_FORMAT,
        "upper_caller": "0x007155e9",
        "origins": [
            {
                "caller": function,
                "call_instruction": "0x00715740",
                "receiver_source": {
                    "kind": "register-relative-load",
                    "instruction": source_instruction,
                    "base_register": "ESI",
                    "displacement": 0x40,
                    "displacement_hex": "0x40",
                },
                "vtable_store_overlaps": overlaps,
            }
        ],
    }
    pointer_path = tmp_path / "pointer.json"
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")

    owner = {
        "format": module.OWNER_FORMAT,
        "upper_caller": "0x007155e9",
        "vtable_store_candidates": [
            {
                "function": function,
                "function_name": f"FUN_{function[2:]}",
                "instruction": store_instruction,
                "instruction_text": f"MOV {store_destination},{store_source}",
                "matching_vtable_references": [{"to": table, "type": "DATA"}],
                "pcode": [_p("STORE")],
                "pcode_opcodes": ["STORE"],
                "has_store": True,
                "has_load": False,
                "simple_memory_operands": [
                    {
                        "base_register": "ESI",
                        "displacement": 0,
                        "displacement_hex": "0x0",
                    }
                ],
                "evidence_state": "ambiguous",
            }
        ],
    }
    owner_path = tmp_path / "owner.json"
    owner_path.write_text(json.dumps(owner), encoding="utf-8")
    return {
        "module": module,
        "function": function,
        "store": store_instruction,
        "source": source_instruction,
        "table": table,
        "instructions": instruction_export,
        "pointer": pointer_path,
        "owner": owner_path,
    }


def test_verifies_exact_table_store_and_linear_same_pointer_value(tmp_path):
    fx = _fixture(
        tmp_path,
        between=[
            _ins("0x00715720", "MOV", ["EAX", "dword ptr [ESI + 0x4]"], pcode=[_p("LOAD")])
        ],
    )
    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    assert report["format"] == "SHIFT.VehicleVtablePointerAlias/1"
    assert report["candidate_count"] == 1
    assert report["verified_same_pointer_table_store_count"] == 1
    assert report["verified_same_pointer_offset_zero_table_store_count"] == 1
    row = report["candidates"][0]
    assert row["store_shape"]["evidence_state"] == "verified"
    assert row["store_shape"]["stored_address_matches_reference"] is True
    assert row["base_register_value_continuity"]["evidence_state"] == "verified"
    assert row["same_pointer_table_store_state"] == "verified"
    assert row["same_pointer_offset_zero_table_store_verified"] is True
    assert row["vptr_semantics_proven"] is False
    assert row["class_identity_proven"] is False
    assert report["scope"]["same_pointer_table_store_is_vptr_semantics_proof"] is False


def test_partial_register_write_clobbers_base_continuity(tmp_path):
    fx = _fixture(
        tmp_path,
        between=[_ins("0x00715720", "MOV", ["SI", "AX"], pcode=[_p("COPY")])],
    )
    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    row = report["candidates"][0]
    assert row["base_register_value_continuity"]["evidence_state"] == "ambiguous"
    assert row["base_register_value_continuity"]["status"] == "explicit-base-register-clobber"
    assert row["same_pointer_table_store_state"] == "ambiguous"


def test_call_barrier_prevents_pointer_value_alias_proof(tmp_path):
    fx = _fixture(
        tmp_path,
        between=[
            _ins(
                "0x00715720",
                "CALL",
                ["0x00710000"],
                pcode=[_p("CALL")],
                flows=["0x00710000"],
            )
        ],
    )
    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    continuity = report["candidates"][0]["base_register_value_continuity"]
    assert continuity["evidence_state"] == "ambiguous"
    assert continuity["status"] == "control-flow-or-call-barrier"


def test_xchg_second_operand_is_treated_as_base_clobber(tmp_path):
    fx = _fixture(
        tmp_path,
        between=[_ins("0x00715720", "XCHG", ["EAX", "ESI"], pcode=[_p("COPY")])],
    )
    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    continuity = report["candidates"][0]["base_register_value_continuity"]
    assert continuity["evidence_state"] == "ambiguous"
    assert continuity["status"] == "implicit-or-multi-register-clobber"


def test_unsupported_interval_instruction_is_not_crossed(tmp_path):
    fx = _fixture(
        tmp_path,
        between=[_ins("0x00715720", "BSF", ["EAX", "EDX"], pcode=[_p("COPY")])],
    )
    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    continuity = report["candidates"][0]["base_register_value_continuity"]
    assert continuity["evidence_state"] == "ambiguous"
    assert continuity["status"] == "unsupported-interval-instruction"


def test_wrong_literal_table_address_keeps_store_shape_ambiguous(tmp_path):
    fx = _fixture(tmp_path, store_source="0x00b20000")
    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    shape = report["candidates"][0]["store_shape"]
    assert shape["evidence_state"] == "ambiguous"
    assert shape["stored_address_matches_reference"] is False
    assert report["verified_same_pointer_table_store_count"] == 0


def test_symbolic_store_source_is_not_promoted_to_exact_address(tmp_path):
    fx = _fixture(tmp_path, store_source="DAT_00b10000")
    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    shape = report["candidates"][0]["store_shape"]
    assert shape["evidence_state"] == "ambiguous"
    assert shape["status"] == "store-shape-not-proven"
    assert "literal" in shape["reason"]


def test_nonzero_same_pointer_table_store_does_not_gain_vptr_semantics(tmp_path):
    fx = _fixture(tmp_path, store_destination="dword ptr [ESI + 0x4]")
    owner = json.loads(fx["owner"].read_text(encoding="utf-8"))
    owner["vtable_store_candidates"][0]["simple_memory_operands"][0]["displacement"] = 4
    owner["vtable_store_candidates"][0]["simple_memory_operands"][0]["displacement_hex"] = "0x4"
    fx["owner"].write_text(json.dumps(owner), encoding="utf-8")
    pointer = json.loads(fx["pointer"].read_text(encoding="utf-8"))
    pointer["origins"][0]["vtable_store_overlaps"][0]["store_displacement"] = 4
    pointer["origins"][0]["vtable_store_overlaps"][0]["store_displacement_hex"] = "0x4"
    fx["pointer"].write_text(json.dumps(pointer), encoding="utf-8")

    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    row = report["candidates"][0]
    assert row["same_pointer_table_store_state"] == "verified"
    assert row["same_pointer_offset_zero_table_store_verified"] is False
    assert row["vptr_semantics_proven"] is False
    assert any(blocker["id"] == "same-pointer-table-store-nonzero-offset" for blocker in report["blockers"])


def test_no_overlap_produces_no_alias_candidate(tmp_path):
    fx = _fixture(tmp_path, overlap=False)
    report = fx["module"].analyze_vehicle_vtable_pointer_alias(
        fx["instructions"], fx["pointer"], fx["owner"]
    )
    assert report["candidate_count"] == 0
    assert report["verified_same_pointer_table_store_count"] == 0


def test_fails_closed_when_overlap_candidate_is_missing(tmp_path):
    fx = _fixture(tmp_path)
    owner = json.loads(fx["owner"].read_text(encoding="utf-8"))
    owner["vtable_store_candidates"] = []
    fx["owner"].write_text(json.dumps(owner), encoding="utf-8")
    with pytest.raises(ValueError, match="no owner-instruction vtable STORE candidate"):
        fx["module"].analyze_vehicle_vtable_pointer_alias(
            fx["instructions"], fx["pointer"], fx["owner"]
        )


def test_fails_closed_on_pointer_format_drift(tmp_path):
    fx = _fixture(tmp_path)
    pointer = json.loads(fx["pointer"].read_text(encoding="utf-8"))
    pointer["format"] = "SHIFT.VehiclePointerOriginFrontier/999"
    fx["pointer"].write_text(json.dumps(pointer), encoding="utf-8")
    with pytest.raises(ValueError, match=fx["module"].POINTER_FORMAT):
        fx["module"].analyze_vehicle_vtable_pointer_alias(
            fx["instructions"], fx["pointer"], fx["owner"]
        )
