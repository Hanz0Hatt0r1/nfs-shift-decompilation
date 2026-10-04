#!/usr/bin/env python3
"""Bound the real Vehicle+0x860 / PhysicsParticipant+0xba0 writer frontier.

PR #1250 retracted the old manager-record zero inference.  The value consumed by
HighDetailVehicle initialization belongs to the separately allocated 0x2b90
PhysicsParticipant object stored in manager record[0].  Its embedded Vehicle
starts at +0x340, therefore actual-participant+0xba0 aliases Vehicle+0x860.

This analyzer consumes the corrected fail-closed object frontier plus one
``SHIFT.GhidraFunctionInstructions/2`` export containing only the exact
constructor chain:

    FUN_007125e0 -> FUN_0072ed20 -> FUN_0079c1c0 -> FUN_0079bfd0

It proves the affine ECX handoff into the embedded Vehicle constructor, inventories
only target-overlapping STOREs on the correct object receiver, and emits same-
receiver forwarded callees when the target is initialized deeper in the chain.
It never revives the retracted +0.0f claim and never treats callgraph adjacency as
a value proof.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite
import analyze_bmw_body0_bind_pose_writer_value_provenance as _values
import analyze_bmw_offset33b_additional_mass_bootstrap_zero as _correction
import analyze_register_relative_accesses as _access

FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassWriterFrontier/1"
CORRECTION_FORMAT = "SHIFT.BMWOffset33bAdditionalMassActualObjectFrontier/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

ACTUAL_PARTICIPANT = "0x0072ed20"
VEHICLE_CTOR = "0x0079c1c0"
VEHICLE_BASE_CTOR = "0x0079bfd0"
ALLOCATOR_WRAPPER = "0x007125e0"
TARGET_PARTICIPANT_OFFSET = 0xBA0
VEHICLE_EMBEDDED_OFFSET = 0x340
TARGET_VEHICLE_OFFSET = 0x860
TARGET_WIDTH = 4

FUNCTIONS: dict[str, dict[str, Any]] = {
    "0x007125e0": {
        "name": "FUN_007125e0",
        "size": 185,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "d0d7c65693b7f3ef34ea399789518ef8c2aee61543bfe0473ddad54f4333adf0",
        "role": "manager-record actual PhysicsParticipant allocation wrapper",
    },
    "0x0072ed20": {
        "name": "FUN_0072ed20",
        "size": 1161,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "d6eb0ccddc64f5df669ab82e905efdfb9484f70d4201110e8eb35148f19908ff",
        "role": "actual 0x2b90 PhysicsParticipant constructor",
    },
    "0x0079c1c0": {
        "name": "FUN_0079c1c0",
        "size": 497,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "6759f1781d58bf38b72e2fa45ab24fc12bccf46bde95d90c4c57e2a0d600c39c",
        "role": "embedded Vehicle constructor",
    },
    "0x0079bfd0": {
        "name": "FUN_0079bfd0",
        "size": 445,
        "calling_convention": "__fastcall",
        "mnemonic_sha256": "06e730897a4a85d93a5f33765fd15b0c52708fb2c864c290804024b109a3d950",
        "role": "Vehicle base-state constructor",
    },
}

REQUIRED_CALLS = (
    ("0x007125e0", "0x0071262b", "0x0072ed20", "construct allocated actual PhysicsParticipant"),
    ("0x0072ed20", "0x0072ed57", "0x0079c1c0", "construct embedded Vehicle at participant+0x340"),
    ("0x0079c1c0", "0x0079c1e1", "0x0079bfd0", "construct Vehicle base state"),
)

_TRACKED = ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP")
_CALLER_SAVED = ("EAX", "ECX", "EDX")
_REGISTER_RE = re.compile(r"^(EAX|EBX|ECX|EDX|ESI|EDI|EBP)$", re.IGNORECASE)
_AFFINE_ENTRY_RE = re.compile(r"^entry:(EAX|EBX|ECX|EDX|ESI|EDI|EBP)([+-]0x[0-9a-f]+)?$", re.IGNORECASE)

State = dict[str, frozenset[str]]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _addr(value: Any, field: str) -> str:
    return _callsite._address(value, field=field)


def _validate_retail(root: Path) -> list[dict[str, Any]]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")

    rows = _read_jsonl(root / "functions.jsonl")
    validated: list[dict[str, Any]] = []
    for address, expected in FUNCTIONS.items():
        hits = [row for row in rows if str(row.get("address") or "").lower() == address]
        if len(hits) != 1:
            raise ValueError(f"expected exactly one function row for {address}; found {len(hits)}")
        row = hits[0]
        for key in ("name", "size", "calling_convention", "mnemonic_sha256"):
            if row.get(key) != expected[key]:
                raise ValueError(f"{address}: {key} drift")
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        validated.append({"address": address, **expected})

    calls = _read_jsonl(root / "callgraph.jsonl")
    for source, instruction, target, _role in REQUIRED_CALLS:
        hits = [
            row for row in calls
            if str(row.get("from_function") or "").lower() == source
            and str(row.get("instruction") or "").lower() == instruction
            and str(row.get("to") or "").lower() == target
            and row.get("indirect") is False
        ]
        if len(hits) != 1:
            raise ValueError(f"required constructor edge drift: {source}:{instruction}->{target}")
    return validated


def _validate_correction(root: Path) -> dict[str, Any]:
    report = _correction.analyze_bmw_offset33b_additional_mass_bootstrap_zero(root)
    if report.get("format") != CORRECTION_FORMAT or report.get("ready") is not False:
        raise ValueError("actual-object correction frontier drift")
    correction = report.get("correction")
    if not isinstance(correction, Mapping):
        raise ValueError("actual-object correction missing")
    if correction.get("manager_record_and_actual_participant_are_distinct_objects") is not True:
        raise ValueError("manager record/object distinction no longer proven")
    if correction.get("additional_mass_zero_value_proven") is not False:
        raise ValueError("retracted zero value was unexpectedly revived")
    gates = report.get("gates")
    if not isinstance(gates, Mapping) or gates.get("BMW_numeric_offset33b_ready") is not False:
        raise ValueError("correction frontier unexpectedly preclaims numeric offset33b")
    return report


def _register(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _REGISTER_RE.fullmatch(value.strip())
    return None if match is None else match.group(1).upper()


def _atom(value: str) -> frozenset[str]:
    return frozenset((value,))


def _initial_state() -> State:
    return {reg: _atom(f"entry:{reg}") for reg in _TRACKED}


def _format_affine(register: str, delta: int) -> str:
    if delta == 0:
        return f"entry:{register}"
    sign = "+" if delta > 0 else "-"
    return f"entry:{register}{sign}0x{abs(delta):x}"


def _shift_origin(value: str, delta: int, *, address: str) -> str:
    match = _AFFINE_ENTRY_RE.fullmatch(value)
    if match is None:
        return f"derived:affine@{address}:{value}:{delta:+#x}"
    base = match.group(1).upper()
    suffix = match.group(2)
    old = 0
    if suffix:
        old = int(suffix[1:], 16) * (1 if suffix[0] == "+" else -1)
    return _format_affine(base, old + delta)


def _parse_immediate(value: str) -> int | None:
    token = value.strip().lower()
    try:
        return int(token, 0)
    except ValueError:
        return None


def _source_value(operand: str, state: State, address: str) -> frozenset[str]:
    reg = _register(operand)
    if reg is not None:
        return state[reg]
    immediate = _parse_immediate(operand)
    if immediate is not None:
        return _atom(f"immediate:{immediate:#x}")
    if "[" in operand and "]" in operand:
        return _atom(f"memory:{operand.strip().lower()}")
    return _atom(f"value:{operand.strip().lower()}@{address}")


def _transfer(instruction: Mapping[str, Any], incoming: State) -> State:
    state: State = dict(incoming)
    address = _addr(instruction.get("address"), "instruction.address")
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{address}: operands must be strings")
    handled: set[str] = set()

    if mnemonic == "MOV" and len(operands) >= 2:
        dest = _register(operands[0])
        if dest in state:
            state[dest] = _source_value(operands[1], incoming, address)
            handled.add(dest)
    elif mnemonic == "LEA" and len(operands) >= 2:
        dest = _register(operands[0])
        parsed = _access._parse_memory_operand(operands[1])
        if dest in state:
            if parsed is None:
                state[dest] = _atom(f"derived:LEA:{dest}@{address}")
            else:
                base, displacement = parsed
                base = base.upper()
                if base not in incoming:
                    state[dest] = _atom(f"derived:LEA:{dest}@{address}")
                else:
                    state[dest] = frozenset(
                        _shift_origin(origin, displacement, address=address)
                        for origin in incoming[base]
                    )
            handled.add(dest)
    elif mnemonic in {"ADD", "SUB"} and len(operands) >= 2:
        dest = _register(operands[0])
        immediate = _parse_immediate(operands[1])
        if dest in state:
            if immediate is None:
                state[dest] = _atom(f"derived:{mnemonic}:{dest}@{address}")
            else:
                delta = immediate if mnemonic == "ADD" else -immediate
                state[dest] = frozenset(
                    _shift_origin(origin, delta, address=address)
                    for origin in incoming[dest]
                )
            handled.add(dest)
    elif mnemonic == "XOR" and len(operands) >= 2:
        dest = _register(operands[0])
        src = _register(operands[1])
        if dest in state:
            state[dest] = _atom("immediate:0") if dest == src else _atom(f"derived:XOR:{dest}@{address}")
            handled.add(dest)

    if mnemonic == "CALL":
        for reg in _CALLER_SAVED:
            state[reg] = _atom(f"unknown:{reg}@{address}:call-clobber")
            handled.add(reg)

    for reg in _callsite._register_engine._structured_register_outputs(dict(instruction)):
        if reg in state and reg not in handled:
            state[reg] = _atom(f"unknown:{reg}@{address}:unmodelled-pcode-write")
    return state


def _merge(existing: State | None, incoming: State) -> tuple[State, bool]:
    if existing is None:
        return dict(incoming), True
    merged: State = {}
    changed = False
    for reg in _TRACKED:
        values = set(existing[reg]) | set(incoming[reg])
        if len(values) > 8:
            values = {f"ambiguous:{reg}:many"}
        frozen = frozenset(values)
        merged[reg] = frozen
        changed |= frozen != existing[reg]
    return merged, changed


def _incoming_states(instructions: list[dict[str, Any]]) -> tuple[dict[str, State], int]:
    by_address = {_addr(row.get("address"), "instruction.address"): row for row in instructions}
    addresses = set(by_address)
    entry = _addr(instructions[0].get("address"), "function.entry")
    incoming: dict[str, State] = {entry: _initial_state()}
    queue: deque[str] = deque((entry,))
    iterations = 0
    while queue:
        address = queue.popleft()
        iterations += 1
        if iterations > max(64, len(instructions) * 64):
            raise ValueError(f"{entry}: affine register provenance did not converge")
        after = _transfer(by_address[address], incoming[address])
        for successor in _callsite._register_engine._successors(by_address[address], addresses):
            merged, changed = _merge(incoming.get(successor), after)
            if changed:
                incoming[successor] = merged
                queue.append(successor)
    return incoming, iterations


def _direct_target(instruction: Mapping[str, Any]) -> str | None:
    if str(instruction.get("mnemonic") or "").upper() != "CALL":
        return None
    values = list(instruction.get("flows") or []) + list(instruction.get("operands") or [])
    for raw in values:
        if not isinstance(raw, str):
            continue
        try:
            return _addr(raw, "call.target")
        except ValueError:
            continue
    return None


def _value_slice(
    address: str,
    op_index: int,
    operation: Mapping[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, list[str]],
    bindings: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    inputs = operation.get("inputs")
    if not isinstance(inputs, list) or len(inputs) < 3:
        raise ValueError(f"{address}:{op_index}: STORE value input missing")
    value = _values._validate_varnode(inputs[2], context=f"{address}:{op_index}:STORE value")
    node_id = f"{address}:{op_index}"
    binding = next(
        (row for row in bindings.get(node_id, []) if row.get("input_index") == 2),
        None,
    )
    if not isinstance(binding, Mapping):
        raise ValueError(f"{node_id}: STORE value binding missing")
    definition = binding.get("definition")
    slice_nodes, roots_raw = _values._slice_from_definition(
        definition if isinstance(definition, str) else None,
        value if definition is None else None,
        nodes,
        edges,
        bindings,
    )
    roots = [_values._classify_root(root) for root in roots_raw]
    return {
        "store_value_varnode": dict(value),
        "store_value_definition": definition,
        "dependency_slice": slice_nodes,
        "terminal_roots": roots,
        "terminal_root_kinds": sorted({str(root.get("root_kind")) for root in roots}),
        "numeric_value_proven": False,
    }


def _target_offset(function: str) -> int | None:
    if function == ACTUAL_PARTICIPANT:
        return TARGET_PARTICIPANT_OFFSET
    if function in {VEHICLE_CTOR, VEHICLE_BASE_CTOR}:
        return TARGET_VEHICLE_OFFSET
    return None


def _analyze_function(function: str, instructions: list[dict[str, Any]]) -> dict[str, Any]:
    incoming, iterations = _incoming_states(instructions)
    nodes, edges, bindings = _values._structured_pcode_graph(instructions)
    target = _target_offset(function)
    stores: list[dict[str, Any]] = []
    forwards: list[dict[str, Any]] = []

    for instruction in instructions:
        address = _addr(instruction.get("address"), "instruction.address")
        state = incoming.get(address)
        if state is None:
            continue
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic == "CALL":
            callee = _direct_target(instruction)
            if callee is not None:
                origins = sorted(state["ECX"])
                forwards.append({
                    "callsite": address,
                    "callee": callee,
                    "ECX_origins_before_call": origins,
                    "ECX_is_current_function_entry_receiver": origins == ["entry:ECX"],
                })

        if target is None:
            continue
        pcode = instruction.get("pcode")
        if not isinstance(pcode, list):
            raise ValueError(f"{address}: pcode missing")
        store_ops = [
            (index, op) for index, op in enumerate(pcode)
            if isinstance(op, Mapping) and str(op.get("opcode") or "").upper() == "STORE"
        ]
        if not store_ops:
            continue
        operands = instruction.get("operands")
        if not isinstance(operands, list):
            raise ValueError(f"{address}: operands missing")
        parsed = [
            (operand, _access._parse_memory_operand(operand))
            for operand in operands if isinstance(operand, str) and "[" in operand and "]" in operand
        ]
        parsed = [(operand, value) for operand, value in parsed if value is not None]
        if len(store_ops) != 1 or len(parsed) != 1:
            continue
        op_index, operation = store_ops[0]
        operand, memory = parsed[0]
        assert memory is not None
        base, displacement = memory
        inputs = operation.get("inputs")
        if not isinstance(inputs, list) or len(inputs) < 3 or not isinstance(inputs[2], Mapping):
            raise ValueError(f"{address}:{op_index}: STORE value input invalid")
        width = inputs[2].get("size")
        if not isinstance(width, int) or width <= 0:
            raise ValueError(f"{address}:{op_index}: STORE width invalid")
        touched = set(range(displacement, displacement + width)) & set(range(target, target + TARGET_WIDTH))
        if not touched:
            continue
        base = base.upper()
        origins = sorted(state.get(base, frozenset()))
        exact_receiver = origins == ["entry:ECX"]
        stores.append({
            "instruction": address,
            "instruction_text": instruction.get("text"),
            "operand": operand,
            "base_register": base,
            "base_register_origins": origins,
            "target_is_current_function_entry_receiver": exact_receiver,
            "displacement": displacement,
            "displacement_hex": f"0x{displacement:x}",
            "store_width": width,
            "target_bytes_touched": sorted(touched),
            **_value_slice(address, op_index, operation, nodes, edges, bindings),
        })

    return {
        "function": function,
        "name": FUNCTIONS[function]["name"],
        "role": FUNCTIONS[function]["role"],
        "target_displacement": None if target is None else f"0x{target:x}",
        "instruction_count": len(instructions),
        "reachable_instruction_count": len(incoming),
        "fixed_point_iterations": iterations,
        "target_store_candidates": stores,
        "direct_calls": forwards,
    }


def analyze_bmw_offset33b_actual_additional_mass_writer_frontier(
    ghidra_export: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    correction = _validate_correction(ghidra_export)
    retail_functions = _validate_retail(ghidra_export)
    rows = _callsite._index_instruction_rows(instruction_export)
    missing = sorted(set(FUNCTIONS) - set(rows))
    extra = sorted(set(rows) - set(FUNCTIONS))
    if missing or extra:
        raise ValueError(f"targeted instruction set drift: missing={missing} extra={extra}")

    analyses = [_analyze_function(address, rows[address]) for address in FUNCTIONS]
    by_function = {row["function"]: row for row in analyses}

    participant_to_vehicle = next(
        row for row in by_function[ACTUAL_PARTICIPANT]["direct_calls"]
        if row["callsite"] == "0x0072ed57" and row["callee"] == VEHICLE_CTOR
    )
    vehicle_to_base = next(
        row for row in by_function[VEHICLE_CTOR]["direct_calls"]
        if row["callsite"] == "0x0079c1e1" and row["callee"] == VEHICLE_BASE_CTOR
    )
    participant_vehicle_affine_ready = (
        participant_to_vehicle["ECX_origins_before_call"] == ["entry:ECX+0x340"]
    )
    vehicle_base_receiver_ready = (
        vehicle_to_base["ECX_origins_before_call"] == ["entry:ECX"]
    )

    direct_writers = [
        {"function": row["function"], **store}
        for row in analyses
        for store in row["target_store_candidates"]
        if store["target_is_current_function_entry_receiver"] is True
    ]
    same_receiver_forwards = [
        {"function": row["function"], **call}
        for row in analyses
        if row["function"] in {ACTUAL_PARTICIPANT, VEHICLE_CTOR, VEHICLE_BASE_CTOR}
        for call in row["direct_calls"]
        if call["ECX_is_current_function_entry_receiver"] is True
        and not (
            (row["function"] == VEHICLE_CTOR and call["callsite"] == "0x0079c1e1")
        )
    ]

    frontier_ready = participant_vehicle_affine_ready and vehicle_base_receiver_ready
    blockers: list[dict[str, Any]] = []
    if not participant_vehicle_affine_ready:
        blockers.append({
            "id": "actual-participant-to-embedded-vehicle-affine-receiver-unproven",
            "callsite": "0x0072ed57",
            "observed_origins": participant_to_vehicle["ECX_origins_before_call"],
            "required": "ECX == FUN_0072ed20 entry ECX + 0x340 on every reachable path",
        })
    if not vehicle_base_receiver_ready:
        blockers.append({
            "id": "embedded-vehicle-to-base-constructor-receiver-unproven",
            "callsite": "0x0079c1e1",
            "observed_origins": vehicle_to_base["ECX_origins_before_call"],
            "required": "ECX == FUN_0079c1c0 entry ECX on every reachable path",
        })
    if frontier_ready and not direct_writers:
        blockers.append({
            "id": "vehicle-plus-0x860-direct-writer-not-in-constructor-chain",
            "required": "expand only same-receiver forwarded callees emitted by this report",
            "candidate_count": len(same_receiver_forwards),
        })
    if direct_writers:
        blockers.append({
            "id": "vehicle-plus-0x860-writer-value-not-yet-numeric",
            "required": "evaluate only the reported writer dependency roots; do not assume zero",
            "writer_count": len(direct_writers),
        })

    return {
        "format": FORMAT,
        "version": 1,
        "ready": frontier_ready,
        "status": "writer-frontier-ready" if frontier_ready else "blocked",
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "instruction_export": str(instruction_export),
            "correction_format": correction.get("format"),
        },
        "retail": {
            "program": PROGRAM,
            "pe_md5": PE_MD5,
            "functions": retail_functions,
            "required_calls": [
                {"source": s, "instruction": i, "target": t, "role": r}
                for s, i, t, r in REQUIRED_CALLS
            ],
        },
        "object_relation": {
            "actual_participant_allocation_size": "0x2b90",
            "vehicle_embedded_offset": "0x340",
            "participant_target_offset": "0xba0",
            "vehicle_alias_target_offset": "0x860",
            "equation": "actual_participant+0xba0 == (actual_participant+0x340)+0x860",
            "participant_to_vehicle_callsite": participant_to_vehicle,
            "participant_to_vehicle_affine_receiver_ready": participant_vehicle_affine_ready,
            "vehicle_to_base_constructor_callsite": vehicle_to_base,
            "vehicle_to_base_receiver_ready": vehicle_base_receiver_ready,
        },
        "analysis": {
            "functions": analyses,
            "direct_target_writers": direct_writers,
            "direct_target_writer_count": len(direct_writers),
            "same_receiver_forward_worklist": same_receiver_forwards,
            "same_receiver_forward_worklist_count": len(same_receiver_forwards),
        },
        "handoff": {
            "actual_participant_to_vehicle_affine_receiver_ready": participant_vehicle_affine_ready,
            "vehicle_base_constructor_receiver_ready": vehicle_base_receiver_ready,
            "actual_additional_mass_writer_frontier_ready": frontier_ready,
            "actual_additional_mass_direct_writer_found": bool(direct_writers),
            "actual_additional_mass_numeric_value_ready": False,
            "offset33b_additional_mass_bootstrap_zero_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "next_proof": {
            "if_direct_writer_found": "evaluate the exact writer value dependency slice",
            "otherwise": "targeted instruction export of only same-receiver forwarded callees",
            "runtime_witness_required_yet": False,
        },
        "scope": {
            "manager_record_zero_assumption_reused": False,
            "callgraph_adjacency_used_as_value_proof": False,
            "source_object_alias_used_without_affine_receiver_proof": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze_bmw_offset33b_actual_additional_mass_writer_frontier(
            args.ghidra_export, args.instruction_export
        )
    except (OSError, ValueError, AssertionError) as exc:
        parser.error(str(exc))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
