#!/usr/bin/env python3
"""Prove exact machine-store/value provenance for the outer Vehicle render-root delta.

``SHIFT.OuterVehicleRenderSnapshotAffineBridge/1`` proves the retail equation

    P_snapshot = P_outer + R_outer * delta_local

and bounds ``delta_local`` to ``outerVehicle+0x19c/+0x1a0/+0x1a4`` with setup
producer ``FUN_00795d60``.  It deliberately does not identify that local delta
with the canonical BMW VHF hierarchy root.

This analyzer consumes exactly one targeted ``SHIFT.GhidraFunctionInstructions/2``
row for ``FUN_00795d60``.  It proves which STOREs cover the three float fields,
proves that their target base is the function entry ECX on every reachable path,
and emits backward structured-pcode value slices.  The resulting contract is a
bounded value-provenance frontier; it never promotes equal constants, nearby
calls, helper names, or callgraph adjacency to VHF ownership/frame identity.
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

FORMAT = "SHIFT.OuterVehicleRenderRootDeltaProvenance/1"
BRIDGE_FORMAT = "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
TARGET = "0x00795d60"
TARGET_NAME = "FUN_00795d60"
TARGET_SIZE = 8797
TARGET_CALLING_CONVENTION = "__fastcall"
TARGET_MNEMONIC_SHA256 = "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"
FIELD_SIZE = 4
FIELDS = (
    (0x19C, "render_root_delta.x"),
    (0x1A0, "render_root_delta.y"),
    (0x1A4, "render_root_delta.z"),
)
REQUIRED_BYTES = frozenset(
    byte for offset, _ in FIELDS for byte in range(offset, offset + FIELD_SIZE)
)
DEFAULT_BRIDGE = (
    Path(__file__).resolve().parents[2]
    / "evidence"
    / "process1_outer_vehicle_render_snapshot_affine_bridge.json"
)


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


def _validate_bridge(path: Path) -> dict[str, Any]:
    bridge = _read_json(path)
    if bridge.get("format") != BRIDGE_FORMAT:
        raise ValueError(f"{path}: expected {BRIDGE_FORMAT}")
    if bridge.get("ready") is not True:
        raise ValueError("outer Vehicle render-snapshot affine bridge is not ready")

    handoff = bridge.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("bridge handoff missing")
    if handoff.get("outer_vehicle_to_render_root_symbolic_affine_ready") is not True:
        raise ValueError("bridge symbolic affine gate is not ready")
    if handoff.get("render_root_translation_delta_producer_bounded") is not True:
        raise ValueError("bridge delta-producer gate is not ready")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("bridge unexpectedly preclaims outer/VHF frame identity")
    if handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is not False:
        raise ValueError("bridge unexpectedly preclaims an outer/VHF affine delta")
    if handoff.get("BODY0_bind_frame_proof_ready") is not False:
        raise ValueError("bridge unexpectedly preclaims BODY0 bind-frame proof")

    outer = bridge.get("outer_transform")
    if not isinstance(outer, Mapping):
        raise ValueError("bridge outer_transform missing")
    if outer.get("local_delta_has_concrete_setup_producer") is not True:
        raise ValueError("bridge does not prove a concrete setup producer")
    if outer.get("render_root_local_delta_offsets") != ["+0x19c", "+0x1a0", "+0x1a4"]:
        raise ValueError("bridge render-root delta field layout drift")

    relation = bridge.get("snapshot_relation")
    if not isinstance(relation, Mapping):
        raise ValueError("bridge snapshot_relation missing")
    if relation.get("translation_formula") != "P_snapshot = P_outer + R_outer * delta_local":
        raise ValueError("bridge affine formula drift")
    return bridge


def _validate_retail_function(root: Path) -> dict[str, Any]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")

    hits = [
        row
        for row in _read_jsonl(root / "functions.jsonl")
        if str(row.get("address") or "").lower() == TARGET
    ]
    if len(hits) != 1:
        raise ValueError(f"expected exactly one {TARGET} function row; found {len(hits)}")
    row = hits[0]
    if row.get("name") != TARGET_NAME:
        raise ValueError("FUN_00795d60 name drift")
    if int(row.get("size", -1)) != TARGET_SIZE:
        raise ValueError("FUN_00795d60 size drift")
    if row.get("calling_convention") != TARGET_CALLING_CONVENTION:
        raise ValueError("FUN_00795d60 calling convention drift")
    if row.get("mnemonic_sha256") != TARGET_MNEMONIC_SHA256:
        raise ValueError("FUN_00795d60 mnemonic fingerprint drift")
    if row.get("external") is True or row.get("thunk") is True:
        raise ValueError("FUN_00795d60 must be a concrete retail function")
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
    return {
        "store_value_varnode": dict(value),
        "store_value_definition": definition,
        "dependency_slice": slice_nodes,
        "dependency_opcodes": sorted({str(row.get("opcode") or "") for row in slice_nodes}),
        "terminal_roots": roots,
        "terminal_root_kinds": sorted({str(root.get("root_kind")) for root in roots}),
        "value_slice_constant_only": bool(roots)
        and all(root.get("semantic_join_required") is False for root in roots),
        "VHF_frame_semantics_proven": False,
        "numeric_delta_value_proven": False,
    }


def analyze_outer_vehicle_render_root_delta_provenance(
    ghidra_export: Path,
    instruction_export: Path,
    bridge_path: Path = DEFAULT_BRIDGE,
) -> dict[str, Any]:
    bridge = _validate_bridge(bridge_path)
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
            and any(token in row[1].lower() for token in ("19c", "1a0", "1a4"))
        ]
        if suspicious_unparsed:
            structural_blockers.append(
                {
                    "instruction": address,
                    "reason": "render-root-delta-looking STORE target is not a simple register-relative operand",
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
                "target_is_FUN_00795d60_entry_ECX_on_all_reachable_paths": exact_entry_receiver,
                "displacement": displacement,
                "displacement_hex": f"0x{displacement:x}",
                "store_width": width,
                "required_bytes_touched": touched,
                "render_root_delta_fields_touched": _field_labels(touched),
                "pcode_store_proven": True,
                "recent_direct_calls_before_store": _values._direct_calls_before(instructions, address)[-8:],
                **value,
                "outer_Vehicle_delta_field_semantics_joined_from_bridge": exact_entry_receiver,
                "outer_vehicle_root_to_VHF_relation_proven": False,
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
                "id": "render-root-delta-store-structural-ambiguity",
                "count": len(structural_blockers),
                "required_evidence": "resolve every delta-looking complex STORE target before positive field coverage",
            }
        )
    if missing:
        blockers.append(
            {
                "id": "render-root-delta-entry-receiver-store-coverage-incomplete",
                "missing_byte_offsets": [f"0x{value:x}" for value in missing],
                "required_evidence": "cover all three +0x19c/+0x1a0/+0x1a4 float fields with STOREs whose base is exactly FUN_00795d60 entry ECX",
            }
        )
    if store_frontier_ready:
        blockers.append(
            {
                "id": "render-root-delta-value-roots-to-canonical-vhf-root",
                "required_evidence": "join the emitted exact terminal value roots to the canonical BMW VHF HIERARCHY Root/frame, proving identity or an exact fixed affine delta",
            }
        )

    terminal_root_kinds = sorted(
        {
            str(kind)
            for row in candidates
            for kind in row.get("terminal_root_kinds", [])
        }
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "delta-store-provenance-ready" if store_frontier_ready else "blocked",
        "ready": store_frontier_ready,
        "BLOCKER": "SHIFT.BMWBody0BindFrameProof/1: outer Vehicle-root -> exact BMW VHF vehicle-root relation",
        "INPUT": {
            "affine_bridge": BRIDGE_FORMAT,
            "instruction_export": INSTRUCTION_FORMAT,
            "target_function": TARGET_NAME,
        },
        "OUTPUT": "exact entry-ECX store coverage and backward p-code value roots for outerVehicle +0x19c/+0x1a0/+0x1a4",
        "CONSUMER": "next Process 1 static value/root semantic join to canonical BMW VHF HIERARCHY Root",
        "retail": {
            "program": PROGRAM,
            "md5": PE_MD5,
            "function": {
                "address": TARGET,
                "name": TARGET_NAME,
                "size": TARGET_SIZE,
                "calling_convention": TARGET_CALLING_CONVENTION,
                "mnemonic_sha256": TARGET_MNEMONIC_SHA256,
            },
        },
        "bridge_provenance": {
            "format": bridge.get("format"),
            "status": bridge.get("status"),
            "translation_formula": bridge["snapshot_relation"]["translation_formula"],
            "render_root_local_delta_offsets": bridge["outer_transform"]["render_root_local_delta_offsets"],
        },
        "analysis": {
            "instruction_count": len(instructions),
            "cfg_fixed_point_iterations": iterations,
            "candidate_store_count": len(candidates),
            "entry_receiver_covered_byte_count": len(coverage_from_entry_receiver),
            "required_byte_count": len(REQUIRED_BYTES),
            "missing_entry_receiver_bytes": [f"0x{value:x}" for value in missing],
            "terminal_root_kinds": terminal_root_kinds,
            "store_candidates": candidates,
            "structural_blockers": structural_blockers,
        },
        "handoff": {
            "render_root_delta_store_provenance_ready": store_frontier_ready,
            "render_root_delta_value_roots_ready": store_frontier_ready,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "scope": {
            "callgraph_adjacency_used_as_value_or_owner_proof": False,
            "helper_names_used_as_owner_proof": False,
            "equal_numeric_values_used_as_frame_identity_proof": False,
            "VHF_frame_identity_assumed": False,
            "runtime_capture_required": False,
            "original_game_executed": False,
            "synthetic_test_values_are_retail_evidence": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze_outer_vehicle_render_root_delta_provenance(
        args.ghidra_export,
        args.instruction_export,
        args.bridge,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
