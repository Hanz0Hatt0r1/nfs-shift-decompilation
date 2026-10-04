#!/usr/bin/env python3
"""Discover exact construction-lane writes to persistent BODY pose fields.

This pass is intentionally narrower than a bind-frame proof.  It consumes a
single targeted SHIFT.GhidraFunctionInstructions/2 export for the already
source-backed BODY construction lane and answers a machine/p-code question:
which exact instructions in FUN_007b3670/FUN_007bba90/FUN_007bbb10/
FUN_007bbb60 STORE bytes overlapping persistent BODY origin/basis lanes, and
what physical register/value roots feed those stores?

No semantic name is assigned from Ghidra parameter names/types or from register
position.  A matching displacement is only a pose-store candidate until target
pointer identity and value provenance are independently joined.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite
import analyze_bmw_body0_bind_pose_writer_target_role as _target
import analyze_bmw_body0_bind_pose_writer_value_provenance as _values
import analyze_register_relative_accesses as _access

FORMAT = "SHIFT.BMWBody0ConstructionPoseStores/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

BODY_BUILDER = "0x007b3670"
BODY_HELPERS = ("0x007bba90", "0x007bbb10", "0x007bbb60")
TARGETS = (BODY_BUILDER, *BODY_HELPERS)
FINGERPRINTS = {
    BODY_BUILDER: "bcf42f221ca37b7ee8f907b0783fc8da894ecc3528e86506f6d58e448a0953d3",
    "0x007bba90": "ade565ab3fa59f77ca0ec62392629eaec5642920ea64d5b7e1760d849fb0e587",
    "0x007bbb10": "345f993d42c3338af314e48791796449516286b95ccdc40a7d188590fc091238",
    "0x007bbb60": "113211b1c93c307c1bac779494a1a6420ceb8d691dfe6d8c0987af615f3752c4",
}

ORIGIN_FIELDS = _target.ORIGIN_FIELDS
BASIS_FIELDS = _target.BASIS_FIELDS
POSE_FIELDS = ORIGIN_FIELDS + BASIS_FIELDS
REQUIRED_BYTES = frozenset(
    byte
    for offset, size in POSE_FIELDS
    for byte in range(offset, offset + size)
)
FRAME_BASES = {"EBP", "ESP"}


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


def _load_retail_identity(root: Path) -> dict[str, Any]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM:
        raise ValueError(f"unexpected program: {binary.get('program_name')!r}")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")
    return binary


def _load_target_function_rows(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _callsite._address(raw, field="functions.address")
        if address not in FINGERPRINTS:
            continue
        if address in rows:
            raise ValueError(f"duplicate function row {address}")
        rows[address] = row

    missing = [address for address in TARGETS if address not in rows]
    if missing:
        raise ValueError("missing required construction function(s): " + ", ".join(missing))
    for address, expected in FINGERPRINTS.items():
        row = rows[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        if row.get("mnemonic_sha256") != expected:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
    return rows


def _load_instruction_rows(path: Path) -> dict[str, list[dict[str, Any]]]:
    rows = _callsite._index_instruction_rows(path)
    actual = set(rows)
    expected = set(TARGETS)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            "targeted construction instruction set mismatch: "
            f"missing={missing} extra={extra}"
        )
    return rows


def _store_ops(instruction: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError(
            f"{_callsite._address(instruction.get('address'), field='instruction.address')}: pcode missing"
        )
    result: list[tuple[int, dict[str, Any]]] = []
    for index, operation in enumerate(pcode):
        if not isinstance(operation, dict):
            raise ValueError("pcode operation must be an object")
        if str(operation.get("opcode") or "").upper() == "STORE":
            result.append((index, operation))
    return result


def _required_intersection(offset: int, size: int) -> list[int]:
    return sorted(set(range(offset, offset + size)) & set(REQUIRED_BYTES))


def _field_labels(bytes_touched: list[int]) -> list[str]:
    touched = set(bytes_touched)
    result: list[str] = []
    for offset, size in ORIGIN_FIELDS:
        if touched & set(range(offset, offset + size)):
            result.append(f"origin+0x{offset:x}")
    for offset, size in BASIS_FIELDS:
        if touched & set(range(offset, offset + size)):
            result.append(f"basis+0x{offset:x}")
    return result


def _memory_operands(instruction: dict[str, Any]) -> list[tuple[int, str, tuple[str, int] | None]]:
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError("instruction operands must be strings")
    result: list[tuple[int, str, tuple[str, int] | None]] = []
    for index, operand in enumerate(operands):
        if "[" not in operand and "]" not in operand:
            continue
        result.append((index, operand, _access._parse_memory_operand(operand)))
    return result


def _value_slice(
    *,
    address: str,
    op_index: int,
    operation: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, list[str]],
    bindings: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    inputs = operation.get("inputs")
    if not isinstance(inputs, list) or len(inputs) < 3:
        raise ValueError(f"{address}:{op_index}: STORE inputs missing")
    value = _values._validate_varnode(inputs[2], context=f"{address}:{op_index}:STORE value")
    node_id = f"{address}:{op_index}"
    node_bindings = bindings.get(node_id)
    if not isinstance(node_bindings, list):
        raise ValueError(f"{node_id}: structured STORE binding missing")
    value_binding = next((row for row in node_bindings if row.get("input_index") == 2), None)
    if not isinstance(value_binding, dict):
        raise ValueError(f"{node_id}: STORE value binding missing")
    definition = value_binding.get("definition")
    slice_nodes, raw_roots = _values._slice_from_definition(
        definition if isinstance(definition, str) else None,
        value if definition is None else None,
        nodes,
        edges,
        bindings,
    )
    roots = [_values._classify_root(root) for root in raw_roots]
    return {
        "store_value_varnode": dict(value),
        "store_value_definition": definition,
        "dependency_slice": slice_nodes,
        "terminal_roots": roots,
        "terminal_root_kinds": sorted({str(root.get("root_kind")) for root in roots}),
        "semantic_join_required": any(root.get("semantic_join_required") is True for root in roots),
    }


def analyze_bmw_body0_construction_pose_stores(
    ghidra_export: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    binary = _load_retail_identity(ghidra_export)
    function_rows = _load_target_function_rows(ghidra_export)
    instruction_rows = _load_instruction_rows(instruction_export)

    candidates: list[dict[str, Any]] = []
    structural_blockers: list[dict[str, Any]] = []
    function_summaries: list[dict[str, Any]] = []

    for function_address in TARGETS:
        instructions = instruction_rows[function_address]
        incoming, iterations = _callsite._analyze_incoming_states(instructions)
        nodes, edges, bindings = _values._structured_pcode_graph(instructions)
        function_candidate_count = 0
        function_blocker_count = 0

        for instruction in instructions:
            address = _callsite._address(instruction.get("address"), field="instruction.address")
            stores = _store_ops(instruction)
            if not stores:
                continue

            memory = _memory_operands(instruction)
            parsed = [row for row in memory if row[2] is not None]
            unparsed = [row for row in memory if row[2] is None]
            if unparsed or len(parsed) != 1 or len(stores) != 1:
                structural_blockers.append(
                    {
                        "function": function_address,
                        "instruction": address,
                        "instruction_text": instruction.get("text"),
                        "store_op_count": len(stores),
                        "memory_operands": [
                            {
                                "operand_index": index,
                                "operand": operand,
                                "parsed": parsed_value is not None,
                            }
                            for index, operand, parsed_value in memory
                        ],
                        "reason": "STORE target/width cannot be uniquely joined to one simple register-relative memory operand",
                    }
                )
                function_blocker_count += 1
                continue

            op_index, operation = stores[0]
            inputs = operation.get("inputs")
            if not isinstance(inputs, list) or len(inputs) < 3 or not isinstance(inputs[2], dict):
                raise ValueError(f"{address}:{op_index}: STORE value input missing")
            width = inputs[2].get("size")
            if not isinstance(width, int) or width <= 0:
                raise ValueError(f"{address}:{op_index}: STORE width invalid")

            operand_index, operand, parsed_memory = parsed[0]
            assert parsed_memory is not None
            base_register, displacement = parsed_memory
            touched = _required_intersection(displacement, width)
            if not touched:
                continue

            state = incoming.get(address)
            if state is None:
                structural_blockers.append(
                    {
                        "function": function_address,
                        "instruction": address,
                        "reason": "pose-overlap STORE is unreachable from function entry in recovered CFG",
                    }
                )
                function_blocker_count += 1
                continue

            base_origins: list[str] = []
            if base_register in state:
                base_origins = _callsite._register_engine._sorted_origins(state[base_register])
            base_flags = _callsite._origin_flags(base_origins) if base_origins else {
                "origin_count": 0,
                "exact_single_origin": False,
                "contains_unknown_or_derived": True,
                "contains_memory_origin": False,
                "contains_entry_origin": False,
            }
            value = _value_slice(
                address=address,
                op_index=op_index,
                operation=operation,
                nodes=nodes,
                edges=edges,
                bindings=bindings,
            )
            candidates.append(
                {
                    "function": function_address,
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "operand_index": operand_index,
                    "operand": operand,
                    "base_register": base_register,
                    "base_register_origins": base_origins,
                    "base_register_origin_flags": base_flags,
                    "base_is_stack_frame": base_register in FRAME_BASES,
                    "displacement": displacement,
                    "displacement_hex": f"0x{displacement:x}",
                    "store_width": width,
                    "required_bytes_touched": touched,
                    "pose_fields_touched": _field_labels(touched),
                    "pcode_store_proven": True,
                    **value,
                    "persistent_BODY_target_identity_proven": False,
                    "BODY0_identity_proven": False,
                    "bind_value_semantics_proven": False,
                }
            )
            function_candidate_count += 1

        function_summaries.append(
            {
                "function": function_address,
                "mnemonic_sha256": function_rows[function_address].get("mnemonic_sha256"),
                "instruction_count": len(instructions),
                "reachable_instruction_count": len(incoming),
                "fixed_point_iterations": iterations,
                "pose_overlap_store_candidate_count": function_candidate_count,
                "structural_blocker_count": function_blocker_count,
            }
        )

    candidates.sort(key=lambda row: (int(row["function"], 0), int(row["instruction"], 0)))
    structural_blockers.sort(key=lambda row: (int(row["function"], 0), int(row["instruction"], 0)))

    object_candidates = [row for row in candidates if row["base_is_stack_frame"] is False]
    frame_candidates = [row for row in candidates if row["base_is_stack_frame"] is True]
    exact_entry_base_candidates = [
        row
        for row in object_candidates
        if row["base_register_origin_flags"]["exact_single_origin"] is True
        and row["base_register_origin_flags"]["contains_entry_origin"] is True
        and row["base_register_origin_flags"]["contains_unknown_or_derived"] is False
    ]

    blockers: list[dict[str, Any]] = []
    if structural_blockers:
        blockers.append(
            {
                "id": "construction-pose-store-structural-ambiguity",
                "status": "blocked",
                "count": len(structural_blockers),
                "required_evidence": "resolve each ambiguous STORE target before excluding or promoting construction pose writes",
            }
        )
    if not object_candidates:
        blockers.append(
            {
                "id": "construction-pose-writer-not-found-in-target-set",
                "status": "unknown",
                "required_evidence": (
                    "follow the exact construction call/side-effect chain beyond FUN_007b3670/FUN_007bba90/"
                    "FUN_007bbb10/FUN_007bbb60; do not revive the rejected resolved-direct FUN_007b7840 bind branch"
                ),
            }
        )
    else:
        blockers.extend(
            [
                {
                    "id": "construction-pose-store-target-object-identity-unproven",
                    "status": "unknown",
                    "required_evidence": "join candidate base provenance to the persistent 0x170 BODY construction record",
                },
                {
                    "id": "construction-pose-store-BODY0-identity-unproven",
                    "status": "unknown",
                    "required_evidence": "join the persistent BODY construction record to exact BMW chassis BODY index 0",
                },
                {
                    "id": "construction-pose-store-bind-value-semantics-unproven",
                    "status": "unknown",
                    "required_evidence": "join STORE value terminal roots to source-backed BODY[0] pos/ori or another proven bind-frame producer",
                },
            ]
        )

    return {
        "format": FORMAT,
        "source": {
            "program": binary.get("program_name"),
            "executable_md5": binary.get("executable_md5"),
            "ghidra_export": str(ghidra_export),
            "instruction_export": str(instruction_export),
            "instruction_format": INSTRUCTION_FORMAT,
        },
        "target_functions": [
            {
                "address": address,
                "mnemonic_sha256": FINGERPRINTS[address],
                "role": "BODY-builder" if address == BODY_BUILDER else "source-backed-BODY-construction-helper",
            }
            for address in TARGETS
        ],
        "pose_fields": {
            "origin": [{"offset": offset, "size": size} for offset, size in ORIGIN_FIELDS],
            "basis": [{"offset": offset, "size": size} for offset, size in BASIS_FIELDS],
        },
        "analysis": {
            "functions": function_summaries,
            "pose_overlap_store_candidates": candidates,
            "object_base_pose_store_candidates": object_candidates,
            "frame_base_pose_store_candidates": frame_candidates,
            "exact_entry_base_pose_store_candidates": exact_entry_base_candidates,
            "structural_blockers": structural_blockers,
        },
        "blockers": blockers,
        "handoff": {
            "construction_pose_store_discovery_complete": not structural_blockers,
            "construction_pose_store_candidate_found": bool(object_candidates),
            "construction_pose_target_parameter_ready": False,
            "BODY0_pointer_at_construction_pose_write_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "required_next_join": (
                "candidate target pointer -> persistent BODY0 AND STORE terminal roots -> source-backed bind values"
                if object_candidates
                else "follow exact construction side effects to the next writer of persistent BODY origin/basis"
            ),
        },
        "scope": {
            "Ghidra_parameter_names_used_as_semantics": False,
            "Ghidra_parameter_types_used_as_semantics": False,
            "register_position_used_as_semantics": False,
            "matching_offset_promoted_to_BODY_identity": False,
            "value_dependency_slice_promoted_to_bind_semantics": False,
            "resolved_direct_FUN_007b7840_bind_branch_reopened": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "native_runtime_changed": False,
            "renderer_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_bmw_body0_construction_pose_stores(
        args.ghidra_export,
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
