#!/usr/bin/env python3
"""Extend verified receiver sources toward their base-pointer origins.

The analysis is deliberately local and fail-closed. It traces only explicit
MOV/LEA definitions inside one linear targeted instruction stream. Calls,
branches, returns, unsupported writes, complex memory expressions and malformed
p-code stop the trace. Reaching a function-entry register only selects the next
direct callers for inspection; it does not prove ownership or object identity.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.VehiclePointerOriginFrontier/1"
RECEIVER_FORMAT = "SHIFT.VehicleReceiverProvenance/1"
LIFECYCLE_FORMAT = "SHIFT.VehicleOwnershipLifecycleFrontier/1"
OWNER_INSTRUCTION_FORMAT = "SHIFT.VehicleOwnershipInstructionEvidence/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
UPPER_CALLER = "0x007155e9"
MAX_COPY_HOPS = 8

REGISTERS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
MEMORY = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword|tword|xmmword)\s+ptr\s+)?"
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*"
    r"(?:([+-])\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]\s*$",
    re.IGNORECASE,
)
REGISTER = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
IMMEDIATE = re.compile(r"^(?:0x[0-9A-Fa-f]+|[0-9]+)$")
BARRIER_PCODE = {"CALL", "CALLIND", "BRANCH", "CBRANCH", "BRANCHIND", "RETURN"}
NONWRITING_FIRST_OPERAND = {"CMP", "TEST", "PUSH", "BT"}


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
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


def load_json(path: Path, expected: str) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(row, dict):
        raise ValueError(f"{path}: expected JSON object")
    if row.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, found {row.get('format')}")
    return row


def parse_register(value: str) -> str | None:
    token = value.strip().upper()
    return token if REGISTER.fullmatch(token) and token in REGISTERS else None


def parse_memory(value: str) -> tuple[str, int] | None:
    match = MEMORY.fullmatch(value)
    if match is None:
        return None
    base = match.group(1).upper()
    if base not in REGISTERS:
        return None
    displacement = 0 if match.group(3) is None else int(match.group(3), 0)
    if match.group(2) == "-":
        displacement = -displacement
    return base, displacement


def hex_offset(value: int) -> str:
    return f"-0x{-value:x}" if value < 0 else f"0x{value:x}"


def validate_pcode(value: Any, address: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"{address}: pcode must be a list")
    result = []
    for op in value:
        if not isinstance(op, dict):
            raise ValueError(f"{address}: pcode operation must be an object")
        opcode, text = op.get("opcode"), op.get("text")
        if not isinstance(opcode, str) or not opcode or not isinstance(text, str) or not text:
            raise ValueError(f"{address}: malformed pcode operation")
        result.append({"opcode": opcode.upper(), "text": text})
    return result


def instruction_parts(instruction: dict[str, Any], function: str):
    address = instruction.get("address")
    mnemonic = instruction.get("mnemonic")
    operands = instruction.get("operands")
    if not isinstance(address, str) or not isinstance(mnemonic, str) or not mnemonic:
        raise ValueError(f"{function}: malformed instruction metadata")
    if not isinstance(operands, list) or any(not isinstance(x, str) for x in operands):
        raise ValueError(f"{address}: operands must be strings")
    pcode = validate_pcode(instruction.get("pcode"), address)
    return mnemonic.upper(), operands, pcode, {op["opcode"] for op in pcode}


def load_instructions(path: Path) -> dict[str, dict[str, Any]]:
    rows = list(read_jsonl(path))
    if not rows:
        raise ValueError(f"{path}: empty instruction export")
    formats = {row.get("format") for row in rows}
    if formats != {INSTRUCTION_FORMAT}:
        raise ValueError(
            f"{path}: pointer-origin analysis requires {INSTRUCTION_FORMAT}; found {sorted(map(str, formats))}"
        )
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        instructions = row.get("instructions")
        if not isinstance(function, dict) or not isinstance(function.get("address"), str):
            raise ValueError(f"{path}: function metadata missing")
        address = function["address"]
        if address in result:
            raise ValueError(f"{path}: duplicate function row {address}")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{address}: instructions missing")
        result[address] = row
    return result


def barrier(mnemonic: str, opcodes: set[str]) -> str | None:
    hits = sorted(opcodes & BARRIER_PCODE)
    if hits:
        return "pcode-barrier:" + ",".join(hits)
    if mnemonic.startswith("J") or mnemonic in {"RET", "RETF", "IRET", "LOOP", "LOOPE", "LOOPNE"}:
        return "control-flow-barrier:" + mnemonic
    return None


def entry_terminal(register: str, calling_convention: Any) -> dict[str, Any]:
    inferred = register == "ECX" and calling_convention == "__thiscall"
    return {
        "register": register,
        "evidence_state": "inferred" if inferred else "unknown",
        "status": "function-entry-abi-receiver-candidate" if inferred else "function-entry-register-state",
        "chain": [],
        "source": {
            "kind": "function-entry-register",
            "register": register,
            "abi_role_candidate": "thiscall-receiver" if inferred else None,
            "object_identity_proven": False,
            "owner_identity_proven": False,
        },
    }


def trace_origin(
    instructions: list[dict[str, Any]],
    before_index: int,
    register: str,
    calling_convention: Any,
    depth: int = 0,
    visited: set[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    if depth > MAX_COPY_HOPS:
        return {"register": register, "evidence_state": "ambiguous", "status": "copy-hop-limit", "chain": [], "source": None}
    visited = set() if visited is None else set(visited)
    key = (before_index, register)
    if key in visited:
        return {"register": register, "evidence_state": "ambiguous", "status": "copy-cycle", "chain": [], "source": None}
    visited.add(key)

    for index in range(before_index - 1, -1, -1):
        ins = instructions[index]
        mnemonic, operands, pcode, opcodes = instruction_parts(ins, "trace")
        address = ins["address"]
        stop = barrier(mnemonic, opcodes)
        if stop:
            return {
                "register": register,
                "evidence_state": "ambiguous",
                "status": "barrier-before-origin",
                "barrier": {"instruction": address, "instruction_text": ins.get("text"), "reason": stop},
                "chain": [],
                "source": None,
            }

        destination = parse_register(operands[0]) if operands else None
        if destination != register:
            continue
        if mnemonic in NONWRITING_FIRST_OPERAND:
            continue
        if mnemonic not in {"MOV", "LEA"}:
            return {
                "register": register,
                "evidence_state": "ambiguous",
                "status": "unsupported-register-definition-or-clobber",
                "clobber": {
                    "instruction": address,
                    "instruction_text": ins.get("text"),
                    "mnemonic": mnemonic,
                    "pcode": pcode,
                },
                "chain": [],
                "source": None,
            }
        if len(operands) < 2:
            return {"register": register, "evidence_state": "ambiguous", "status": "definition-missing-source-operand", "chain": [], "source": None}

        source_operand = operands[1].strip()
        step = {
            "instruction": address,
            "instruction_text": ins.get("text"),
            "mnemonic": mnemonic,
            "destination_register": register,
            "source_operand": source_operand,
            "pcode": pcode,
        }
        source_register = parse_register(source_operand)
        if mnemonic == "MOV" and source_register:
            upstream = trace_origin(
                instructions, index, source_register, calling_convention,
                depth + 1, visited,
            )
            return {
                "register": register,
                "evidence_state": upstream["evidence_state"],
                "status": "register-copy-origin-chain",
                "chain": [step] + list(upstream.get("chain") or []),
                "source": upstream.get("source"),
                "upstream_status": upstream.get("status"),
                "upstream_barrier": upstream.get("barrier"),
                "upstream_clobber": upstream.get("clobber"),
            }

        memory = parse_memory(source_operand)
        if memory:
            base, displacement = memory
            if mnemonic == "MOV" and "LOAD" not in opcodes:
                return {"register": register, "evidence_state": "ambiguous", "status": "memory-origin-without-load-pcode", "chain": [step], "source": None}
            if mnemonic == "LEA" and "LOAD" in opcodes:
                return {"register": register, "evidence_state": "ambiguous", "status": "lea-origin-with-unexpected-load", "chain": [step], "source": None}
            return {
                "register": register,
                "evidence_state": "verified",
                "status": "local-origin-resolved",
                "chain": [step],
                "source": {
                    "kind": "register-relative-load" if mnemonic == "MOV" else "register-relative-address",
                    "base_register": base,
                    "displacement": displacement,
                    "displacement_hex": hex_offset(displacement),
                    "instruction": address,
                    "object_identity_proven": False,
                    "field_semantics_proven": False,
                },
            }
        if mnemonic == "MOV" and IMMEDIATE.fullmatch(source_operand):
            return {
                "register": register,
                "evidence_state": "ambiguous",
                "status": "immediate-origin",
                "chain": [step],
                "source": {"kind": "immediate", "value": source_operand, "pointer_identity_proven": False},
            }
        if "[" in source_operand or "]" in source_operand:
            return {
                "register": register,
                "evidence_state": "ambiguous",
                "status": "complex-memory-origin",
                "chain": [step],
                "source": {"kind": "complex-memory", "operand": source_operand, "object_identity_proven": False},
            }
        return {
            "register": register,
            "evidence_state": "ambiguous",
            "status": "unsupported-origin-source",
            "chain": [step],
            "source": {"kind": "unknown", "operand": source_operand},
        }
    return entry_terminal(register, calling_convention)


def lifecycle_callers(frontier: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = frontier.get("upper_direct_callers")
    if not isinstance(rows, list) or not rows:
        raise ValueError("lifecycle frontier has no upper_direct_callers")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("address"), str):
            raise ValueError("lifecycle frontier contains invalid upper caller row")
        incoming = row.get("direct_incoming_calls")
        if not isinstance(incoming, list):
            raise ValueError(f"{row['address']}: direct_incoming_calls must be a list")
        result[row["address"]] = incoming
    return result


def vtable_store_overlaps(owner: dict[str, Any], function: str, base_register: str) -> list[dict[str, Any]]:
    rows = owner.get("vtable_store_candidates")
    if not isinstance(rows, list):
        raise ValueError("owner instruction evidence vtable_store_candidates must be a list")
    result = []
    for row in rows:
        if not isinstance(row, dict) or row.get("function") != function:
            continue
        for memory in row.get("simple_memory_operands") or []:
            if isinstance(memory, dict) and memory.get("base_register") == base_register:
                result.append(
                    {
                        "function": function,
                        "vtable_store_instruction": row.get("instruction"),
                        "vtable_store_instruction_text": row.get("instruction_text"),
                        "base_register": base_register,
                        "store_displacement": memory.get("displacement"),
                        "store_displacement_hex": memory.get("displacement_hex"),
                        "matching_vtable_references": row.get("matching_vtable_references") or [],
                        "evidence_state": "ambiguous",
                        "pointer_alias_proven": False,
                        "vptr_store_proven": False,
                    }
                )
    return result


def analyze_vehicle_pointer_origin_frontier(
    instruction_export: Path,
    receiver_provenance: Path,
    lifecycle_frontier: Path,
    owner_instruction_evidence: Path,
) -> dict[str, Any]:
    receiver = load_json(receiver_provenance, RECEIVER_FORMAT)
    lifecycle = load_json(lifecycle_frontier, LIFECYCLE_FORMAT)
    owner = load_json(owner_instruction_evidence, OWNER_INSTRUCTION_FORMAT)
    instructions_by_function = load_instructions(instruction_export)
    if receiver.get("callee") != UPPER_CALLER:
        raise ValueError("receiver provenance callee anchor changed")
    if (lifecycle.get("anchors") or {}).get("upper_caller") != UPPER_CALLER:
        raise ValueError("lifecycle frontier upper-caller anchor changed")
    if owner.get("upper_caller") != UPPER_CALLER:
        raise ValueError("owner instruction evidence upper-caller anchor changed")

    incoming_by_caller = lifecycle_callers(lifecycle)
    callsites = receiver.get("callsites")
    if not isinstance(callsites, list) or not callsites:
        raise ValueError("receiver provenance has no callsites")

    origins = []
    next_targets: dict[str, set[str]] = defaultdict(set)
    for callsite in callsites:
        if not isinstance(callsite, dict):
            raise ValueError("receiver provenance contains invalid callsite")
        caller, call_instruction = callsite.get("caller"), callsite.get("call_instruction")
        trace = callsite.get("receiver_definition_trace")
        if not isinstance(caller, str) or not isinstance(call_instruction, str) or not isinstance(trace, dict):
            raise ValueError("receiver callsite metadata missing")
        if caller not in instructions_by_function:
            raise ValueError(f"instruction export missing receiver caller {caller}")
        if caller not in incoming_by_caller:
            raise ValueError(f"lifecycle frontier missing receiver caller {caller}")

        source = trace.get("source")
        if trace.get("evidence_state") != "verified" or not isinstance(source, dict):
            origins.append(
                {
                    "caller": caller,
                    "call_instruction": call_instruction,
                    "receiver_trace_state": trace.get("evidence_state", "unknown"),
                    "receiver_source": source,
                    "base_register": None,
                    "base_origin_trace": None,
                    "vtable_store_overlaps": [],
                    "evidence_state": "unknown" if trace.get("evidence_state") == "unknown" else "ambiguous",
                    "status": "receiver-source-not-eligible-for-base-origin-trace",
                }
            )
            continue

        if source.get("kind") not in {"register-relative-load", "register-relative-address"}:
            origins.append(
                {
                    "caller": caller,
                    "call_instruction": call_instruction,
                    "receiver_trace_state": "verified",
                    "receiver_source": source,
                    "base_register": None,
                    "base_origin_trace": None,
                    "vtable_store_overlaps": [],
                    "evidence_state": "ambiguous",
                    "status": "verified-receiver-source-has-no-simple-base-register",
                }
            )
            continue

        base_register, source_instruction = source.get("base_register"), source.get("instruction")
        if not isinstance(base_register, str) or base_register not in REGISTERS:
            raise ValueError(f"{caller}: verified receiver source has invalid base register")
        if not isinstance(source_instruction, str):
            raise ValueError(f"{caller}: verified receiver source instruction missing")

        function_row = instructions_by_function[caller]
        instructions = function_row["instructions"]
        index = {
            ins.get("address"): i for i, ins in enumerate(instructions)
            if isinstance(ins, dict) and isinstance(ins.get("address"), str)
        }
        if source_instruction not in index:
            raise ValueError(f"{caller}: receiver source instruction absent from export: {source_instruction}")

        base_trace = trace_origin(
            instructions,
            index[source_instruction],
            base_register,
            function_row["function"].get("calling_convention"),
        )
        overlaps = vtable_store_overlaps(owner, caller, base_register)
        incoming_sources = sorted(
            {
                edge.get("from_function") for edge in incoming_by_caller[caller]
                if isinstance(edge, dict) and isinstance(edge.get("from_function"), str)
            }
        )
        terminal_source = base_trace.get("source")
        reached_entry = isinstance(terminal_source, dict) and terminal_source.get("kind") == "function-entry-register"
        if reached_entry:
            for address in incoming_sources:
                next_targets[address].add(
                    f"direct caller of {caller}; base-register origin reached function entry"
                )

        origins.append(
            {
                "caller": caller,
                "caller_name": function_row["function"].get("name"),
                "caller_calling_convention": function_row["function"].get("calling_convention"),
                "call_instruction": call_instruction,
                "receiver_source": source,
                "base_register": base_register,
                "base_origin_trace": base_trace,
                "direct_incoming_callers": incoming_sources,
                "vtable_store_overlaps": overlaps,
                "evidence_state": base_trace.get("evidence_state", "unknown"),
                "status": "base-origin-traced",
                "base_register_is_object_pointer_proven": False,
                "vtable_overlap_is_alias_proof": False,
            }
        )

    target_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(next_targets.items())
    ]
    counts = {
        state: sum(row["evidence_state"] == state for row in origins)
        for state in ("verified", "inferred", "ambiguous", "unknown")
    }
    overlap_count = sum(len(row["vtable_store_overlaps"]) for row in origins)
    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "receiver_provenance": str(receiver_provenance),
        "lifecycle_frontier": str(lifecycle_frontier),
        "owner_instruction_evidence": str(owner_instruction_evidence),
        "upper_caller": UPPER_CALLER,
        "origin_record_count": len(origins),
        "verified_origin_count": counts["verified"],
        "inferred_entry_origin_count": counts["inferred"],
        "ambiguous_origin_count": counts["ambiguous"],
        "unknown_origin_count": counts["unknown"],
        "vtable_overlap_candidate_count": overlap_count,
        "origins": origins,
        "next_instruction_export_targets": target_rows,
        "next_instruction_export_addresses": [row["address"] for row in target_rows],
        "blockers": [
            {
                "id": "entry-register-to-caller-value",
                "evidence_state": "unknown" if target_rows else "verified",
                "required_evidence": "targeted caller callsite instruction/p-code proving the value supplied to the callee entry register" if target_rows else "none",
            },
            {
                "id": "vtable-store-pointer-alias",
                "evidence_state": "ambiguous" if overlap_count else "unknown",
                "required_evidence": "prove same textual base register carries one pointer identity across receiver-source and heuristic-vtable STORE instructions",
            },
            {"id": "local-origin-barriers", "evidence_state": "ambiguous" if counts["ambiguous"] else "verified", "count": counts["ambiguous"]},
            {"id": "unresolved-local-or-entry-origins", "evidence_state": "unknown" if counts["unknown"] else "verified", "count": counts["unknown"]},
        ],
        "scope": {
            "receiver_source_must_be_verified_before_extension": True,
            "local_mov_lea_trace_only": True,
            "cross_call_trace_allowed": False,
            "cross_branch_trace_allowed": False,
            "unknown_first_operand_writer_crossed": False,
            "function_entry_ecx_thiscall_role_is_inferred_only": True,
            "function_entry_register_is_object_identity_proof": False,
            "direct_incoming_caller_is_owner_proof": False,
            "same_register_name_is_pointer_alias_proof": False,
            "heuristic_vtable_store_is_vptr_proof": False,
            "object_identity_proven": False,
            "owner_identity_proven": False,
            "field_semantics_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("receiver_provenance", type=Path)
    parser.add_argument("lifecycle_frontier", type=Path)
    parser.add_argument("owner_instruction_evidence", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--fail-on-unresolved", action="store_true")
    args = parser.parse_args()
    report = analyze_vehicle_pointer_origin_frontier(
        args.instruction_export,
        args.receiver_provenance,
        args.lifecycle_frontier,
        args.owner_instruction_evidence,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["next_instruction_export_addresses"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"origins: {report['origin_record_count']}")
    print(f"verified local origins: {report['verified_origin_count']}")
    print(f"inferred entry origins: {report['inferred_entry_origin_count']}")
    print(f"ambiguous origins: {report['ambiguous_origin_count']}")
    print(f"unknown origins: {report['unknown_origin_count']}")
    print(f"next instruction targets: {len(report['next_instruction_export_addresses'])}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.fail_on_unresolved and (report["ambiguous_origin_count"] or report["unknown_origin_count"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
