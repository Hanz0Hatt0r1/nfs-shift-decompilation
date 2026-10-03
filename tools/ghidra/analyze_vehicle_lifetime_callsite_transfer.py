#!/usr/bin/env python3
"""Audit exact create/delete callsite value transfer for vehicle lifetime candidates.

The input lifetime frontier narrows the class to a finite factory/initializer and
deleting-wrapper/teardown set.  Source-backed create/delete evidence supplies the
exact structural relationships.  This analyzer then requires the corresponding
machine CALL instructions, flow targets and structured p-code from a targeted
SHIFT.GhidraFunctionInstructions/2 export.

The result is deliberately ABI-level.  It may prove a register value path across
one local call sequence, but it does not promote allocator, constructor,
destructor, release, ownership, or same-runtime-object semantics.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.VehicleLifetimeCallsiteTransfer/1"
FRONTIER_FORMAT = "SHIFT.VehicleLifetimePairFrontier/1"
CREATE_FORMAT = "SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1"
DELETE_FORMAT = "SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

STATE_STRENGTH = {"unknown": 0, "ambiguous": 1, "inferred": 2, "verified": 3, "proven": 4}
STATES = set(STATE_STRENGTH)
_GPR = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
_ALIAS_TO_GPR = {
    "AL": "EAX", "AH": "EAX", "AX": "EAX", "EAX": "EAX",
    "BL": "EBX", "BH": "EBX", "BX": "EBX", "EBX": "EBX",
    "CL": "ECX", "CH": "ECX", "CX": "ECX", "ECX": "ECX",
    "DL": "EDX", "DH": "EDX", "DX": "EDX", "EDX": "EDX",
    "SI": "ESI", "ESI": "ESI", "DI": "EDI", "EDI": "EDI",
    "BP": "EBP", "EBP": "EBP", "SP": "ESP", "ESP": "ESP",
}
_REGISTER = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_BARRIER_PCODE = {"CALLIND", "BRANCH", "CBRANCH", "BRANCHIND", "RETURN"}
_NO_WRITE = {
    "NOP", "CMP", "TEST", "BT", "PUSH", "PREFETCH", "PREFETCHNTA",
    "PREFETCHT0", "PREFETCHT1", "PREFETCHT2", "CLD", "STD", "CLC", "STC", "CMC",
}
_EXPLICIT_DEST = {
    "MOV", "LEA", "MOVZX", "MOVSX", "ADD", "ADC", "SUB", "SBB", "AND", "OR",
    "XOR", "INC", "DEC", "NEG", "NOT", "SHL", "SAL", "SHR", "SAR", "ROL",
    "ROR", "RCL", "RCR", "BSWAP", "POP",
}


def _load(path: Path, expected: str) -> dict[str, Any]:
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
    checked = [_state(value, "state merge") for value in values]
    return min(checked, key=lambda value: STATE_STRENGTH[value]) if checked else "unknown"


def _normalize_address(value: Any) -> str:
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        token = value.strip()
        if token.upper().startswith("FUN_"):
            number = int(token[4:], 16)
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
        if token.upper().startswith("FUN_") or token.lower().startswith("0x"):
            return _normalize_address(token)
    except ValueError:
        return None
    return None


def _canonical_register(value: str) -> str | None:
    token = value.strip().upper()
    if not _REGISTER.fullmatch(token):
        return None
    return _ALIAS_TO_GPR.get(token)


def _full_register(value: str) -> str | None:
    token = value.strip().upper()
    return token if token in _GPR else None


def _load_instructions(path: Path) -> dict[str, dict[str, Any]]:
    rows = list(_read_jsonl(path))
    if not rows:
        raise ValueError(f"{path}: empty instruction export")
    formats = {row.get("format") for row in rows}
    if formats != {INSTRUCTION_FORMAT}:
        raise ValueError(f"{path}: expected only {INSTRUCTION_FORMAT}; found {sorted(map(str, formats))}")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        instructions = row.get("instructions")
        if not isinstance(function, dict) or not isinstance(function.get("address"), str):
            raise ValueError(f"{path}: function metadata missing")
        address = _normalize_address(function["address"])
        if address in result:
            raise ValueError(f"{path}: duplicate function row {address}")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{address}: instructions missing")
        result[address] = row
    return result


def _parts(instruction: dict[str, Any], function: str) -> tuple[str, list[str], list[dict[str, str]], set[str]]:
    address = instruction.get("address")
    mnemonic = instruction.get("mnemonic")
    operands = instruction.get("operands")
    pcode = instruction.get("pcode")
    if not isinstance(address, str) or not isinstance(mnemonic, str) or not mnemonic:
        raise ValueError(f"{function}: malformed instruction metadata")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{address}: operands must be strings")
    if not isinstance(pcode, list):
        raise ValueError(f"{address}: pcode must be a list")
    normalized: list[dict[str, str]] = []
    for op in pcode:
        if not isinstance(op, dict) or not isinstance(op.get("opcode"), str) or not isinstance(op.get("text"), str):
            raise ValueError(f"{address}: malformed pcode operation")
        normalized.append({"opcode": op["opcode"].upper(), "text": op["text"]})
    return mnemonic.upper(), operands, normalized, {op["opcode"] for op in normalized}


def _direct_call_indices(row: dict[str, Any], target: str) -> list[int]:
    function = _normalize_address(row["function"]["address"])
    result: list[int] = []
    for index, instruction in enumerate(row["instructions"]):
        if not isinstance(instruction, dict):
            raise ValueError(f"{function}: invalid instruction row")
        _, _, _, opcodes = _parts(instruction, function)
        flows = instruction.get("flows")
        if not isinstance(flows, list):
            raise ValueError(f"{instruction.get('address')}: flows must be a list")
        normalized_flows = {
            _normalize_address(value)
            for value in flows
            if isinstance(value, str)
        }
        if target in normalized_flows and "CALL" in opcodes:
            result.append(index)
    return result


def _implicit_clobber(mnemonic: str, operands: list[str], register: str) -> str | None:
    m = mnemonic.upper()
    if m in {"PUSH", "PUSHF", "PUSHFD", "PUSHA", "PUSHAD", "POP", "POPF", "POPFD", "POPA", "POPAD"} and register == "ESP":
        return "implicit-ESP-stack-update"
    if m in {"ENTER", "LEAVE"} and register in {"ESP", "EBP"}:
        return "implicit-frame-register-update"
    if m.startswith("MOVS") or m.startswith("CMPS"):
        if register in {"ESI", "EDI"}:
            return "implicit-string-index-update"
    if m.startswith("LODS") and register in {"ESI", "EAX"}:
        return "implicit-LODS-register-update"
    if (m.startswith("STOS") or m.startswith("SCAS")) and register == "EDI":
        return "implicit-destination-index-update"
    if m in {"MUL", "DIV", "IDIV"} and register in {"EAX", "EDX"}:
        return "implicit-EAX-EDX-result"
    if m == "IMUL" and len(operands) == 1 and register in {"EAX", "EDX"}:
        return "implicit-EAX-EDX-result"
    if m in {"CWD", "CDQ"} and register == "EDX":
        return "implicit-EDX-result"
    if m in {"CBW", "CWDE"} and register == "EAX":
        return "implicit-EAX-result"
    if m == "CPUID" and register in {"EAX", "EBX", "ECX", "EDX"}:
        return "implicit-CPUID-result"
    if m in {"RDTSC", "RDTSCP"} and register in {"EAX", "EDX", "ECX"}:
        return "implicit-timestamp-result"
    if m.startswith("LOOP") and register == "ECX":
        return "implicit-loop-counter-update"
    if m in {"XCHG", "XADD"}:
        if any(_canonical_register(value) == register for value in operands[:2]):
            return "multi-destination-register-write"
    return None


def _control_barrier(mnemonic: str, opcodes: set[str]) -> str | None:
    hits = sorted(opcodes & _BARRIER_PCODE)
    if hits:
        return "pcode-barrier:" + ",".join(hits)
    if mnemonic.startswith("J") or mnemonic in {"RET", "RETF", "IRET", "LOOP", "LOOPE", "LOOPNE"}:
        return "control-flow-barrier:" + mnemonic
    return None


def _trace_register_to_entry(
    row: dict[str, Any],
    before_index: int,
    register: str,
    *,
    depth: int = 0,
    visited: set[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    if depth > 8:
        return {"evidence_state": "ambiguous", "status": "copy-hop-limit", "source": None, "chain": []}
    visited = set() if visited is None else set(visited)
    key = (before_index, register)
    if key in visited:
        return {"evidence_state": "ambiguous", "status": "copy-cycle", "source": None, "chain": []}
    visited.add(key)
    instructions = row["instructions"]
    function = _normalize_address(row["function"]["address"])

    for index in range(before_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = _parts(instruction, function)
        address = instruction["address"]
        barrier = _control_barrier(mnemonic, opcodes)
        if barrier is not None or "CALL" in opcodes:
            reason = barrier or "pcode-barrier:CALL"
            return {
                "evidence_state": "ambiguous",
                "status": "barrier-before-entry",
                "source": None,
                "chain": [],
                "barrier": {"instruction": address, "reason": reason, "instruction_text": instruction.get("text")},
            }
        implicit = _implicit_clobber(mnemonic, operands, register)
        if implicit is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "implicit-register-clobber",
                "source": None,
                "chain": [],
                "clobber": {"instruction": address, "reason": implicit, "instruction_text": instruction.get("text")},
            }
        destination = _canonical_register(operands[0]) if operands else None
        if destination != register:
            continue
        if mnemonic in _NO_WRITE:
            continue
        if _full_register(operands[0]) != register:
            return {
                "evidence_state": "ambiguous",
                "status": "partial-register-write",
                "source": None,
                "chain": [],
                "clobber": {"instruction": address, "instruction_text": instruction.get("text")},
            }
        if mnemonic != "MOV" or len(operands) < 2:
            return {
                "evidence_state": "ambiguous",
                "status": "unsupported-register-definition",
                "source": None,
                "chain": [],
                "clobber": {"instruction": address, "mnemonic": mnemonic, "instruction_text": instruction.get("text")},
            }
        source_register = _full_register(operands[1])
        step = {
            "instruction": address,
            "instruction_text": instruction.get("text"),
            "destination_register": register,
            "source_operand": operands[1],
            "pcode": pcode,
        }
        if source_register is None:
            return {
                "evidence_state": "unknown",
                "status": "non-register-source-before-entry",
                "source": {"kind": "non-register", "operand": operands[1]},
                "chain": [step],
            }
        upstream = _trace_register_to_entry(
            row, index, source_register, depth=depth + 1, visited=visited
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

    return {
        "evidence_state": "verified",
        "status": "function-entry-register",
        "source": {"kind": "function-entry-register", "register": register},
        "chain": [],
    }


def _trace_initializer_receiver_to_helper_return(
    row: dict[str, Any],
    initializer_index: int,
    helper_index: int,
) -> dict[str, Any]:
    instructions = row["instructions"]
    function = _normalize_address(row["function"]["address"])
    tracked = "ECX"
    chain: list[dict[str, Any]] = []
    visited_registers: set[str] = set()

    for index in range(initializer_index - 1, helper_index - 1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = _parts(instruction, function)
        address = instruction["address"]
        if index == helper_index:
            if "CALL" not in opcodes:
                raise ValueError(f"{function}: helper index {address} lost CALL p-code")
            if tracked == "EAX":
                return {
                    "evidence_state": "verified",
                    "status": "initializer-receiver-reaches-helper-return-register",
                    "receiver_register": "ECX",
                    "helper_return_register": "EAX",
                    "chain": chain,
                    "terminal_call_instruction": address,
                    "return_register_semantics_state": "inferred",
                    "note": "machine register continuity is verified; interpreting EAX as the helper return value uses the recovered source return assignment plus x86 ABI convention",
                }
            return {
                "evidence_state": "unknown",
                "status": "helper-call-reached-with-different-register",
                "receiver_register": "ECX",
                "terminal_register": tracked,
                "chain": chain,
            }

        barrier = _control_barrier(mnemonic, opcodes)
        if barrier is not None or "CALL" in opcodes:
            return {
                "evidence_state": "ambiguous",
                "status": "barrier-between-helper-and-initializer",
                "receiver_register": "ECX",
                "tracked_register": tracked,
                "chain": chain,
                "barrier": {"instruction": address, "reason": barrier or "pcode-barrier:CALL", "instruction_text": instruction.get("text")},
            }
        implicit = _implicit_clobber(mnemonic, operands, tracked)
        if implicit is not None:
            return {
                "evidence_state": "ambiguous",
                "status": "tracked-register-clobbered",
                "receiver_register": "ECX",
                "tracked_register": tracked,
                "chain": chain,
                "clobber": {"instruction": address, "reason": implicit, "instruction_text": instruction.get("text")},
            }
        destination = _canonical_register(operands[0]) if operands else None
        if destination != tracked:
            continue
        if mnemonic in _NO_WRITE:
            continue
        if _full_register(operands[0]) != tracked:
            return {
                "evidence_state": "ambiguous",
                "status": "partial-register-write",
                "receiver_register": "ECX",
                "tracked_register": tracked,
                "chain": chain,
                "clobber": {"instruction": address, "instruction_text": instruction.get("text")},
            }
        if mnemonic != "MOV" or len(operands) < 2:
            return {
                "evidence_state": "ambiguous",
                "status": "unsupported-register-definition",
                "receiver_register": "ECX",
                "tracked_register": tracked,
                "chain": chain,
                "clobber": {"instruction": address, "mnemonic": mnemonic, "instruction_text": instruction.get("text")},
            }
        source_register = _full_register(operands[1])
        chain.append(
            {
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "destination_register": tracked,
                "source_operand": operands[1],
                "pcode": pcode,
            }
        )
        if source_register is None:
            return {
                "evidence_state": "unknown",
                "status": "receiver-loaded-from-non-register-source",
                "receiver_register": "ECX",
                "tracked_register": tracked,
                "chain": chain,
                "source": {"kind": "non-register", "operand": operands[1]},
            }
        if source_register in visited_registers:
            return {
                "evidence_state": "ambiguous",
                "status": "register-copy-cycle",
                "receiver_register": "ECX",
                "tracked_register": source_register,
                "chain": chain,
            }
        visited_registers.add(source_register)
        tracked = source_register

    return {
        "evidence_state": "unknown",
        "status": "helper-call-not-reached-by-receiver-trace",
        "receiver_register": "ECX",
        "tracked_register": tracked,
        "chain": chain,
    }


def _frontier_rows(frontier: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    rows = frontier.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("lifetime frontier: candidates must be a list")
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("descriptor"), int):
            raise ValueError("lifetime frontier: invalid descriptor row")
        result[row["descriptor"]].append(row)
    return result


def _address_set(values: Any, label: str) -> set[str]:
    if not isinstance(values, list):
        raise ValueError(f"{label}: expected list")
    result: set[str] = set()
    for value in values:
        address = _function_address(value)
        if address is None:
            raise ValueError(f"{label}: invalid address {value!r}")
        result.add(address)
    return result


def analyze_vehicle_lifetime_callsite_transfer(
    lifetime_frontier_path: Path,
    create_wrapper_path: Path,
    deleting_wrapper_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    frontier = _load(lifetime_frontier_path, FRONTIER_FORMAT)
    create = _load(create_wrapper_path, CREATE_FORMAT)
    delete = _load(deleting_wrapper_path, DELETE_FORMAT)
    instructions = _load_instructions(instruction_export_path)
    frontier_by_descriptor = _frontier_rows(frontier)

    create_rows: list[dict[str, Any]] = []
    delete_rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    next_targets: dict[str, set[str]] = defaultdict(set)

    for source_row in create.get("links") or []:
        if not isinstance(source_row, dict) or source_row.get("create_wrapper_shape") is not True:
            continue
        descriptor = source_row.get("descriptor")
        if not isinstance(descriptor, int):
            continue
        factory = _function_address(source_row.get("factory_function"))
        initializer = _function_address(source_row.get("initializer_candidate"))
        helper = _function_address(source_row.get("immediate_preinitializer_helper"))
        if None in {factory, initializer, helper}:
            continue
        matches = [
            row for row in frontier_by_descriptor.get(descriptor, [])
            if factory in _address_set(row.get("factory_functions"), "factory_functions")
            and initializer in _address_set(row.get("initializer_candidates"), "initializer_candidates")
        ]
        if len(matches) != 1:
            blockers.append({
                "id": "create-frontier-match-not-unique",
                "descriptor": descriptor,
                "factory": factory,
                "initializer": initializer,
                "match_count": len(matches),
                "evidence_state": "ambiguous" if matches else "unknown",
            })
            continue
        frontier_row = matches[0]
        frontier_state = _state(frontier_row.get("frontier_evidence_state", "unknown"), "lifetime frontier")
        source_state = "verified" if (
            source_row.get("ghidra_factory_to_initializer") is True
            and source_row.get("ghidra_factory_to_helper") is True
            and source_row.get("helper_result_flows_to_initializer") is True
        ) else "inferred"

        if factory not in instructions or initializer not in instructions:
            raise ValueError(f"instruction export missing create target(s) for descriptor {descriptor}: {factory}, {initializer}")
        factory_row = instructions[factory]
        helper_calls = _direct_call_indices(factory_row, helper)
        initializer_calls = _direct_call_indices(factory_row, initializer)
        if len(helper_calls) != 1 or len(initializer_calls) != 1:
            machine_state = "ambiguous"
            trace = {
                "evidence_state": "ambiguous",
                "status": "create-callsite-not-unique",
                "helper_call_count": len(helper_calls),
                "initializer_call_count": len(initializer_calls),
            }
        else:
            helper_index, initializer_index = helper_calls[0], initializer_calls[0]
            if helper_index >= initializer_index:
                machine_state = "ambiguous"
                trace = {
                    "evidence_state": "ambiguous",
                    "status": "helper-not-before-initializer-in-machine-order",
                    "helper_call": factory_row["instructions"][helper_index]["address"],
                    "initializer_call": factory_row["instructions"][initializer_index]["address"],
                }
            else:
                initializer_cc = instructions[initializer]["function"].get("calling_convention")
                if initializer_cc != "__thiscall":
                    machine_state = "unknown"
                    trace = {
                        "evidence_state": "unknown",
                        "status": "initializer-receiver-register-not-statically-fixed",
                        "calling_convention": initializer_cc,
                    }
                else:
                    trace = _trace_initializer_receiver_to_helper_return(
                        factory_row, initializer_index, helper_index
                    )
                    machine_state = _state(trace.get("evidence_state", "unknown"), "create machine trace")

        transfer_state = _weakest(frontier_state, source_state, machine_state, "inferred")
        create_rows.append({
            "descriptor": descriptor,
            "class_name": frontier_row.get("lifetime_pair_class_name"),
            "factory_function": factory,
            "preinitializer_helper": helper,
            "initializer_candidate": initializer,
            "vehicle_lifetime_frontier_state": frontier_state,
            "source_create_wrapper_state": source_state,
            "machine_receiver_value_path_state": machine_state,
            "machine_receiver_value_path": trace,
            "create_value_transfer_state": transfer_state,
            "verified_machine_register_path": machine_state == "verified",
            "helper_return_value_semantics_state": "inferred" if machine_state == "verified" else "unknown",
            "allocation_semantics_proven": False,
            "constructor_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
        })
        next_targets[helper].add(f"create-side helper for descriptor {descriptor}; inspect return/value semantics")

    wrappers = delete.get("wrappers")
    if not isinstance(wrappers, list):
        raise ValueError("deleting wrapper evidence: wrappers must be a list")
    for source_row in wrappers:
        if not isinstance(source_row, dict) or source_row.get("deleting_wrapper_shape") is not True:
            continue
        descriptor = source_row.get("descriptor")
        if not isinstance(descriptor, int):
            continue
        wrapper = _function_address(source_row.get("wrapper_function"))
        teardown = _function_address(source_row.get("teardown_transition_function"))
        release = _function_address(source_row.get("release_helper"))
        if None in {wrapper, teardown, release}:
            continue
        matches = [
            row for row in frontier_by_descriptor.get(descriptor, [])
            if wrapper in _address_set(row.get("deleting_wrapper_functions"), "deleting_wrapper_functions")
            and teardown in _address_set(row.get("teardown_transition_functions"), "teardown_transition_functions")
        ]
        if len(matches) != 1:
            blockers.append({
                "id": "delete-frontier-match-not-unique",
                "descriptor": descriptor,
                "wrapper": wrapper,
                "teardown": teardown,
                "match_count": len(matches),
                "evidence_state": "ambiguous" if matches else "unknown",
            })
            continue
        frontier_row = matches[0]
        frontier_state = _state(frontier_row.get("frontier_evidence_state", "unknown"), "lifetime frontier")
        source_state = "verified" if (
            source_row.get("ghidra_teardown_edge") is True
            and source_row.get("ghidra_release_edge") is True
            and source_row.get("teardown_before_release") is True
            and source_row.get("bit0_delete_guard") is True
        ) else "inferred"

        if wrapper not in instructions or teardown not in instructions:
            raise ValueError(f"instruction export missing delete target(s) for descriptor {descriptor}: {wrapper}, {teardown}")
        wrapper_row = instructions[wrapper]
        teardown_calls = _direct_call_indices(wrapper_row, teardown)
        release_calls = _direct_call_indices(wrapper_row, release)
        wrapper_cc = wrapper_row["function"].get("calling_convention")
        teardown_cc = instructions[teardown]["function"].get("calling_convention")
        if len(teardown_calls) != 1 or len(release_calls) != 1:
            teardown_state = "ambiguous"
            teardown_trace = {
                "evidence_state": "ambiguous",
                "status": "delete-callsite-not-unique",
                "teardown_call_count": len(teardown_calls),
                "release_call_count": len(release_calls),
            }
            order_state = "ambiguous"
        else:
            teardown_index, release_index = teardown_calls[0], release_calls[0]
            order_state = "verified" if teardown_index < release_index else "ambiguous"
            if wrapper_cc == "__thiscall" and teardown_cc == "__thiscall":
                teardown_trace = _trace_register_to_entry(wrapper_row, teardown_index, "ECX")
                terminal = teardown_trace.get("source") if isinstance(teardown_trace, dict) else None
                if (
                    teardown_trace.get("evidence_state") == "verified"
                    and isinstance(terminal, dict)
                    and terminal.get("kind") == "function-entry-register"
                    and terminal.get("register") == "ECX"
                ):
                    teardown_state = "verified"
                else:
                    teardown_state = _state(teardown_trace.get("evidence_state", "unknown"), "teardown trace")
            else:
                teardown_state = "unknown"
                teardown_trace = {
                    "evidence_state": "unknown",
                    "status": "wrapper-or-teardown-not-thiscall",
                    "wrapper_calling_convention": wrapper_cc,
                    "teardown_calling_convention": teardown_cc,
                }

        transfer_state = _weakest(frontier_state, source_state, teardown_state, order_state, "inferred")
        delete_rows.append({
            "descriptor": descriptor,
            "class_name": frontier_row.get("lifetime_pair_class_name"),
            "deleting_wrapper_function": wrapper,
            "teardown_transition_function": teardown,
            "release_helper": release,
            "vehicle_lifetime_frontier_state": frontier_state,
            "source_deleting_wrapper_state": source_state,
            "teardown_call_order_state": order_state,
            "machine_wrapper_entry_to_teardown_receiver_state": teardown_state,
            "machine_wrapper_entry_to_teardown_receiver": teardown_trace,
            "teardown_value_transfer_state": transfer_state,
            "release_argument_value_transfer_state": "unknown",
            "release_argument_value_transfer_proven": False,
            "delete_flag_semantics_proven": False,
            "destructor_semantics_proven": False,
            "release_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
        })
        next_targets[release].add(f"delete-side release helper for descriptor {descriptor}; inspect argument/value semantics")

    create_rows.sort(key=lambda row: (row["descriptor"], row["factory_function"], row["initializer_candidate"]))
    delete_rows.sort(key=lambda row: (row["descriptor"], row["deleting_wrapper_function"], row["teardown_transition_function"]))
    target_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(next_targets.items())
    ]
    return {
        "format": FORMAT,
        "vehicle_lifetime_pair_frontier": str(lifetime_frontier_path),
        "create_wrapper_evidence": str(create_wrapper_path),
        "deleting_wrapper_evidence": str(deleting_wrapper_path),
        "instruction_export": str(instruction_export_path),
        "create_transfer_count": len(create_rows),
        "delete_transfer_count": len(delete_rows),
        "create_transfers": create_rows,
        "delete_transfers": delete_rows,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_instruction_export_targets": target_rows,
        "next_instruction_export_addresses": [row["address"] for row in target_rows],
        "scope": {
            "exact_direct_call_flow_and_pcode_required": True,
            "create_machine_receiver_path_can_be_verified": True,
            "helper_return_value_semantics_are_abi_inferred": True,
            "wrapper_entry_to_teardown_receiver_machine_path_can_be_verified": True,
            "thiscall_ecx_role_is_semantic_object_identity_proof": False,
            "source_local_name_is_machine_register_identity_proof": False,
            "release_argument_transfer_proven": False,
            "allocator_semantics_proven": False,
            "constructor_semantics_proven": False,
            "destructor_semantics_proven": False,
            "same_runtime_object_across_lifetime_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "owner_identity_proven": False,
            "next_step": (
                "Use helper/release instruction targets plus the existing pointer closure to prove "
                "return/argument value origins before attempting whole-lifetime object identity."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicle_lifetime_pair_frontier", type=Path)
    parser.add_argument("create_wrapper_evidence", type=Path)
    parser.add_argument("deleting_wrapper_evidence", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = analyze_vehicle_lifetime_callsite_transfer(
        args.vehicle_lifetime_pair_frontier,
        args.create_wrapper_evidence,
        args.deleting_wrapper_evidence,
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
    print(f"create transfers: {report['create_transfer_count']}")
    print(f"delete transfers: {report['delete_transfer_count']}")
    print(f"blockers: {report['blocker_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
