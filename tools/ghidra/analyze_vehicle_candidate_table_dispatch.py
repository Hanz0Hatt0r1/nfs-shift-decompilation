#!/usr/bin/env python3
"""Correlate verified same-pointer candidate-table stores with indirect dispatch.

This layer proves only a machine-level pattern inside one targeted function:

    exact candidate-table-address STORE through object base + offset
    -> LOAD table pointer from the same stable object base + same offset
    -> CALLIND through table register + slot displacement

The candidate table itself remains heuristic. A matching slot in vtables.json is
reported as candidate static-table consistency, not runtime target/class proof.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleCandidateTableDispatch/1"
ALIAS_FORMAT = "SHIFT.VehicleVtablePointerAlias/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
VTABLE_FORMAT = "SHIFT.GhidraVtableCandidates/1"

_CALL_MEMORY = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword)\s+ptr\s+)?"
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*"
    r"(?:\+\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]\s*$",
    re.IGNORECASE,
)


def _load_module(name: str, filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, found {payload.get('format')}")
    return payload


def _instruction_index(row: dict[str, Any], function: str) -> dict[str, int]:
    instructions = row.get("instructions")
    if not isinstance(instructions, list):
        raise ValueError(f"{function}: instructions missing")
    result: dict[str, int] = {}
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction, dict) or not isinstance(instruction.get("address"), str):
            raise ValueError(f"{function}: invalid instruction row")
        address = instruction["address"]
        if address in result:
            raise ValueError(f"{function}: duplicate instruction address {address}")
        result[address] = index
    return result


def _parse_call_slot(operand: str) -> tuple[str, int] | None:
    match = _CALL_MEMORY.fullmatch(operand)
    if match is None:
        return None
    register = match.group(1).upper()
    displacement = int(match.group(2), 0) if match.group(2) is not None else 0
    return register, displacement


def _table_inventory(root: Path) -> tuple[int, dict[str, dict[str, Any]]]:
    binary_path = root / "binary.json"
    vtable_path = root / "vtables.json"
    if not binary_path.is_file() or not vtable_path.is_file():
        raise FileNotFoundError("Ghidra export requires binary.json and vtables.json")
    binary = json.loads(binary_path.read_text(encoding="utf-8"))
    vtables = json.loads(vtable_path.read_text(encoding="utf-8"))
    if not isinstance(binary, dict):
        raise ValueError("binary.json must contain an object")
    pointer_size = binary.get("pointer_size")
    if not isinstance(pointer_size, int) or pointer_size <= 0:
        raise ValueError("binary.json pointer_size missing/invalid")
    if not isinstance(vtables, dict) or vtables.get("format") != VTABLE_FORMAT:
        raise ValueError(f"vtables.json: expected {VTABLE_FORMAT}")
    if vtables.get("status") != "heuristic-candidates":
        raise ValueError("vtables.json: expected heuristic-candidates status")
    result: dict[str, dict[str, Any]] = {}
    for row in vtables.get("vtables") or []:
        if not isinstance(row, dict) or not isinstance(row.get("address"), str):
            raise ValueError("vtables.json contains invalid candidate")
        address = f"0x{int(row['address'], 0):08x}"
        if address in result:
            raise ValueError(f"duplicate heuristic table candidate {address}")
        result[address] = row
    return pointer_size, result


def _find_table_loads(pointer_helper, function_row: dict[str, Any], object_base: str, table_offset: int) -> list[dict[str, Any]]:
    function = function_row["function"]["address"]
    result = []
    for index, instruction in enumerate(function_row["instructions"]):
        mnemonic, operands, pcode, opcodes = pointer_helper.instruction_parts(instruction, function)
        if mnemonic != "MOV" or len(operands) < 2 or "LOAD" not in opcodes:
            continue
        destination = pointer_helper.parse_register(operands[0])
        memory = pointer_helper.parse_memory(operands[1])
        if destination is None or memory is None:
            continue
        base, displacement = memory
        if base != object_base.upper() or displacement != table_offset:
            continue
        result.append(
            {
                "index": index,
                "instruction": instruction["address"],
                "instruction_text": instruction.get("text"),
                "table_register": destination,
                "object_base_register": base,
                "table_offset": displacement,
                "table_offset_hex": pointer_helper.hex_offset(displacement),
                "pcode": pcode,
                "evidence_state": "verified",
            }
        )
    return result


def _find_indirect_calls(pointer_helper, function_row: dict[str, Any]) -> list[dict[str, Any]]:
    function = function_row["function"]["address"]
    result = []
    for index, instruction in enumerate(function_row["instructions"]):
        mnemonic, operands, pcode, opcodes = pointer_helper.instruction_parts(instruction, function)
        if mnemonic != "CALL" or not operands:
            continue
        parsed = _parse_call_slot(operands[0])
        if parsed is None:
            continue
        base, displacement = parsed
        result.append(
            {
                "index": index,
                "instruction": instruction["address"],
                "instruction_text": instruction.get("text"),
                "operand": operands[0],
                "table_register": base,
                "slot_displacement": displacement,
                "slot_displacement_hex": pointer_helper.hex_offset(displacement),
                "has_callind_pcode": "CALLIND" in opcodes,
                "pcode": pcode,
            }
        )
    return result


def _candidate_slot(table: dict[str, Any], pointer_size: int, displacement: int) -> dict[str, Any]:
    if displacement < 0 or displacement % pointer_size != 0:
        return {
            "aligned": False,
            "slot_index": None,
            "slot_present": False,
            "candidate_target": None,
            "candidate_target_name": None,
        }
    slot_index = displacement // pointer_size
    matches = [
        slot
        for slot in table.get("slots") or []
        if isinstance(slot, dict) and slot.get("slot") == slot_index
    ]
    if len(matches) > 1:
        raise ValueError(f"heuristic table has duplicate slot {slot_index}")
    slot = matches[0] if matches else None
    return {
        "aligned": True,
        "slot_index": slot_index,
        "slot_present": slot is not None,
        "candidate_target": slot.get("target") if slot else None,
        "candidate_target_name": slot.get("name") if slot else None,
    }


def analyze_vehicle_candidate_table_dispatch(
    ghidra_root: Path,
    instruction_export: Path,
    alias_report_path: Path,
) -> dict[str, Any]:
    pointer_helper = _load_module(
        "vehicle_pointer_origin_helper_dispatch",
        "analyze_vehicle_pointer_origin_frontier.py",
    )
    alias_helper = _load_module(
        "vehicle_vtable_pointer_alias_helper_dispatch",
        "analyze_vehicle_vtable_pointer_alias.py",
    )
    alias = _load_json(alias_report_path, ALIAS_FORMAT)
    instruction_rows = pointer_helper.load_instructions(instruction_export)
    pointer_size, tables = _table_inventory(ghidra_root)

    alias_candidates = alias.get("candidates")
    if not isinstance(alias_candidates, list):
        raise ValueError("alias report candidates must be a list")

    dispatches: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    functions_with_verified_alias: set[str] = set()
    for candidate in alias_candidates:
        if not isinstance(candidate, dict):
            raise ValueError("alias report contains invalid candidate")
        if candidate.get("same_pointer_table_store_state") != "verified":
            continue
        function = candidate.get("function")
        store_instruction = candidate.get("vtable_store_instruction")
        store_shape = candidate.get("store_shape")
        if not isinstance(function, str) or not isinstance(store_instruction, str) or not isinstance(store_shape, dict):
            raise ValueError("verified alias candidate identity/store shape missing")
        if function not in instruction_rows:
            raise ValueError(f"instruction export missing verified-alias function {function}")
        functions_with_verified_alias.add(function)
        function_row = instruction_rows[function]
        index = _instruction_index(function_row, function)
        if store_instruction not in index:
            raise ValueError(f"{function}: verified STORE instruction absent: {store_instruction}")

        object_base = store_shape.get("destination_base_register")
        table_offset = store_shape.get("destination_displacement")
        table_address = store_shape.get("stored_address")
        if not isinstance(object_base, str) or not isinstance(table_offset, int) or not isinstance(table_address, str):
            raise ValueError(f"{function}: verified alias store shape incomplete")
        normalized_table = f"0x{int(table_address, 0):08x}"
        table = tables.get(normalized_table)
        if table is None:
            raise ValueError(
                f"{function}: verified alias table {normalized_table} absent from heuristic vtable inventory"
            )

        loads = _find_table_loads(pointer_helper, function_row, object_base, table_offset)
        calls = _find_indirect_calls(pointer_helper, function_row)
        matched_any = False
        for load in loads:
            if load["index"] <= index[store_instruction]:
                continue
            object_continuity = alias_helper._interval_continuity(
                pointer_helper,
                function_row,
                index[store_instruction],
                load["index"],
                object_base,
            )
            if object_continuity.get("evidence_state") != "verified":
                continue
            for call in calls:
                if call["index"] <= load["index"] or call["table_register"] != load["table_register"]:
                    continue
                table_continuity = alias_helper._interval_continuity(
                    pointer_helper,
                    function_row,
                    load["index"],
                    call["index"],
                    load["table_register"],
                )
                slot = _candidate_slot(table, pointer_size, call["slot_displacement"])
                callind_state = "verified" if call["has_callind_pcode"] else "unknown"
                continuity_state = (
                    "verified"
                    if table_continuity.get("evidence_state") == "verified"
                    else "ambiguous"
                )
                slot_state = "verified" if slot["aligned"] and slot["slot_present"] else "ambiguous"
                dispatch_state = (
                    "verified"
                    if callind_state == continuity_state == slot_state == "verified"
                    else "ambiguous"
                )
                dispatches.append(
                    {
                        "function": function,
                        "function_name": function_row["function"].get("name"),
                        "heuristic_table_address": normalized_table,
                        "store_instruction": store_instruction,
                        "store_object_base_register": object_base.upper(),
                        "store_table_offset": table_offset,
                        "store_table_offset_hex": pointer_helper.hex_offset(table_offset),
                        "table_load_instruction": load["instruction"],
                        "table_load_register": load["table_register"],
                        "object_pointer_continuity": object_continuity,
                        "indirect_call_instruction": call["instruction"],
                        "indirect_call_instruction_text": call["instruction_text"],
                        "indirect_call_operand": call["operand"],
                        "callind_pcode_state": callind_state,
                        "table_register_continuity": table_continuity,
                        "slot_displacement": call["slot_displacement"],
                        "slot_displacement_hex": call["slot_displacement_hex"],
                        "candidate_slot": slot,
                        "dispatch_consistency_state": dispatch_state,
                        "runtime_target_identity_proven": False,
                        "heuristic_table_identity_state": "ambiguous",
                        "class_identity_proven": False,
                        "virtual_dispatch_semantics_proven": False,
                    }
                )
                matched_any = True
        if not loads:
            blockers.append(
                {
                    "id": "candidate-table-pointer-load-not-found",
                    "function": function,
                    "heuristic_table_address": normalized_table,
                    "evidence_state": "unknown",
                }
            )
        elif not matched_any:
            blockers.append(
                {
                    "id": "candidate-table-dispatch-chain-not-closed",
                    "function": function,
                    "heuristic_table_address": normalized_table,
                    "evidence_state": "ambiguous",
                    "load_count": len(loads),
                    "indirect_call_count": len(calls),
                }
            )

    verified = sum(row["dispatch_consistency_state"] == "verified" for row in dispatches)
    ambiguous = sum(row["dispatch_consistency_state"] == "ambiguous" for row in dispatches)
    return {
        "format": FORMAT,
        "ghidra_export": str(ghidra_root),
        "instruction_export": str(instruction_export),
        "vtable_pointer_alias": str(alias_report_path),
        "pointer_size": pointer_size,
        "verified_alias_function_count": len(functions_with_verified_alias),
        "dispatch_candidate_count": len(dispatches),
        "verified_dispatch_consistency_count": verified,
        "ambiguous_dispatch_consistency_count": ambiguous,
        "dispatches": dispatches,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "scope": {
            "candidate_table_store_must_be_same_pointer_verified": True,
            "table_pointer_load_must_use_same_object_base_and_offset": True,
            "object_base_continuity_must_be_verified": True,
            "table_register_continuity_must_be_verified": True,
            "callind_pcode_required_for_verified_dispatch": True,
            "slot_must_align_to_pointer_size": True,
            "slot_must_exist_in_heuristic_table_for_verified_consistency": True,
            "heuristic_table_candidate_remains_heuristic": True,
            "candidate_slot_target_is_runtime_target_proof": False,
            "dispatch_consistency_is_class_identity_proof": False,
            "virtual_dispatch_semantics_proven": False,
            "owner_identity_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("vtable_pointer_alias", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-unclosed", action="store_true")
    args = parser.parse_args()
    report = analyze_vehicle_candidate_table_dispatch(
        args.ghidra_export,
        args.instruction_export,
        args.vtable_pointer_alias,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"dispatch candidates: {report['dispatch_candidate_count']}")
    print(f"verified dispatch consistency: {report['verified_dispatch_consistency_count']}")
    print(f"ambiguous dispatch consistency: {report['ambiguous_dispatch_consistency_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.fail_on_unclosed and (
        report["ambiguous_dispatch_consistency_count"] or report["blocker_count"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
