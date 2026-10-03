#!/usr/bin/env python3
"""Join lifecycle vtable-store evidence to the proven vehicle pointer-value graph.

This is a fail-closed composition layer.  It requires an exact vtable-address
STORE from the Ghidra v2 instruction export, traces the STORE destination base
register backwards with a deliberately small MOV/LEA model, and only joins that
trace to an already-existing node in SHIFT.VehiclePointerValueClosure/1.

Even a verified join proves only a static value-source relationship at one
instruction.  It does not by itself prove C++ constructor/destructor semantics,
whole-lifetime class identity, ownership, or that a register is `this`.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.VehicleLifecyclePointerJoin/1"
POINTER_FORMAT = "SHIFT.VehiclePointerValueClosure/1"
VTABLE_AUDIT_FORMAT = "SHIFT.GhidraVtableXrefInstructionAudit/1"
LIFECYCLE_FORMAT = "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

STATES = {"proven", "verified", "inferred", "ambiguous", "unknown"}
STATE_STRENGTH = {"unknown": 0, "ambiguous": 1, "inferred": 2, "verified": 3, "proven": 4}
_GENERAL_REGISTERS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
_MEMORY_OPERAND = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword|tword|xmmword)\s+ptr\s+)?"
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*"
    r"(?:([+-])\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]\s*$",
    re.IGNORECASE,
)
_IMMEDIATE = re.compile(r"^(?:0x[0-9A-Fa-f]+|[0-9]+)$")
_BARRIER_PCODE = {"CALL", "CALLIND", "BRANCH", "CBRANCH", "BRANCHIND", "RETURN"}
_READ_ONLY_FIRST = {
    "CMP", "TEST", "PUSH", "BT", "BTS", "BTR", "BTC", "NOP", "PREFETCHNTA",
    "PREFETCHT0", "PREFETCHT1", "PREFETCHT2",
}
_SUPPORTED_DEFINERS = {"MOV", "LEA"}
MAX_COPY_HOPS = 8


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, found {payload.get('format')}")
    return payload


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


def _state(value: Any, label: str) -> str:
    if value not in STATES:
        raise ValueError(f"{label}: invalid evidence state {value!r}")
    return str(value)


def _weakest(*values: str) -> str:
    if not values:
        return "unknown"
    checked = [_state(value, "state merge") for value in values]
    return min(checked, key=lambda value: STATE_STRENGTH[value])


def _normalize_address(value: Any) -> str:
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        token = value.strip()
        if token.upper().startswith("FUN_"):
            token = token[4:]
            number = int(token, 16)
        else:
            number = int(token, 0)
    else:
        raise ValueError(f"invalid address value {value!r}")
    if number < 0 or number > 0xFFFFFFFF:
        raise ValueError(f"address out of 32-bit range: {value!r}")
    return f"0x{number:08x}"


def _function_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    try:
        if token.upper().startswith("FUN_"):
            return _normalize_address(token)
        if token.lower().startswith("0x"):
            return _normalize_address(token)
    except ValueError:
        return None
    return None


def _parse_displacement(sign: str | None, token: str | None) -> int:
    if token is None:
        return 0
    value = int(token, 0)
    return -value if sign == "-" else value


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
    return token if token in _GENERAL_REGISTERS else None


def _pcode(instruction: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    address = instruction.get("address")
    rows = instruction.get("pcode")
    if not isinstance(rows, list):
        raise ValueError(f"{address}: pcode must be a list")
    result: list[dict[str, Any]] = []
    opcodes: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("opcode"), str):
            raise ValueError(f"{address}: malformed pcode operation")
        opcode = row["opcode"].upper()
        opcodes.add(opcode)
        result.append(row)
    return result, opcodes


def _barrier(instruction: dict[str, Any], opcodes: set[str]) -> str | None:
    hits = sorted(opcodes & _BARRIER_PCODE)
    if hits:
        return "pcode-barrier:" + ",".join(hits)
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    if mnemonic.startswith("J") or mnemonic in {"RET", "RETF", "IRET", "LOOP", "LOOPE", "LOOPNE"}:
        return "control-flow-barrier:" + mnemonic
    return None


def _instruction_operands(instruction: dict[str, Any]) -> tuple[str, list[str], list[dict[str, Any]], set[str]]:
    address = instruction.get("address")
    mnemonic = instruction.get("mnemonic")
    operands = instruction.get("operands")
    if not isinstance(address, str):
        raise ValueError("instruction address missing")
    if not isinstance(mnemonic, str) or not mnemonic:
        raise ValueError(f"{address}: mnemonic missing")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{address}: operands must be strings")
    pcode, opcodes = _pcode(instruction)
    return mnemonic.upper(), operands, pcode, opcodes


def _looks_like_unknown_write(mnemonic: str, operands: list[str], register: str) -> bool:
    if mnemonic in _READ_ONLY_FIRST:
        return False
    parsed = [_parse_register(value) for value in operands]
    if mnemonic == "XCHG":
        return register in parsed[:2]
    return bool(parsed and parsed[0] == register)


def _source_node_id(function: str, source: dict[str, Any]) -> str | None:
    kind = source.get("kind")
    if kind == "function-entry-register":
        register = source.get("register")
        if isinstance(register, str):
            return f"entry:{function}:{register.upper()}"
        return None
    if kind in {"register-relative-load", "register-relative-address"}:
        instruction = source.get("instruction")
        base = source.get("base_register")
        displacement = source.get("displacement")
        if isinstance(instruction, str) and isinstance(base, str) and isinstance(displacement, int):
            return f"memory-source:{function}:{instruction}:{base.upper()}:{displacement}"
    return None


def _trace_register(
    instructions: list[dict[str, Any]],
    before_index: int,
    register: str,
    *,
    depth: int = 0,
    visited: set[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    if depth > MAX_COPY_HOPS:
        return {"evidence_state": "ambiguous", "status": "copy-hop-limit", "source": None, "chain": []}
    visited = set() if visited is None else set(visited)
    key = (before_index, register)
    if key in visited:
        return {"evidence_state": "ambiguous", "status": "copy-cycle", "source": None, "chain": []}
    visited.add(key)

    for index in range(before_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = _instruction_operands(instruction)
        address = instruction["address"]
        barrier = _barrier(instruction, opcodes)
        if barrier is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "barrier-before-definition",
                "source": None,
                "chain": [],
                "barrier": {"instruction": address, "reason": barrier, "instruction_text": instruction.get("text")},
            }

        destination = _parse_register(operands[0]) if operands else None
        if destination != register:
            if _looks_like_unknown_write(mnemonic, operands, register):
                return {
                    "evidence_state": "ambiguous",
                    "status": "unknown-register-clobber",
                    "source": None,
                    "chain": [],
                    "clobber": {"instruction": address, "mnemonic": mnemonic, "instruction_text": instruction.get("text")},
                }
            continue

        if mnemonic not in _SUPPORTED_DEFINERS:
            return {
                "evidence_state": "ambiguous",
                "status": "unsupported-register-definition",
                "source": None,
                "chain": [],
                "clobber": {"instruction": address, "mnemonic": mnemonic, "instruction_text": instruction.get("text")},
            }
        if len(operands) < 2:
            return {"evidence_state": "ambiguous", "status": "definition-missing-source", "source": None, "chain": []}

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
                index,
                source_register,
                depth=depth + 1,
                visited=visited,
            )
            return {
                "evidence_state": upstream["evidence_state"],
                "status": "register-copy-chain",
                "source": upstream.get("source"),
                "chain": [step] + list(upstream.get("chain") or []),
                "upstream_status": upstream.get("status"),
                "upstream_barrier": upstream.get("barrier"),
                "upstream_clobber": upstream.get("clobber"),
            }

        memory = _parse_memory_operand(source_operand)
        if memory is not None:
            base, displacement = memory
            if mnemonic == "MOV":
                if "LOAD" not in opcodes:
                    return {"evidence_state": "ambiguous", "status": "memory-source-without-load", "source": None, "chain": [step]}
                kind = "register-relative-load"
            else:
                if "LOAD" in opcodes:
                    return {"evidence_state": "ambiguous", "status": "lea-with-load-pcode", "source": None, "chain": [step]}
                kind = "register-relative-address"
            return {
                "evidence_state": "verified",
                "status": "syntactic-source-resolved",
                "source": {
                    "kind": kind,
                    "instruction": address,
                    "base_register": base,
                    "displacement": displacement,
                    "object_identity_proven": False,
                },
                "chain": [step],
            }

        if mnemonic == "MOV" and _IMMEDIATE.fullmatch(source_operand):
            return {
                "evidence_state": "ambiguous",
                "status": "immediate-source",
                "source": {"kind": "immediate", "value": source_operand},
                "chain": [step],
            }
        return {
            "evidence_state": "ambiguous",
            "status": "unsupported-definition-source",
            "source": {"kind": "unknown", "operand": source_operand},
            "chain": [step],
        }

    return {
        "evidence_state": "verified",
        "status": "function-entry-register",
        "source": {"kind": "function-entry-register", "register": register, "object_identity_proven": False},
        "chain": [],
    }


def _load_instruction_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows = list(_read_jsonl(path))
    if not rows:
        raise ValueError(f"{path}: empty instruction export")
    if {row.get("format") for row in rows} != {INSTRUCTION_FORMAT}:
        raise ValueError(f"{path}: expected only {INSTRUCTION_FORMAT}")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("address"), str):
            raise ValueError(f"{path}: function metadata missing")
        address = _normalize_address(function["address"])
        if address in result:
            raise ValueError(f"{path}: duplicate function {address}")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{address}: instructions missing")
        result[address] = row
    return result


def _lifecycle_index(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = report.get("targets")
    if not isinstance(rows, list):
        raise ValueError("class lifecycle evidence: targets must be a list")
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("class lifecycle evidence: invalid target row")
        own = row.get("own_vtable")
        if own is None:
            continue
        address = _normalize_address(own)
        result.setdefault(address, []).append(row)
    return result


def _function_role(class_row: dict[str, Any], function: str) -> dict[str, Any]:
    initializer = _function_address(class_row.get("initializer_candidate"))
    if initializer == function and class_row.get("initializer_writes_own_vtable") is True:
        return {"role": "initializer-candidate", "evidence_state": "verified", "constructor_semantics_proven": False}
    teardown_matches = []
    for row in class_row.get("teardown_transition_candidates") or []:
        if isinstance(row, dict) and _function_address(row.get("function")) == function:
            teardown_matches.append(row)
    if teardown_matches:
        return {
            "role": "teardown-transition-candidate",
            "evidence_state": "ambiguous",
            "destructor_semantics_proven": False,
            "candidate_count": len(teardown_matches),
        }
    writers = {
        value for value in (_function_address(item) for item in class_row.get("own_vtable_writer_functions") or [])
        if value is not None
    }
    if function in writers:
        return {"role": "own-vtable-writer", "evidence_state": "verified", "lifecycle_semantics_proven": False}
    return {"role": "unclassified-vtable-store-function", "evidence_state": "unknown", "lifecycle_semantics_proven": False}


def _next_lifecycle_targets(class_row: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    initializer = _function_address(class_row.get("initializer_candidate"))
    if initializer:
        result.add(initializer)
    for item in class_row.get("initializer_callers") or []:
        if isinstance(item, dict):
            address = _function_address(item.get("function"))
            if address:
                result.add(address)
    for item in class_row.get("teardown_transition_candidates") or []:
        if isinstance(item, dict):
            address = _function_address(item.get("function"))
            if address:
                result.add(address)
    return result


def build_vehicle_lifecycle_pointer_join(
    pointer_closure_path: Path,
    vtable_audit_path: Path,
    lifecycle_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    pointer = _load_json(pointer_closure_path, POINTER_FORMAT)
    vtable = _load_json(vtable_audit_path, VTABLE_AUDIT_FORMAT)
    lifecycle = _load_json(lifecycle_path, LIFECYCLE_FORMAT)
    instruction_rows = _load_instruction_rows(instruction_export_path)

    nodes = pointer.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("pointer closure: nodes must be a list")
    closure_nodes: dict[str, dict[str, Any]] = {}
    for row in nodes:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("pointer closure: invalid node")
        node_id = row["id"]
        if node_id in closure_nodes:
            raise ValueError(f"pointer closure: duplicate node {node_id}")
        closure_nodes[node_id] = row

    class_by_vtable = _lifecycle_index(lifecycle)
    stores = vtable.get("store_candidates")
    if not isinstance(stores, list):
        raise ValueError("vtable audit: store_candidates must be a list")

    candidates: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    next_targets: dict[str, set[str]] = {}

    for store in stores:
        if not isinstance(store, dict):
            raise ValueError("vtable audit: invalid store candidate")
        function_raw = store.get("function")
        instruction_address = store.get("instruction")
        if not isinstance(function_raw, str) or not isinstance(instruction_address, str):
            raise ValueError("vtable audit: store function/instruction missing")
        function = _normalize_address(function_raw)
        instruction_address = _normalize_address(instruction_address)
        refs = store.get("matching_vtable_references")
        memories = store.get("simple_memory_operands")
        if not isinstance(refs, list) or not isinstance(memories, list):
            raise ValueError(f"{function}@{instruction_address}: malformed vtable store")

        instruction_row = instruction_rows.get(function)
        if instruction_row is None:
            raise ValueError(f"instruction export missing vtable-store function {function}")
        instructions = instruction_row["instructions"]
        index_by_address = {
            _normalize_address(item.get("address")): index
            for index, item in enumerate(instructions)
            if isinstance(item, dict) and isinstance(item.get("address"), str)
        }
        store_index = index_by_address.get(instruction_address)
        if store_index is None:
            raise ValueError(f"instruction export missing store {function}@{instruction_address}")
        raw_store = instructions[store_index]
        _, raw_operands, _, raw_opcodes = _instruction_operands(raw_store)
        if "STORE" not in raw_opcodes:
            raise ValueError(f"{function}@{instruction_address}: raw instruction no longer has STORE p-code")
        raw_refs = {
            _normalize_address(ref.get("to"))
            for ref in raw_store.get("references") or []
            if isinstance(ref, dict) and ref.get("to") is not None
        }

        normalized_refs: list[str] = []
        for ref in refs:
            if not isinstance(ref, dict) or ref.get("to") is None:
                raise ValueError(f"{function}@{instruction_address}: invalid vtable reference")
            address = _normalize_address(ref["to"])
            if address not in raw_refs:
                raise ValueError(f"{function}@{instruction_address}: audit/raw reference drift for {address}")
            normalized_refs.append(address)

        for vtable_address in sorted(set(normalized_refs)):
            classes = class_by_vtable.get(vtable_address, [])
            class_state = "verified" if len(classes) == 1 else ("ambiguous" if len(classes) > 1 else "unknown")
            if len(classes) != 1:
                blockers.append(
                    {
                        "id": "lifecycle-class-vtable-match-not-unique" if classes else "vtable-absent-from-lifecycle-evidence",
                        "function": function,
                        "instruction": instruction_address,
                        "vtable": vtable_address,
                        "class_candidate_count": len(classes),
                        "evidence_state": class_state,
                    }
                )

            for memory in memories:
                if not isinstance(memory, dict):
                    raise ValueError(f"{function}@{instruction_address}: invalid memory operand")
                operand = memory.get("operand")
                base = memory.get("base_register")
                displacement = memory.get("displacement")
                if not isinstance(operand, str) or not isinstance(base, str) or not isinstance(displacement, int):
                    raise ValueError(f"{function}@{instruction_address}: incomplete memory operand")
                if operand not in raw_operands:
                    raise ValueError(f"{function}@{instruction_address}: audit/raw operand drift for {operand}")
                base = base.upper()
                trace = _trace_register(instructions, store_index, base)
                source = trace.get("source")
                source_node = _source_node_id(function, source) if isinstance(source, dict) else None
                closure_match = source_node in closure_nodes if source_node else False
                trace_state = _state(trace.get("evidence_state", "unknown"), "vtable-store pointer trace")
                pointer_join_state = trace_state if closure_match else ("ambiguous" if trace_state == "ambiguous" else "unknown")

                class_rows = classes if classes else [None]
                for class_row in class_rows:
                    role = _function_role(class_row, function) if isinstance(class_row, dict) else {
                        "role": "no-class-lifecycle-match", "evidence_state": "unknown", "lifecycle_semantics_proven": False
                    }
                    overall = _weakest(class_state, pointer_join_state)
                    row = {
                        "function": function,
                        "instruction": instruction_address,
                        "vtable": vtable_address,
                        "class_name": class_row.get("class_name") if isinstance(class_row, dict) else None,
                        "descriptor": class_row.get("descriptor") if isinstance(class_row, dict) else None,
                        "class_lifecycle_complete": class_row.get("complete") if isinstance(class_row, dict) else None,
                        "class_vtable_match_state": class_state,
                        "lifecycle_role": role,
                        "memory_operand": {
                            "operand": operand,
                            "base_register": base,
                            "displacement": displacement,
                            "displacement_hex": memory.get("displacement_hex"),
                        },
                        "store_base_origin_trace": trace,
                        "pointer_closure_node": source_node,
                        "pointer_closure_node_present": closure_match,
                        "pointer_value_join_state": pointer_join_state,
                        "join_evidence_state": overall,
                        "verified_static_value_source_join": overall == "verified",
                        "vtable_written_at_zero_displacement": displacement == 0,
                        "vptr_field_proven": False,
                        "constructor_semantics_proven": False,
                        "destructor_semantics_proven": False,
                        "whole_lifetime_class_identity_proven": False,
                        "owner_identity_proven": False,
                    }
                    candidates.append(row)
                    if overall != "verified":
                        blockers.append(
                            {
                                "id": "vtable-store-not-joined-to-pointer-closure",
                                "function": function,
                                "instruction": instruction_address,
                                "vtable": vtable_address,
                                "class_name": row["class_name"],
                                "trace_status": trace.get("status"),
                                "source_node": source_node,
                                "evidence_state": pointer_join_state,
                            }
                        )
                    if isinstance(class_row, dict):
                        for address in _next_lifecycle_targets(class_row):
                            if address == function:
                                continue
                            next_targets.setdefault(address, set()).add(
                                f"lifecycle neighbor of exact vtable {vtable_address} ({class_row.get('class_name')})"
                            )

    candidates.sort(key=lambda row: (row["function"], row["instruction"], row["vtable"], str(row.get("class_name"))))
    verified = [row for row in candidates if row["verified_static_value_source_join"]]
    next_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(next_targets.items())
    ]
    return {
        "format": FORMAT,
        "pointer_closure": str(pointer_closure_path),
        "vtable_instruction_audit": str(vtable_audit_path),
        "class_lifecycle_source_evidence": str(lifecycle_path),
        "instruction_export": str(instruction_export_path),
        "candidate_count": len(candidates),
        "verified_static_value_source_join_count": len(verified),
        "candidates": candidates,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_instruction_export_targets": next_rows,
        "next_instruction_export_addresses": [row["address"] for row in next_rows],
        "scope": {
            "exact_raw_store_pcode_crosschecked": True,
            "exact_raw_vtable_reference_crosschecked": True,
            "exact_memory_operand_crosschecked": True,
            "linear_mov_lea_origin_trace_only": True,
            "calls_and_branches_are_trace_barriers": True,
            "pointer_join_requires_existing_closure_node": True,
            "unique_lifecycle_vtable_match_is_whole_object_class_proof": False,
            "same_static_value_source_is_runtime_object_identity_proof": False,
            "zero_displacement_store_is_vptr_proof": False,
            "initializer_candidate_is_constructor_proof": False,
            "teardown_transition_candidate_is_destructor_proof": False,
            "whole_lifetime_class_identity_proven": False,
            "owner_identity_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pointer_closure", type=Path)
    parser.add_argument("vtable_instruction_audit", type=Path)
    parser.add_argument("class_lifecycle_source_evidence", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--require-verified-join", action="store_true")
    args = parser.parse_args()

    report = build_vehicle_lifecycle_pointer_join(
        args.pointer_closure,
        args.vtable_instruction_audit,
        args.class_lifecycle_source_evidence,
        args.instruction_export,
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
    print(f"candidates: {report['candidate_count']}")
    print(f"verified static value-source joins: {report['verified_static_value_source_join_count']}")
    print(f"blockers: {report['blocker_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.require_verified_join and not report["verified_static_value_source_join_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
