#!/usr/bin/env python3
"""Resolve memory LOAD roots feeding the three BMW offset33b STORE slices.

``SHIFT.BMWOffset33bStoreProvenance/1`` already proves the physical HDVehicle
STORE targets and records conservative backward p-code value slices.  Memory
inputs in those slices still terminate as anonymous roots, which is too weak for
a numeric BMW bind translation.

This pass reuses the same targeted ``FUN_0076b280`` instruction export.  For
every p-code LOAD that actually appears in an admitted offset33b STORE dependency
slice it joins that LOAD to one simple machine memory operand, proves the all-path
origin of the operand base register, and records exact displacement and width.

The independent first-bootstrap additional-mass reduction is accepted only from
the corrected actual-object contract
``SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1``.  The retracted
manager-record zero contract is not an accepted input.  Even the correct +0.0f
reduction is not attached to a machine LOAD merely because its displacement is
0xba0 or 0x860; pointer identity remains a separate proof.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite
import analyze_bmw_body0_bind_pose_writer_value_provenance as _values
import analyze_bmw_offset33b_store_provenance as _stores
import analyze_register_relative_accesses as _access

FORMAT = "SHIFT.BMWOffset33bMemoryLoadProvenance/1"
STORE_FORMAT = _stores.FORMAT
ADDITIONAL_MASS_FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1"
INSTRUCTION_FORMAT = _stores.INSTRUCTION_FORMAT
TARGET = _stores.TARGET

_ENTRY_ORIGIN = re.compile(r"^entry:([A-Z][A-Z0-9]*)$", re.IGNORECASE)
_MEMORY_ORIGIN = re.compile(r"^memory:(.+)$", re.IGNORECASE)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _validate_store_report(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report = _read_json(path)
    if report.get("format") != STORE_FORMAT:
        raise ValueError(f"{path}: expected {STORE_FORMAT}")
    if report.get("ready") is not True:
        raise ValueError("offset33b STORE provenance is not ready")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("offset33b STORE provenance handoff missing")
    if handoff.get("offset33b_store_provenance_ready") is not True:
        raise ValueError("offset33b STORE provenance gate is not ready")
    if handoff.get("offset33b_value_root_frontier_ready") is not True:
        raise ValueError("offset33b value-root frontier is not ready")
    if handoff.get("BMW_numeric_offset33b_ready") is not False:
        raise ValueError("STORE provenance unexpectedly preclaims numeric offset33b")
    if handoff.get("vehicle_world_transform_ready") is not False:
        raise ValueError("STORE provenance unexpectedly preclaims vehicle world transform")

    retail = report.get("retail")
    function = retail.get("function") if isinstance(retail, Mapping) else None
    if not isinstance(function, Mapping):
        raise ValueError("STORE provenance retail function identity missing")
    if str(function.get("address") or "").lower() != TARGET:
        raise ValueError("STORE provenance producer address drift")
    if function.get("mnemonic_sha256") != _stores.TARGET_MNEMONIC_SHA256:
        raise ValueError("STORE provenance producer fingerprint drift")

    analysis = report.get("analysis")
    if not isinstance(analysis, Mapping):
        raise ValueError("STORE provenance analysis missing")
    candidates = analysis.get("store_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("STORE provenance has no admitted store candidates")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(candidates):
        if not isinstance(raw, Mapping):
            raise ValueError(f"store_candidates[{index}] must be an object")
        instruction = _callsite._address(
            raw.get("instruction"), field=f"store_candidates[{index}].instruction"
        )
        if instruction in seen:
            raise ValueError(f"duplicate STORE provenance instruction {instruction}")
        seen.add(instruction)
        if raw.get("target_is_FUN_0076b280_entry_ECX_on_all_reachable_paths") is not True:
            raise ValueError(f"{instruction}: STORE target is not exact FUN_0076b280 entry ECX")
        if raw.get("HDVehicle_field_semantics_joined_from_symbolic_relation") is not True:
            raise ValueError(f"{instruction}: HDVehicle field semantics are not joined")
        if raw.get("BMW_numeric_offset_value_proven") is not False:
            raise ValueError(f"{instruction}: STORE provenance unexpectedly preclaims numeric value")
        fields = raw.get("offset33b_fields_touched")
        if not isinstance(fields, list) or not fields or any(not isinstance(v, str) for v in fields):
            raise ValueError(f"{instruction}: offset33b field coverage missing")
        dependency = raw.get("dependency_slice")
        if not isinstance(dependency, list):
            raise ValueError(f"{instruction}: dependency_slice missing")
        normalized.append({**raw, "instruction": instruction})
    return report, normalized


def _validate_additional_mass_proof(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if report.get("format") != ADDITIONAL_MASS_FORMAT:
        raise ValueError(f"{path}: expected {ADDITIONAL_MASS_FORMAT}")
    if report.get("ready") is not True:
        raise ValueError("actual additional-mass bootstrap-zero proof is not ready")

    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("actual additional-mass proof handoff missing")
    if handoff.get("offset33b_actual_additional_mass_bootstrap_zero_ready") is not True:
        raise ValueError("actual additional-mass bootstrap-zero gate is not ready")
    if handoff.get("offset33b_additional_mass_term_can_be_elided_for_first_bootstrap") is not True:
        raise ValueError("actual additional-mass term is not proven elidable")
    if handoff.get("BMW_numeric_offset33b_ready") is not False:
        raise ValueError("actual additional-mass proof unexpectedly preclaims numeric offset33b")

    object_graph = report.get("object_graph")
    proven = report.get("proven_value")
    scope = report.get("scope")
    if not isinstance(object_graph, Mapping) or not isinstance(proven, Mapping):
        raise ValueError("actual additional-mass object graph/value proof missing")
    if int(object_graph.get("participant_additional_mass_offset", -1)) != 0xBA0:
        raise ValueError("actual additional-mass participant offset drift")
    if int(object_graph.get("vehicle_additional_mass_offset", -1)) != 0x860:
        raise ValueError("actual additional-mass Vehicle offset drift")
    if object_graph.get("manager_record_plus_0xba0_is_not_the_proven_storage") is not True:
        raise ValueError("actual additional-mass proof lost manager-record/object distinction")
    if float(proven.get("value", 1.0)) != 0.0 or proven.get("type") != "float32":
        raise ValueError("actual additional-mass proven value is not exact float32 zero")
    if isinstance(scope, Mapping) and scope.get("retracted_manager_record_zero_claim_reused") is not False:
        raise ValueError("actual additional-mass proof unexpectedly reuses retracted manager-record zero")
    return report


def _instruction_map(path: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    instructions = _stores._load_instruction_row(path)
    by_address: dict[str, dict[str, Any]] = {}
    for instruction in instructions:
        address = _callsite._address(instruction.get("address"), field="instruction.address")
        if address in by_address:
            raise ValueError(f"duplicate instruction address {address}")
        by_address[address] = instruction
    return instructions, by_address


def _load_node_ids(candidates: list[dict[str, Any]]) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    fields_by_node: dict[str, set[str]] = defaultdict(set)
    stores_by_node: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates:
        store = str(candidate["instruction"])
        fields = [str(value) for value in candidate.get("offset33b_fields_touched") or []]
        for index, raw in enumerate(candidate.get("dependency_slice") or []):
            if not isinstance(raw, Mapping):
                raise ValueError(f"{store}: dependency_slice[{index}] must be an object")
            node_id = raw.get("id")
            opcode = str(raw.get("opcode") or "").upper()
            if not isinstance(node_id, str) or not node_id:
                raise ValueError(f"{store}: dependency node id missing")
            if opcode != "LOAD":
                continue
            fields_by_node[node_id].update(fields)
            if store not in stores_by_node[node_id]:
                stores_by_node[node_id].append(store)
    return fields_by_node, stores_by_node


def _memory_operands(instruction: Mapping[str, Any]) -> list[tuple[int, str, tuple[str, int] | None]]:
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{instruction.get('address')}: instruction operands must be strings")
    return [
        (index, operand, _access._parse_memory_operand(operand))
        for index, operand in enumerate(operands)
        if "[" in operand or "]" in operand
    ]


def _pcode_loads(instruction: Mapping[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError(f"{instruction.get('address')}: pcode missing")
    return [
        (index, operation)
        for index, operation in enumerate(pcode)
        if isinstance(operation, dict) and str(operation.get("opcode") or "").upper() == "LOAD"
    ]


def _node_address(node_id: str) -> str:
    raw, separator, _index = node_id.rpartition(":")
    if not separator:
        raise ValueError(f"invalid p-code node id {node_id!r}")
    return _callsite._address(raw, field="p-code node instruction")


def _origin_class(origins: list[str]) -> str:
    if len(origins) != 1:
        return "multi-or-unresolved-origin"
    origin = origins[0]
    if _ENTRY_ORIGIN.fullmatch(origin):
        return "single-entry-register-origin"
    if _MEMORY_ORIGIN.fullmatch(origin):
        return "single-memory-derived-origin"
    if origin.lower().startswith("constant:"):
        return "single-constant-derived-origin"
    if "unknown" in origin.lower() or "derived" in origin.lower():
        return "single-unresolved-derived-origin"
    return "single-other-origin"


def _group_key(row: Mapping[str, Any]) -> tuple[tuple[str, ...], int, int]:
    return (
        tuple(str(value) for value in row.get("base_register_origins") or []),
        int(row["displacement"]),
        int(row["load_width"]),
    )


def analyze_bmw_offset33b_memory_load_provenance(
    store_provenance_path: Path,
    instruction_export: Path,
    additional_mass_proof_path: Path,
) -> dict[str, Any]:
    _store_report, candidates = _validate_store_report(store_provenance_path)
    additional_mass = _validate_additional_mass_proof(additional_mass_proof_path)
    instructions, instruction_by_address = _instruction_map(instruction_export)
    incoming, iterations = _callsite._analyze_incoming_states(instructions)
    nodes, _edges, _bindings = _values._structured_pcode_graph(instructions)

    fields_by_node, stores_by_node = _load_node_ids(candidates)
    load_rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    consumed_nodes: set[str] = set()

    for node_id in sorted(
        fields_by_node,
        key=lambda value: (int(_node_address(value), 0), int(value.rpartition(":")[2]),),
    ):
        node = nodes.get(node_id)
        if not isinstance(node, Mapping):
            blockers.append(
                {
                    "id": "offset33b-slice-load-node-missing-from-instruction-export",
                    "node_id": node_id,
                    "required_evidence": "use the exact instruction export that produced the STORE provenance report",
                }
            )
            continue
        if str(node.get("opcode") or "").upper() != "LOAD":
            raise ValueError(f"{node_id}: STORE report marks a non-LOAD p-code node as LOAD")
        address = _callsite._address(node.get("instruction"), field=f"{node_id}.instruction")
        instruction = instruction_by_address.get(address)
        if instruction is None:
            blockers.append(
                {
                    "id": "offset33b-slice-load-instruction-missing",
                    "node_id": node_id,
                    "instruction": address,
                }
            )
            continue

        pcode_loads = _pcode_loads(instruction)
        memory = _memory_operands(instruction)
        parsed = [row for row in memory if row[2] is not None]
        unparsed = [row for row in memory if row[2] is None]
        expected_node_ids = {f"{address}:{index}" for index, _operation in pcode_loads}
        if node_id not in expected_node_ids:
            raise ValueError(f"{node_id}: LOAD p-code ordinal drift")
        if len(pcode_loads) != 1 or len(parsed) != 1 or unparsed:
            blockers.append(
                {
                    "id": "offset33b-slice-load-machine-operand-ambiguous",
                    "node_id": node_id,
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "pcode_load_count": len(pcode_loads),
                    "memory_operands": [
                        {
                            "operand_index": index,
                            "operand": operand,
                            "simple_register_relative": parsed_value is not None,
                        }
                        for index, operand, parsed_value in memory
                    ],
                    "required_evidence": "resolve the exact machine LOAD address/width before assigning a field source",
                }
            )
            continue

        pcode_index, operation = pcode_loads[0]
        output = operation.get("output")
        if not isinstance(output, Mapping):
            raise ValueError(f"{node_id}: LOAD output varnode missing")
        width = output.get("size")
        if not isinstance(width, int) or width <= 0:
            raise ValueError(f"{node_id}: LOAD width invalid")

        operand_index, operand, parsed_memory = parsed[0]
        assert parsed_memory is not None
        base_register, displacement = parsed_memory
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
        deterministic = (
            flags.get("exact_single_origin") is True
            and flags.get("contains_unknown_or_derived") is False
        )
        displacement_only_alias = displacement in {0xBA0, 0x860}
        load_rows.append(
            {
                "node_id": node_id,
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "pcode_load_index": pcode_index,
                "operand_index": operand_index,
                "operand": operand,
                "base_register": base_register,
                "base_register_origins": origins,
                "base_register_origin_flags": flags,
                "base_origin_class": _origin_class(origins),
                "base_origin_deterministic": deterministic,
                "displacement": displacement,
                "displacement_hex": (
                    f"0x{displacement:x}" if displacement >= 0 else f"-0x{-displacement:x}"
                ),
                "load_width": width,
                "feeds_store_instructions": sorted(
                    stores_by_node[node_id], key=lambda value: int(value, 0)
                ),
                "feeds_offset33b_fields": sorted(fields_by_node[node_id]),
                "machine_LOAD_join_proven": True,
                "object_field_reference_ready": deterministic,
                "matches_additional_mass_displacement_only": displacement_only_alias,
                "additional_mass_pointer_identity_proven": False,
                "additional_mass_zero_applied_to_this_load": False,
                "resource_or_object_semantics_proven": False,
                "numeric_loaded_value_proven": False,
            }
        )
        consumed_nodes.add(node_id)

    unresolved_nodes = sorted(set(fields_by_node) - consumed_nodes)
    deterministic_rows = [row for row in load_rows if row["base_origin_deterministic"] is True]
    nondeterministic_rows = [row for row in load_rows if row["base_origin_deterministic"] is False]
    if nondeterministic_rows:
        blockers.append(
            {
                "id": "offset33b-memory-load-base-origin-unresolved",
                "count": len(nondeterministic_rows),
                "node_ids": [row["node_id"] for row in nondeterministic_rows],
                "required_evidence": "resolve the all-path object base origin before semantic resource-field promotion",
            }
        )

    grouped: dict[tuple[tuple[str, ...], int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in deterministic_rows:
        grouped[_group_key(row)].append(row)
    field_worklist: list[dict[str, Any]] = []
    for (origins, displacement, width), rows in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])
    ):
        field_worklist.append(
            {
                "base_origin_expression_set": list(origins),
                "displacement": displacement,
                "displacement_hex": (
                    f"0x{displacement:x}" if displacement >= 0 else f"-0x{-displacement:x}"
                ),
                "load_width": width,
                "load_node_ids": [row["node_id"] for row in rows],
                "load_instructions": sorted(
                    {row["instruction"] for row in rows}, key=lambda value: int(value, 0)
                ),
                "feeds_offset33b_fields": sorted(
                    {field for row in rows for field in row["feeds_offset33b_fields"]}
                ),
                "semantic_owner_or_resource": None,
                "semantic_field_name": None,
                "semantic_join_ready": False,
            }
        )

    memory_root_kind_observed = any(
        "external-or-memory-varnode" in (candidate.get("terminal_root_kinds") or [])
        for candidate in candidates
    )
    if memory_root_kind_observed and not fields_by_node:
        blockers.append(
            {
                "id": "offset33b-memory-root-without-structured-LOAD-node",
                "required_evidence": "trace the unresolved memory root to a structured LOAD or narrower helper-return producer",
            }
        )

    structural_ready = not unresolved_nodes and not any(
        blocker["id"] in {
            "offset33b-slice-load-node-missing-from-instruction-export",
            "offset33b-slice-load-instruction-missing",
            "offset33b-slice-load-machine-operand-ambiguous",
        }
        for blocker in blockers
    )
    exact_worklist_ready = structural_ready and bool(load_rows) and not nondeterministic_rows

    object_graph = additional_mass["object_graph"]
    proven = additional_mass["proven_value"]
    displacement_matches = [
        row["node_id"] for row in load_rows if row["matches_additional_mass_displacement_only"]
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "exact-memory-field-worklist-ready"
            if exact_worklist_ready
            else "memory-load-frontier-ready"
            if structural_ready
            else "blocked"
        ),
        "ready": structural_ready,
        "inputs": {
            "store_provenance": str(store_provenance_path),
            "instruction_export": str(instruction_export),
            "actual_additional_mass_proof": str(additional_mass_proof_path),
        },
        "producer": {
            "function": TARGET,
            "mnemonic_sha256": _stores.TARGET_MNEMONIC_SHA256,
            "instruction_count": len(instructions),
            "reachable_instruction_count": len(incoming),
            "fixed_point_iterations": iterations,
        },
        "known_semantic_reductions": {
            "additional_mass_first_bootstrap": {
                "semantic_name": "actual participant additional mass term",
                "participant_storage": "actual_participant+0xba0",
                "vehicle_alias_storage": "embedded_vehicle+0x860",
                "participant_offset": object_graph.get("participant_additional_mass_offset"),
                "vehicle_offset": object_graph.get("vehicle_additional_mass_offset"),
                "value_type": proven.get("type"),
                "value": proven.get("value"),
                "numeric_value_proven": True,
                "term_elidable_for_first_bootstrap": True,
                "machine_LOAD_pointer_identity_joined": False,
                "displacement_only_candidate_load_nodes": displacement_matches,
                "displacement_match_is_semantic_identity": False,
                "proof_format": additional_mass.get("format"),
                "retracted_manager_record_zero_claim_reused": False,
            }
        },
        "analysis": {
            "store_candidate_count": len(candidates),
            "slice_LOAD_node_count": len(fields_by_node),
            "machine_LOAD_join_count": len(load_rows),
            "deterministic_base_load_count": len(deterministic_rows),
            "nondeterministic_base_load_count": len(nondeterministic_rows),
            "unresolved_LOAD_node_ids": unresolved_nodes,
            "load_sources": load_rows,
            "exact_object_field_worklist": field_worklist,
        },
        "handoff": {
            "offset33b_store_provenance_ready": True,
            "offset33b_memory_LOAD_frontier_ready": structural_ready,
            "offset33b_exact_memory_field_worklist_ready": exact_worklist_ready,
            "offset33b_actual_additional_mass_bootstrap_zero_proof_consumed": True,
            "offset33b_additional_mass_machine_LOAD_join_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "next_proof": {
            "target": "join each exact base-origin/displacement load group to HDV/VDF/SDF/tire semantic fields",
            "field_worklist": field_worklist,
            "additional_mass_join_rule": (
                "only apply the proven +0.0f reduction after pointer provenance proves a load is "
                "the actual PhysicsParticipant+0xba0 / embedded Vehicle+0x860 storage"
            ),
            "runtime_value_witness_required_if_static_resource_joins_fail": True,
        },
        "scope": {
            "same_FUN_0076b280_instruction_export_reused": True,
            "machine_operand_join_requires_one_simple_register_relative_LOAD": True,
            "base_register_semantics_inferred_from_displacement": False,
            "matching_0xba0_or_0x860_displacement_promoted_to_additional_mass": False,
            "memory_load_promoted_to_resource_field": False,
            "additional_mass_zero_promoted_to_unjoined_machine_LOAD": False,
            "retracted_manager_record_zero_contract_accepted": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("store_provenance", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("actual_additional_mass_proof", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze_bmw_offset33b_memory_load_provenance(
        args.store_provenance,
        args.instruction_export,
        args.actual_additional_mass_proof,
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
