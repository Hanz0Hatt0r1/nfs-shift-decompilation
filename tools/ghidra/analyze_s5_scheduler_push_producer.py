#!/usr/bin/env python3
"""Prove the exact local machine producer of the S5 scheduler stack argument.

Consumes the same targeted SHIFT.GhidraFunctionInstructions/2 export as the
scheduler accumulator proof plus positive parent reports.  It freezes the exact
PUSH feeding call 0x00715602 (FUN_007155e9 -> FUN_00715380), extracts the PUSH
STORE value from structured Ghidra p-code, and builds a conservative backward
value slice.

This layer proves only local machine-value provenance.  It does not name the
value as elapsed time, assign physical units, equate one invocation with one
rendered frame, or admit retail cadence.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_pose_writer_value_provenance as _values
import analyze_s5_scheduler_accumulator_slice as _surface
import analyze_s5_scheduler_accumulator_value_provenance as _accum_value

FORMAT = "SHIFT.SchedulerPushProducerValueProvenance/1"
SURFACE_FORMAT = _surface.FORMAT
ACCUM_VALUE_FORMAT = _accum_value.FORMAT
UPPER = _surface.UPPER
OWNER = _surface.OWNER
CALL_ADDRESS = _surface.UPPER_OWNER_CALL
_CONTROL_PCODE = {"CALL", "CALLIND", "BRANCH", "CBRANCH", "BRANCHIND", "RETURN"}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _validate_parents(
    surface_path: Path, value_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    surface = _load_json(surface_path)
    if surface.get("format") != SURFACE_FORMAT:
        raise ValueError(f"{surface_path}: expected {SURFACE_FORMAT}")
    if surface.get("ready") is not True:
        raise ValueError("scheduler accumulator producer frontier is not ready")

    calls = surface.get("exact_calls")
    edge = calls.get("FUN_007155e9_to_FUN_00715380") if isinstance(calls, Mapping) else None
    if not isinstance(edge, Mapping) or edge.get("verified") is not True:
        raise ValueError("exact FUN_007155e9 -> FUN_00715380 call is not positive")
    if edge.get("instruction") != _surface._hex(CALL_ADDRESS):
        raise ValueError("FUN_007155e9 -> FUN_00715380 callsite drift")

    argument = surface.get("upper_to_owner_argument")
    if not isinstance(argument, Mapping) or argument.get("proven") is not True:
        raise ValueError("FUN_007155e9 explicit stack-argument setup is not positive")
    if argument.get("status") != "single-explicit-stack-argument-push":
        raise ValueError("FUN_007155e9 argument setup is no longer a single PUSH")
    push_address = argument.get("instruction")
    operand = argument.get("operand")
    if not isinstance(push_address, str) or not isinstance(operand, str):
        raise ValueError("FUN_007155e9 PUSH address/operand missing")
    if argument.get("semantic_elapsed_value_proven") is not False:
        raise ValueError("parent frontier unexpectedly assigns elapsed-time semantics")

    value = _load_json(value_path)
    if value.get("format") != ACCUM_VALUE_FORMAT:
        raise ValueError(f"{value_path}: expected {ACCUM_VALUE_FORMAT}")
    if value.get("ready") is not True:
        raise ValueError("scheduler accumulator value provenance is not positive")
    handoff = value.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("scheduler accumulator value handoff missing")
    if handoff.get("FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven") is not True:
        raise ValueError("FUN_00715380 param1 -> +0x348 value dependency is not positive")
    if handoff.get("FUN_007155e9_argument_producer_proven") is not False:
        raise ValueError("parent value report unexpectedly preclaims PUSH producer")
    if handoff.get("retail_cadence_admitted") is not False:
        raise ValueError("parent value report unexpectedly admits retail cadence")

    return surface, value, dict(argument)


def _instruction_index(instructions: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, instruction in enumerate(instructions):
        address = instruction.get("address")
        if not isinstance(address, str):
            raise ValueError("instruction address missing")
        result[address.lower()] = index
    return result


def _control_barriers(
    instructions: list[dict[str, Any]], start_index: int, end_index: int
) -> list[dict[str, Any]]:
    barriers: list[dict[str, Any]] = []
    for instruction in instructions[start_index:end_index]:
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        opcodes = _surface._pcode_opcodes(instruction)
        hits = sorted(opcodes & _CONTROL_PCODE)
        textual = (
            mnemonic.startswith("J")
            or mnemonic.startswith("RET")
            or mnemonic.startswith("LOOP")
        )
        if hits or textual:
            barriers.append(
                {
                    "instruction": instruction.get("address"),
                    "instruction_text": instruction.get("text"),
                    "mnemonic": mnemonic,
                    "pcode_control_ops": hits,
                }
            )
    return barriers


def _push_value(
    instruction: Mapping[str, Any], expected_operand: str
) -> tuple[int, dict[str, Any]]:
    if str(instruction.get("mnemonic") or "").upper() != "PUSH":
        raise ValueError("frozen argument instruction is no longer PUSH")
    operands = instruction.get("operands")
    if not isinstance(operands, list) or operands != [expected_operand]:
        raise ValueError("frozen PUSH operand drift")
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError("PUSH p-code missing")
    stores: list[tuple[int, dict[str, Any]]] = []
    for index, operation in enumerate(pcode):
        if not isinstance(operation, dict):
            raise ValueError("malformed PUSH p-code operation")
        if str(operation.get("opcode") or "").upper() == "STORE":
            stores.append((index, operation))
    if len(stores) != 1:
        raise ValueError(
            f"PUSH must contain exactly one structured STORE; found {len(stores)}"
        )
    store_index, store = stores[0]
    inputs = store.get("inputs")
    if not isinstance(inputs, list) or len(inputs) < 3:
        raise ValueError("PUSH STORE value input missing")
    value = _values._validate_varnode(
        inputs[2], context=f"{instruction.get('address')}:{store_index}:PUSH STORE value"
    )
    return store_index, value


def _binding_definition(
    node_id: str,
    input_index: int,
    bindings: Mapping[str, list[dict[str, Any]]],
) -> str | None:
    rows = bindings.get(node_id)
    if not isinstance(rows, list):
        raise ValueError(f"{node_id}: p-code input bindings missing")
    row = next((item for item in rows if item.get("input_index") == input_index), None)
    if not isinstance(row, Mapping):
        raise ValueError(f"{node_id}: input[{input_index}] binding missing")
    definition = row.get("definition")
    if definition is not None and not isinstance(definition, str):
        raise ValueError(f"{node_id}: input[{input_index}] definition malformed")
    return definition


def _dependency_ids(root: str | None, edges: Mapping[str, list[str]]) -> set[str]:
    if root is None:
        return set()
    result: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in result:
            return
        result.add(node_id)
        for dependency in edges.get(node_id, []):
            visit(dependency)

    visit(root)
    return result


def analyze(
    instruction_export: Path,
    surface_path: Path,
    accumulator_value_path: Path,
) -> dict[str, Any]:
    surface, accumulator_value, parent_argument = _validate_parents(
        surface_path, accumulator_value_path
    )
    rows = _surface._instruction_rows(instruction_export)
    upper = rows[UPPER]
    instructions = upper["instructions"]
    call_index, call_instruction = _surface._find_exact_direct_call(
        upper, CALL_ADDRESS, OWNER
    )
    live_argument = _surface._argument_setup(upper, call_index)
    if live_argument.get("proven") is not True:
        raise ValueError("live instruction slice no longer proves explicit PUSH setup")
    for key in ("status", "instruction", "operand"):
        if live_argument.get(key) != parent_argument.get(key):
            raise ValueError(f"live PUSH setup drift for {key}")

    push_address = str(parent_argument["instruction"]).lower()
    indices = _instruction_index(instructions)
    push_index = indices.get(push_address)
    if push_index is None or push_index >= call_index:
        raise ValueError("frozen PUSH instruction missing before call")
    push_instruction = instructions[push_index]
    store_op_index, pushed_value = _push_value(
        push_instruction, str(parent_argument["operand"])
    )

    nodes, edges, bindings = _values._structured_pcode_graph(instructions)
    push_store_node = f"{push_address}:{store_op_index}"
    if push_store_node not in nodes:
        push_store_node = next(
            (
                key
                for key, node in nodes.items()
                if str(node.get("instruction") or "").lower() == push_address
                and node.get("opcode") == "STORE"
            ),
            push_store_node,
        )
    if push_store_node not in nodes:
        raise ValueError("PUSH STORE p-code node missing from structured graph")

    definition = _binding_definition(push_store_node, 2, bindings)
    slice_nodes, roots_raw = _values._slice_from_definition(
        definition if isinstance(definition, str) else None,
        pushed_value if definition is None else None,
        nodes,
        edges,
        bindings,
    )
    roots = [_values._classify_root(root) for root in roots_raw]
    dependency_ids = _dependency_ids(definition, edges)
    dependency_indices = [
        indices.get(str(nodes[node_id].get("instruction") or "").lower())
        for node_id in dependency_ids
        if node_id in nodes
    ]
    dependency_indices = [value for value in dependency_indices if isinstance(value, int)]
    start_index = min([push_index, *dependency_indices]) if dependency_indices else push_index
    barriers = _control_barriers(instructions, start_index, push_index)

    producer_node = nodes.get(definition) if isinstance(definition, str) else None
    producer_instruction = (
        producer_node.get("instruction") if isinstance(producer_node, Mapping) else push_address
    )
    direct_constant = (
        definition is None
        and (pushed_value.get("constant") is True or str(pushed_value.get("space") or "").lower() == "const")
    )
    local_machine_producer_proven = (
        not barriers
        and (
            isinstance(definition, str)
            and isinstance(producer_node, Mapping)
            or direct_constant
        )
    )

    semantic_root_blockers = [
        root for root in roots if root.get("semantic_join_required") is True
    ]
    scheduler_semantic_join_ready = local_machine_producer_proven and not semantic_root_blockers

    blockers: list[str] = []
    if not local_machine_producer_proven:
        blockers.append("FUN_007155e9-local-PUSH-machine-producer-not-proven")
    if barriers:
        blockers.append("FUN_007155e9-PUSH-provenance-crosses-control-barrier")
    if semantic_root_blockers:
        blockers.append("FUN_007155e9-PUSH-root-semantic-join-not-proven")
    blockers.extend(
        [
            "scheduler-push-value-physical-units-not-proven",
            "retail-cadence-dynamic-multiplicity-not-proven",
        ]
    )

    return {
        "format": FORMAT,
        "ready": local_machine_producer_proven,
        "status": "local-push-machine-producer-proven" if local_machine_producer_proven else "blocked",
        "inputs": {
            "instruction_export": str(instruction_export),
            "scheduler_accumulator_frontier": str(surface_path),
            "scheduler_accumulator_value_provenance": str(accumulator_value_path),
        },
        "callsite": {
            "caller": _surface._hex(UPPER),
            "callee": _surface._hex(OWNER),
            "call_instruction": call_instruction.get("address"),
            "push_instruction": parent_argument["instruction"],
            "push_operand": parent_argument["operand"],
        },
        "push_value": {
            "store_pcode_node": push_store_node,
            "store_value_varnode": dict(pushed_value),
            "store_value_definition": definition,
            "producer_instruction": producer_instruction,
            "dependency_slice": slice_nodes,
            "dependency_opcodes": sorted({str(row.get("opcode")) for row in slice_nodes}),
            "terminal_roots": roots,
            "terminal_root_kinds": sorted({str(row.get("root_kind")) for row in roots}),
            "control_barriers_to_push": barriers,
            "local_machine_producer_proven": local_machine_producer_proven,
            "scheduler_semantic_join_ready": scheduler_semantic_join_ready,
        },
        "blocking_reasons": sorted(set(blockers)),
        "next_exact_question": (
            "join the exact PUSH producer/root to the already-positive BManager/Physics Manager "
            "scheduler path; only after that independently prove physical time units and dynamic "
            "invocation multiplicity"
        ),
        "handoff": {
            "scheduler_accumulator_param1_dependency_proven": accumulator_value[
                "handoff"
            ]["FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven"],
            "FUN_007155e9_argument_machine_producer_proven": local_machine_producer_proven,
            "FUN_007155e9_argument_scheduler_semantic_join_ready": scheduler_semantic_join_ready,
            "scheduler_entry_elapsed_or_accumulator_input_proven": False,
            "retail_cadence_admitted": False,
        },
        "limits": {
            "machine_producer_is_elapsed_time_semantics": False,
            "physical_time_units_proven": False,
            "rendered_frame_equivalence_proven": False,
            "dynamic_invocation_multiplicity_proven": False,
            "host_fixed_step_substitution_allowed": False,
            "original_game_executed": False,
            "runtime_capture_used": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("scheduler_accumulator_frontier", type=Path)
    parser.add_argument("scheduler_accumulator_value_provenance", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze(
        args.instruction_export,
        args.scheduler_accumulator_frontier,
        args.scheduler_accumulator_value_provenance,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(
        "argument_machine_producer_proven: "
        f"{str(report['handoff']['FUN_007155e9_argument_machine_producer_proven']).lower()}"
    )
    print(
        "retail_cadence_admitted: "
        f"{str(report['handoff']['retail_cadence_admitted']).lower()}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
