#!/usr/bin/env python3
"""Join vehicle ownership/lifecycle targets to exact Ghidra instruction evidence.

This analyzer consumes the Process 1 ownership/lifecycle frontier plus a targeted
`SHIFT.GhidraFunctionInstructions/2` export. It verifies direct calls into
FUN_007155e9, inventories p-code-backed register-relative LOAD/STORE shapes, and
finds same-instruction references to relevant heuristic vtable candidates.

All pointer/object meaning remains fail-closed. Register identity, adjacency,
and vtable-address stores are not promoted to `this`, ownership, constructors,
destructors, class identity, or field semantics without independent provenance.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.VehicleOwnershipInstructionEvidence/1"
FRONTIER_FORMAT = "SHIFT.VehicleOwnershipLifecycleFrontier/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

UPPER_CALLER = "0x007155e9"
ALTERNATE_CALLER = "0x0079b2d0"

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


def _load_frontier(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != FRONTIER_FORMAT:
        raise ValueError(
            f"{path}: expected {FRONTIER_FORMAT}, found {payload.get('format')}"
        )
    anchors = payload.get("anchors") or {}
    if anchors.get("upper_caller") != UPPER_CALLER:
        raise ValueError("ownership frontier upper-caller anchor changed")
    if anchors.get("alternate_caller") != ALTERNATE_CALLER:
        raise ValueError("ownership frontier alternate-caller anchor changed")
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


def _validate_pcode(value: Any, address: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"{address}: pcode must be a list")
    result: list[dict[str, str]] = []
    for operation in value:
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


def _reference_rows(value: Any, address: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"{address}: references must be a list")
    result: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict):
            raise ValueError(f"{address}: invalid reference row")
        target = row.get("to")
        ref_type = row.get("type")
        if not isinstance(target, str) or not isinstance(ref_type, str):
            raise ValueError(f"{address}: reference target/type missing")
        result.append({"to": target, "type": ref_type})
    return result


def _instruction_rows(export: Path) -> dict[str, dict[str, Any]]:
    rows = list(_read_jsonl(export))
    if not rows:
        raise ValueError(f"{export}: empty instruction export")
    formats = {row.get("format") for row in rows}
    if formats != {INSTRUCTION_FORMAT}:
        found = ", ".join(sorted(map(str, formats)))
        raise ValueError(
            f"{export}: vehicle ownership instruction audit requires {INSTRUCTION_FORMAT}; found {found}"
        )

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("found") is not True:
            raise ValueError(f"{export}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{export}: function metadata missing")
        address = function.get("address")
        if not isinstance(address, str):
            raise ValueError(f"{export}: function address missing")
        if address in result:
            raise ValueError(f"{export}: duplicate function row {address}")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{address}: instructions missing")
        result[address] = row
    return result


def _relevant_vtables(frontier: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for key in ("upper_vtable_memberships", "alternate_vtable_memberships"):
        rows = frontier.get(key) or []
        if not isinstance(rows, list):
            raise ValueError(f"ownership frontier {key} must be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"ownership frontier {key} contains invalid row")
            address = row.get("vtable_address")
            if isinstance(address, str):
                result.add(address)
    return result


def _expected_upper_callers(frontier: dict[str, Any]) -> dict[str, int]:
    rows = frontier.get("upper_direct_callers")
    if not isinstance(rows, list) or not rows:
        raise ValueError("ownership frontier has no upper_direct_callers")
    result: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("ownership frontier contains invalid upper caller row")
        address = row.get("address")
        count = row.get("direct_call_count_to_upper")
        if not isinstance(address, str) or not isinstance(count, int) or count < 1:
            raise ValueError("ownership frontier upper caller address/count invalid")
        if address in result:
            raise ValueError(f"ownership frontier duplicate upper caller {address}")
        result[address] = count
    return result


def _memory_kind(opcodes: set[str]) -> str | None:
    if "LOAD" in opcodes and "STORE" in opcodes:
        return "read-write"
    if "STORE" in opcodes:
        return "write"
    if "LOAD" in opcodes:
        return "read"
    return None


def _analyze_function(
    row: dict[str, Any],
    *,
    relevant_vtables: set[str],
    call_target: str | None,
) -> dict[str, Any]:
    function = row["function"]
    function_address = function["address"]
    accesses: list[dict[str, Any]] = []
    vtable_references: list[dict[str, Any]] = []
    direct_calls: list[dict[str, Any]] = []
    unparsed_memory: list[dict[str, Any]] = []

    for instruction in row["instructions"]:
        if not isinstance(instruction, dict):
            raise ValueError(f"{function_address}: invalid instruction row")
        address = instruction.get("address")
        operands = instruction.get("operands")
        flows = instruction.get("flows")
        if not isinstance(address, str):
            raise ValueError(f"{function_address}: instruction address missing")
        if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
            raise ValueError(f"{address}: operands must be strings")
        if not isinstance(flows, list) or any(not isinstance(value, str) for value in flows):
            raise ValueError(f"{address}: flows must be strings")
        pcode = _validate_pcode(instruction.get("pcode"), address)
        opcodes = {operation["opcode"] for operation in pcode}
        references = _reference_rows(instruction.get("references"), address)

        if call_target is not None and call_target in flows:
            if "CALL" not in opcodes:
                raise ValueError(
                    f"{function_address}: flow to {call_target} at {address} lacks CALL p-code"
                )
            direct_calls.append(
                {
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "flows": list(flows),
                    "pcode": pcode,
                    "evidence_state": "verified",
                }
            )

        memory_kind = _memory_kind(opcodes)
        simple_memory: list[dict[str, Any]] = []
        for operand_index, operand in enumerate(operands):
            if "[" not in operand and "]" not in operand:
                continue
            parsed = _parse_memory_operand(operand)
            if parsed is None:
                unparsed_memory.append(
                    {
                        "instruction": address,
                        "instruction_text": instruction.get("text"),
                        "operand_index": operand_index,
                        "operand": operand,
                        "status": "complex-or-unparsed-memory-operand",
                    }
                )
                continue
            base_register, displacement = parsed
            memory = {
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "operand_index": operand_index,
                "operand": operand,
                "base_register": base_register,
                "displacement": displacement,
                "displacement_hex": _format_displacement(displacement),
                "pcode_memory_kind": memory_kind,
                "pcode_opcodes": sorted(opcodes),
                "evidence_state": "verified" if memory_kind is not None else "ambiguous",
                "object_identity_proven": False,
                "field_semantics_proven": False,
            }
            simple_memory.append(memory)
            if memory_kind is not None:
                accesses.append(memory)

        matching_vtables = [
            ref for ref in references if ref["to"] in relevant_vtables
        ]
        if matching_vtables:
            vtable_references.append(
                {
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "matching_vtable_references": matching_vtables,
                    "pcode": pcode,
                    "pcode_opcodes": sorted(opcodes),
                    "has_store": "STORE" in opcodes,
                    "has_load": "LOAD" in opcodes,
                    "simple_memory_operands": simple_memory,
                    "evidence_state": "ambiguous",
                    "vptr_store_proven": False,
                    "constructor_role_proven": False,
                    "class_identity_proven": False,
                }
            )

    accesses.sort(
        key=lambda item: (
            int(item["instruction"], 16),
            item["operand_index"],
        )
    )
    vtable_references.sort(key=lambda item: int(item["instruction"], 16))
    direct_calls.sort(key=lambda item: int(item["instruction"], 16))
    unparsed_memory.sort(key=lambda item: int(item["instruction"], 16))

    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for access in accesses:
        groups[(access["base_register"], access["displacement"])].append(access)
    access_groups = [
        {
            "base_register": base,
            "displacement": displacement,
            "displacement_hex": _format_displacement(displacement),
            "access_count": len(items),
            "read_count": sum(
                item["pcode_memory_kind"] in {"read", "read-write"} for item in items
            ),
            "write_count": sum(
                item["pcode_memory_kind"] in {"write", "read-write"} for item in items
            ),
            "evidence_state": "verified",
            "object_identity_proven": False,
        }
        for (base, displacement), items in sorted(
            groups.items(), key=lambda item: (item[0][0], item[0][1])
        )
    ]

    store_bases: set[str] = set()
    for vtable_ref in vtable_references:
        if not vtable_ref["has_store"]:
            continue
        for memory in vtable_ref["simple_memory_operands"]:
            store_bases.add(memory["base_register"])
    same_base_overlaps = [
        {
            "base_register": base,
            "access_displacements": sorted(
                {
                    access["displacement_hex"]
                    for access in accesses
                    if access["base_register"] == base
                }
            ),
            "status": "syntactic-same-base-vtable-store-and-memory-access-overlap",
            "evidence_state": "ambiguous",
            "object_identity_proven": False,
            "vptr_field_proven": False,
        }
        for base in sorted(store_bases)
    ]

    return {
        "address": function_address,
        "name": function.get("name"),
        "instruction_count": row.get("instruction_count"),
        "direct_calls_to_required_target": direct_calls,
        "register_relative_accesses": accesses,
        "register_relative_access_groups": access_groups,
        "vtable_reference_instructions": vtable_references,
        "same_base_overlaps": same_base_overlaps,
        "unparsed_memory_operands": unparsed_memory,
        "scope": {
            "register_relative_access_is_object_field_proof": False,
            "same_base_overlap_is_pointer_alias_proof": False,
            "vtable_store_candidate_is_vptr_store_proof": False,
        },
    }


def analyze_vehicle_ownership_instruction_evidence(
    instruction_export: Path,
    ownership_frontier: Path,
) -> dict[str, Any]:
    frontier = _load_frontier(ownership_frontier)
    rows = _instruction_rows(instruction_export)
    expected_targets = frontier.get("instruction_export_addresses")
    if not isinstance(expected_targets, list) or not expected_targets:
        raise ValueError("ownership frontier instruction_export_addresses missing")
    if any(not isinstance(value, str) for value in expected_targets):
        raise ValueError("ownership frontier instruction_export_addresses must be strings")

    missing = sorted(set(expected_targets) - set(rows))
    if missing:
        raise ValueError(
            "instruction export missing ownership target(s): " + ", ".join(missing)
        )

    relevant_vtables = _relevant_vtables(frontier)
    expected_callers = _expected_upper_callers(frontier)

    caller_reports: list[dict[str, Any]] = []
    for address, expected_call_count in sorted(expected_callers.items()):
        report = _analyze_function(
            rows[address],
            relevant_vtables=relevant_vtables,
            call_target=UPPER_CALLER,
        )
        actual = len(report["direct_calls_to_required_target"])
        if actual != expected_call_count:
            raise ValueError(
                f"{address}: expected {expected_call_count} direct CALL(s) to {UPPER_CALLER}; found {actual}"
            )
        report["expected_direct_call_count"] = expected_call_count
        report["call_count_crosscheck_state"] = "verified"
        caller_reports.append(report)

    auxiliary_reports: list[dict[str, Any]] = []
    for address in sorted(set(expected_targets) - set(expected_callers)):
        auxiliary_reports.append(
            _analyze_function(
                rows[address],
                relevant_vtables=relevant_vtables,
                call_target=None,
            )
        )

    all_reports = caller_reports + auxiliary_reports
    vtable_store_candidates = [
        {
            "function": report["address"],
            "function_name": report["name"],
            **candidate,
        }
        for report in all_reports
        for candidate in report["vtable_reference_instructions"]
        if candidate["has_store"]
    ]
    same_base_overlap_candidates = [
        {
            "function": report["address"],
            "function_name": report["name"],
            **overlap,
        }
        for report in all_reports
        for overlap in report["same_base_overlaps"]
    ]
    unparsed = [
        {
            "function": report["address"],
            "function_name": report["name"],
            **row,
        }
        for report in all_reports
        for row in report["unparsed_memory_operands"]
    ]

    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "ownership_frontier": str(ownership_frontier),
        "instruction_export_format": INSTRUCTION_FORMAT,
        "ownership_frontier_format": FRONTIER_FORMAT,
        "upper_caller": UPPER_CALLER,
        "alternate_caller": ALTERNATE_CALLER,
        "relevant_heuristic_vtables": sorted(relevant_vtables),
        "upper_caller_reports": caller_reports,
        "auxiliary_target_reports": auxiliary_reports,
        "vtable_store_candidate_count": len(vtable_store_candidates),
        "vtable_store_candidates": vtable_store_candidates,
        "same_base_overlap_candidate_count": len(same_base_overlap_candidates),
        "same_base_overlap_candidates": same_base_overlap_candidates,
        "unparsed_memory_operand_count": len(unparsed),
        "unparsed_memory_operands": unparsed,
        "blockers": [
            {
                "id": "receiver-pointer-provenance",
                "evidence_state": "unknown",
                "required_evidence": "prove which register/value at each direct CALL is the FUN_007155e9 receiver and trace that value to an object source",
            },
            {
                "id": "vptr-object-alias",
                "evidence_state": "ambiguous" if vtable_store_candidates else "unknown",
                "required_evidence": "prove a vtable-address STORE destination aliases the same object pointer that reaches FUN_007155e9",
            },
            {
                "id": "field-base-object-identity",
                "evidence_state": "ambiguous" if same_base_overlap_candidates else "unknown",
                "required_evidence": "prove syntactically matching base registers carry the same object across the relevant instructions and calls",
            },
            {
                "id": "complex-memory-operands",
                "evidence_state": "ambiguous" if unparsed else "verified",
                "required_evidence": "manual or stronger symbolic treatment for complex x86 memory operands" if unparsed else "none",
            },
        ],
        "scope": {
            "exact_direct_call_flow_and_call_pcode_required": True,
            "register_relative_load_store_pcode_required": True,
            "same_instruction_vtable_reference_used": True,
            "vtable_candidates_remain_heuristic": True,
            "register_name_is_object_identity_proof": False,
            "same_base_register_is_pointer_alias_proof": False,
            "vtable_address_store_is_vptr_store_proof": False,
            "call_adjacency_is_receiver_provenance_proof": False,
            "owner_identity_proven": False,
            "constructor_identity_proven": False,
            "destructor_identity_proven": False,
            "field_semantics_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("ownership_frontier", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-unparsed-memory", action="store_true")
    args = parser.parse_args()

    report = analyze_vehicle_ownership_instruction_evidence(
        args.instruction_export,
        args.ownership_frontier,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"upper callers: {len(report['upper_caller_reports'])}")
    print(f"vtable STORE candidates: {report['vtable_store_candidate_count']}")
    print(f"same-base overlaps: {report['same_base_overlap_candidate_count']}")
    print(f"unparsed memory operands: {report['unparsed_memory_operand_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.fail_on_unparsed_memory and report["unparsed_memory_operand_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
