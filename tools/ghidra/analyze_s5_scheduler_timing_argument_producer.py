#!/usr/bin/env python3
"""Build the exact local producer frontier for the S5 timing argument.

This is the next finite static step after
SHIFT.SchedulerAccumulatorValueProvenance/1.  It reuses the same exact
three-function SHIFT.GhidraFunctionInstructions/2 export and traces the machine
value pushed by FUN_007155e9 into the direct FUN_00715380 call at 0x00715602.

The report proves only a structured local value slice and its terminal machine
roots.  It does not name the value as elapsed seconds, assign physical units,
prove BManager/controller ownership of the roots, or admit retail cadence.
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
import analyze_s5_scheduler_accumulator_value_provenance as _accum

FORMAT = "SHIFT.SchedulerTimingArgumentProducerFrontier/1"
INSTRUCTION_FORMAT = _surface.INSTRUCTION_FORMAT
SURFACE_FORMAT = _surface.FORMAT
VALUE_FORMAT = _accum.FORMAT
UPPER = _surface.UPPER
OWNER = _surface.OWNER
CALL_ADDRESS = _surface.UPPER_OWNER_CALL
_CONTROL_PCODE = {"CALL", "CALLIND", "BRANCH", "CBRANCH", "BRANCHIND", "RETURN"}


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _validate_surface(path: Path) -> dict[str, Any]:
    report = _load_json(path, SURFACE_FORMAT)
    if report.get("ready") is not True:
        raise ValueError("scheduler accumulator writer surface is not ready")
    exact = report.get("exact_calls")
    edge = exact.get("FUN_007155e9_to_FUN_00715380") if isinstance(exact, Mapping) else None
    if not isinstance(edge, Mapping):
        raise ValueError("writer surface direct call metadata missing")
    if _surface._norm(edge.get("instruction")) != CALL_ADDRESS or edge.get("verified") is not True:
        raise ValueError("writer surface direct callsite drift")
    argument = report.get("upper_to_owner_argument")
    if not isinstance(argument, Mapping) or argument.get("proven") is not True:
        raise ValueError("writer surface explicit argument setup is not positive")
    instruction = _surface._norm(argument.get("instruction"))
    operand = argument.get("operand")
    if instruction is None or not isinstance(operand, str) or not operand.strip():
        raise ValueError("writer surface argument PUSH metadata missing")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping) or handoff.get("retail_cadence_admitted") is not False:
        raise ValueError("writer surface unexpectedly admits retail cadence")
    return report


def _validate_value_provenance(path: Path) -> dict[str, Any]:
    report = _load_json(path, VALUE_FORMAT)
    if report.get("ready") is not True:
        raise ValueError("scheduler accumulator param1 value provenance is not ready")
    if report.get("stored_value_depends_on_FUN_00715380_param1_proven") is not True:
        raise ValueError("FUN_00715380 param1 dependency is not positive")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("value provenance handoff missing")
    if handoff.get("FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven") is not True:
        raise ValueError("value provenance handoff lost the param1 dependency")
    if handoff.get("FUN_007155e9_argument_producer_proven") is not False:
        raise ValueError("value provenance unexpectedly preclaims the upper argument producer")
    if handoff.get("retail_cadence_admitted") is not False:
        raise ValueError("value provenance unexpectedly admits retail cadence")
    return report


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


def _instruction_indices(instructions: list[dict[str, Any]]) -> dict[str, int]:
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
    result: list[dict[str, Any]] = []
    for instruction in instructions[start_index:end_index]:
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        opcodes = _surface._pcode_opcodes(instruction)
        hits = sorted(opcodes & _CONTROL_PCODE)
        textual = mnemonic.startswith("J") or mnemonic.startswith("RET") or mnemonic.startswith("LOOP")
        if hits or textual:
            result.append(
                {
                    "instruction": instruction.get("address"),
                    "instruction_text": instruction.get("text"),
                    "mnemonic": mnemonic,
                    "pcode_control_ops": hits,
                }
            )
    return result


def _find_push(
    row: dict[str, Any], surface: Mapping[str, Any], call_index: int
) -> tuple[int, dict[str, Any]]:
    argument = surface["upper_to_owner_argument"]
    expected_address = _surface._norm(argument.get("instruction"))
    expected_operand = str(argument.get("operand"))
    matches: list[tuple[int, dict[str, Any]]] = []
    for index, instruction in enumerate(row["instructions"][:call_index]):
        if _surface._norm(instruction.get("address")) != expected_address:
            continue
        if str(instruction.get("mnemonic") or "").upper() != "PUSH":
            continue
        operands = instruction.get("operands")
        if not isinstance(operands, list) or len(operands) != 1:
            continue
        if operands[0] != expected_operand:
            continue
        matches.append((index, instruction))
    if len(matches) != 1:
        raise ValueError(
            f"expected one exact argument PUSH before {_surface._hex(CALL_ADDRESS)}, found {len(matches)}"
        )
    return matches[0]


def _push_store_node(
    instruction: Mapping[str, Any], nodes: Mapping[str, dict[str, Any]]
) -> str | None:
    address = str(instruction.get("address") or "").lower()
    matches = [
        node_id
        for node_id, node in nodes.items()
        if str(node.get("instruction") or "").lower() == address
        and str(node.get("opcode") or "").upper() == "STORE"
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _slice_start_index(
    slice_nodes: list[dict[str, Any]], indices: Mapping[str, int], fallback: int
) -> int:
    found = [
        indices.get(str(node.get("instruction") or "").lower())
        for node in slice_nodes
    ]
    found = [value for value in found if isinstance(value, int)]
    return min(found) if found else fallback


def analyze(
    instruction_export: Path,
    writer_surface_path: Path,
    value_provenance_path: Path,
) -> dict[str, Any]:
    surface = _validate_surface(writer_surface_path)
    _validate_value_provenance(value_provenance_path)

    rows = _surface._instruction_rows(instruction_export)
    upper = rows[UPPER]
    instructions = upper["instructions"]
    call_index, call = _surface._find_exact_direct_call(
        upper, CALL_ADDRESS, OWNER
    )
    push_index, push = _find_push(upper, surface, call_index)

    nodes, edges, bindings = _values._structured_pcode_graph(instructions)
    push_store = _push_store_node(push, nodes)
    blockers: list[str] = []
    value_slice = None
    roots: list[dict[str, Any]] = []
    barriers: list[dict[str, Any]] = []

    if push_store is None:
        blockers.append("argument-PUSH-does-not-have-exactly-one-structured-STORE")
    else:
        node = nodes[push_store]
        inputs = node.get("inputs")
        if not isinstance(inputs, list) or len(inputs) < 3 or not isinstance(inputs[2], Mapping):
            raise ValueError(f"{push_store}: PUSH STORE value input missing")
        value_varnode = _values._validate_varnode(
            inputs[2], context=f"{push_store}:PUSH STORE value"
        )
        definition = _binding_definition(push_store, 2, bindings)
        slice_nodes, roots_raw = _values._slice_from_definition(
            definition,
            value_varnode if definition is None else None,
            nodes,
            edges,
            bindings,
        )
        roots = [_values._classify_root(root) for root in roots_raw]
        indices = _instruction_indices(instructions)
        start_index = _slice_start_index(slice_nodes, indices, push_index)
        barriers = _control_barriers(instructions, start_index, push_index)
        if barriers:
            blockers.append("control-barrier-inside-upper-argument-value-slice")
        value_slice = {
            "push_pcode_store_node": push_store,
            "push_value_varnode": dict(value_varnode),
            "push_value_definition": definition,
            "dependency_slice": slice_nodes,
            "dependency_opcodes": sorted({str(item.get("opcode")) for item in slice_nodes}),
            "terminal_roots": roots,
            "terminal_root_kinds": sorted({str(item.get("root_kind")) for item in roots}),
            "control_barriers_before_push": barriers,
        }

    slice_ready = push_store is not None and value_slice is not None and not barriers
    if not slice_ready:
        blockers.append("FUN_007155e9-pushed-value-local-provenance-slice-not-proven")

    blockers.extend(
        [
            "timing-value-semantic-source-owner-not-proven",
            "scheduler-accumulator-physical-units-not-proven",
            "retail-cadence-dynamic-multiplicity-not-proven",
        ]
    )

    return {
        "format": FORMAT,
        "ready": slice_ready,
        "status": "upper-argument-value-slice-ready" if slice_ready else "blocked",
        "inputs": {
            "instruction_export": str(instruction_export),
            "writer_surface": str(writer_surface_path),
            "value_provenance": str(value_provenance_path),
        },
        "callsite": {
            "caller": _surface._hex(UPPER),
            "callee": _surface._hex(OWNER),
            "instruction": call.get("address"),
        },
        "argument_push": {
            "instruction": push.get("address"),
            "instruction_text": push.get("text"),
            "operand": push.get("operands", [None])[0],
            "surface_proven": True,
        },
        "value_slice": value_slice,
        "terminal_root_count": len(roots),
        "blocking_reasons": sorted(set(blockers)),
        "next_exact_question": (
            "join the terminal machine roots of the FUN_007155e9 argument value slice to "
            "the already-proven BManager/Physics Manager scheduler path and prove physical "
            "time units/dynamic multiplicity without rendered-frame or host-cadence substitution"
        ),
        "handoff": {
            "FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven": True,
            "FUN_007155e9_argument_value_slice_ready": slice_ready,
            "FUN_007155e9_argument_producer_semantics_proven": False,
            "scheduler_entry_elapsed_or_accumulator_input_proven": False,
            "retail_cadence_admitted": False,
        },
        "limits": {
            "terminal_machine_root_is_semantic_time_source": False,
            "physical_time_units_proven": False,
            "rendered_frame_equivalence_proven": False,
            "host_fixed_step_substitution_allowed": False,
            "original_game_executed": False,
            "runtime_capture_used": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("writer_surface", type=Path)
    parser.add_argument("value_provenance", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze(
        args.instruction_export,
        args.writer_surface,
        args.value_provenance,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(
        "argument_value_slice_ready: "
        f"{str(report['handoff']['FUN_007155e9_argument_value_slice_ready']).lower()}"
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
