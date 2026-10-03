#!/usr/bin/env python3
"""Audit exact heuristic-vtable references in targeted Ghidra instruction exports.

A same-instruction reference to a heuristic table address plus Ghidra p-code
STORE is stronger evidence than a function-level xref, but it still does not
prove class identity, a vptr field, or constructor/destructor semantics. This
tool preserves that boundary explicitly.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraVtableXrefInstructionAudit/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
CONSTRUCTION_FORMAT = "SHIFT.GhidraConstructionFrontier/1"
_GENERAL_REGISTERS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
_MEMORY_OPERAND = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword|tword|xmmword)\s+ptr\s+)?"
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*"
    r"(?:([+-])\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]\s*$",
    re.IGNORECASE,
)


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected object")
    return payload


def _parse_displacement(sign: str | None, token: str | None) -> int:
    if token is None:
        return 0
    value = int(token, 0)
    return -value if sign == "-" else value


def _format_displacement(value: int) -> str:
    return f"-0x{-value:x}" if value < 0 else f"0x{value:x}"


def _parse_memory_operand(operand: str) -> tuple[str, int] | None:
    match = _MEMORY_OPERAND.fullmatch(operand)
    if match is None:
        return None
    register = match.group(1).upper()
    if register not in _GENERAL_REGISTERS:
        return None
    return register, _parse_displacement(match.group(2), match.group(3))


def _validate_pcode(pcode: Any, address: str) -> list[dict[str, str]]:
    if not isinstance(pcode, list):
        raise ValueError(f"{address}: pcode must be a list")
    result: list[dict[str, str]] = []
    for operation in pcode:
        if not isinstance(operation, dict):
            raise ValueError(f"{address}: pcode operation must be an object")
        opcode = operation.get("opcode")
        text = operation.get("text")
        if not isinstance(opcode, str) or not opcode:
            raise ValueError(f"{address}: pcode opcode missing")
        if not isinstance(text, str) or not text:
            raise ValueError(f"{address}: pcode text missing")
        result.append({"opcode": opcode.upper(), "text": text})
    return result


def _load_frontier(path: Path) -> tuple[dict[str, dict[str, Any]], set[str]]:
    payload = _read_json(path)
    if payload.get("format") != CONSTRUCTION_FORMAT:
        raise ValueError(f"{path}: expected {CONSTRUCTION_FORMAT}")
    rows = payload.get("frontier_candidates")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: frontier_candidates must be a list")

    by_function: dict[str, dict[str, Any]] = {}
    all_vtables: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{path}: invalid frontier candidate")
        function = row.get("function")
        if not isinstance(function, str):
            raise ValueError(f"{path}: frontier candidate missing function")
        if function in by_function:
            raise ValueError(f"{path}: duplicate frontier function {function}")
        vtables = row.get("referenced_vtable_addresses")
        if not isinstance(vtables, list) or any(not isinstance(value, str) for value in vtables):
            raise ValueError(f"{path}: {function} referenced_vtable_addresses must be a string list")
        by_function[function] = row
        all_vtables.update(vtables)
    return by_function, all_vtables


def _reference_rows(references: Any, address: str) -> list[dict[str, str]]:
    if not isinstance(references, list):
        raise ValueError(f"{address}: references must be a list")
    result: list[dict[str, str]] = []
    for ref in references:
        if not isinstance(ref, dict):
            raise ValueError(f"{address}: invalid reference row")
        target = ref.get("to")
        ref_type = ref.get("type")
        if not isinstance(target, str) or not isinstance(ref_type, str):
            raise ValueError(f"{address}: reference target/type missing")
        result.append({"to": target, "type": ref_type})
    return result


def audit_vtable_xref_instructions(
    instruction_export: Path,
    construction_frontier: Path,
) -> dict[str, Any]:
    frontier_by_function, all_vtables = _load_frontier(construction_frontier)
    rows = list(_read_jsonl(instruction_export))
    if not rows:
        raise ValueError(f"{instruction_export}: empty instruction export")

    formats = {row.get("format") for row in rows}
    if formats != {INSTRUCTION_FORMAT}:
        found = ", ".join(sorted(map(str, formats)))
        raise ValueError(
            f"{instruction_export}: vtable instruction audit requires {INSTRUCTION_FORMAT}; found {found}"
        )

    xrefs: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    function_count = 0
    instruction_count = 0

    for row in rows:
        if row.get("found") is not True:
            raise ValueError(f"{instruction_export}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{instruction_export}: missing function metadata")
        function_address = function.get("address")
        if not isinstance(function_address, str):
            raise ValueError(f"{instruction_export}: function address missing")
        frontier = frontier_by_function.get(function_address)
        if frontier is None:
            raise ValueError(
                f"{instruction_export}: function {function_address} is absent from construction frontier"
            )
        allowed_vtables = set(frontier["referenced_vtable_addresses"])

        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{function_address}: instructions missing")
        function_count += 1
        instruction_count += len(instructions)

        for instruction in instructions:
            if not isinstance(instruction, dict):
                raise ValueError(f"{function_address}: invalid instruction row")
            address = instruction.get("address")
            operands = instruction.get("operands")
            if not isinstance(address, str):
                raise ValueError(f"{function_address}: instruction address missing")
            if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
                raise ValueError(f"{address}: operands must be strings")
            refs = _reference_rows(instruction.get("references"), address)
            pcode = _validate_pcode(instruction.get("pcode"), address)
            opcodes = {operation["opcode"] for operation in pcode}

            matching_refs = [
                ref for ref in refs
                if ref["to"] in allowed_vtables and ref["to"] in all_vtables
            ]
            if not matching_refs:
                continue

            simple_memory_operands: list[dict[str, Any]] = []
            complex_memory_operands: list[dict[str, Any]] = []
            for operand_index, operand in enumerate(operands):
                if "[" not in operand and "]" not in operand:
                    continue
                parsed = _parse_memory_operand(operand)
                if parsed is None:
                    complex_memory_operands.append(
                        {"operand_index": operand_index, "operand": operand}
                    )
                    continue
                base_register, displacement = parsed
                simple_memory_operands.append(
                    {
                        "operand_index": operand_index,
                        "operand": operand,
                        "base_register": base_register,
                        "displacement": displacement,
                        "displacement_hex": _format_displacement(displacement),
                    }
                )

            has_store = "STORE" in opcodes
            has_load = "LOAD" in opcodes
            if has_store:
                status = "heuristic-vtable-address-store-candidate"
            elif has_load:
                status = "heuristic-vtable-address-load-candidate"
            else:
                status = "heuristic-vtable-address-reference-without-load-store"

            record = {
                "function": function_address,
                "function_name": function.get("name"),
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "matching_vtable_references": matching_refs,
                "pcode": pcode,
                "pcode_opcodes": sorted(opcodes),
                "simple_memory_operands": simple_memory_operands,
                "complex_memory_operands": complex_memory_operands,
                "has_store": has_store,
                "has_load": has_load,
                "frontier_status": frontier.get("status"),
                "promoted": False,
                "status": status,
            }
            xrefs.append(record)

            if has_store and not simple_memory_operands:
                blockers.append(
                    {
                        "function": function_address,
                        "instruction": address,
                        "matching_vtable_references": matching_refs,
                        "complex_memory_operands": complex_memory_operands,
                        "status": "vtable-address-store-without-simple-register-relative-memory-operand",
                        "promoted": False,
                    }
                )

    xrefs.sort(key=lambda item: (item["function"], int(item["instruction"], 16)))
    blockers.sort(key=lambda item: (item["function"], int(item["instruction"], 16)))

    store_candidates = [row for row in xrefs if row["has_store"]]
    load_candidates = [row for row in xrefs if row["has_load"] and not row["has_store"]]
    non_memory_refs = [row for row in xrefs if not row["has_load"] and not row["has_store"]]

    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in store_candidates:
        for memory in row["simple_memory_operands"]:
            for ref in row["matching_vtable_references"]:
                groups[(memory["base_register"], memory["displacement"], ref["to"])].append(row)

    store_groups = [
        {
            "base_register": base,
            "displacement": displacement,
            "displacement_hex": _format_displacement(displacement),
            "heuristic_vtable": vtable,
            "instruction_count": len(group_rows),
            "function_addresses": sorted({row["function"] for row in group_rows}),
            "status": "repeated-heuristic-vtable-address-store-shape",
            "promoted": False,
        }
        for (base, displacement, vtable), group_rows in sorted(
            groups.items(), key=lambda item: (item[0][2], item[0][0], item[0][1])
        )
    ]

    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "construction_frontier": str(construction_frontier),
        "instruction_export_format": INSTRUCTION_FORMAT,
        "construction_frontier_format": CONSTRUCTION_FORMAT,
        "function_count": function_count,
        "instruction_count": instruction_count,
        "vtable_reference_instruction_count": len(xrefs),
        "store_candidate_count": len(store_candidates),
        "load_candidate_count": len(load_candidates),
        "non_memory_reference_count": len(non_memory_refs),
        "store_shape_group_count": len(store_groups),
        "blocker_count": len(blockers),
        "vtable_reference_instructions": xrefs,
        "store_candidates": store_candidates,
        "load_candidates": load_candidates,
        "non_memory_references": non_memory_refs,
        "store_shape_groups": store_groups,
        "blockers": blockers,
        "scope": {
            "exact_same_instruction_vtable_reference_required": True,
            "structured_pcode_opcode_used": True,
            "vtable_candidates_remain_heuristic": True,
            "store_candidate_is_vptr_store_proof": False,
            "base_register_is_object_pointer": False,
            "base_register_is_this_pointer": False,
            "constructor_identity_proven": False,
            "destructor_identity_proven": False,
            "class_identity_proven": False,
            "object_layout_proven": False,
            "virtual_dispatch_target_proven": False,
            "automatic_function_renaming_performed": False,
            "note": (
                "A STORE candidate proves only that one selected machine instruction both references "
                "an address carried by the heuristic-vtable frontier and contains Ghidra STORE p-code. "
                "The destination register+offset is syntactic. Proving a vptr field, constructor, "
                "destructor, class identity, subobject offset, or virtual target requires independent "
                "pointer provenance and layout/call-site evidence."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("construction_frontier", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--fail-on-blocker",
        action="store_true",
        help="return non-zero when a vtable-address STORE lacks a simple register-relative memory operand",
    )
    args = parser.parse_args()

    report = audit_vtable_xref_instructions(
        args.instruction_export,
        args.construction_frontier,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"functions: {report['function_count']}")
    print(f"vtable-reference instructions: {report['vtable_reference_instruction_count']}")
    print(f"store candidates: {report['store_candidate_count']}")
    print(f"load candidates: {report['load_candidate_count']}")
    print(f"non-memory references: {report['non_memory_reference_count']}")
    print(f"blockers: {report['blocker_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.fail_on_blocker and report["blocker_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
