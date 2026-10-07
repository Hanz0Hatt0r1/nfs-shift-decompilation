#!/usr/bin/env python3
"""Recover the physical explicit argument passed to PC FUN_007618f0.

The target is a thiscall-style routine whose HDVehicle receiver is carried in
ECX and whose remaining source object is an explicit stack argument.  This
analyzer deliberately proves only the physical value pushed immediately before
each direct FUN_007618f0 callsite.  It does not assign a semantic class/name to
that object merely from offsets +0x338/+0x918.

A callsite is promoted only when the instruction immediately preceding CALL is
an unambiguous single PUSH.  Register PUSH operands are resolved with the
existing finite all-path IA-32 register-provenance engine.  Anything less exact
stays unresolved rather than guessing stack history.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_fun_00765470_body_owner_receiver as _reg

FORMAT = "SHIFT.Fun007618f0SecondArgumentProvenance/1"
WORKLIST_FORMAT = "SHIFT.Fun007618f0SecondArgumentWorklist/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
TARGET = "0x007618f0"
TARGET_NAME = "FUN_007618f0"


def _address(value: Any, *, field: str) -> str:
    try:
        return _reg._normalize_address(value)
    except ValueError as exc:
        raise ValueError(f"{field}: {exc}") from exc


def _read_rows(path: Path) -> list[dict[str, Any]]:
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
    return rows


def _load_worklist(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != WORKLIST_FORMAT:
        raise ValueError(f"{path}: expected {WORKLIST_FORMAT}")
    if _address(value.get("target"), field="worklist.target") != TARGET:
        raise ValueError("worklist target drift")
    calls = value.get("direct_calls")
    if not isinstance(calls, list) or not calls:
        raise ValueError("worklist contains no direct calls")
    return value


def _validate_instruction_row(row: dict[str, Any], source: Path) -> tuple[str, list[dict[str, Any]]]:
    if row.get("format") != INSTRUCTION_FORMAT:
        raise ValueError(f"{source}: expected {INSTRUCTION_FORMAT}")
    if row.get("found") is not True:
        raise ValueError(f"{source}: targeted function was not resolved")
    function = row.get("function")
    if not isinstance(function, dict):
        raise ValueError(f"{source}: function metadata missing")
    function_address = _address(function.get("address"), field="function.address")
    instructions = row.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError(f"{function_address}: instruction list empty")
    if row.get("instruction_count") != len(instructions):
        raise ValueError(f"{function_address}: instruction_count mismatch")
    previous = -1
    for ordinal, insn in enumerate(instructions):
        if not isinstance(insn, dict):
            raise ValueError(f"{function_address}: instruction {ordinal} is not an object")
        address = _address(insn.get("address"), field="instruction.address")
        numeric = int(address, 0)
        if numeric <= previous:
            raise ValueError(f"{function_address}: instruction addresses not strictly increasing")
        previous = numeric
        if not isinstance(insn.get("mnemonic"), str):
            raise ValueError(f"{address}: mnemonic missing")
        if not isinstance(insn.get("operands"), list):
            raise ValueError(f"{address}: operands missing")
        if not isinstance(insn.get("flows"), list):
            raise ValueError(f"{address}: flows missing")
    return function_address, instructions


def _index_instruction_rows(path: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in _read_rows(path):
        function, instructions = _validate_instruction_row(row, path)
        if function in result:
            raise ValueError(f"{path}: duplicate function row {function}")
        result[function] = instructions
    return result


def _call_targets(insn: dict[str, Any]) -> set[str]:
    targets: set[str] = set()
    for raw in insn.get("flows", []):
        if isinstance(raw, str):
            try:
                targets.add(_address(raw, field="call flow"))
            except ValueError:
                pass
    for raw in insn.get("operands", []):
        if isinstance(raw, str):
            try:
                targets.add(_address(raw, field="call operand"))
            except ValueError:
                pass
    return targets


def _incoming_states(instructions: list[dict[str, Any]]) -> dict[str, Any]:
    by_address = {_address(row["address"], field="instruction.address"): row for row in instructions}
    address_set = set(by_address)
    entry = _address(instructions[0]["address"], field="function entry")
    incoming: dict[str, Any] = {entry: _reg._initial_state()}
    queue: deque[str] = deque((entry,))
    iterations = 0
    maximum = max(64, len(instructions) * 64)
    while queue:
        address = queue.popleft()
        iterations += 1
        if iterations > maximum:
            raise ValueError(f"{entry}: register provenance did not converge")
        before = incoming[address]
        after = _reg._transfer(by_address[address], before)
        for successor in _reg._successors(by_address[address], address_set):
            merged, changed = _reg._merge(incoming.get(successor), after)
            if changed:
                incoming[successor] = merged
                queue.append(successor)
    return incoming


def _origins_for_push_operand(operand: str, state: dict[str, Any], address: str) -> list[str]:
    register = _reg._register(operand)
    if register is not None:
        origins = state[register]
    else:
        origins = _reg._source_value(operand, state, address)
    return sorted(str(value) for value in origins)


def _flags(origins: list[str]) -> dict[str, Any]:
    unresolved_prefixes = ("unknown:", "ambiguous:", "derived:", "value:")
    exact_single = len(origins) == 1 and not origins[0].startswith(unresolved_prefixes)
    return {
        "origin_count": len(origins),
        "exact_single_physical_origin": exact_single,
        "contains_memory_origin": any(value.startswith("memory:") for value in origins),
        "contains_entry_register_origin": any(value.startswith("entry:") for value in origins),
        "contains_unresolved_origin": any(value.startswith(unresolved_prefixes) for value in origins),
    }


def analyze(worklist: dict[str, Any], instruction_rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    required_callers = sorted(
        {str(row["caller"]) for row in worklist["direct_calls"]}, key=lambda value: int(value, 0)
    )
    missing = [caller for caller in required_callers if caller not in instruction_rows]
    if missing:
        raise ValueError("instruction export missing caller(s): " + ", ".join(missing))

    results: list[dict[str, Any]] = []
    for call in worklist["direct_calls"]:
        caller = _address(call.get("caller"), field="direct_calls.caller")
        callsite = _address(call.get("callsite"), field="direct_calls.callsite")
        instructions = instruction_rows[caller]
        positions = {
            _address(insn["address"], field="instruction.address"): index
            for index, insn in enumerate(instructions)
        }
        if callsite not in positions:
            raise ValueError(f"{caller}: callsite {callsite} absent from instruction export")
        index = positions[callsite]
        call_insn = instructions[index]
        if str(call_insn.get("mnemonic") or "").upper() != "CALL":
            raise ValueError(f"{caller}: {callsite} is not CALL")
        if TARGET not in _call_targets(call_insn):
            raise ValueError(f"{caller}: {callsite} no longer targets {TARGET_NAME}")

        incoming = _incoming_states(instructions)
        call_state = incoming.get(callsite)
        if call_state is None:
            raise ValueError(f"{caller}: callsite {callsite} is unreachable in exported CFG")
        receiver_origins = sorted(str(value) for value in call_state["ECX"])

        row: dict[str, Any] = {
            "caller": caller,
            "caller_name": call.get("caller_name"),
            "callsite": callsite,
            "receiver_register": "ECX",
            "receiver_origins": receiver_origins,
            "receiver_flags": _flags(receiver_origins),
            "explicit_argument_push_ready": False,
            "explicit_argument_push": None,
            "explicit_argument_operand": None,
            "explicit_argument_origins": [],
            "explicit_argument_flags": _flags([]),
            "semantic_owner_claimed": False,
        }
        if index > 0:
            push = instructions[index - 1]
            push_address = _address(push.get("address"), field="push.address")
            operands = push.get("operands")
            if str(push.get("mnemonic") or "").upper() == "PUSH" and isinstance(operands, list) and len(operands) == 1 and isinstance(operands[0], str):
                push_state = incoming.get(push_address)
                if push_state is None:
                    raise ValueError(f"{caller}: argument PUSH {push_address} unreachable")
                origins = _origins_for_push_operand(operands[0], push_state, push_address)
                row.update(
                    {
                        "explicit_argument_push_ready": True,
                        "explicit_argument_push": push_address,
                        "explicit_argument_operand": operands[0],
                        "explicit_argument_origins": origins,
                        "explicit_argument_flags": _flags(origins),
                    }
                )
        results.append(row)

    physically_resolved = bool(results) and all(
        row["explicit_argument_push_ready"]
        and row["explicit_argument_flags"]["exact_single_physical_origin"]
        for row in results
    )
    return {
        "format": FORMAT,
        "version": 1,
        "target": TARGET,
        "target_name": TARGET_NAME,
        "direct_call_count": len(results),
        "callsites": results,
        "all_callsites_immediate_push_ready": bool(results)
        and all(row["explicit_argument_push_ready"] for row in results),
        "all_callsites_argument_physically_resolved": physically_resolved,
        "semantic_owner_claimed": False,
        "ready_for_semantic_owner_join": physically_resolved,
        "policy": "physical callsite argument provenance only; +0x338/+0x918 semantic owner requires an independent object/storage join",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("worklist", type=Path)
    parser.add_argument("instructions", type=Path)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()

    worklist = _load_worklist(args.worklist)
    rows = _index_instruction_rows(args.instructions)
    report = analyze(worklist, rows)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
