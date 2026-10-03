#!/usr/bin/env python3
"""Prove the physical ECX receiver at FUN_00765470 -> FUN_007b2270.

The playable Linux slice already has a proven BMW chassis BODY index and a
proven global vehicle component base.  The remaining pose-selection identity
boundary is whether the BODY-array loop at 0x0076582a receives the same physical
receiver with which FUN_00765470 was entered.

This analyzer consumes exactly one SHIFT.GhidraFunctionInstructions/2 row for
FUN_00765470 and performs finite all-path register provenance.  It deliberately
proves only physical register-value continuity; it does not promote class names,
BODY ownership, rendered-frame cadence, or Phase 698 selection by itself.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import deque
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.Fun00765470BodyOwnerReceiverProvenance/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
TARGET_ADDRESS = "0x00765470"
TARGET_NAME = "FUN_00765470"
BODY_LOOP_CALL = "0x0076582a"
BODY_LOOP_TARGET = "0x007b2270"
ENTRY_RECEIVER = "ECX"

_TRACKED = ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP")
_CALLER_SAVED = ("EAX", "ECX", "EDX")
_REGISTER_RE = re.compile(r"^(EAX|EBX|ECX|EDX|ESI|EDI|EBP)$", re.IGNORECASE)
_SIMPLE_LEA_RE = re.compile(
    r"^\s*(?:dword\s+ptr\s+)?\[\s*(EAX|EBX|ECX|EDX|ESI|EDI|EBP)\s*\]\s*$",
    re.IGNORECASE,
)

State = dict[str, frozenset[str]]


def _normalize_address(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid address: {value!r}")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"invalid address: {value!r}") from exc


def _read_single_row(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    if len(rows) != 1:
        raise ValueError(f"{path}: expected one targeted function row; found {len(rows)}")
    return rows[0]


def _register(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _REGISTER_RE.fullmatch(value.strip())
    return None if match is None else match.group(1).upper()


def _atom(label: str) -> frozenset[str]:
    return frozenset((label,))


def _initial_state() -> State:
    return {register: _atom(f"entry:{register}") for register in _TRACKED}


def _unknown(register: str, address: str, reason: str) -> frozenset[str]:
    return _atom(f"unknown:{register}@{address}:{reason}")


def _source_value(operand: str, state: State, address: str) -> frozenset[str]:
    register = _register(operand)
    if register is not None:
        return state[register]
    token = operand.strip()
    if token.startswith("0x"):
        try:
            int(token, 16)
        except ValueError:
            pass
        else:
            return _atom(f"immediate:{token.lower()}")
    if re.fullmatch(r"[-+]?\d+", token):
        return _atom(f"immediate:{token}")
    if "[" in token and "]" in token:
        return _atom(f"memory:{token.lower()}")
    return _atom(f"value:{token.lower()}@{address}")


def _structured_register_outputs(instruction: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        return result
    for operation in pcode:
        if not isinstance(operation, dict):
            continue
        output = operation.get("output")
        if not isinstance(output, dict):
            continue
        text = output.get("text")
        register = _register(text)
        if output.get("register") is True and register is not None:
            result.add(register)
    return result


def _transfer(instruction: dict[str, Any], incoming: State) -> State:
    state: State = dict(incoming)
    address = _normalize_address(instruction.get("address"))
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{address}: operands must be a string list")

    handled: set[str] = set()

    if mnemonic in {"MOV", "MOVZX", "MOVSX", "MOVSXD"} and len(operands) >= 2:
        destination = _register(operands[0])
        if destination in state:
            source = _source_value(operands[1], incoming, address)
            if mnemonic == "MOV":
                state[destination] = source
            else:
                state[destination] = _atom(
                    f"derived:{mnemonic}:{destination}@{address}"
                )
            handled.add(destination)

    elif mnemonic == "LEA" and len(operands) >= 2:
        destination = _register(operands[0])
        if destination in state:
            simple = _SIMPLE_LEA_RE.fullmatch(operands[1])
            if simple is not None:
                state[destination] = incoming[simple.group(1).upper()]
            else:
                state[destination] = _atom(f"derived:LEA:{destination}@{address}")
            handled.add(destination)

    elif mnemonic == "XCHG" and len(operands) >= 2:
        left = _register(operands[0])
        right = _register(operands[1])
        if left in state and right in state:
            state[left], state[right] = incoming[right], incoming[left]
            handled.update((left, right))

    elif mnemonic == "XOR" and len(operands) >= 2:
        destination = _register(operands[0])
        source = _register(operands[1])
        if destination in state:
            if destination == source:
                state[destination] = _atom("immediate:0")
            else:
                state[destination] = _atom(f"derived:XOR:{destination}@{address}")
            handled.add(destination)

    elif mnemonic in {
        "ADD", "SUB", "ADC", "SBB", "AND", "OR", "IMUL", "SHL", "SHR", "SAR",
        "ROL", "ROR", "INC", "DEC", "NEG", "NOT",
    } and operands:
        destination = _register(operands[0])
        if destination in state:
            state[destination] = _atom(f"derived:{mnemonic}:{destination}@{address}")
            handled.add(destination)

    elif mnemonic == "POP" and operands:
        destination = _register(operands[0])
        if destination in state:
            state[destination] = _unknown(destination, address, "stack-pop")
            handled.add(destination)

    if mnemonic == "CALL":
        # IA-32 caller-saved registers are not assumed to survive a call.  This
        # is intentionally conservative even if a particular callee happens to
        # preserve them in one recovered body.
        for register in _CALLER_SAVED:
            state[register] = _unknown(register, address, "call-clobber")
            handled.add(register)

    # Structured p-code is used as a safety net: if Ghidra says an instruction
    # writes a tracked register that the audited transfer rules above did not
    # model, invalidate that register instead of silently preserving provenance.
    for register in _structured_register_outputs(instruction):
        if register in state and register not in handled:
            state[register] = _unknown(register, address, "unmodelled-pcode-write")

    return state


def _merge(existing: State | None, incoming: State) -> tuple[State, bool]:
    if existing is None:
        return dict(incoming), True
    merged: State = {}
    changed = False
    for register in _TRACKED:
        values = set(existing[register]) | set(incoming[register])
        # The lattice is deliberately finite. More than eight distinct origins
        # cannot establish exact identity and collapses to one ambiguous atom.
        if len(values) > 8:
            values = {f"ambiguous:{register}:many"}
        frozen = frozenset(values)
        merged[register] = frozen
        if frozen != existing[register]:
            changed = True
    return merged, changed


def _successors(
    instruction: dict[str, Any],
    address_set: set[str],
) -> list[str]:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    flow_type = str(instruction.get("flow_type") or "").upper()
    fallthrough_raw = instruction.get("fallthrough")
    fallthrough = None
    if isinstance(fallthrough_raw, str):
        normalized = _normalize_address(fallthrough_raw)
        if normalized in address_set:
            fallthrough = normalized
    raw_flows = instruction.get("flows")
    if not isinstance(raw_flows, list):
        raise ValueError(
            f"{_normalize_address(instruction.get('address'))}: flows must be a list"
        )
    flows = []
    for raw in raw_flows:
        if not isinstance(raw, str):
            raise ValueError("flow target must be a string")
        target = _normalize_address(raw)
        if target in address_set and target not in flows:
            flows.append(target)

    if mnemonic in {"RET", "RETF", "IRET"} or "TERMINATOR" in flow_type:
        return []
    if mnemonic == "JMP" or "UNCONDITIONAL_JUMP" in flow_type:
        return flows
    if mnemonic.startswith("J") and mnemonic != "JMP":
        result = list(flows)
        if fallthrough is not None and fallthrough not in result:
            result.append(fallthrough)
        return result
    # CALL flows point at the callee and are not intraprocedural CFG successors.
    return [] if fallthrough is None else [fallthrough]


def _call_target(instruction: dict[str, Any]) -> str | None:
    flows = instruction.get("flows")
    if isinstance(flows, list):
        normalized = []
        for value in flows:
            if isinstance(value, str):
                try:
                    normalized.append(_normalize_address(value))
                except ValueError:
                    pass
        if BODY_LOOP_TARGET in normalized:
            return BODY_LOOP_TARGET
    operands = instruction.get("operands")
    if isinstance(operands, list):
        for operand in operands:
            if not isinstance(operand, str):
                continue
            try:
                if _normalize_address(operand) == BODY_LOOP_TARGET:
                    return BODY_LOOP_TARGET
            except ValueError:
                continue
    return None


def _validate_instruction_row(row: dict[str, Any], export: Path) -> list[dict[str, Any]]:
    if row.get("format") != INSTRUCTION_FORMAT:
        raise ValueError(
            f"{export}: requires {INSTRUCTION_FORMAT}; found {row.get('format')!r}"
        )
    if row.get("found") is not True:
        raise ValueError(f"{export}: FUN_00765470 was not resolved")
    function = row.get("function")
    if not isinstance(function, dict):
        raise ValueError(f"{export}: function metadata missing")
    if _normalize_address(function.get("address")) != TARGET_ADDRESS:
        raise ValueError(f"{export}: expected {TARGET_NAME} at {TARGET_ADDRESS}")
    instructions = row.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError(f"{export}: instruction list is empty")
    if row.get("instruction_count") != len(instructions):
        raise ValueError(f"{export}: instruction_count mismatch")

    previous = -1
    seen: set[str] = set()
    for ordinal, instruction in enumerate(instructions):
        if not isinstance(instruction, dict):
            raise ValueError(f"{export}: instruction {ordinal} is not an object")
        address = _normalize_address(instruction.get("address"))
        numeric = int(address, 16)
        if numeric <= previous:
            raise ValueError(f"{export}: instruction addresses are not strictly increasing")
        previous = numeric
        if address in seen:
            raise ValueError(f"{export}: duplicate instruction address {address}")
        seen.add(address)
        if not isinstance(instruction.get("mnemonic"), str):
            raise ValueError(f"{address}: mnemonic missing")
        if not isinstance(instruction.get("operands"), list):
            raise ValueError(f"{address}: operands missing")
        if not isinstance(instruction.get("flows"), list):
            raise ValueError(f"{address}: flows missing")
    if _normalize_address(instructions[0].get("address")) != TARGET_ADDRESS:
        raise ValueError(f"{export}: first instruction is not {TARGET_ADDRESS}")
    return instructions


def _sorted_origins(values: Iterable[str]) -> list[str]:
    return sorted(set(values))


def analyze_fun_00765470_body_owner_receiver(export: Path) -> dict[str, Any]:
    row = _read_single_row(export)
    instructions = _validate_instruction_row(row, export)
    by_address = {
        _normalize_address(instruction["address"]): instruction
        for instruction in instructions
    }
    address_set = set(by_address)

    call = by_address.get(BODY_LOOP_CALL)
    if call is None:
        raise ValueError(f"{export}: missing required call instruction {BODY_LOOP_CALL}")
    if str(call.get("mnemonic") or "").upper() != "CALL":
        raise ValueError(f"{BODY_LOOP_CALL}: required instruction is not CALL")
    if _call_target(call) != BODY_LOOP_TARGET:
        raise ValueError(
            f"{BODY_LOOP_CALL}: expected direct target {BODY_LOOP_TARGET}"
        )

    entry = TARGET_ADDRESS
    incoming: dict[str, State] = {entry: _initial_state()}
    queue: deque[str] = deque((entry,))
    iterations = 0
    max_iterations = max(64, len(instructions) * 64)

    while queue:
        address = queue.popleft()
        iterations += 1
        if iterations > max_iterations:
            raise ValueError("register provenance did not converge")
        before = incoming[address]
        after = _transfer(by_address[address], before)
        for successor in _successors(by_address[address], address_set):
            merged, changed = _merge(incoming.get(successor), after)
            if changed:
                incoming[successor] = merged
                queue.append(successor)

    call_state = incoming.get(BODY_LOOP_CALL)
    if call_state is None:
        raise ValueError(f"{BODY_LOOP_CALL}: callsite is unreachable from function entry")
    ecx_origins = _sorted_origins(call_state[ENTRY_RECEIVER])
    exact_entry_receiver = ecx_origins == [f"entry:{ENTRY_RECEIVER}"]

    ambiguous = len(ecx_origins) != 1 or any(
        value.startswith(("unknown:", "ambiguous:", "derived:", "memory:", "value:"))
        for value in ecx_origins
    )

    blockers: list[dict[str, Any]] = []
    if not exact_entry_receiver:
        blockers.append(
            {
                "id": "body-loop-ECX-not-proven-as-half-step-entry-ECX",
                "evidence_state": "ambiguous" if ambiguous else "verified-nonidentity",
                "call_instruction": BODY_LOOP_CALL,
                "observed_origins": ecx_origins,
                "required_evidence": (
                    "resolve every reachable ECX producer at 0x0076582a to the "
                    "FUN_00765470 entry ECX value"
                ),
            }
        )

    return {
        "format": FORMAT,
        "input": str(export),
        "target": {
            "function": TARGET_NAME,
            "address": TARGET_ADDRESS,
            "body_loop_call_instruction": BODY_LOOP_CALL,
            "body_loop_target": BODY_LOOP_TARGET,
            "physical_receiver_register": ENTRY_RECEIVER,
        },
        "analysis": {
            "reachable_instruction_count": len(incoming),
            "function_instruction_count": len(instructions),
            "fixed_point_iterations": iterations,
            "receiver_origins_before_body_loop_call": ecx_origins,
            "receiver_origin_cardinality": len(ecx_origins),
            "receiver_equals_half_step_entry_ECX_on_all_reachable_paths": exact_entry_receiver,
            "receiver_provenance_ambiguous": ambiguous,
        },
        "handoff": {
            "half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven": exact_entry_receiver,
            "global_vehicle_to_BODY_owner_composition_ready": exact_entry_receiver,
            "phase703_gate_rewrite_ready": exact_entry_receiver,
            "phase698_positive_selection_admissible_by_this_artifact_alone": False,
            "next_required_composition": (
                "SHIFT.GlobalVehicleComponentBaseIdentity/1 + this artifact + "
                "proven BMW chassis BODY 0"
                if exact_entry_receiver
                else "exact ECX producer resolution at 0x0076582a"
            ),
        },
        "blockers": blockers,
        "scope": {
            "physical_register_provenance_only": True,
            "FUN_00765470_class_identity_proven": False,
            "FUN_007b2270_class_identity_proven": False,
            "BODY_owner_semantic_class_name_proven": False,
            "outer_update_entry_ECX_joined_by_this_artifact": False,
            "vehicle_BODY_selection_emitted": False,
            "vehicle_world_transform_mapping_proven": False,
            "rendered_frame_cadence_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze_fun_00765470_body_owner_receiver(args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
