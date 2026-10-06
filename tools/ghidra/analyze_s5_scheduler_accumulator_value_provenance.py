#!/usr/bin/env python3
"""Prove the local FUN_00715380 param_1 dependency of the +0x348 STORE.

This is the next finite S5 step after SHIFT.SchedulerAccumulatorProducerFrontier/1.
It reuses the same three-function SHIFT.GhidraFunctionInstructions/2 export and
requires the already-positive unique writer surface.  The proof is deliberately
narrow: the unique FUN_00715380 STORE value must have a structured p-code
backward dependency on a 4-byte RAM LOAD whose address reduces to function-entry
ESP + 4, matching the frozen __thiscall Stack[0x4]:4 float parameter.

The report proves a value dependency, not equality, physical time units, caller
producer semantics, or retail/render cadence.  Any CALL/control barrier in the
relevant local dependency segment keeps the result fail-closed.
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

FORMAT = "SHIFT.SchedulerAccumulatorValueProvenance/1"
SURFACE_FORMAT = _surface.FORMAT
OWNER = _surface.OWNER
ACCUMULATOR_DISPLACEMENT = _surface.ACCUMULATOR_DISPLACEMENT
PARAM_STACK_OFFSET = 0x4
PARAM_SIZE = 4
_EXPECTED_PARENT_BLOCKER = (
    "FUN_00715380-param1-to-this-plus-0x348-stored-value-provenance-not-proven"
)
_CONTROL_PCODE = {"CALL", "CALLIND", "BRANCH", "CBRANCH", "BRANCHIND", "RETURN"}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _validate_surface(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != SURFACE_FORMAT:
        raise ValueError(f"{path}: expected {SURFACE_FORMAT}")
    if report.get("ready") is not True:
        raise ValueError("scheduler accumulator writer surface is not ready")

    abi = report.get("abi")
    owner_abi = abi.get("owner") if isinstance(abi, Mapping) else None
    if not isinstance(owner_abi, Mapping):
        raise ValueError("writer surface owner ABI metadata missing")
    if owner_abi.get("address") != _surface._hex(OWNER):
        raise ValueError("writer surface owner address drift")
    if owner_abi.get("calling_convention") != "__thiscall":
        raise ValueError("FUN_00715380 calling convention drift")
    if owner_abi.get("explicit_argument_storage") != "Stack[0x4]:4":
        raise ValueError("FUN_00715380 explicit argument storage drift")
    if owner_abi.get("explicit_argument_type") != "float":
        raise ValueError("FUN_00715380 explicit argument type drift")

    accumulator = report.get("accumulator")
    if not isinstance(accumulator, Mapping):
        raise ValueError("writer surface accumulator section missing")
    if accumulator.get("displacement") != ACCUMULATOR_DISPLACEMENT:
        raise ValueError("writer surface accumulator displacement drift")
    if accumulator.get("unique_owner_writer_surface_proven") is not True:
        raise ValueError("writer surface lost unique FUN_00715380 writer")
    if accumulator.get("stored_value_from_FUN_00715380_param1_proven") is not False:
        raise ValueError("writer surface unexpectedly preclaims param1 value provenance")

    blockers = report.get("blocking_reasons")
    if not isinstance(blockers, list) or _EXPECTED_PARENT_BLOCKER not in blockers:
        raise ValueError("writer surface no longer exposes the expected param1 blocker")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping) or handoff.get(
        "scheduler_accumulator_writer_surface_ready"
    ) is not True:
        raise ValueError("writer surface handoff is not positive")
    if handoff.get("retail_cadence_admitted") is not False:
        raise ValueError("writer surface unexpectedly admits retail cadence")
    return report


def _varnode_int(value: Mapping[str, Any]) -> int | None:
    token = value.get("offset")
    if not isinstance(token, str):
        return None
    try:
        return int(token, 0)
    except ValueError:
        try:
            return int(token, 16)
        except ValueError:
            return None


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


def _unknown(reason: str, *, nodes: set[str] | None = None) -> dict[str, Any]:
    return {
        "kind": "unknown",
        "reason": reason,
        "definition_nodes": sorted(nodes or set()),
    }


def _constant(value: int, nodes: set[str] | None = None) -> dict[str, Any]:
    return {
        "kind": "constant",
        "value": value,
        "definition_nodes": sorted(nodes or set()),
    }


def _affine(register: str, offset: int, nodes: set[str] | None = None) -> dict[str, Any]:
    return {
        "kind": "entry-register-plus-constant",
        "entry_register": register,
        "offset": offset,
        "offset_hex": f"-0x{-offset:x}" if offset < 0 else f"0x{offset:x}",
        "definition_nodes": sorted(nodes or set()),
    }


def _node_set(*values: Mapping[str, Any], extra: str | None = None) -> set[str]:
    result: set[str] = set()
    for value in values:
        raw = value.get("definition_nodes")
        if isinstance(raw, list):
            result.update(item for item in raw if isinstance(item, str))
    if extra is not None:
        result.add(extra)
    return result


def _add(left: Mapping[str, Any], right: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    nodes = _node_set(left, right, extra=node_id)
    if left.get("kind") == "constant" and right.get("kind") == "constant":
        return _constant(int(left["value"]) + int(right["value"]), nodes)
    if left.get("kind") == "entry-register-plus-constant" and right.get("kind") == "constant":
        return _affine(str(left["entry_register"]), int(left["offset"]) + int(right["value"]), nodes)
    if right.get("kind") == "entry-register-plus-constant" and left.get("kind") == "constant":
        return _affine(str(right["entry_register"]), int(right["offset"]) + int(left["value"]), nodes)
    return _unknown("unsupported-add-shape", nodes=nodes)


def _sub(left: Mapping[str, Any], right: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    nodes = _node_set(left, right, extra=node_id)
    if left.get("kind") == "constant" and right.get("kind") == "constant":
        return _constant(int(left["value"]) - int(right["value"]), nodes)
    if left.get("kind") == "entry-register-plus-constant" and right.get("kind") == "constant":
        return _affine(str(left["entry_register"]), int(left["offset"]) - int(right["value"]), nodes)
    return _unknown("unsupported-sub-shape", nodes=nodes)


def _mul(left: Mapping[str, Any], right: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    nodes = _node_set(left, right, extra=node_id)
    if left.get("kind") == "constant" and right.get("kind") == "constant":
        return _constant(int(left["value"]) * int(right["value"]), nodes)
    return _unknown("unsupported-multiply-shape", nodes=nodes)


def _eval_affine(
    value: Mapping[str, Any],
    definition: str | None,
    nodes: Mapping[str, dict[str, Any]],
    bindings: Mapping[str, list[dict[str, Any]]],
    *,
    seen: set[str] | None = None,
    depth: int = 0,
) -> dict[str, Any]:
    if depth > 32:
        return _unknown("affine-depth-limit")
    if definition is None:
        if value.get("constant") is True or str(value.get("space") or "").lower() == "const":
            integer = _varnode_int(value)
            return _constant(integer) if integer is not None else _unknown("invalid-constant-varnode")
        text = str(value.get("text") or "").upper()
        if value.get("register") is True or str(value.get("space") or "").lower() == "register":
            register = _surface._canonical_register(text)
            if register is not None:
                return _affine(register, 0)
        return _unknown("unresolved-nonconstant-root")

    seen = set() if seen is None else set(seen)
    if definition in seen:
        return _unknown("affine-definition-cycle", nodes={definition})
    seen.add(definition)
    node = nodes.get(definition)
    if not isinstance(node, Mapping):
        return _unknown("missing-affine-definition-node", nodes={definition})
    opcode = str(node.get("opcode") or "").upper()
    inputs = node.get("inputs")
    if not isinstance(inputs, list):
        return _unknown("affine-definition-inputs-missing", nodes={definition})

    def evaluate(index: int) -> dict[str, Any]:
        if index >= len(inputs) or not isinstance(inputs[index], Mapping):
            return _unknown("affine-input-missing", nodes={definition})
        return _eval_affine(
            inputs[index],
            _binding_definition(definition, index, bindings),
            nodes,
            bindings,
            seen=seen,
            depth=depth + 1,
        )

    if opcode in {"COPY", "CAST", "INT_ZEXT", "INT_SEXT"}:
        result = evaluate(0)
        result = dict(result)
        result["definition_nodes"] = sorted(_node_set(result, extra=definition))
        return result
    if opcode == "INT_ADD":
        return _add(evaluate(0), evaluate(1), definition)
    if opcode == "INT_SUB":
        return _sub(evaluate(0), evaluate(1), definition)
    if opcode == "PTRSUB":
        return _add(evaluate(0), evaluate(1), definition)
    if opcode == "INT_MULT":
        return _mul(evaluate(0), evaluate(1), definition)
    if opcode == "PTRADD":
        base = evaluate(0)
        index = evaluate(1)
        scale = evaluate(2)
        scaled = _mul(index, scale, definition)
        return _add(base, scaled, definition)
    return _unknown(f"unsupported-affine-opcode:{opcode}", nodes={definition})


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


def _instruction_index(instructions: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, instruction in enumerate(instructions):
        address = instruction.get("address")
        if not isinstance(address, str):
            raise ValueError("instruction address missing")
        result[address.lower()] = index
    return result


def _control_barriers(
    instructions: list[dict[str, Any]],
    start_index: int,
    end_index: int,
) -> list[dict[str, Any]]:
    barriers: list[dict[str, Any]] = []
    for instruction in instructions[start_index:end_index]:
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        opcodes = _surface._pcode_opcodes(instruction)
        hits = sorted(opcodes & _CONTROL_PCODE)
        textual = mnemonic.startswith("J") or mnemonic.startswith("RET") or mnemonic.startswith("LOOP")
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


def _stack_parameter_loads(
    instructions: list[dict[str, Any]],
    store_address: str,
    dependency_ids: set[str],
    nodes: Mapping[str, dict[str, Any]],
    bindings: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    indices = _instruction_index(instructions)
    store_index = indices.get(store_address.lower())
    if store_index is None:
        raise ValueError("writer STORE instruction missing from owner instruction row")

    result: list[dict[str, Any]] = []
    for node_id in sorted(dependency_ids):
        node = nodes.get(node_id)
        if not isinstance(node, Mapping) or str(node.get("opcode") or "").upper() != "LOAD":
            continue
        inputs = node.get("inputs")
        output = node.get("output")
        if not isinstance(inputs, list) or len(inputs) < 2 or not isinstance(inputs[1], Mapping):
            continue
        if not isinstance(output, Mapping):
            continue
        address = str(node.get("instruction") or "").lower()
        load_index = indices.get(address)
        if load_index is None or load_index > store_index:
            continue

        space = inputs[0] if isinstance(inputs[0], Mapping) else {}
        is_ram = str(space.get("text") or "").upper() == "RAM"
        affine = _eval_affine(
            inputs[1],
            _binding_definition(node_id, 1, bindings),
            nodes,
            bindings,
        )
        definition_indices = [
            indices.get(str(nodes[item].get("instruction") or "").lower())
            for item in affine.get("definition_nodes", [])
            if item in nodes
        ]
        definition_indices = [item for item in definition_indices if isinstance(item, int)]
        segment_start = min([load_index, *definition_indices]) if definition_indices else load_index
        barriers = _control_barriers(instructions, segment_start, store_index)
        width = output.get("size")
        exact_slot = (
            is_ram
            and width == PARAM_SIZE
            and affine.get("kind") == "entry-register-plus-constant"
            and affine.get("entry_register") == "ESP"
            and affine.get("offset") == PARAM_STACK_OFFSET
        )
        result.append(
            {
                "pcode_node": node_id,
                "instruction": node.get("instruction"),
                "pcode_text": node.get("text"),
                "load_width": width,
                "ram_space": is_ram,
                "address_expression": affine,
                "matches_entry_Stack_0x4_size4": exact_slot,
                "control_barriers_to_store": barriers,
                "dependency_to_store_proven": exact_slot and not barriers,
            }
        )
    return result


def _writer_surface(report: Mapping[str, Any]) -> dict[str, Any]:
    accumulator = report["accumulator"]
    owner_accesses = accumulator.get("owner_accesses")
    if not isinstance(owner_accesses, list):
        raise ValueError("writer surface owner_accesses missing")
    writers = [
        row
        for row in owner_accesses
        if isinstance(row, Mapping)
        and row.get("this_relative_access_proven") is True
        and row.get("access") in {"write", "read-write"}
    ]
    if len(writers) != 1:
        raise ValueError("writer surface no longer has exactly one proven owner writer")
    return dict(writers[0])


def analyze(instruction_export: Path, writer_surface_path: Path) -> dict[str, Any]:
    surface = _validate_surface(writer_surface_path)
    rows = _surface._instruction_rows(instruction_export)
    owner_row = rows[OWNER]
    instructions = owner_row["instructions"]
    writer = _writer_surface(surface)
    store_address = writer.get("instruction")
    if not isinstance(store_address, str):
        raise ValueError("writer surface instruction address missing")

    instruction = next(
        (
            item
            for item in instructions
            if isinstance(item, Mapping)
            and str(item.get("address") or "").lower() == store_address.lower()
        ),
        None,
    )
    if not isinstance(instruction, Mapping):
        raise ValueError("writer surface instruction not present in targeted export")
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError(f"{store_address}: pcode missing")
    store_ops = [
        (index, operation)
        for index, operation in enumerate(pcode)
        if isinstance(operation, Mapping)
        and str(operation.get("opcode") or "").upper() == "STORE"
    ]

    blockers: list[str] = []
    if len(store_ops) != 1:
        blockers.append("unique-writer-instruction-does-not-have-exactly-one-structured-STORE")
        value_slice = None
        loads: list[dict[str, Any]] = []
    else:
        store_index, store_op = store_ops[0]
        inputs = store_op.get("inputs")
        if not isinstance(inputs, list) or len(inputs) < 3:
            raise ValueError(f"{store_address}:{store_index}: STORE value input missing")
        value_varnode = _values._validate_varnode(
            inputs[2], context=f"{store_address}:{store_index}:STORE value"
        )
        nodes, edges, bindings = _values._structured_pcode_graph(instructions)
        store_node = f"{store_address.lower()}:{store_index}"
        if store_node not in nodes:
            # _values normalizes instruction addresses; tolerate canonical string
            store_node = next(
                (
                    key
                    for key, node in nodes.items()
                    if str(node.get("instruction") or "").lower() == store_address.lower()
                    and node.get("opcode") == "STORE"
                ),
                store_node,
            )
        definition = _binding_definition(store_node, 2, bindings)
        slice_nodes, roots_raw = _values._slice_from_definition(
            definition if isinstance(definition, str) else None,
            value_varnode if definition is None else None,
            nodes,
            edges,
            bindings,
        )
        roots = [_values._classify_root(root) for root in roots_raw]
        dependency_ids = _dependency_ids(definition, edges)
        loads = _stack_parameter_loads(
            instructions,
            store_address,
            dependency_ids,
            nodes,
            bindings,
        )
        value_slice = {
            "store_pcode_node": store_node,
            "store_value_varnode": dict(value_varnode),
            "store_value_definition": definition,
            "dependency_slice": slice_nodes,
            "dependency_opcodes": sorted({row["opcode"] for row in slice_nodes}),
            "terminal_roots": roots,
            "terminal_root_kinds": sorted({str(row.get("root_kind")) for row in roots}),
        }

    proven_loads = [row for row in loads if row.get("dependency_to_store_proven") is True]
    dependency_proven = len(proven_loads) >= 1
    if not dependency_proven:
        blockers.append("FUN_00715380-Stack-0x4-param1-dependency-to-plus-0x348-STORE-not-proven")

    # This layer intentionally does not prove the pushed value producer in
    # FUN_007155e9, physical time units, equality with param_1, or cadence.
    blockers.extend(
        [
            "FUN_007155e9-pushed-value-producer-not-proven",
            "scheduler-accumulator-physical-units-not-proven",
            "retail-cadence-dynamic-multiplicity-not-proven",
        ]
    )

    return {
        "format": FORMAT,
        "ready": dependency_proven,
        "status": "owner-param1-dependency-proven" if dependency_proven else "blocked",
        "inputs": {
            "instruction_export": str(instruction_export),
            "writer_surface": str(writer_surface_path),
        },
        "owner": {
            "address": _surface._hex(OWNER),
            "name": "FUN_00715380",
            "explicit_parameter": {
                "name": "param_1",
                "type": "float",
                "storage": "Stack[0x4]:4",
                "entry_esp_byte_offset": PARAM_STACK_OFFSET,
                "size": PARAM_SIZE,
            },
        },
        "writer": writer,
        "value_slice": value_slice,
        "stack_parameter_load_candidates": loads,
        "proven_stack_parameter_dependency_count": len(proven_loads),
        "stored_value_depends_on_FUN_00715380_param1_proven": dependency_proven,
        "stored_value_equals_FUN_00715380_param1_proven": False,
        "blocking_reasons": sorted(set(blockers)),
        "next_exact_question": (
            "trace the PUSH operand feeding 0x00715602 in FUN_007155e9 backward to its "
            "exact local producer, then join that producer to the already-proven "
            "BManager/Physics Manager scheduler path without naming physical time units"
        ),
        "handoff": {
            "scheduler_accumulator_writer_surface_ready": True,
            "FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven": dependency_proven,
            "FUN_007155e9_argument_producer_proven": False,
            "scheduler_entry_elapsed_or_accumulator_input_proven": False,
            "retail_cadence_admitted": False,
        },
        "limits": {
            "value_dependency_is_value_equality": False,
            "x87_or_SSE_transform_semantics_promoted": False,
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
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze(args.instruction_export, args.writer_surface)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(
        "param1_dependency_proven: "
        f"{str(report['handoff']['FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven']).lower()}"
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
