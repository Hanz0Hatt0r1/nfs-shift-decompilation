#!/usr/bin/env python3
"""Trace conservative receiver-register definition candidates into FUN_007155e9.

This analyzer consumes the exact instruction export plus
SHIFT.VehicleOwnershipInstructionEvidence/1.  It treats the retail Ghidra
`__thiscall` annotation as an ABI hint that ECX is the receiver-register
candidate, not as proof that ECX contains a vehicle/manager/owner object.

Backward tracing is intentionally restricted to one linear instruction stream
and explicit MOV/LEA definitions.  Calls, branches, returns, unsupported writes,
complex memory operands, or missing definitions stop the trace as ambiguous or
unknown rather than being crossed heuristically.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.VehicleReceiverProvenance/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
OWNER_EVIDENCE_FORMAT = "SHIFT.VehicleOwnershipInstructionEvidence/1"
UPPER_CALLER = "0x007155e9"
ABI_RECEIVER_REGISTER = "ECX"
MAX_COPY_HOPS = 8

_GENERAL_REGISTERS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
_MEMORY_OPERAND = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword|tword|xmmword)\s+ptr\s+)?"
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*"
    r"(?:([+-])\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]\s*$",
    re.IGNORECASE,
)
_REGISTER = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_IMMEDIATE = re.compile(r"^(?:0x[0-9A-Fa-f]+|[0-9]+)$")

_BARRIER_PCODE = {"CALL", "CALLIND", "BRANCH", "CBRANCH", "BRANCHIND", "RETURN"}
_SUPPORTED_DEFINERS = {"MOV", "LEA"}
# Conservative x86 instructions whose first operand is normally written.  If one
# targets the tracked register and is not a supported definer, tracing stops.
_FIRST_OPERAND_WRITERS = {
    "MOV", "LEA", "POP", "XOR", "AND", "OR", "ADD", "ADC", "SUB", "SBB",
    "INC", "DEC", "NEG", "NOT", "IMUL", "MUL", "DIV", "IDIV", "SHL", "SAL",
    "SHR", "SAR", "ROL", "ROR", "RCL", "RCR", "MOVZX", "MOVSX", "BSWAP",
}


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


def _load_json(path: Path, expected_format: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != expected_format:
        raise ValueError(
            f"{path}: expected {expected_format}, found {payload.get('format')}"
        )
    return payload


def _parse_displacement(sign: str | None, token: str | None) -> int:
    if token is None:
        return 0
    value = int(token, 0)
    return -value if sign == "-" else value


def _format_displacement(value: int) -> str:
    return f"-0x{-value:x}" if value < 0 else f"0x{value:x}"


def _parse_memory_operand(value: str) -> tuple[str, int] | None:
    match = _MEMORY_OPERAND.fullmatch(value)
    if match is None:
        return None
    register = match.group(1).upper()
    if register not in _GENERAL_REGISTERS:
        return None
    return register, _parse_displacement(match.group(2), match.group(3))


def _parse_register(value: str) -> str | None:
    token = value.strip().upper()
    if _REGISTER.fullmatch(token) and token in _GENERAL_REGISTERS:
        return token
    return None


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


def _load_instruction_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows = list(_read_jsonl(path))
    if not rows:
        raise ValueError(f"{path}: empty instruction export")
    formats = {row.get("format") for row in rows}
    if formats != {INSTRUCTION_FORMAT}:
        found = ", ".join(sorted(map(str, formats)))
        raise ValueError(
            f"{path}: receiver provenance requires {INSTRUCTION_FORMAT}; found {found}"
        )
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("address"), str):
            raise ValueError(f"{path}: function metadata missing")
        address = function["address"]
        if address in result:
            raise ValueError(f"{path}: duplicate function row {address}")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{address}: instructions missing")
        result[address] = row
    return result


def _owner_calls(report: dict[str, Any]) -> dict[str, list[str]]:
    if report.get("upper_caller") != UPPER_CALLER:
        raise ValueError("owner instruction evidence upper-caller anchor changed")
    rows = report.get("upper_caller_reports")
    if not isinstance(rows, list) or not rows:
        raise ValueError("owner instruction evidence has no upper caller reports")
    result: dict[str, list[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("owner instruction evidence contains invalid caller report")
        address = row.get("address")
        calls = row.get("direct_calls_to_required_target")
        if not isinstance(address, str) or not isinstance(calls, list) or not calls:
            raise ValueError("owner instruction evidence caller address/calls invalid")
        call_addresses: list[str] = []
        for call in calls:
            if not isinstance(call, dict) or not isinstance(call.get("instruction"), str):
                raise ValueError(f"{address}: invalid direct call evidence")
            call_addresses.append(call["instruction"])
        result[address] = call_addresses
    return result


def _instruction_operands(instruction: dict[str, Any], function: str) -> tuple[str, list[str], list[dict[str, str]], set[str]]:
    address = instruction.get("address")
    operands = instruction.get("operands")
    mnemonic = instruction.get("mnemonic")
    if not isinstance(address, str):
        raise ValueError(f"{function}: instruction address missing")
    if not isinstance(mnemonic, str) or not mnemonic:
        raise ValueError(f"{address}: mnemonic missing")
    if not isinstance(operands, list) or any(not isinstance(item, str) for item in operands):
        raise ValueError(f"{address}: operands must be strings")
    pcode = _validate_pcode(instruction.get("pcode"), address)
    return mnemonic.upper(), operands, pcode, {row["opcode"] for row in pcode}


def _barrier_reason(mnemonic: str, opcodes: set[str]) -> str | None:
    hits = sorted(opcodes & _BARRIER_PCODE)
    if hits:
        return "pcode-barrier:" + ",".join(hits)
    if mnemonic.startswith("J") or mnemonic in {"RET", "RETF", "IRET", "LOOP", "LOOPE", "LOOPNE"}:
        return "control-flow-barrier:" + mnemonic
    return None


def _trace_register(
    instructions: list[dict[str, Any]],
    *,
    before_index: int,
    register: str,
    depth: int = 0,
    visited: set[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    if depth > MAX_COPY_HOPS:
        return {
            "register": register,
            "evidence_state": "ambiguous",
            "status": "copy-hop-limit",
            "chain": [],
            "source": None,
        }
    if visited is None:
        visited = set()
    key = (before_index, register)
    if key in visited:
        return {
            "register": register,
            "evidence_state": "ambiguous",
            "status": "copy-cycle",
            "chain": [],
            "source": None,
        }
    visited = set(visited)
    visited.add(key)

    for index in range(before_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = _instruction_operands(instruction, "trace")
        address = instruction["address"]

        barrier = _barrier_reason(mnemonic, opcodes)
        if barrier is not None:
            return {
                "register": register,
                "evidence_state": "ambiguous",
                "status": "barrier-before-definition",
                "barrier": {
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "reason": barrier,
                },
                "chain": [],
                "source": None,
            }

        destination = _parse_register(operands[0]) if operands else None
        if destination != register:
            continue

        if mnemonic not in _SUPPORTED_DEFINERS:
            if mnemonic in _FIRST_OPERAND_WRITERS:
                return {
                    "register": register,
                    "evidence_state": "ambiguous",
                    "status": "unsupported-register-clobber",
                    "clobber": {
                        "instruction": address,
                        "instruction_text": instruction.get("text"),
                        "mnemonic": mnemonic,
                        "pcode": pcode,
                    },
                    "chain": [],
                    "source": None,
                }
            continue

        if len(operands) < 2:
            return {
                "register": register,
                "evidence_state": "ambiguous",
                "status": "definition-missing-source-operand",
                "definition": address,
                "chain": [],
                "source": None,
            }
        source_operand = operands[1].strip()
        step = {
            "instruction": address,
            "instruction_text": instruction.get("text"),
            "mnemonic": mnemonic,
            "destination_register": register,
            "source_operand": source_operand,
            "pcode": pcode,
        }

        source_register = _parse_register(source_operand)
        if mnemonic == "MOV" and source_register is not None:
            upstream = _trace_register(
                instructions,
                before_index=index,
                register=source_register,
                depth=depth + 1,
                visited=visited,
            )
            return {
                "register": register,
                "evidence_state": upstream["evidence_state"],
                "status": "register-copy-chain",
                "chain": [step] + list(upstream.get("chain") or []),
                "source": upstream.get("source"),
                "upstream_status": upstream.get("status"),
                "upstream_barrier": upstream.get("barrier"),
                "upstream_clobber": upstream.get("clobber"),
            }

        memory = _parse_memory_operand(source_operand)
        if memory is not None:
            base_register, displacement = memory
            if mnemonic == "MOV":
                if "LOAD" not in opcodes:
                    return {
                        "register": register,
                        "evidence_state": "ambiguous",
                        "status": "memory-source-without-load-pcode",
                        "chain": [step],
                        "source": None,
                    }
                source_kind = "register-relative-load"
            else:
                # LEA forms an address rather than loading memory.
                if "LOAD" in opcodes:
                    return {
                        "register": register,
                        "evidence_state": "ambiguous",
                        "status": "lea-unexpected-load-pcode",
                        "chain": [step],
                        "source": None,
                    }
                source_kind = "register-relative-address"
            return {
                "register": register,
                "evidence_state": "verified",
                "status": "syntactic-source-resolved",
                "chain": [step],
                "source": {
                    "kind": source_kind,
                    "base_register": base_register,
                    "displacement": displacement,
                    "displacement_hex": _format_displacement(displacement),
                    "instruction": address,
                    "object_identity_proven": False,
                    "field_semantics_proven": False,
                },
            }

        if mnemonic == "MOV" and _IMMEDIATE.fullmatch(source_operand):
            return {
                "register": register,
                "evidence_state": "ambiguous",
                "status": "immediate-source",
                "chain": [step],
                "source": {
                    "kind": "immediate",
                    "value": source_operand,
                    "pointer_identity_proven": False,
                },
            }

        if "[" in source_operand or "]" in source_operand:
            return {
                "register": register,
                "evidence_state": "ambiguous",
                "status": "complex-memory-source",
                "chain": [step],
                "source": {
                    "kind": "complex-memory",
                    "operand": source_operand,
                    "object_identity_proven": False,
                },
            }

        return {
            "register": register,
            "evidence_state": "ambiguous",
            "status": "unsupported-definition-source",
            "chain": [step],
            "source": {"kind": "unknown", "operand": source_operand},
        }

    return {
        "register": register,
        "evidence_state": "unknown",
        "status": "no-local-definition-before-call",
        "chain": [],
        "source": None,
    }


def analyze_vehicle_receiver_provenance(
    instruction_export: Path,
    owner_instruction_evidence: Path,
) -> dict[str, Any]:
    owner = _load_json(owner_instruction_evidence, OWNER_EVIDENCE_FORMAT)
    expected_calls = _owner_calls(owner)
    rows = _load_instruction_rows(instruction_export)

    missing = sorted((set(expected_calls) | {UPPER_CALLER}) - set(rows))
    if missing:
        raise ValueError(
            "instruction export missing receiver-provenance target(s): " + ", ".join(missing)
        )

    upper_metadata = rows[UPPER_CALLER]["function"]
    calling_convention = upper_metadata.get("calling_convention")
    if calling_convention == "__thiscall":
        abi_register = ABI_RECEIVER_REGISTER
        abi_state = "inferred"
        abi_reason = "Ghidra function metadata reports __thiscall; x86 ABI convention nominates ECX"
    else:
        abi_register = None
        abi_state = "unknown"
        abi_reason = "callee is not annotated __thiscall in the targeted export"

    callsites: list[dict[str, Any]] = []
    for caller, addresses in sorted(expected_calls.items()):
        row = rows[caller]
        instructions = row["instructions"]
        by_address = {
            instruction.get("address"): index
            for index, instruction in enumerate(instructions)
            if isinstance(instruction, dict) and isinstance(instruction.get("address"), str)
        }
        for call_address in addresses:
            if call_address not in by_address:
                raise ValueError(
                    f"{caller}: expected call instruction absent from instruction export: {call_address}"
                )
            index = by_address[call_address]
            instruction = instructions[index]
            mnemonic, operands, pcode, opcodes = _instruction_operands(instruction, caller)
            flows = instruction.get("flows")
            if not isinstance(flows, list) or UPPER_CALLER not in flows:
                raise ValueError(
                    f"{caller}: {call_address} no longer flows to {UPPER_CALLER}"
                )
            if "CALL" not in opcodes:
                raise ValueError(
                    f"{caller}: {call_address} flow to {UPPER_CALLER} lacks CALL p-code"
                )
            if abi_register is None:
                trace = {
                    "register": None,
                    "evidence_state": "unknown",
                    "status": "abi-receiver-register-unknown",
                    "chain": [],
                    "source": None,
                }
            else:
                trace = _trace_register(
                    instructions,
                    before_index=index,
                    register=abi_register,
                )
            callsites.append(
                {
                    "caller": caller,
                    "caller_name": row["function"].get("name"),
                    "call_instruction": call_address,
                    "call_instruction_text": instruction.get("text"),
                    "call_operands": operands,
                    "call_pcode": pcode,
                    "callee": UPPER_CALLER,
                    "call_edge_state": "verified",
                    "abi_receiver_register_candidate": abi_register,
                    "abi_receiver_register_state": abi_state,
                    "abi_receiver_register_reason": abi_reason,
                    "receiver_definition_trace": trace,
                    "receiver_object_identity_proven": False,
                    "receiver_owner_identity_proven": False,
                }
            )

    verified_sources = [
        row for row in callsites
        if (row["receiver_definition_trace"] or {}).get("evidence_state") == "verified"
    ]
    ambiguous = [
        row for row in callsites
        if (row["receiver_definition_trace"] or {}).get("evidence_state") == "ambiguous"
    ]
    unknown = [
        row for row in callsites
        if (row["receiver_definition_trace"] or {}).get("evidence_state") == "unknown"
    ]

    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "owner_instruction_evidence": str(owner_instruction_evidence),
        "instruction_export_format": INSTRUCTION_FORMAT,
        "owner_instruction_evidence_format": OWNER_EVIDENCE_FORMAT,
        "callee": UPPER_CALLER,
        "callee_calling_convention": calling_convention,
        "abi_receiver_register_candidate": abi_register,
        "abi_receiver_register_state": abi_state,
        "callsite_count": len(callsites),
        "verified_syntactic_source_count": len(verified_sources),
        "ambiguous_trace_count": len(ambiguous),
        "unknown_trace_count": len(unknown),
        "callsites": callsites,
        "blockers": [
            {
                "id": "abi-register-is-object-proof",
                "evidence_state": "unknown",
                "required_evidence": "independent pointer provenance tying the ABI receiver-register value to one concrete object",
            },
            {
                "id": "register-source-object-identity",
                "evidence_state": "ambiguous" if verified_sources else "unknown",
                "required_evidence": "trace the resolved base-register/value source to allocation/owner/vtable evidence without crossing an unproven alias",
            },
            {
                "id": "blocked-local-traces",
                "evidence_state": "ambiguous" if ambiguous else "verified",
                "count": len(ambiguous),
                "required_evidence": "CFG/SSA-level provenance for traces blocked by call, branch, clobber, complex addressing, or unsupported definitions" if ambiguous else "none",
            },
            {
                "id": "entry-state-traces",
                "evidence_state": "unknown" if unknown else "verified",
                "count": len(unknown),
                "required_evidence": "caller-entry ABI/SSA provenance or predecessor block evidence" if unknown else "none",
            },
        ],
        "scope": {
            "thiscall_annotation_used_as_abi_hint_only": True,
            "ecx_is_this_proven": False,
            "linear_backward_trace_only": True,
            "cross_call_trace_allowed": False,
            "cross_branch_trace_allowed": False,
            "unsupported_register_clobber_crossed": False,
            "simple_mov_register_copy_supported": True,
            "simple_mov_register_relative_load_supported": True,
            "simple_lea_register_relative_address_supported": True,
            "register_source_is_object_identity_proof": False,
            "receiver_owner_identity_proven": False,
            "vehicle_class_identity_proven": False,
            "field_semantics_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("owner_instruction_evidence", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-ambiguous", action="store_true")
    args = parser.parse_args()

    report = analyze_vehicle_receiver_provenance(
        args.instruction_export,
        args.owner_instruction_evidence,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"callsites: {report['callsite_count']}")
    print(f"ABI receiver candidate: {report['abi_receiver_register_candidate']}")
    print(f"verified syntactic sources: {report['verified_syntactic_source_count']}")
    print(f"ambiguous traces: {report['ambiguous_trace_count']}")
    print(f"unknown traces: {report['unknown_trace_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.fail_on_ambiguous and (
        report["ambiguous_trace_count"] or report["unknown_trace_count"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
