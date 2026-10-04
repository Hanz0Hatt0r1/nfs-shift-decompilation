from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "promote_fun_00765470_body_owner_field.py"
    spec = importlib.util.spec_from_file_location("promote_fun_00765470_body_owner_field", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _register_varnode(offset: str):
    return {
        "text": f"(register, {offset}, 4)",
        "space": "register",
        "offset": offset,
        "size": 4,
        "constant": False,
        "register": True,
        "unique": False,
    }


def _pcode_copy(output_offset: str, input_offset: str = "0x4"):
    return {
        "opcode": "COPY",
        "text": f"(register, {output_offset}, 4) COPY (register, {input_offset}, 4)",
        "output": _register_varnode(output_offset),
        "inputs": [_register_varnode(input_offset)],
    }


def _receiver(m):
    return {
        "format": m.RECEIVER_FORMAT,
        "target": {
            "function": m.TARGET_NAME,
            "address": m.TARGET_ADDRESS,
            "body_loop_call_instruction": m.BODY_LOOP_CALL,
            "body_loop_target": m.BODY_LOOP_TARGET,
            "physical_receiver_register": "ECX",
        },
        "analysis": {
            "fixed_point_iterations": 100,
            "function_instruction_count": 5,
            "reachable_instruction_count": 5,
            "receiver_equals_half_step_entry_ECX_on_all_reachable_paths": False,
            "receiver_origin_cardinality": 1,
            "receiver_origins_before_body_loop_call": [m.EXPECTED_OLD_ORIGIN],
            "receiver_provenance_ambiguous": True,
        },
        "scope": {
            "physical_register_provenance_only": True,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def _ins(address, mnemonic, operands, *, payload="90", fallthrough=None, flows=None, pcode=None):
    return {
        "address": address,
        "bytes": payload,
        "mnemonic": mnemonic,
        "text": f"{mnemonic} {','.join(operands)}".rstrip(),
        "operands": list(operands),
        "flow_type": "UNCONDITIONAL_CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": [] if flows is None else list(flows),
        "references": [],
        "pcode": [] if pcode is None else list(pcode),
    }


def _instructions(m, *, explicit_writer=False, implicit_writer=False, offset="0x339c"):
    rows = [
        _ins(m.TARGET_ADDRESS, "PUSH", ["EBX"], fallthrough=m.ENTRY_COPY),
        _ins(
            m.ENTRY_COPY,
            "MOV",
            ["ESI", "ECX"],
            payload=m.ENTRY_COPY_BYTES,
            fallthrough="0x0076548c",
            pcode=[_pcode_copy("0x18", "0x4")],
        ),
    ]
    if explicit_writer:
        rows.append(
            _ins(
                "0x00765820",
                "MOV",
                ["ESI", "EDI"],
                payload="8bf7",
                fallthrough=m.OWNER_LOAD,
                pcode=[_pcode_copy("0x18", "0x1c")],
            )
        )
    elif implicit_writer:
        rows.append(
            _ins(
                "0x00765820",
                "NOP",
                [],
                payload="90",
                fallthrough=m.OWNER_LOAD,
                pcode=[_pcode_copy("0x18", "0x1c")],
            )
        )
    else:
        rows.append(_ins("0x00765820", "NOP", [], fallthrough=m.OWNER_LOAD))
    rows.extend(
        [
            _ins(
                m.OWNER_LOAD,
                "MOV",
                ["ECX", f"dword ptr [ESI + {offset}]"],
                payload=m.OWNER_LOAD_BYTES,
                fallthrough=m.BODY_LOOP_CALL,
                pcode=[_pcode_copy("0x4", "0x18")],
            ),
            _ins(
                m.BODY_LOOP_CALL,
                "CALL",
                [m.BODY_LOOP_TARGET],
                payload="e800000000",
                fallthrough="0x0076582f",
                flows=[m.BODY_LOOP_TARGET],
            ),
        ]
    )
    return rows


def _row(m, rows):
    return {
        "format": m.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": m.TARGET_ADDRESS,
        "found": True,
        "function": {
            "address": m.TARGET_ADDRESS,
            "name": m.TARGET_NAME,
            "size": 967,
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(rows),
        "instructions": rows,
    }


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_jsonl(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _inputs(tmp_path: Path, m, rows):
    receiver_value = _receiver(m)
    receiver_value["analysis"]["function_instruction_count"] = len(rows)
    receiver_value["analysis"]["reachable_instruction_count"] = len(rows)
    return (
        _write_json(tmp_path / "receiver.json", receiver_value),
        _write_jsonl(tmp_path / "instructions.jsonl", _row(m, rows)),
    )


def test_promotes_exact_vehicle_field_edge_without_pointer_equality(tmp_path: Path):
    m = _module()
    receiver, instructions = _inputs(tmp_path, m, _instructions(m))
    report = m.promote_fun_00765470_body_owner_field(receiver, instructions)
    edge = report["machine_edge"]
    assert report["format"] == "SHIFT.Fun00765470BodyOwnerFieldProvenance/1"
    assert edge["entry_receiver_copy_instruction"] == "0x0076548a"
    assert edge["ESI_machine_writer_addresses_before_owner_load"] == ["0x0076548a"]
    assert edge["ESI_pcode_writer_addresses_before_owner_load"] == ["0x0076548a"]
    assert edge["BODY_owner_pointer_load_instruction"] == "0x00765824"
    assert edge["BODY_owner_pointer_field_offset"] == "0x339c"
    assert edge["BODY_owner_pointer_expression"] == "dword ptr [entry:ECX + 0x339c]"
    assert edge["entry_receiver_equals_call_receiver_pointer"] is False
    assert edge["entry_receiver_to_BODY_owner_pointer_field_edge_proven"] is True
    assert report["handoff"]["global_vehicle_to_BODY_owner_composition_ready"] is True
    assert report["handoff"]["phase698_positive_selection_admissible_by_this_artifact_alone"] is False
    assert report["blockers"] == []


def test_rejects_second_explicit_esi_writer_before_owner_load(tmp_path: Path):
    m = _module()
    receiver, instructions = _inputs(tmp_path, m, _instructions(m, explicit_writer=True))
    with pytest.raises(ValueError, match="explicit ESI provenance before owner load is not unique"):
        m.promote_fun_00765470_body_owner_field(receiver, instructions)


def test_rejects_hidden_pcode_esi_writer_before_owner_load(tmp_path: Path):
    m = _module()
    receiver, instructions = _inputs(tmp_path, m, _instructions(m, implicit_writer=True))
    with pytest.raises(ValueError, match="pcode ESI provenance before owner load is not unique"):
        m.promote_fun_00765470_body_owner_field(receiver, instructions)


def test_rejects_missing_structured_pcode(tmp_path: Path):
    m = _module()
    rows = _instructions(m)
    del rows[2]["pcode"]
    receiver, instructions = _inputs(tmp_path, m, rows)
    with pytest.raises(ValueError, match="structured pcode list missing"):
        m.promote_fun_00765470_body_owner_field(receiver, instructions)


def test_rejects_wrong_owner_field_offset(tmp_path: Path):
    m = _module()
    receiver, instructions = _inputs(tmp_path, m, _instructions(m, offset="0x33a0"))
    with pytest.raises(ValueError, match="field load operands drift"):
        m.promote_fun_00765470_body_owner_field(receiver, instructions)


def test_rejects_receiver_report_without_unique_retail_origin(tmp_path: Path):
    m = _module()
    rows = _instructions(m)
    receiver_value = _receiver(m)
    receiver_value["analysis"]["function_instruction_count"] = len(rows)
    receiver_value["analysis"]["reachable_instruction_count"] = len(rows)
    receiver_value["analysis"]["receiver_origins_before_body_loop_call"] = [m.EXPECTED_OLD_ORIGIN, "entry:ECX"]
    receiver_value["analysis"]["receiver_origin_cardinality"] = 2
    receiver = _write_json(tmp_path / "receiver.json", receiver_value)
    instructions = _write_jsonl(tmp_path / "instructions.jsonl", _row(m, rows))
    with pytest.raises(ValueError, match="exact retail \\+0x339c field origin"):
        m.promote_fun_00765470_body_owner_field(receiver, instructions)
