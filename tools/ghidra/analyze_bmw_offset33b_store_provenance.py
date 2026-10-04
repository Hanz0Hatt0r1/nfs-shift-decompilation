#!/usr/bin/env python3
"""Bound the exact machine stores that produce the symbolic BMW offset33b state.

The already-merged ``SHIFT.BMWBody0VehicleRootBindRelation/1`` proves that the
BODY0-local -> outer-Vehicle-root bind relation has identity rotation and
translation ``-offset33b`` where ``offset33b`` is the three-double HDVehicle
state at +0x33b0/+0x33b8/+0x33c0.  It deliberately leaves the BMW numeric
values unknown.

This analyzer consumes one targeted ``SHIFT.GhidraFunctionInstructions/2`` row
for the source-backed producer ``FUN_0076b280``.  It finds p-code STOREs whose
simple register-relative target overlaps the three offset33b fields, proves the
all-path origin of each target base register, and builds a backward p-code slice
for each stored value.  It is a finite static frontier, not a numeric-value
proof: constant/memory/register roots are reported without inventing SDF field
semantics, CALL return values, x87 state, or values across unresolved CFG joins.
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

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite
import analyze_bmw_body0_bind_pose_writer_value_provenance as _values
import analyze_register_relative_accesses as _access

FORMAT = "SHIFT.BMWOffset33bStoreProvenance/1"
RELATION_FORMAT = "SHIFT.BMWBody0VehicleRootBindRelation/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
TARGET = "0x0076b280"
TARGET_NAME = "FUN_0076b280"
TARGET_SIZE = 7796
TARGET_CALLING_CONVENTION = "__thiscall"
TARGET_MNEMONIC_SHA256 = "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6"
FIELD_SIZE = 8
FIELDS = (
    (0x33B0, "offset33b.x"),
    (0x33B8, "offset33b.y"),
    (0x33C0, "offset33b.z"),
)
REQUIRED_BYTES = frozenset(
    byte for offset, _ in FIELDS for byte in range(offset, offset + FIELD_SIZE)
)
DEFAULT_RELATION = Path(__file__).resolve().parents[2] / "evidence" / "bmw_body0_vehicle_root_bind_relation.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
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
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _validate_relation(path: Path) -> dict[str, Any]:
    relation = _read_json(path)
    if relation.get("format") != RELATION_FORMAT:
        raise ValueError(f"{path}: expected {RELATION_FORMAT}")
    if relation.get("ready") is not True:
        raise ValueError("BODY0/Vehicle-root symbolic relation is not ready")
    gates = relation.get("gates")
    if not isinstance(gates, Mapping):
        raise ValueError("BODY0/Vehicle-root relation gates missing")
    if gates.get("BODY0_to_outer_vehicle_root_translation_symbolic_ready") is not True:
        raise ValueError("symbolic offset33b translation is not ready")
    if gates.get("BMW_numeric_offset33b_ready") is not False:
        raise ValueError("relation unexpectedly preclaims BMW numeric offset33b")
    symbolic = relation.get("symbolic_bind_relation")
    if not isinstance(symbolic, Mapping):
        raise ValueError("symbolic bind relation missing")
    expected = ["-HDVehicle[0x33b0]", "-HDVehicle[0x33b8]", "-HDVehicle[0x33c0]"]
    if symbolic.get("translation") != expected:
        raise ValueError("symbolic offset33b field relation drift")
    retail = relation.get("retail")
    functions = retail.get("functions") if isinstance(retail, Mapping) else None
    if not isinstance(functions, list):
        raise ValueError("relation retail function inventory missing")
    hit = next(
        (
            row
            for row in functions
            if isinstance(row, Mapping)
            and str(row.get("address") or "").lower() == TARGET
        ),
        None,
    )
    if not isinstance(hit, Mapping) or hit.get("mnemonic_sha256") != TARGET_MNEMONIC_SHA256:
        raise ValueError("relation FUN_0076b280 producer anchor drift")
    return relation


def _validate_retail_function(root: Path) -> dict[str, Any]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")

    hits: list[dict[str, Any]] = []
    for row in _read_jsonl(root / "functions.jsonl"):
        if str(row.get("address") or "").lower() == TARGET:
            hits.append(row)
    if len(hits) != 1:
        raise ValueError(f"expected exactly one {TARGET} function row; found {len(hits)}")
    row = hits[0]
    if row.get("name") != TARGET_NAME:
        raise ValueError("FUN_0076b280 name drift")
    if int(row.get("size", -1)) != TARGET_SIZE:
        raise ValueError("FUN_0076b280 size drift")
    if row.get("calling_convention") != TARGET_CALLING_CONVENTION:
        raise ValueError("FUN_0076b280 calling convention drift")
    if row.get("mnemonic_sha256") != TARGET_MNEMONIC_SHA256:
        raise ValueError("FUN_0076b280 mnemonic fingerprint drift")
    if row.get("external") is True or row.get("thunk") is True:
        raise ValueError("FUN_0076b280 must be a concrete retail function")
    return row


def _load_instruction_row(path: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(path)
    if len(rows) != 1:
        raise ValueError(f"{path}: expected one targeted instruction row; found {len(rows)}")
    row = rows[0]
    if row.get("format") != INSTRUCTION_FORMAT:
        raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
    address, instructions = _callsite._validate_instruction_row(row, path)
    if address != TARGET:
        raise ValueError(f"{path}: expected exact {TARGET} instruction row")
    function = row.get("function") or {}
    if function.get("name") != TARGET_NAME:
        raise ValueError("targeted instruction function name drift")
    return instructions


def _store_ops(instruction: Mapping[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError("instruction pcode missing")
    result: list[tuple[int, dict[str, Any]]] = []
    for index, raw in enumerate(pcode):
        if not isinstance(raw, dict):
            raise ValueError("pcode operation must be an object")
        if str(raw.get("opcode") or "").upper() == "STORE":
            result.append((index, raw))
    return result


def _simple_memory_operands(
    instruction: Mapping[str, Any],
) -> list[tuple[int, str, tuple[str, int] | None]]:
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError("instruction operands must be strings")
    return [
        (index, operand, _access._parse_memory_operand(operand))
        for index, operand in enumerate(operands)
        if "[" in operand or "]" in operand
    ]


def _touched_required_bytes(displacement: int, width: int) -> list[int]:
    return sorted(set(range(displacement, displacement + width)) & set(REQUIRED_BYTES))


def _field_labels(touched: list[int]) -> list[str]:
    values = set(touched)
    return [
        label
        for offset, label in FIELDS
        if values & set(range(offset, offset + FIELD_SIZE))
    ]


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
    rows = bindings.get(node_id)
    if not isinstance(rows, list):
        raise ValueError(f"{node_id}: STORE bindings missing")
    binding = next((row for row in rows if row.get("input_index") == 2), None)
    if not isinstance(binding, dict):
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
    opcodes = sorted({str(row.get("opcode") or "") for row in slice_nodes})
    return {
        "store_value_varnode": dict(value),
        "store_value_definition": definition,
        "dependency_slice": slice_nodes,
        "dependency_opcodes": opcodes,
        "terminal_roots": roots,
        "terminal_root_kinds": sorted({str(root.get("root_kind")) for root in roots}),
        "value_slice_constant_only": bool(roots)
        and all(root.get("semantic_join_required") is False for root in roots),
        "value_semantics_proven": False,
        "numeric_value_proven": False,
    }


def analyze_bmw_offset33b_store_provenance(
    ghidra_export: Path,
    instruction_export: Path,
    relation_path: Path = DEFAULT_RELATION,
) -> dict[str, Any]:
    relation = _validate_relation(relation_path)
    function = _validate_retail_function(ghidra_export)
    instructions = _load_instruction_row(instruction_export)

    incoming, iterations = _callsite._analyze_incoming_states(instructions)
    nodes, edges, bindings = _values._structured_pcode_graph(instructions)

    candidates: list[dict[str, Any]] = []
    structural_blockers: list[dict[str, Any]] = []
    coverage_from_entry_receiver: set[int] = set()

    for instruction in instructions:
        stores = _store_ops(instruction)
        if not stores:
            continue
        address = _callsite._address(instruction.get("address"), field="instruction.address")
        memory = _simple_memory_operands(instruction)
        parsed = [row for row in memory if row[2] is not None]
        suspicious_unparsed = [
            row
            for row in memory
            if row[2] is None
            and any(token in row[1].lower() for token in ("33b0", "33b8", "33c0", "c16ab0", "c16ab8", "c16ac0"))
        ]
        if suspicious_unparsed:
            structural_blockers.append(
                {
                    "instruction": address,
                    "reason": "offset33b-looking memory operand is not a simple register-relative operand",
                    "operands": [row[1] for row in suspicious_unparsed],
                }
            )
        if len(stores) != 1 or len(parsed) != 1:
            continue

        op_index, operation = stores[0]
        inputs = operation.get("inputs")
        if not isinstance(inputs, list) or len(inputs) < 3 or not isinstance(inputs[2], Mapping):
            raise ValueError(f"{address}:{op_index}: STORE value input missing")
        width = inputs[2].get("size")
        if not isinstance(width, int) or width <= 0:
            raise ValueError(f"{address}:{op_index}: STORE width invalid")

        operand_index, operand, parsed_memory = parsed[0]
        assert parsed_memory is not None
        base_register, displacement = parsed_memory
        touched = _touched_required_bytes(displacement, width)
        if not touched:
            continue

        state = incoming.get(address)
        origins: list[str] = []
        if state is not None and base_register in state:
            origins = _callsite._register_engine._sorted_origins(state[base_register])
        flags = _callsite._origin_flags(origins) if origins else {
            "origin_count": 0,
            "exact_single_origin": False,
            "contains_unknown_or_derived": True,
            "contains_memory_origin": False,
            "contains_entry_origin": False,
        }
        exact_entry_receiver = (
            origins == ["entry:ECX"]
            and flags.get("exact_single_origin") is True
            and flags.get("contains_unknown_or_derived") is False
        )
        if exact_entry_receiver:
            coverage_from_entry_receiver.update(touched)

        direct_calls = _values._direct_calls_before(instructions, address)
        value = _value_slice(address, op_index, operation, nodes, edges, bindings)
        candidates.append(
            {
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "operand_index": operand_index,
                "operand": operand,
                "base_register": base_register,
                "base_register_origins": origins,
                "base_register_origin_flags": flags,
                "target_is_FUN_0076b280_entry_ECX_on_all_reachable_paths": exact_entry_receiver,
                "displacement": displacement,
                "displacement_hex": f"0x{displacement:x}",
                "store_width": width,
                "required_bytes_touched": touched,
                "offset33b_fields_touched": _field_labels(touched),
                "pcode_store_proven": True,
                "recent_direct_calls_before_store": direct_calls[-8:],
                **value,
                "HDVehicle_field_semantics_joined_from_symbolic_relation": exact_entry_receiver,
                "BMW_numeric_offset_value_proven": False,
            }
        )

    candidates.sort(key=lambda row: int(row["instruction"], 0))
    structural_blockers.sort(key=lambda row: int(row["instruction"], 0))
    missing = sorted(REQUIRED_BYTES - coverage_from_entry_receiver)
    store_frontier_ready = bool(candidates) and not missing and not structural_blockers

    blockers: list[dict[str, Any]] = []
    if structural_blockers:
        blockers.append(
            {
                "id": "offset33b-store-structural-ambiguity",
                "count": len(structural_blockers),
                "required_evidence": "resolve every offset33b-looking complex STORE target before positive field coverage",
            }
        )
    if missing:
        blockers.append(
            {
                "id": "offset33b-entry-receiver-store-coverage-incomplete",
                "missing_byte_offsets": [f"0x{value:x}" for value in missing],
                "required_evidence": "trace the missing field stores or any derived target-address path from FUN_0076b280 entry ECX",
            }
        )
    if store_frontier_ready:
        blockers.append(
            {
                "id": "offset33b-store-value-semantics-not-numeric",
                "required_evidence": "join the reported value roots/dependency slices to exact BMW resource/init inputs and evaluate all three doubles",
            }
        )

    root_kinds = sorted(
        {
            kind
            for row in candidates
            for kind in row.get("terminal_root_kinds") or []
        }
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "store-frontier-ready" if store_frontier_ready else "blocked",
        "ready": store_frontier_ready,
        "inputs": {
            "symbolic_relation": str(relation_path),
            "ghidra_export": str(ghidra_export),
            "instruction_export": str(instruction_export),
        },
        "retail": {
            "program_name": PROGRAM,
            "executable_md5": PE_MD5,
            "function": {
                "address": TARGET,
                "name": TARGET_NAME,
                "size": TARGET_SIZE,
                "calling_convention": TARGET_CALLING_CONVENTION,
                "mnemonic_sha256": function.get("mnemonic_sha256"),
            },
        },
        "symbolic_relation": {
            "format": relation.get("format"),
            "translation": relation["symbolic_bind_relation"]["translation"],
            "producer": TARGET,
        },
        "analysis": {
            "instruction_count": len(instructions),
            "reachable_instruction_count": len(incoming),
            "fixed_point_iterations": iterations,
            "candidate_store_count": len(candidates),
            "structural_blockers": structural_blockers,
            "entry_receiver_covered_byte_count": len(coverage_from_entry_receiver),
            "required_byte_count": len(REQUIRED_BYTES),
            "missing_entry_receiver_bytes": [f"0x{value:x}" for value in missing],
            "terminal_root_kinds": root_kinds,
            "store_candidates": candidates,
        },
        "handoff": {
            "offset33b_store_provenance_ready": store_frontier_ready,
            "offset33b_value_root_frontier_ready": store_frontier_ready,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "next_proof": {
            "target": "evaluate three offset33b doubles from exact BMW resource/init inputs",
            "preferred_static_input": "reported STORE value dependency roots and the exact resource-driven bootstrap artifacts",
            "runtime_value_witness_required_if_static_join_fails": True,
        },
        "scope": {
            "source_relation_used_for_field_semantics": True,
            "callgraph_adjacency_used_as_value_identity": False,
            "Ghidra_parameter_types_used_as_semantics": False,
            "constant_roots_auto_promoted_to_double_values": False,
            "CALL_return_values_invented": False,
            "x87_state_invented": False,
            "numeric_offset_assumed": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path, help="retail Ghidra evidence directory")
    parser.add_argument("instruction_export", type=Path, help="targeted FUN_0076b280 instruction JSONL")
    parser.add_argument("--relation", type=Path, default=DEFAULT_RELATION)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze_bmw_offset33b_store_provenance(
        args.ghidra_export,
        args.instruction_export,
        args.relation,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
