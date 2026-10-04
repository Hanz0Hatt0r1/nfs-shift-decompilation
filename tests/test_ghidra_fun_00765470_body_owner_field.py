from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools" / "ghidra" / "promote_fun_00765470_body_owner_field.py"
    )
    spec = importlib.util.spec_from_file_location(
        "promote_fun_00765470_body_owner_field", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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
            "function_instruction_count": 4,
            "reachable_instruction_count": 4,
            "receiver_equals_half_step_entry_ECX_on_all_reachable_paths": False,
            "receiver_origin_cardinality": 1,
            "receiver_origins_before_body_loop_call": [m.EXPECTED_OLD_ORIGIN],
            "receiver_provenance_ambiguous": True,
        },
        "handoff": {
            "global_vehicle_to_BODY_owner_composition_ready": False,
            "half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven": False,
            "phase703_gate_rewrite_ready": False,
            "phase698_positive_selection_admissible_by_this_artifact_alone": False,
        },
        "blockers": [{"id": "body-loop-ECX-not-proven-as-half-step-entry-ECX"}],
        "scope": {
            "physical_register_provenance_only": True,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def _ins(address, mnemonic, operands, *, payload="90", fallthrough=None, flows=None):
    return {
        "address": address,
        "bytes": payload,
        "mnemonic": mnemonic,
        "text": f"{mnemonic} {','.join(operands)}",
        "operands": list(operands),
        "flow_type": "UNCONDITIONAL_CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": [] if flows is None else list(flows),
        "references": [],
        "pcode": [],
    }


def _instructions(m, *, extra_writer=False, offset="0x339c"):
    rows = [
        _ins(
            m.TARGET_ADDRESS,
            "PUSH",
            ["EBX"],
            fallthrough=m.ENTRY_COPY,
        ),
        _ins(
            m.ENTRY_COPY,
            "MOV",
            ["ESI", "ECX"],
            payload=m.ENTRY_COPY_BYTES,
            fallthrough="0x0076548c",
        ),
    ]
    if extra_writer:
        rows.append(
            _ins(
                "0x00765820",
                "MOV",
                ["ESI", "EDI"],
                payload="8bf7",
                fallthrough=m.OWNER_LOAD,
            )
        )
    rows.extend(
        [
            _ins(
                m.OWNER_LOAD,
                "MOV",
                ["ECX", f"dword ptr [ESI + {offset}]"],
                payload=m.OWNER_LOAD_BYTES,
                fallthrough=m.BODY_LOOP_CALL,
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


def test_promotes_exact_vehicle_field_edge_without_pointer_equality(tmp_path: Path):
    m = _module()
    receiver = _write_json(tmp_path / "receiver.json", _receiver(m))
    instruction_rows = _instructions(m)
    instructions = _write_jsonl(tmp_path / "instructions.jsonl", _row(m, instruction_rows))

    report = m.promote_fun_00765470_body_owner_field(receiver, instructions)

    assert report["format"] == "SHIFT.Fun00765470BodyOwnerFieldProvenance/1"
    edge = report["machine_edge"]
    assert edge["entry_receiver_copy_instruction"] == "0x0076548a"
    assert edge["BODY_owner_pointer_load_instruction"] == "0x00765824"
    assert edge["BODY_owner_pointer_field_offset"] == "0x339c"
    assert edge["BODY_owner_pointer_expression"] == "dword ptr [entry:ECX + 0x339c]"
    assert edge["entry_receiver_equals_call_receiver_pointer"] is False
    assert edge["entry_receiver_to_BODY_owner_pointer_field_edge_proven"] is True
    handoff = report["handoff"]
    assert handoff["half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven"] is True
    assert handoff["global_vehicle_to_BODY_owner_composition_ready"] is True
    assert handoff["phase698_positive_selection_admissible_by_this_artifact_alone"] is False
    assert report["blockers"] == []


def test_rejects_second_esi_writer_before_owner_load(tmp_path: Path):
    m = _module()
    receiver = _write_json(tmp_path / "receiver.json", _receiver(m))
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        _row(m, _instructions(m, extra_writer=True)),
    )
    with pytest.raises(ValueError, match="ESI provenance before owner load is not unique"):
        m.promote_fun_00765470_body_owner_field(receiver, instructions)


def test_rejects_wrong_owner_field_offset(tmp_path: Path):
    m = _module()
    receiver = _write_json(tmp_path / "receiver.json", _receiver(m))
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl",
        _row(m, _instructions(m, offset="0x33a0")),
    )
    with pytest.raises(ValueError, match="field load operands drift"):
        m.promote_fun_00765470_body_owner_field(receiver, instructions)


def test_rejects_receiver_report_without_unique_retail_origin(tmp_path: Path):
    m = _module()
    value = _receiver(m)
    value["analysis"]["receiver_origins_before_body_loop_call"] = [
        m.EXPECTED_OLD_ORIGIN,
        "entry:ECX",
    ]
    value["analysis"]["receiver_origin_cardinality"] = 2
    receiver = _write_json(tmp_path / "receiver.json", value)
    instructions = _write_jsonl(
        tmp_path / "instructions.jsonl", _row(m, _instructions(m))
    )
    with pytest.raises(ValueError, match="exact retail \+0x339c field origin"):
        m.promote_fun_00765470_body_owner_field(receiver, instructions)
