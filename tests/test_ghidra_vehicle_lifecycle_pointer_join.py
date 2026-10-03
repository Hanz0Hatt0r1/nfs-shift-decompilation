import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_lifecycle_pointer_join.py"
    )
    spec = importlib.util.spec_from_file_location("build_vehicle_lifecycle_pointer_join", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _pcode(opcode):
    return {"opcode": opcode, "text": opcode.lower()}


def _instruction(address, mnemonic, operands, *, pcode=None, refs=None, flows=None):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": f"{mnemonic} " + ",".join(operands),
        "operands": operands,
        "flow_type": "FALL_THROUGH",
        "fallthrough": None,
        "flows": flows or [],
        "references": refs or [],
        "pcode": pcode or [],
    }


def _instruction_row(module, function, instructions):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": function,
        "found": True,
        "function": {
            "address": function,
            "name": f"FUN_{function[2:]}",
            "size": len(instructions) * 4,
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _fixture(tmp_path, *, base_register="ECX", displacement=0, prefix=None, closure_node=None):
    module = _load_module()
    function = "0x00102000"
    vtable = "0x00402200"
    store_address = "0x00102010"
    operand = (
        f"dword ptr [{base_register}]"
        if displacement == 0
        else f"dword ptr [{base_register}+0x{displacement:x}]"
    )

    if closure_node is None:
        closure_node = f"entry:{function}:ECX"
    pointer = {
        "format": module.POINTER_FORMAT,
        "upper_caller": "0x007155e9",
        "nodes": [
            {
                "id": closure_node,
                "kind": "function-entry-register" if closure_node.startswith("entry:") else "register-relative-load",
                "function": function,
                "object_identity_proven": False,
            }
        ],
        "edges": [],
    }
    pointer_path = tmp_path / "pointer.json"
    _write_json(pointer_path, pointer)

    vtable_audit = {
        "format": module.VTABLE_AUDIT_FORMAT,
        "instruction_export_format": module.INSTRUCTION_FORMAT,
        "store_candidates": [
            {
                "function": function,
                "function_name": "FUN_00102000",
                "instruction": store_address,
                "instruction_text": f"MOV {operand},{vtable}",
                "matching_vtable_references": [{"to": vtable, "type": "DATA"}],
                "simple_memory_operands": [
                    {
                        "operand_index": 0,
                        "operand": operand,
                        "base_register": base_register,
                        "displacement": displacement,
                        "displacement_hex": f"0x{displacement:x}",
                    }
                ],
                "complex_memory_operands": [],
                "has_store": True,
                "has_load": False,
                "status": "heuristic-vtable-address-store-candidate",
            }
        ],
    }
    vtable_path = tmp_path / "vtable.json"
    _write_json(vtable_path, vtable_audit)

    lifecycle = {
        "format": module.LIFECYCLE_FORMAT,
        "targets": [
            {
                "class_name": "Child",
                "descriptor": 2,
                "own_vtable": int(vtable, 16),
                "initializer_candidate": "FUN_00102000",
                "initializer_writes_own_vtable": True,
                "initializer_callers": [
                    {"function": "FUN_00103000", "ghidra_direct_call": True}
                ],
                "own_vtable_writer_functions": ["FUN_00102000", "FUN_00102100"],
                "teardown_transition_candidates": [
                    {
                        "function": "FUN_00102100",
                        "evidence_kind": "own-vtable-write-followed-by-call-to-ancestor-vtable-writer",
                    }
                ],
                "complete": True,
                "missing": [],
            }
        ],
    }
    lifecycle_path = tmp_path / "lifecycle.json"
    _write_json(lifecycle_path, lifecycle)

    instructions = list(prefix or [])
    instructions.append(
        _instruction(
            store_address,
            "MOV",
            [operand, vtable],
            pcode=[_pcode("STORE")],
            refs=[{"to": vtable, "type": "DATA"}],
        )
    )
    export_path = tmp_path / "instructions.jsonl"
    _write_jsonl(export_path, [_instruction_row(module, function, instructions)])
    return module, pointer_path, vtable_path, lifecycle_path, export_path


def test_joins_entry_register_vtable_store_to_pointer_closure(tmp_path):
    module, pointer, vtable, lifecycle, export = _fixture(tmp_path)
    report = module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)

    assert report["format"] == "SHIFT.VehicleLifecyclePointerJoin/1"
    assert report["candidate_count"] == 1
    assert report["verified_static_value_source_join_count"] == 1
    row = report["candidates"][0]
    assert row["class_name"] == "Child"
    assert row["class_vtable_match_state"] == "verified"
    assert row["pointer_closure_node"] == "entry:0x00102000:ECX"
    assert row["pointer_value_join_state"] == "verified"
    assert row["join_evidence_state"] == "verified"
    assert row["lifecycle_role"]["role"] == "initializer-candidate"
    assert row["lifecycle_role"]["constructor_semantics_proven"] is False
    assert row["whole_lifetime_class_identity_proven"] is False
    assert row["owner_identity_proven"] is False
    assert set(report["next_instruction_export_addresses"]) == {
        "0x00102100",
        "0x00103000",
    }


def test_register_copy_chain_can_reach_existing_entry_node(tmp_path):
    prefix = [
        _instruction(
            "0x00102004",
            "MOV",
            ["ESI", "ECX"],
            pcode=[_pcode("COPY")],
        )
    ]
    module, pointer, vtable, lifecycle, export = _fixture(
        tmp_path, base_register="ESI", prefix=prefix
    )
    report = module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)
    row = report["candidates"][0]
    assert row["verified_static_value_source_join"] is True
    assert row["pointer_closure_node"] == "entry:0x00102000:ECX"
    assert row["store_base_origin_trace"]["status"] == "register-copy-chain"


def test_register_relative_source_can_match_memory_node(tmp_path):
    memory_node = "memory-source:0x00102000:0x00102004:EBX:64"
    prefix = [
        _instruction(
            "0x00102004",
            "MOV",
            ["ESI", "dword ptr [EBX+0x40]"],
            pcode=[_pcode("LOAD"), _pcode("COPY")],
        )
    ]
    module, pointer, vtable, lifecycle, export = _fixture(
        tmp_path,
        base_register="ESI",
        prefix=prefix,
        closure_node=memory_node,
    )
    report = module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)
    row = report["candidates"][0]
    assert row["verified_static_value_source_join"] is True
    assert row["pointer_closure_node"] == memory_node
    assert row["store_base_origin_trace"]["source"]["kind"] == "register-relative-load"


def test_call_barrier_keeps_alias_ambiguous(tmp_path):
    prefix = [
        _instruction(
            "0x00102008",
            "CALL",
            ["0x00109900"],
            pcode=[_pcode("CALL")],
            flows=["0x00109900"],
        )
    ]
    module, pointer, vtable, lifecycle, export = _fixture(tmp_path, prefix=prefix)
    report = module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)
    row = report["candidates"][0]
    assert row["verified_static_value_source_join"] is False
    assert row["pointer_value_join_state"] == "ambiguous"
    assert row["store_base_origin_trace"]["status"] == "barrier-before-definition"
    assert any(item["id"] == "vtable-store-not-joined-to-pointer-closure" for item in report["blockers"])


def test_nonzero_store_offset_is_not_promoted_to_vptr(tmp_path):
    module, pointer, vtable, lifecycle, export = _fixture(tmp_path, displacement=12)
    report = module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)
    row = report["candidates"][0]
    assert row["verified_static_value_source_join"] is True
    assert row["vtable_written_at_zero_displacement"] is False
    assert row["vptr_field_proven"] is False


def test_duplicate_lifecycle_vtable_stays_ambiguous(tmp_path):
    module, pointer, vtable, lifecycle, export = _fixture(tmp_path)
    payload = json.loads(lifecycle.read_text(encoding="utf-8"))
    duplicate = dict(payload["targets"][0])
    duplicate["class_name"] = "OtherChild"
    duplicate["descriptor"] = 3
    payload["targets"].append(duplicate)
    _write_json(lifecycle, payload)

    report = module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)
    assert report["candidate_count"] == 2
    assert report["verified_static_value_source_join_count"] == 0
    assert all(row["class_vtable_match_state"] == "ambiguous" for row in report["candidates"])
    assert any(item["id"] == "lifecycle-class-vtable-match-not-unique" for item in report["blockers"])


def test_raw_reference_drift_fails_closed(tmp_path):
    module, pointer, vtable, lifecycle, export = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    rows[0]["instructions"][-1]["references"] = []
    _write_jsonl(export, rows)

    with pytest.raises(ValueError, match="audit/raw reference drift"):
        module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)


def test_missing_instruction_export_function_fails_closed(tmp_path):
    module, pointer, vtable, lifecycle, export = _fixture(tmp_path)
    export.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty instruction export"):
        module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)


def test_instruction_format_drift_fails_closed(tmp_path):
    module, pointer, vtable, lifecycle, export = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    rows[0]["format"] = "SHIFT.GhidraFunctionInstructions/1"
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="expected only SHIFT.GhidraFunctionInstructions/2"):
        module.build_vehicle_lifecycle_pointer_join(pointer, vtable, lifecycle, export)
