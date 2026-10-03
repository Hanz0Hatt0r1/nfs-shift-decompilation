#!/usr/bin/env python3
"""Narrow the exact machine callsite for the outer-update source gate.

Consumes SHIFT.OuterUpdateSchedulingGate/1 plus a targeted
SHIFT.GhidraFunctionInstructions/2 export containing FUN_00713050 and
FUN_00794a30.  It verifies the three exact direct CALL instructions and supports
only the conservative 32-bit x86 PUSH-form setup for the five explicit stack
arguments of the Ghidra-annotated __thiscall target.

The result can identify a unique machine CALL whose fifth explicit stack
argument is the same unique non-zero constant observed in source.  The join is
kept `inferred`, not `proven`, because the semantic mapping of that fifth stack
slot to source `param_5` still depends on the Ghidra/source __thiscall ABI model.
A later callee-side machine trace must independently connect the tested gate
value to that entry storage before the semantic param_5 mapping is promoted.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.OuterUpdateMachineGate/1"
SCHEDULING_FORMAT = "SHIFT.OuterUpdateSchedulingGate/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
BATCH = "0x00713050"
FIRST_CALLER = "0x00794a30"
EXPLICIT_STACK_ARGUMENT_COUNT = 5
GATE_STACK_RANK_FROM_CALL = 5
GATE_ENTRY_STORAGE_CANDIDATE = "Stack[0x14]:4"


def _load_helper():
    path = Path(__file__).with_name("analyze_vehicle_lifetime_callsite_transfer.py")
    spec = importlib.util.spec_from_file_location("outer_update_machine_gate_helper", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _norm(helper, value: Any) -> str:
    return helper._normalize_address(value)


def _candidate_call_addresses(helper, scheduling: dict[str, Any]) -> list[str]:
    if scheduling.get("outer_update") != "0x00770e80":
        raise ValueError("scheduling gate outer-update anchor drift")
    if scheduling.get("first_caller") != FIRST_CALLER:
        raise ValueError("scheduling gate first-caller anchor drift")
    if scheduling.get("upstream_batch") != BATCH:
        raise ValueError("scheduling gate batch anchor drift")
    if scheduling.get("source_to_machine_callsite_mapping_state") != "unknown":
        raise ValueError("scheduling gate unexpectedly preclaims source-to-machine mapping")
    scope = scheduling.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("scheduling gate scope missing")
    if scope.get("source_to_machine_callsite_mapping_proven") is not False:
        raise ValueError("scheduling gate unexpectedly preclaims machine callsite identity")
    if scope.get("fixed_step_cadence_owner_proven") is not False:
        raise ValueError("scheduling gate unexpectedly preclaims fixed-step ownership")
    if scheduling.get("unique_nonzero_param5_source_call_proven") is not True:
        raise ValueError("scheduling gate has no unique non-zero source gate call")

    source_rows = scheduling.get("source_calls_to_first_caller")
    if not isinstance(source_rows, list) or len(source_rows) != 3:
        raise ValueError("scheduling gate must retain exactly three source calls")
    source_values = [row.get("param5_constant_value") if isinstance(row, dict) else None for row in source_rows]
    if any(value is None for value in source_values):
        raise ValueError("scheduling gate source gate values are not all constant")
    nonzero_values = [int(value) for value in source_values if int(value) != 0]
    if len(nonzero_values) != 1:
        raise ValueError("scheduling gate source non-zero value is not unique")

    rows = scheduling.get("machine_callsite_candidates")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("scheduling gate must retain exactly three machine call candidates")
    addresses: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("scheduling gate contains invalid machine candidate")
        if _norm(helper, row.get("from_function")) != BATCH:
            raise ValueError("scheduling machine candidate source drift")
        if _norm(helper, row.get("to")) != FIRST_CALLER:
            raise ValueError("scheduling machine candidate target drift")
        if row.get("indirect") is not False:
            raise ValueError("scheduling machine candidate is no longer direct")
        addresses.append(_norm(helper, row.get("instruction")))
    if len(set(addresses)) != 3:
        raise ValueError("scheduling machine candidates contain duplicate instruction addresses")
    return sorted(addresses, key=lambda value: int(value, 16))


def _immediate(value: str) -> int | None:
    token = re.sub(r"\s+", "", value).lower()
    # Ghidra's x86 operand representation for integer immediates is normally
    # decimal or 0x-prefixed hexadecimal.  Do not accept symbolic expressions.
    try:
        if token.startswith("-"):
            return int(token, 0)
        if token.startswith("0x") or token.isdigit():
            return int(token, 0)
    except ValueError:
        return None
    return None


def _stack_memory_operand(value: str) -> bool:
    token = re.sub(r"\s+", "", value).upper()
    return "[ESP" in token or "[SP" in token


def _collect_push_arguments(helper, row: dict[str, Any], call_index: int) -> dict[str, Any]:
    function = _norm(helper, row["function"]["address"])
    instructions = row["instructions"]
    pushes: list[dict[str, Any]] = []

    for index in range(call_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = helper._parts(instruction, function)
        address = _norm(helper, instruction["address"])

        if mnemonic == "PUSH":
            if len(operands) != 1:
                return {
                    "evidence_state": "ambiguous",
                    "status": "push-operand-count-unsupported",
                    "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
                    "arguments": pushes,
                }
            pushes.append(
                {
                    "rank_from_call": len(pushes) + 1,
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "operand": operands[0],
                    "immediate_value": _immediate(operands[0]),
                    "pcode": pcode,
                }
            )
            if len(pushes) == EXPLICIT_STACK_ARGUMENT_COUNT:
                return {
                    "evidence_state": "verified",
                    "status": "five-push-explicit-argument-setup",
                    "arguments": pushes,
                    "gate_argument": pushes[GATE_STACK_RANK_FROM_CALL - 1],
                    "gate_entry_storage_candidate": GATE_ENTRY_STORAGE_CANDIDATE,
                }
            continue

        if "CALL" in opcodes or "CALLIND" in opcodes:
            return {
                "evidence_state": "ambiguous",
                "status": "call-before-complete-argument-setup",
                "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
                "arguments": pushes,
            }
        control = helper._control_barrier(mnemonic, opcodes)
        if control is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "control-flow-before-complete-argument-setup",
                "barrier": {"instruction": address, "reason": control, "instruction_text": instruction.get("text")},
                "arguments": pushes,
            }

        # A direct stack-pointer change or a memory write through ESP can alter
        # the relationship between collected PUSHes and callee entry slots.
        if operands and _stack_memory_operand(operands[0]) and mnemonic not in helper._NO_WRITE:
            return {
                "evidence_state": "ambiguous",
                "status": "stack-memory-write-before-complete-argument-setup",
                "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
                "arguments": pushes,
            }
        implicit = helper._implicit_clobber(mnemonic, operands, "ESP")
        if implicit is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "stack-pointer-clobber-before-complete-argument-setup",
                "barrier": {"instruction": address, "reason": implicit, "instruction_text": instruction.get("text")},
                "arguments": pushes,
            }
        destination = helper._canonical_register(operands[0]) if operands else None
        if destination == "ESP" and mnemonic not in helper._NO_WRITE:
            return {
                "evidence_state": "ambiguous",
                "status": "explicit-stack-pointer-write-before-complete-argument-setup",
                "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
                "arguments": pushes,
            }

    return {
        "evidence_state": "unknown",
        "status": "function-entry-before-complete-argument-setup",
        "arguments": pushes,
    }


def _call_indices_by_address(helper, batch_row: dict[str, Any], target: str) -> dict[str, int]:
    indices = helper._direct_call_indices(batch_row, target)
    result: dict[str, int] = {}
    for index in indices:
        instruction = batch_row["instructions"][index]
        address = _norm(helper, instruction["address"])
        if address in result:
            raise ValueError(f"duplicate direct CALL instruction {address}")
        result[address] = index
    return result


def analyze_outer_update_machine_gate(
    scheduling_gate_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    helper = _load_helper()
    scheduling = _load_json(scheduling_gate_path, SCHEDULING_FORMAT)
    candidate_addresses = _candidate_call_addresses(helper, scheduling)
    rows = helper._load_instructions(instruction_export_path)

    batch_row = rows.get(BATCH)
    if batch_row is None:
        raise ValueError("instruction export missing FUN_00713050")
    caller_row = rows.get(FIRST_CALLER)
    if caller_row is None:
        raise ValueError("instruction export missing FUN_00794a30 ABI row")
    caller_cc = (caller_row.get("function") or {}).get("calling_convention")
    if caller_cc != "__thiscall":
        raise ValueError(f"FUN_00794a30 calling convention drift: {caller_cc!r}")

    machine_indices = _call_indices_by_address(helper, batch_row, FIRST_CALLER)
    if sorted(machine_indices, key=lambda value: int(value, 16)) != candidate_addresses:
        raise ValueError(
            "FUN_00713050 direct CALL instruction set does not match scheduling frontier"
        )

    call_rows: list[dict[str, Any]] = []
    unknown_gate_sites: list[str] = []
    nonzero_sites: list[str] = []
    known_gate_values: list[int] = []
    for address in candidate_addresses:
        trace = _collect_push_arguments(helper, batch_row, machine_indices[address])
        gate = trace.get("gate_argument") if isinstance(trace, dict) else None
        gate_value = gate.get("immediate_value") if isinstance(gate, dict) else None
        if trace.get("evidence_state") == "verified" and isinstance(gate_value, int):
            known_gate_values.append(gate_value)
            gate_state = "machine-fifth-stack-arg-zero" if gate_value == 0 else "machine-fifth-stack-arg-nonzero"
            if gate_value != 0:
                nonzero_sites.append(address)
        else:
            unknown_gate_sites.append(address)
            gate_state = "unknown"
        call_rows.append(
            {
                "call_instruction": address,
                "target": FIRST_CALLER,
                "stack_setup": trace,
                "fifth_explicit_stack_argument_value": gate_value,
                "machine_gate_value_state": gate_state,
                "semantic_param5_mapping_state": "inferred" if trace.get("evidence_state") == "verified" else "unknown",
            }
        )

    source_rows = scheduling["source_calls_to_first_caller"]
    source_values = [int(row["param5_constant_value"]) for row in source_rows]
    source_nonzero_value = next(value for value in source_values if value != 0)
    machine_profile_complete = not unknown_gate_sites and len(known_gate_values) == 3
    machine_profile_matches_source = machine_profile_complete and sorted(known_gate_values) == sorted(source_values)
    unique_nonzero_machine_site = len(nonzero_sites) == 1 and machine_profile_matches_source
    selected = nonzero_sites[0] if unique_nonzero_machine_site else None

    blockers: list[str] = []
    if unknown_gate_sites:
        blockers.append("one_or_more_machine_gate_arguments_not_recovered")
    if not machine_profile_matches_source:
        blockers.append("machine_gate_value_profile_does_not_match_source_profile")
    if not unique_nonzero_machine_site:
        blockers.append("unique_nonzero_machine_gate_callsite_not_verified")
    # The target convention plus PUSH position nominates the source param_5 slot,
    # but it is not independent callee-side machine proof of the tested gate.
    blockers.extend(
        [
            "callee_gate_entry_storage_to_tested_value_not_machine_proven",
            "gate_eligible_statement_dynamic_execution_count_not_proven",
            "FUN_00713050_invocation_cadence_owner_not_proven",
            "FUN_0079b2d0_dispatch_owner_not_proven",
            "rendered_frame_relation_not_proven",
        ]
    )

    return {
        "format": FORMAT,
        "inputs": {
            "scheduling_gate": str(scheduling_gate_path),
            "instruction_export": str(instruction_export_path),
        },
        "batch": BATCH,
        "target": FIRST_CALLER,
        "target_calling_convention": caller_cc,
        "explicit_stack_argument_count": EXPLICIT_STACK_ARGUMENT_COUNT,
        "gate_stack_rank_from_call": GATE_STACK_RANK_FROM_CALL,
        "gate_entry_storage_candidate": GATE_ENTRY_STORAGE_CANDIDATE,
        "source_gate_value_profile": source_values,
        "source_unique_nonzero_gate_value": source_nonzero_value,
        "machine_calls": call_rows,
        "machine_gate_value_profile_complete": machine_profile_complete,
        "machine_gate_value_profile_matches_source": machine_profile_matches_source,
        "unique_nonzero_machine_callsite_state": "verified" if unique_nonzero_machine_site else "unknown",
        "unique_nonzero_machine_callsite": selected,
        "source_unique_nonzero_to_machine_callsite_join_state": "inferred" if unique_nonzero_machine_site else "unknown",
        "semantic_param5_machine_mapping_state": "inferred" if unique_nonzero_machine_site else "unknown",
        "dynamic_execution_count_state": "unknown",
        "cadence_owner_state": "unknown",
        "next_instruction_targets": [FIRST_CALLER] if unique_nonzero_machine_site else [BATCH, FIRST_CALLER],
        "blockers": sorted(set(blockers)),
        "scope": {
            "exact_machine_call_instruction_set_verified": True,
            "five_push_argument_shape_required": True,
            "machine_gate_value_profile_verified": machine_profile_matches_source,
            "unique_nonzero_machine_callsite_verified": unique_nonzero_machine_site,
            "source_order_equals_machine_order_assumed": False,
            "source_to_machine_join_uses_unique_value_profile": unique_nonzero_machine_site,
            "source_param5_to_stack_slot_semantics_proven": False,
            "callee_gate_test_to_entry_storage_machine_proven": False,
            "dynamic_statement_execution_count_proven": False,
            "fixed_step_cadence_owner_proven": False,
            "rendered_frame_cadence_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "note": (
                "A complete 0,0,nonzero machine fifth-stack-argument profile can select one exact CALL "
                "without source-order pairing. The source param_5 semantic join remains inferred until "
                "FUN_00794a30 machine evidence proves that the tested gate value comes from this entry slot."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scheduling_gate", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_outer_update_machine_gate(args.scheduling_gate, args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"machine profile matches source: {report['machine_gate_value_profile_matches_source']}")
    print(f"unique nonzero machine callsite: {report['unique_nonzero_machine_callsite']}")
    print(f"semantic param_5 mapping: {report['semantic_param5_machine_mapping_state']}")
    print(f"blockers: {len(report['blockers'])}")
    if args.json_out:
        print(f"json: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
