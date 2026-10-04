#!/usr/bin/env python3
"""Trace physical register origins at BMW BODY0 bind pose-writer callsites.

This consumes the exact caller/callsite frontier produced by
``build_bmw_body0_bind_initialization_frontier.py`` plus targeted
``SHIFT.GhidraFunctionInstructions/2`` rows.  It reuses the finite all-path IA-32
register provenance engine already regression-tested for FUN_00765470.

The result is deliberately physical only: it does not decide which register is a
BODY pointer, does not promote FUN_007b7840 to the bind initializer, and does not
infer stack-argument semantics or a BODY0 bind matrix.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Iterable

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_fun_00765470_body_owner_receiver as _register_engine

FORMAT = "SHIFT.BMWBody0BindCallsiteRegisterProvenance/1"
FRONTIER_FORMAT = "SHIFT.BMWBody0BindInitializationFrontier/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
POSE_WRITER = "0x007b7840"
LEXICAL_WINDOW = 12

_TRACKED = tuple(_register_engine._TRACKED)


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


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


def _address(value: Any, *, field: str) -> str:
    try:
        return _register_engine._normalize_address(value)
    except ValueError as exc:
        raise ValueError(f"{field}: {exc}") from exc


def _call_target(instruction: dict[str, Any]) -> str | None:
    normalized: list[str] = []
    flows = instruction.get("flows")
    if isinstance(flows, list):
        for value in flows:
            if not isinstance(value, str):
                continue
            try:
                normalized.append(_address(value, field="call flow"))
            except ValueError:
                pass
    if POSE_WRITER in normalized:
        return POSE_WRITER
    operands = instruction.get("operands")
    if isinstance(operands, list):
        for value in operands:
            if not isinstance(value, str):
                continue
            try:
                if _address(value, field="call operand") == POSE_WRITER:
                    return POSE_WRITER
            except ValueError:
                continue
    return None


def _validate_frontier(frontier: dict[str, Any]) -> list[dict[str, Any]]:
    if frontier.get("format") != FRONTIER_FORMAT:
        raise ValueError(f"expected {FRONTIER_FORMAT}")
    writer = frontier.get("pose_writer_candidate")
    if not isinstance(writer, dict):
        raise ValueError("pose_writer_candidate missing")
    if _address(writer.get("function"), field="pose_writer_candidate.function") != POSE_WRITER:
        raise ValueError("pose-writer anchor drift")
    if writer.get("bind_initializer_semantics_proven") is not False:
        raise ValueError("frontier unexpectedly preclaims bind initializer semantics")
    callers = writer.get("direct_callers")
    if not isinstance(callers, list):
        raise ValueError("pose_writer_candidate.direct_callers must be a list")
    if writer.get("direct_caller_count") != len(callers):
        raise ValueError("pose-writer direct caller count mismatch")

    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(callers):
        if not isinstance(row, dict):
            raise ValueError(f"direct_callers[{index}] must be an object")
        caller = _address(row.get("caller"), field=f"direct_callers[{index}].caller")
        callsite = _address(row.get("callsite"), field=f"direct_callers[{index}].callsite")
        key = (caller, callsite)
        if key in seen:
            raise ValueError(f"duplicate pose-writer caller/callsite: {caller} {callsite}")
        seen.add(key)
        if row.get("bind_initializer_semantics_proven") is not False:
            raise ValueError(f"{caller}: frontier preclaims initializer semantics")
        if row.get("BODY0_pointer_proven") is not False:
            raise ValueError(f"{caller}: frontier preclaims BODY0 pointer identity")
        normalized.append(
            {
                "caller": caller,
                "caller_name": row.get("caller_name"),
                "callsite": callsite,
                "candidate_class": row.get("candidate_class"),
                "from_BODY_builder": row.get("from_BODY_builder"),
                "from_SDF_loader": row.get("from_SDF_loader"),
            }
        )
    normalized.sort(key=lambda row: (int(row["caller"], 0), int(row["callsite"], 0)))
    return normalized


def _validate_instruction_row(row: dict[str, Any], source: Path) -> tuple[str, list[dict[str, Any]]]:
    if row.get("format") != INSTRUCTION_FORMAT:
        raise ValueError(
            f"{source}: requires {INSTRUCTION_FORMAT}; found {row.get('format')!r}"
        )
    if row.get("found") is not True:
        raise ValueError(f"{source}: targeted function was not resolved")
    function = row.get("function")
    if not isinstance(function, dict):
        raise ValueError(f"{source}: function metadata missing")
    function_address = _address(function.get("address"), field="function.address")
    instructions = row.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError(f"{function_address}: instruction list is empty")
    if row.get("instruction_count") != len(instructions):
        raise ValueError(f"{function_address}: instruction_count mismatch")

    previous = -1
    seen: set[str] = set()
    for ordinal, instruction in enumerate(instructions):
        if not isinstance(instruction, dict):
            raise ValueError(f"{function_address}: instruction {ordinal} is not an object")
        address = _address(instruction.get("address"), field="instruction.address")
        numeric = int(address, 0)
        if numeric <= previous:
            raise ValueError(f"{function_address}: instruction addresses are not strictly increasing")
        previous = numeric
        if address in seen:
            raise ValueError(f"{function_address}: duplicate instruction address {address}")
        seen.add(address)
        if not isinstance(instruction.get("mnemonic"), str):
            raise ValueError(f"{address}: mnemonic missing")
        if not isinstance(instruction.get("operands"), list):
            raise ValueError(f"{address}: operands missing")
        if not isinstance(instruction.get("flows"), list):
            raise ValueError(f"{address}: flows missing")
    first = _address(instructions[0].get("address"), field="first instruction")
    if first != function_address:
        raise ValueError(f"{function_address}: first instruction does not match function entry")
    return function_address, instructions


def _index_instruction_rows(path: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in _read_rows(path):
        function, instructions = _validate_instruction_row(row, path)
        if function in result:
            raise ValueError(f"{path}: duplicate instruction row for {function}")
        result[function] = instructions
    return result


def _analyze_incoming_states(instructions: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    by_address = {
        _address(instruction["address"], field="instruction.address"): instruction
        for instruction in instructions
    }
    address_set = set(by_address)
    entry = _address(instructions[0]["address"], field="function entry")
    incoming: dict[str, Any] = {entry: _register_engine._initial_state()}
    queue: deque[str] = deque((entry,))
    iterations = 0
    max_iterations = max(64, len(instructions) * 64)
    while queue:
        address = queue.popleft()
        iterations += 1
        if iterations > max_iterations:
            raise ValueError(f"{entry}: register provenance did not converge")
        before = incoming[address]
        after = _register_engine._transfer(by_address[address], before)
        for successor in _register_engine._successors(by_address[address], address_set):
            merged, changed = _register_engine._merge(incoming.get(successor), after)
            if changed:
                incoming[successor] = merged
                queue.append(successor)
    return incoming, iterations


def _origin_flags(origins: list[str]) -> dict[str, Any]:
    exact = len(origins) == 1
    unknown_prefixes = ("unknown:", "ambiguous:", "derived:", "value:")
    return {
        "origin_count": len(origins),
        "exact_single_origin": exact,
        "contains_unknown_or_derived": any(value.startswith(unknown_prefixes) for value in origins),
        "contains_memory_origin": any(value.startswith("memory:") for value in origins),
        "contains_entry_origin": any(value.startswith("entry:") for value in origins),
    }


def _lexical_window(instructions: list[dict[str, Any]], callsite: str) -> list[dict[str, Any]]:
    positions = {
        _address(instruction["address"], field="instruction.address"): index
        for index, instruction in enumerate(instructions)
    }
    index = positions[callsite]
    start = max(0, index - LEXICAL_WINDOW)
    result = []
    for instruction in instructions[start : index + 1]:
        result.append(
            {
                "address": _address(instruction.get("address"), field="window.address"),
                "mnemonic": str(instruction.get("mnemonic") or "").upper(),
                "text": instruction.get("text"),
                "operands": list(instruction.get("operands") or []),
                "flow_type": instruction.get("flow_type"),
                "fallthrough": instruction.get("fallthrough"),
                "flows": list(instruction.get("flows") or []),
                "pcode": list(instruction.get("pcode") or []),
            }
        )
    return result


def analyze_bmw_body0_bind_callsite_register_provenance(
    frontier_path: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    frontier = _load_json(frontier_path, FRONTIER_FORMAT)
    callers = _validate_frontier(frontier)
    instruction_rows = _index_instruction_rows(instruction_export)

    required_callers = sorted({row["caller"] for row in callers}, key=lambda value: int(value, 0))
    missing = [address for address in required_callers if address not in instruction_rows]
    if missing:
        raise ValueError(
            "instruction export missing required pose-writer caller(s): " + ", ".join(missing)
        )

    state_cache: dict[str, tuple[dict[str, Any], int]] = {}
    analyses: list[dict[str, Any]] = []
    for caller in callers:
        function = caller["caller"]
        instructions = instruction_rows[function]
        by_address = {
            _address(instruction["address"], field="instruction.address"): instruction
            for instruction in instructions
        }
        callsite = caller["callsite"]
        call = by_address.get(callsite)
        if call is None:
            raise ValueError(f"{function}: missing required callsite {callsite}")
        if str(call.get("mnemonic") or "").upper() != "CALL":
            raise ValueError(f"{function}:{callsite}: frontier callsite is not CALL")
        if _call_target(call) != POSE_WRITER:
            raise ValueError(
                f"{function}:{callsite}: expected direct target {POSE_WRITER}"
            )

        if function not in state_cache:
            state_cache[function] = _analyze_incoming_states(instructions)
        incoming, iterations = state_cache[function]
        state = incoming.get(callsite)
        if state is None:
            raise ValueError(f"{function}:{callsite}: callsite is unreachable from function entry")

        registers: dict[str, Any] = {}
        exact_entry_aliases: dict[str, str] = {}
        unresolved_registers: list[str] = []
        for register in _TRACKED:
            origins = _register_engine._sorted_origins(state[register])
            flags = _origin_flags(origins)
            registers[register] = {"origins": origins, **flags}
            if len(origins) == 1 and origins[0].startswith("entry:"):
                exact_entry_aliases[register] = origins[0].split(":", 1)[1]
            if not flags["exact_single_origin"] or flags["contains_unknown_or_derived"]:
                unresolved_registers.append(register)

        analyses.append(
            {
                **caller,
                "target": POSE_WRITER,
                "reachable_instruction_count": len(incoming),
                "function_instruction_count": len(instructions),
                "fixed_point_iterations": iterations,
                "registers_before_call": registers,
                "exact_entry_register_aliases": exact_entry_aliases,
                "unresolved_or_ambiguous_registers": unresolved_registers,
                "lexical_pre_call_window": _lexical_window(instructions, callsite),
                "lexical_window_is_path_proof": False,
                "physical_register_provenance_ready": True,
                "BODY_pointer_register_proven": False,
                "BODY0_pointer_proven": False,
                "bind_initializer_semantics_proven": False,
                "origin_basis_argument_semantics_proven": False,
            }
        )

    blockers: list[dict[str, Any]] = []
    if not analyses:
        blockers.append(
            {
                "id": "pose-writer-direct-caller-set-empty",
                "evidence_state": "blocked",
                "required_evidence": "resolve direct/reference/dispatch callers before callsite provenance",
            }
        )
    else:
        blockers.extend(
            [
                {
                    "id": "pose-writer-physical-ABI-semantic-binding-unproven",
                    "evidence_state": "unknown",
                    "required_evidence": (
                        "bind physical registers/stack arguments at each relevant FUN_007b7840 callsite "
                        "to source-backed parameters without naming them from register position alone"
                    ),
                },
                {
                    "id": "BODY0-pointer-at-bind-callsite-unproven",
                    "evidence_state": "unknown",
                    "required_evidence": (
                        "join one physical call argument to exact BMW BODY index 0 pointer provenance"
                    ),
                },
                {
                    "id": "bind-origin-basis-value-provenance-unproven",
                    "evidence_state": "unknown",
                    "required_evidence": (
                        "trace exact bind origin/basis source values through the relevant initialization caller"
                    ),
                },
                {
                    "id": "stack-argument-value-provenance-unmodeled",
                    "evidence_state": "unknown",
                    "required_evidence": (
                        "if the proven FUN_007b7840 ABI uses stack arguments, add exact stack-value provenance; "
                        "the lexical window in this report is discovery evidence only"
                    ),
                },
            ]
        )

    return {
        "format": FORMAT,
        "inputs": {
            "initialization_frontier": str(frontier_path),
            "instruction_export": str(instruction_export),
        },
        "target": {
            "pose_writer_candidate": POSE_WRITER,
            "direct_caller_count": len(callers),
            "required_caller_functions": required_callers,
        },
        "analysis": {
            "analyzed_callsite_count": len(analyses),
            "all_frontier_callsites_analyzed": len(analyses) == len(callers),
            "tracked_registers": list(_TRACKED),
            "call_clobber_model": list(_register_engine._CALLER_SAVED),
            "callsites": analyses,
        },
        "handoff": {
            "pose_writer_callsite_register_provenance_ready": bool(analyses) and len(analyses) == len(callers),
            "pose_writer_ABI_semantics_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "next_required_join": (
                "physical FUN_007b7840 ABI + BODY0 pointer identity + origin/basis value provenance"
                if analyses
                else "resolve pose-writer direct caller set"
            ),
        },
        "blockers": blockers,
        "scope": {
            "register_engine_reused_from_FUN_00765470_proof": True,
            "physical_register_provenance_only": True,
            "stack_argument_semantics_inferred": False,
            "lexical_window_used_as_path_proof": False,
            "register_position_used_as_parameter_semantics": False,
            "pose_writer_candidate_promoted_to_initializer": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("initialization_frontier", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_bmw_body0_bind_callsite_register_provenance(
        args.initialization_frontier,
        args.instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
