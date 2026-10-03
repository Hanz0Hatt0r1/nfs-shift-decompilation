#!/usr/bin/env python3
"""Strengthen heuristic vtable overlaps with local pointer-value continuity.

The analyzer never promotes a heuristic vtable candidate to a recovered C++
vtable/class.  It proves only narrower instruction facts:
- whether one exact MOV stores the referenced candidate-table address through a
  simple register-relative destination; and
- whether the same base-register value is unchanged on the linear instruction
  interval between that STORE and the receiver/base-source use.

Calls, branches, returns, register clobbers, implicit-GPR writers, partial
register writes, or unsupported interval instructions keep aliasing ambiguous.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleVtablePointerAlias/1"
POINTER_FORMAT = "SHIFT.VehiclePointerOriginFrontier/1"
OWNER_FORMAT = "SHIFT.VehicleOwnershipInstructionEvidence/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

STATE_STRENGTH = {"unknown": 0, "ambiguous": 1, "inferred": 2, "verified": 3, "proven": 4}

_ALIAS_TO_GPR = {
    "AL": "EAX", "AH": "EAX", "AX": "EAX", "EAX": "EAX",
    "BL": "EBX", "BH": "EBX", "BX": "EBX", "EBX": "EBX",
    "CL": "ECX", "CH": "ECX", "CX": "ECX", "ECX": "ECX",
    "DL": "EDX", "DH": "EDX", "DX": "EDX", "EDX": "EDX",
    "SI": "ESI", "ESI": "ESI",
    "DI": "EDI", "EDI": "EDI",
    "BP": "EBP", "EBP": "EBP",
    "SP": "ESP", "ESP": "ESP",
}
_REGISTER_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_IMMEDIATE_ADDRESS = re.compile(r"^(?:offset\s+)?(0x[0-9A-Fa-f]+|[0-9]+)$", re.IGNORECASE)

# Instructions whose first explicit operand is their only GPR destination for
# the purpose of this narrow continuity check. Special multi-destination and
# implicit-destination instructions are handled separately below.
_EXPLICIT_DEST = {
    "MOV", "LEA", "MOVZX", "MOVSX", "ADD", "ADC", "SUB", "SBB",
    "AND", "OR", "XOR", "INC", "DEC", "NEG", "NOT", "SHL", "SAL",
    "SHR", "SAR", "ROL", "ROR", "RCL", "RCR", "BSWAP", "POP",
}
_NO_GPR_WRITE = {
    "NOP", "CMP", "TEST", "BT", "PREFETCH", "PREFETCHNTA", "PREFETCHT0",
    "PREFETCHT1", "PREFETCHT2", "CLD", "STD", "CLC", "STC", "CMC",
}
_MULTI_EXPLICIT_WRITE = {"XCHG", "XADD"}


def _load_helper():
    path = Path(__file__).with_name("analyze_vehicle_pointer_origin_frontier.py")
    spec = importlib.util.spec_from_file_location("vehicle_pointer_origin_helper_alias", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    spec.loader.exec_module(module)
    return module


def _load(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, found {payload.get('format')}")
    return payload


def _state(value: Any, label: str) -> str:
    if value not in STATE_STRENGTH:
        raise ValueError(f"{label}: invalid evidence state {value!r}")
    return str(value)


def _weakest(*values: str) -> str:
    return min(values, key=lambda value: STATE_STRENGTH[_state(value, "state merge")])


def _canonical_register(value: str) -> str | None:
    token = value.strip().upper()
    if not _REGISTER_TOKEN.fullmatch(token):
        return None
    return _ALIAS_TO_GPR.get(token)


def _immediate_address(value: str) -> int | None:
    match = _IMMEDIATE_ADDRESS.fullmatch(value.strip())
    if match is None:
        return None
    return int(match.group(1), 0)


def _candidate_index(owner: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = owner.get("vtable_store_candidates")
    if not isinstance(rows, list):
        raise ValueError("owner instruction evidence vtable_store_candidates must be a list")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("owner instruction evidence contains invalid vtable candidate")
        function, instruction = row.get("function"), row.get("instruction")
        if not isinstance(function, str) or not isinstance(instruction, str):
            raise ValueError("vtable STORE candidate identity missing")
        key = function, instruction
        if key in result:
            raise ValueError(f"duplicate vtable STORE candidate {function}@{instruction}")
        result[key] = row
    return result


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


def _implicit_clobber(mnemonic: str, operands: list[str], base: str) -> str | None:
    m = mnemonic.upper()
    if m in {"PUSH", "PUSHF", "PUSHFD", "PUSHA", "PUSHAD", "POP", "POPF", "POPFD", "POPA", "POPAD"} and base == "ESP":
        return "implicit-ESP-stack-update"
    if m in {"ENTER", "LEAVE"} and base in {"ESP", "EBP"}:
        return "implicit-frame-register-update"
    if m.startswith("MOVS") or m.startswith("CMPS"):
        if base in {"ESI", "EDI"}:
            return "implicit-string-index-update"
    if m.startswith("LODS"):
        if base in {"ESI", "EAX"}:
            return "implicit-LODS-register-update"
    if m.startswith("STOS") or m.startswith("SCAS"):
        if base == "EDI":
            return "implicit-destination-index-update"
    if m in {"MUL", "DIV", "IDIV"} and base in {"EAX", "EDX"}:
        return "implicit-EAX-EDX-result"
    if m == "IMUL" and len(operands) == 1 and base in {"EAX", "EDX"}:
        return "implicit-EAX-EDX-result"
    if m in {"CWD", "CDQ"} and base == "EDX":
        return "implicit-EDX-result"
    if m in {"CBW", "CWDE"} and base == "EAX":
        return "implicit-EAX-result"
    if m == "CPUID" and base in {"EAX", "EBX", "ECX", "EDX"}:
        return "implicit-CPUID-result"
    if m == "RDTSC" and base in {"EAX", "EDX"}:
        return "implicit-RDTSC-result"
    if m == "RDTSCP" and base in {"EAX", "EDX", "ECX"}:
        return "implicit-RDTSCP-result"
    if m.startswith("LOOP") and base == "ECX":
        return "implicit-loop-counter-update"
    if m in {"CMPXCHG", "CMPXCHG8B"} and base == "EAX":
        return "implicit-CMPXCHG-EAX-update"
    if m in _MULTI_EXPLICIT_WRITE:
        for operand in operands[:2]:
            if _canonical_register(operand) == base:
                return "multi-destination-register-write"
    return None


def _interval_continuity(
    helper,
    function_row: dict[str, Any],
    first_index: int,
    second_index: int,
    base_register: str,
) -> dict[str, Any]:
    base = base_register.upper()
    start, end = sorted((first_index, second_index))
    instructions = function_row["instructions"]
    checked: list[str] = []
    for index in range(start + 1, end):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = helper.instruction_parts(
            instruction, function_row["function"]["address"]
        )
        address = instruction["address"]
        stop = helper.barrier(mnemonic, opcodes)
        if stop is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "control-flow-or-call-barrier",
                "barrier_instruction": address,
                "barrier_instruction_text": instruction.get("text"),
                "reason": stop,
                "checked_instructions": checked,
            }
        implicit = _implicit_clobber(mnemonic, operands, base)
        if implicit is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "implicit-or-multi-register-clobber",
                "barrier_instruction": address,
                "barrier_instruction_text": instruction.get("text"),
                "reason": implicit,
                "checked_instructions": checked,
            }

        destination = _canonical_register(operands[0]) if operands else None
        if destination == base:
            if mnemonic in _NO_GPR_WRITE:
                pass
            else:
                return {
                    "evidence_state": "ambiguous",
                    "status": "explicit-base-register-clobber",
                    "barrier_instruction": address,
                    "barrier_instruction_text": instruction.get("text"),
                    "reason": f"{mnemonic} writes {base}",
                    "checked_instructions": checked,
                }

        if mnemonic in _NO_GPR_WRITE:
            checked.append(address)
            continue
        if mnemonic in _EXPLICIT_DEST:
            checked.append(address)
            continue
        if mnemonic == "IMUL" and len(operands) >= 2:
            checked.append(address)
            continue
        if mnemonic in _MULTI_EXPLICIT_WRITE:
            checked.append(address)
            continue
        # SIMD/x87 instructions are safe only when no operand names the tracked
        # GPR and their mnemonic clearly belongs to those register files.
        if mnemonic.startswith(("F", "P", "V")) and not any(
            _canonical_register(operand) == base for operand in operands
        ):
            checked.append(address)
            continue
        if mnemonic.startswith(("MOVAPS", "MOVUPS", "MOVDQA", "MOVDQU", "MOVSS", "MOVSD")) and not any(
            _canonical_register(operand) == base for operand in operands
        ):
            checked.append(address)
            continue
        return {
            "evidence_state": "ambiguous",
            "status": "unsupported-interval-instruction",
            "barrier_instruction": address,
            "barrier_instruction_text": instruction.get("text"),
            "reason": f"no fail-closed GPR write rule for {mnemonic}",
            "checked_instructions": checked,
        }

    return {
        "evidence_state": "verified",
        "status": "linear-base-register-value-stable",
        "checked_instructions": checked,
        "base_register": base,
        "instruction_span": abs(second_index - first_index),
        "pointer_identity_proven_beyond_interval": False,
    }


def _exact_store_shape(helper, instruction: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    function = candidate["function"]
    mnemonic, operands, pcode, opcodes = helper.instruction_parts(instruction, function)
    references = candidate.get("matching_vtable_references")
    if not isinstance(references, list) or not references:
        raise ValueError(f"{function}: vtable candidate has no matching references")
    ref_addresses = {
        row.get("to")
        for row in references
        if isinstance(row, dict) and isinstance(row.get("to"), str)
    }
    if not ref_addresses:
        raise ValueError(f"{function}: vtable candidate references malformed")

    result = {
        "instruction": instruction.get("address"),
        "instruction_text": instruction.get("text"),
        "mnemonic": mnemonic,
        "matching_vtable_references": sorted(ref_addresses),
        "pcode_opcodes": sorted(opcodes),
        "evidence_state": "ambiguous",
        "status": "store-shape-not-proven",
        "destination_base_register": None,
        "destination_displacement": None,
        "destination_displacement_hex": None,
        "stored_address": None,
        "stored_address_matches_reference": False,
        "heuristic_table_semantics_proven": False,
        "vptr_store_proven": False,
    }
    if mnemonic != "MOV" or len(operands) < 2 or "STORE" not in opcodes:
        result["reason"] = "requires MOV with STORE p-code and two operands"
        return result
    memory = helper.parse_memory(operands[0])
    if memory is None:
        result["reason"] = "destination is not a simple register-relative memory operand"
        return result
    base, displacement = memory
    result["destination_base_register"] = base
    result["destination_displacement"] = displacement
    result["destination_displacement_hex"] = helper.hex_offset(displacement)
    stored = _immediate_address(operands[1])
    if stored is None:
        result["reason"] = "source operand is not an exact literal address"
        return result
    result["stored_address"] = f"0x{stored:08x}"
    match = any(int(address, 0) == stored for address in ref_addresses)
    result["stored_address_matches_reference"] = match
    if not match:
        result["reason"] = "literal source does not equal a referenced heuristic table address"
        return result
    result["evidence_state"] = "verified"
    result["status"] = "exact-literal-heuristic-table-address-store"
    return result


def analyze_vehicle_vtable_pointer_alias(
    instruction_export: Path,
    pointer_origin_frontier: Path,
    owner_instruction_evidence: Path,
) -> dict[str, Any]:
    helper = _load_helper()
    pointer = _load(pointer_origin_frontier, POINTER_FORMAT)
    owner = _load(owner_instruction_evidence, OWNER_FORMAT)
    rows = helper.load_instructions(instruction_export)
    if pointer.get("upper_caller") != owner.get("upper_caller"):
        raise ValueError("pointer and owner-instruction upper-caller anchors disagree")

    candidates = _candidate_index(owner)
    origins = pointer.get("origins")
    if not isinstance(origins, list):
        raise ValueError("pointer-origin report origins must be a list")

    results: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for origin in origins:
        if not isinstance(origin, dict):
            raise ValueError("pointer-origin report contains invalid origin")
        function = origin.get("caller")
        receiver_source = origin.get("receiver_source")
        overlaps = origin.get("vtable_store_overlaps") or []
        if not isinstance(function, str) or not isinstance(receiver_source, dict):
            continue
        if not isinstance(overlaps, list):
            raise ValueError(f"{function}: vtable_store_overlaps must be a list")
        if not overlaps:
            continue
        source_instruction = receiver_source.get("instruction")
        source_base = receiver_source.get("base_register")
        if not isinstance(source_instruction, str) or not isinstance(source_base, str):
            raise ValueError(f"{function}: receiver source lacks instruction/base register")
        if function not in rows:
            raise ValueError(f"instruction export missing overlap function {function}")
        function_row = rows[function]
        index = _instruction_index(function_row, function)
        if source_instruction not in index:
            raise ValueError(f"{function}: receiver source instruction absent: {source_instruction}")

        for overlap in overlaps:
            if not isinstance(overlap, dict):
                raise ValueError(f"{function}: invalid vtable overlap row")
            store_instruction = overlap.get("vtable_store_instruction")
            overlap_base = overlap.get("base_register")
            if not isinstance(store_instruction, str) or not isinstance(overlap_base, str):
                raise ValueError(f"{function}: vtable overlap identity missing")
            if overlap_base.upper() != source_base.upper():
                raise ValueError(f"{function}: overlap base register changed")
            if store_instruction not in index:
                raise ValueError(f"{function}: vtable STORE instruction absent: {store_instruction}")
            key = function, store_instruction
            candidate = candidates.get(key)
            if candidate is None:
                raise ValueError(f"{function}: overlap has no owner-instruction vtable STORE candidate at {store_instruction}")

            raw_store = function_row["instructions"][index[store_instruction]]
            store_shape = _exact_store_shape(helper, raw_store, candidate)
            continuity = _interval_continuity(
                helper,
                function_row,
                index[store_instruction],
                index[source_instruction],
                source_base,
            )
            combined = _weakest(
                store_shape["evidence_state"], continuity["evidence_state"]
            )
            destination_base = store_shape.get("destination_base_register")
            destination_matches = (
                isinstance(destination_base, str)
                and destination_base.upper() == source_base.upper()
            )
            if store_shape["evidence_state"] == "verified" and not destination_matches:
                combined = "ambiguous"
            zero_offset = store_shape.get("destination_displacement") == 0
            same_pointer_zero_offset = (
                combined == "verified" and destination_matches and zero_offset
            )

            row = {
                "function": function,
                "function_name": function_row["function"].get("name"),
                "receiver_source_instruction": source_instruction,
                "receiver_source_base_register": source_base.upper(),
                "receiver_source_displacement": receiver_source.get("displacement"),
                "receiver_source_displacement_hex": receiver_source.get("displacement_hex"),
                "vtable_store_instruction": store_instruction,
                "store_shape": store_shape,
                "base_register_value_continuity": continuity,
                "destination_base_matches_receiver_source_base": destination_matches,
                "same_pointer_table_store_state": combined,
                "same_pointer_offset_zero_table_store_verified": same_pointer_zero_offset,
                "heuristic_table_identity_state": "ambiguous",
                "vptr_semantics_proven": False,
                "class_identity_proven": False,
                "constructor_role_proven": False,
                "destructor_role_proven": False,
                "owner_identity_proven": False,
            }
            results.append(row)
            if combined != "verified":
                blockers.append(
                    {
                        "id": "vtable-pointer-alias-not-closed",
                        "function": function,
                        "store_instruction": store_instruction,
                        "receiver_source_instruction": source_instruction,
                        "evidence_state": combined,
                        "store_shape_status": store_shape["status"],
                        "continuity_status": continuity["status"],
                    }
                )
            elif not zero_offset:
                blockers.append(
                    {
                        "id": "same-pointer-table-store-nonzero-offset",
                        "function": function,
                        "store_instruction": store_instruction,
                        "offset": store_shape.get("destination_displacement_hex"),
                        "evidence_state": "verified",
                        "note": "same pointer value and table-address STORE are verified, but no vptr/subobject meaning is inferred",
                    }
                )

    verified = sum(row["same_pointer_table_store_state"] == "verified" for row in results)
    zero_verified = sum(row["same_pointer_offset_zero_table_store_verified"] for row in results)
    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "pointer_origin_frontier": str(pointer_origin_frontier),
        "owner_instruction_evidence": str(owner_instruction_evidence),
        "candidate_count": len(results),
        "verified_same_pointer_table_store_count": verified,
        "verified_same_pointer_offset_zero_table_store_count": zero_verified,
        "candidates": results,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "scope": {
            "heuristic_vtable_candidates_remain_heuristic": True,
            "exact_literal_table_address_store_can_be_verified": True,
            "linear_base_register_continuity_can_be_verified": True,
            "cross_call_continuity_allowed": False,
            "cross_branch_continuity_allowed": False,
            "partial_register_writes_are_clobbers": True,
            "unsupported_interval_instruction_crossed": False,
            "same_pointer_table_store_is_vptr_semantics_proof": False,
            "offset_zero_table_store_is_class_identity_proof": False,
            "constructor_identity_proven": False,
            "destructor_identity_proven": False,
            "owner_identity_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("pointer_origin_frontier", type=Path)
    parser.add_argument("owner_instruction_evidence", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-unclosed-alias", action="store_true")
    args = parser.parse_args()
    report = analyze_vehicle_vtable_pointer_alias(
        args.instruction_export,
        args.pointer_origin_frontier,
        args.owner_instruction_evidence,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"candidates: {report['candidate_count']}")
    print(f"verified same-pointer table stores: {report['verified_same_pointer_table_store_count']}")
    print(f"verified same-pointer offset-zero table stores: {report['verified_same_pointer_offset_zero_table_store_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.fail_on_unclosed_alias and report["verified_same_pointer_table_store_count"] != report["candidate_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
