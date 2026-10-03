import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_outer_update_machine_gate.py"
    )
    spec = importlib.util.spec_from_file_location("outer_update_machine_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _p(opcode, text=None):
    return {"opcode": opcode, "text": text or opcode}


def _ins(address, mnemonic, operands=None, *, flows=None, pcode=None):
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


def _call_setup(base, call_address, gate_value, target):
    # x86 __thiscall explicit stack args are pushed right-to-left here:
    # param_5 first, param_1 nearest the CALL. The analyzer walks backwards,
    # therefore rank 5 from CALL is the first PUSH below.
    values = [str(gate_value), "0x44", "0x33", "0x22", "0x11"]
    rows = []
    for offset, value in enumerate(values):
        rows.append(_ins(f"0x{base + offset:08x}", "PUSH", [value]))
    rows.append(_ins(f"0x{base + 5:08x}", "MOV", ["ECX", "ESI"], pcode=[_p("COPY")]))
    rows.append(
        _ins(
            call_address,
            "CALL",
            ["FUN_00794a30"],
            flows=[target],
            pcode=[_p("CALL")],
        )
    )
    return rows


def _row(module, address, instructions, *, cc="__cdecl"):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": f"FUN_{address[2:]}",
            "size": len(instructions),
            "calling_convention": cc,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(tmp_path, *, machine_values=(0, 1, 0)):
    module = _load_module()
    calls = ["0x00713112", "0x00713135", "0x007131b5"]
    scheduling = {
        "format": module.SCHEDULING_FORMAT,
        "outer_update": "0x00770e80",
        "first_caller": module.FIRST_CALLER,
        "upstream_batch": module.BATCH,
        "source_calls_to_first_caller": [
            {"source_ordinal": 0, "param5_constant_value": 0},
            {"source_ordinal": 1, "param5_constant_value": 0},
            {"source_ordinal": 2, "param5_constant_value": 1},
        ],
        "unique_nonzero_param5_source_call_proven": True,
        "machine_callsite_candidates": [
            {
                "from_function": module.BATCH,
                "instruction": address,
                "to": module.FIRST_CALLER,
                "indirect": False,
            }
            for address in calls
        ],
        "source_to_machine_callsite_mapping_state": "unknown",
        "scope": {
            "source_to_machine_callsite_mapping_proven": False,
            "fixed_step_cadence_owner_proven": False,
        },
    }
    scheduling_path = tmp_path / "outer_update_scheduling_gate.json"
    scheduling_path.write_text(json.dumps(scheduling), encoding="utf-8")

    instructions = []
    for index, (call_address, gate_value) in enumerate(zip(calls, machine_values)):
        instructions.extend(
            _call_setup(0x00713080 + index * 0x20, call_address, gate_value, module.FIRST_CALLER)
        )
    instruction_path = tmp_path / "outer_update_machine_instructions.jsonl"
    _write_jsonl(
        instruction_path,
        [
            _row(module, module.BATCH, instructions),
            _row(module, module.FIRST_CALLER, [_ins("0x00794a30", "RET", pcode=[_p("RETURN")])], cc="__thiscall"),
        ],
    )
    return module, scheduling_path, instruction_path


def test_selects_unique_machine_site_by_value_profile_not_source_order(tmp_path):
    module, scheduling, instructions = _fixture(tmp_path, machine_values=(0, 1, 0))
    report = module.analyze_outer_update_machine_gate(scheduling, instructions)

    assert report["format"] == "SHIFT.OuterUpdateMachineGate/1"
    assert report["source_gate_value_profile"] == [0, 0, 1]
    assert [row["fifth_explicit_stack_argument_value"] for row in report["machine_calls"]] == [0, 1, 0]
    assert report["machine_gate_value_profile_complete"] is True
    assert report["machine_gate_value_profile_matches_source"] is True
    assert report["unique_nonzero_machine_callsite_state"] == "verified"
    assert report["unique_nonzero_machine_callsite"] == "0x00713135"
    assert report["source_unique_nonzero_to_machine_callsite_join_state"] == "inferred"
    assert report["semantic_param5_machine_mapping_state"] == "inferred"
    assert report["next_instruction_targets"] == [module.FIRST_CALLER]
    assert report["scope"]["source_order_equals_machine_order_assumed"] is False
    assert report["scope"]["unique_nonzero_machine_callsite_verified"] is True
    assert report["scope"]["source_param5_to_stack_slot_semantics_proven"] is False
    assert report["scope"]["fixed_step_cadence_owner_proven"] is False
    assert "unique_nonzero_machine_gate_callsite_not_verified" not in report["blockers"]
    assert "callee_gate_entry_storage_to_tested_value_not_machine_proven" in report["blockers"]


def test_non_immediate_fifth_stack_argument_keeps_machine_site_unknown(tmp_path):
    module, scheduling, instructions = _fixture(tmp_path)
    rows = [json.loads(line) for line in instructions.read_text(encoding="utf-8").splitlines()]
    # The first PUSH belonging to the middle call is the fifth explicit argument.
    middle_setup_start = 7
    rows[0]["instructions"][middle_setup_start]["operands"] = ["EAX"]
    rows[0]["instructions"][middle_setup_start]["text"] = "PUSH EAX"
    _write_jsonl(instructions, rows)

    report = module.analyze_outer_update_machine_gate(scheduling, instructions)
    assert report["machine_gate_value_profile_complete"] is False
    assert report["unique_nonzero_machine_callsite"] is None
    assert report["source_unique_nonzero_to_machine_callsite_join_state"] == "unknown"
    assert "one_or_more_machine_gate_arguments_not_recovered" in report["blockers"]


def test_stack_memory_write_is_fail_closed_argument_setup_barrier(tmp_path):
    module, scheduling, instructions = _fixture(tmp_path)
    rows = [json.loads(line) for line in instructions.read_text(encoding="utf-8").splitlines()]
    # Insert an unsupported stack-slot write between the final PUSH and first CALL.
    first_call_index = next(
        i for i, ins in enumerate(rows[0]["instructions"])
        if ins["address"] == "0x00713112"
    )
    rows[0]["instructions"].insert(
        first_call_index,
        _ins("0x00713086", "MOV", ["dword ptr [ESP + 0x4]", "EAX"], pcode=[_p("STORE")]),
    )
    rows[0]["instruction_count"] = len(rows[0]["instructions"])
    _write_jsonl(instructions, rows)

    report = module.analyze_outer_update_machine_gate(scheduling, instructions)
    first = report["machine_calls"][0]
    assert first["stack_setup"]["evidence_state"] == "ambiguous"
    assert first["stack_setup"]["status"] == "stack-memory-write-before-complete-argument-setup"
    assert report["machine_gate_value_profile_complete"] is False


def test_other_call_before_five_pushes_is_barrier(tmp_path):
    module, scheduling, instructions = _fixture(tmp_path)
    rows = [json.loads(line) for line in instructions.read_text(encoding="utf-8").splitlines()]
    first_call_index = next(
        i for i, ins in enumerate(rows[0]["instructions"])
        if ins["address"] == "0x00713112"
    )
    # Remove the oldest two PUSHes, forcing the backward trace to hit a CALL
    # after only three recovered arguments.
    del rows[0]["instructions"][0:2]
    rows[0]["instructions"].insert(
        0,
        _ins("0x00713070", "CALL", ["FUN_00600000"], flows=["0x00600000"], pcode=[_p("CALL")]),
    )
    rows[0]["instruction_count"] = len(rows[0]["instructions"])
    _write_jsonl(instructions, rows)

    report = module.analyze_outer_update_machine_gate(scheduling, instructions)
    assert report["machine_calls"][0]["stack_setup"]["status"] == "call-before-complete-argument-setup"
    assert report["unique_nonzero_machine_callsite"] is None


def test_rejects_target_calling_convention_drift(tmp_path):
    module, scheduling, instructions = _fixture(tmp_path)
    rows = [json.loads(line) for line in instructions.read_text(encoding="utf-8").splitlines()]
    rows[1]["function"]["calling_convention"] = "__cdecl"
    _write_jsonl(instructions, rows)

    with pytest.raises(ValueError, match="calling convention drift"):
        module.analyze_outer_update_machine_gate(scheduling, instructions)


def test_rejects_direct_call_instruction_set_drift(tmp_path):
    module, scheduling, instructions = _fixture(tmp_path)
    payload = json.loads(scheduling.read_text(encoding="utf-8"))
    payload["machine_callsite_candidates"][2]["instruction"] = "0x007131c0"
    scheduling.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match scheduling frontier"):
        module.analyze_outer_update_machine_gate(scheduling, instructions)


def test_rejects_upstream_preclaimed_source_to_machine_identity(tmp_path):
    module, scheduling, instructions = _fixture(tmp_path)
    payload = json.loads(scheduling.read_text(encoding="utf-8"))
    payload["source_to_machine_callsite_mapping_state"] = "verified"
    payload["scope"]["source_to_machine_callsite_mapping_proven"] = True
    scheduling.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="preclaims source-to-machine mapping"):
        module.analyze_outer_update_machine_gate(scheduling, instructions)
