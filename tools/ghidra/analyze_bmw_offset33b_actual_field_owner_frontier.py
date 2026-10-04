#!/usr/bin/env python3
"""Classify exact BMW offset33b LOAD groups into conservative owner domains.

Input must come from the actual-object memory-LOAD adapter, so the retracted
manager-record additional-mass proof cannot enter this stage.  Only an exact
``entry:ECX`` base is promoted to HDVehicle ``this``.  Deterministic memory
origins remain indirect owner slots and every other origin remains unresolved.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWOffset33bActualFieldOwnerFrontier/1"
INPUT_FORMAT = "SHIFT.BMWOffset33bMemoryLoadProvenance/1"
ACTUAL_ZERO_FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1"
PRODUCER = "0x0076b280"
PRODUCER_MNEMONIC_SHA256 = "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6"

_ENTRY = re.compile(r"^entry:([A-Z][A-Z0-9]*)$", re.IGNORECASE)
_MEMORY = re.compile(r"^memory:(.+)$", re.IGNORECASE)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field}: expected list")
    result = [item for item in value if isinstance(item, str) and item]
    if len(result) != len(value) or not result:
        raise ValueError(f"{field}: expected non-empty strings")
    return result


def _validate(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report = _read_json(path)
    if report.get("format") != INPUT_FORMAT:
        raise ValueError(f"{path}: expected {INPUT_FORMAT}")
    if report.get("ready") is not True:
        raise ValueError("memory-LOAD provenance is not ready")

    producer = report.get("producer")
    if not isinstance(producer, Mapping):
        raise ValueError("memory-LOAD producer missing")
    if str(producer.get("function") or "").lower() != PRODUCER:
        raise ValueError("memory-LOAD producer address drift")
    if producer.get("mnemonic_sha256") != PRODUCER_MNEMONIC_SHA256:
        raise ValueError("memory-LOAD producer fingerprint drift")

    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("memory-LOAD handoff missing")
    required_true = (
        "offset33b_store_provenance_ready",
        "offset33b_memory_LOAD_frontier_ready",
        "offset33b_exact_memory_field_worklist_ready",
        "offset33b_actual_additional_mass_bootstrap_zero_proof_consumed",
    )
    for field in required_true:
        if handoff.get(field) is not True:
            raise ValueError(f"{field} is not ready")
    if handoff.get("offset33b_additional_mass_bootstrap_zero_proof_consumed") is not False:
        raise ValueError("historical manager-record zero proof was consumed")
    for field in ("BMW_numeric_offset33b_ready", "BODY0_bind_frame_proof_ready", "vehicle_world_transform_ready"):
        if handoff.get(field) is not False:
            raise ValueError(f"input unexpectedly preclaims {field}")

    scope = report.get("scope")
    if not isinstance(scope, Mapping):
        raise ValueError("memory-LOAD scope missing")
    if scope.get("historical_manager_record_zero_proof_consumed") is not False:
        raise ValueError("historical manager-record zero proof scope drift")
    if scope.get("actual_object_allocator_zero_proof_consumed") is not True:
        raise ValueError("actual-object allocator zero proof was not consumed")

    reduction = report.get("known_semantic_reductions")
    additional = reduction.get("additional_mass_first_bootstrap") if isinstance(reduction, Mapping) else None
    if not isinstance(additional, Mapping):
        raise ValueError("actual additional-mass reduction missing")
    if additional.get("proof_format") != ACTUAL_ZERO_FORMAT:
        raise ValueError("additional-mass reduction proof format drift")
    if additional.get("proof_object_base") != "actual PhysicsParticipant":
        raise ValueError("additional-mass reduction object base drift")
    if additional.get("manager_record_plus_0xba0_reused") is not False:
        raise ValueError("manager-record +0xba0 reduction was reused")
    if additional.get("numeric_value_proven") is not True or float(additional.get("value", 1.0)) != 0.0:
        raise ValueError("actual additional-mass reduction is not exact zero")

    analysis = report.get("analysis")
    worklist = analysis.get("exact_object_field_worklist") if isinstance(analysis, Mapping) else None
    if not isinstance(worklist, list) or not worklist:
        raise ValueError("exact object-field worklist missing")

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, ...], int, int]] = set()
    for index, raw in enumerate(worklist):
        if not isinstance(raw, Mapping):
            raise ValueError(f"worklist[{index}] must be object")
        origins = _strings(raw.get("base_origin_expression_set"), f"worklist[{index}].base_origin_expression_set")
        displacement = raw.get("displacement")
        width = raw.get("load_width")
        fields = _strings(raw.get("feeds_offset33b_fields"), f"worklist[{index}].feeds_offset33b_fields")
        if not isinstance(displacement, int):
            raise ValueError(f"worklist[{index}].displacement invalid")
        if not isinstance(width, int) or width <= 0:
            raise ValueError(f"worklist[{index}].load_width invalid")
        if raw.get("semantic_join_ready") is not False:
            raise ValueError(f"worklist[{index}] unexpectedly preclaims semantic join")
        if raw.get("semantic_owner_or_resource") is not None or raw.get("semantic_field_name") is not None:
            raise ValueError(f"worklist[{index}] unexpectedly preclaims semantic identity")
        key = (tuple(origins), displacement, width)
        if key in seen:
            raise ValueError(f"duplicate exact field group {key!r}")
        seen.add(key)
        normalized.append({**raw, "base_origin_expression_set": origins, "displacement": displacement, "load_width": width, "feeds_offset33b_fields": fields})
    return report, normalized


def _classify(origins: list[str]) -> tuple[str, str | None]:
    if origins == ["entry:ECX"]:
        return "direct-HDVehicle-this", "HDVehicle"
    if len(origins) == 1 and _MEMORY.fullmatch(origins[0]):
        return "indirect-owner-slot", None
    if len(origins) == 1 and _ENTRY.fullmatch(origins[0]):
        return "other-entry-register", None
    if len(origins) == 1:
        return "single-unresolved-origin", None
    return "multi-origin-unresolved", None


def _field_ref(displacement: int) -> str:
    sign = "+" if displacement >= 0 else "-"
    return f"HDVehicle{sign}0x{abs(displacement):x}"


def analyze(path: Path) -> dict[str, Any]:
    source, worklist = _validate(path)
    classified: list[dict[str, Any]] = []
    direct: list[dict[str, Any]] = []
    indirect: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for index, row in enumerate(worklist):
        origins = row["base_origin_expression_set"]
        owner_class, owner = _classify(origins)
        result = {
            "source_worklist_index": index,
            "base_origin_expression_set": origins,
            "displacement": row["displacement"],
            "load_width": row["load_width"],
            "load_node_ids": list(row.get("load_node_ids") or []),
            "load_instructions": list(row.get("load_instructions") or []),
            "feeds_offset33b_fields": row["feeds_offset33b_fields"],
            "owner_class": owner_class,
            "semantic_owner_domain": owner,
            "semantic_field_name": None,
            "semantic_field_value_ready": False,
            "numeric_loaded_value_proven": False,
            "owner_join_ready": owner_class == "direct-HDVehicle-this",
            "exact_owner_field_reference": _field_ref(row["displacement"]) if owner_class == "direct-HDVehicle-this" else None,
        }
        if owner_class == "indirect-owner-slot":
            result["indirect_owner_origin_expression"] = origins[0]
            result["HDV_VDF_SDF_tire_identity_assumed"] = False
            indirect.append(result)
        elif owner_class == "direct-HDVehicle-this":
            result["producer_this_identity_basis"] = {
                "function": PRODUCER,
                "calling_convention": "__thiscall",
                "entry_receiver_register": "ECX",
            }
            direct.append(result)
        else:
            result["required_evidence"] = "resolve this base origin to one concrete object before assigning resource semantics"
            unresolved.append(result)
        classified.append(result)

    blockers: list[dict[str, Any]] = []
    if indirect:
        blockers.append({
            "id": "offset33b-indirect-owner-slot-semantics-unproven",
            "count": len(indirect),
            "origin_expressions": sorted({row["indirect_owner_origin_expression"] for row in indirect}),
            "required_evidence": "join each indirect base expression to the exact HDV/VDF/SDF/tire owner pointer",
        })
    if unresolved:
        blockers.append({
            "id": "offset33b-field-owner-origin-unresolved",
            "count": len(unresolved),
            "required_evidence": "resolve non-ECX entry/multi/derived origins before semantic-field joining",
        })

    all_domains_classified = not unresolved
    all_owner_semantics_ready = bool(classified) and all(row["owner_join_ready"] for row in classified)
    additional = source["known_semantic_reductions"]["additional_mass_first_bootstrap"]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "status": "all-owner-semantics-ready" if all_owner_semantics_ready else "owner-domain-frontier-ready",
        "inputs": {"actual_memory_load_provenance": str(path)},
        "producer_semantics": {
            "function": PRODUCER,
            "mnemonic_sha256": PRODUCER_MNEMONIC_SHA256,
            "calling_convention": "__thiscall",
            "entry_ECX_is_HDVehicle_this": True,
        },
        "analysis": {
            "input_field_group_count": len(worklist),
            "classified_field_group_count": len(classified),
            "direct_HDVehicle_field_count": len(direct),
            "indirect_owner_slot_count": len(indirect),
            "unresolved_owner_group_count": len(unresolved),
            "classified_groups": classified,
            "direct_HDVehicle_fields": direct,
            "indirect_owner_slots": indirect,
            "unresolved_owner_groups": unresolved,
        },
        "known_semantic_reductions": {
            "actual_additional_mass_first_bootstrap_zero_ready": True,
            "actual_additional_mass_proof_format": additional["proof_format"],
            "additional_mass_machine_LOAD_join_ready": source["handoff"].get("offset33b_additional_mass_machine_LOAD_join_ready") is True,
            "additional_mass_zero_applied_by_this_stage": False,
            "historical_manager_record_zero_used": False,
        },
        "handoff": {
            "offset33b_memory_LOAD_frontier_ready": True,
            "offset33b_exact_memory_field_worklist_ready": True,
            "offset33b_direct_HDVehicle_field_owner_joins_ready": bool(direct),
            "offset33b_all_LOAD_owner_domains_classified": all_domains_classified,
            "offset33b_all_field_owner_semantics_ready": all_owner_semantics_ready,
            "offset33b_semantic_field_names_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "next_proof": {
            "target": "resolve only indirect/unresolved bases, then map exact owner+offset references to BMW HDV/VDF/SDF/tire fields",
            "direct_HDVehicle_fields_ready_for_semantic_lookup": [row["exact_owner_field_reference"] for row in direct],
            "indirect_owner_slots_requiring_pointer_join": [
                {
                    "origin_expression": row["indirect_owner_origin_expression"],
                    "displacement": row["displacement"],
                    "load_width": row["load_width"],
                    "feeds_offset33b_fields": row["feeds_offset33b_fields"],
                }
                for row in indirect
            ],
        },
        "scope": {
            "historical_manager_record_zero_proof_consumed": False,
            "actual_object_allocator_zero_proof_consumed": True,
            "FUN_0076b280_entry_ECX_promoted_to_HDVehicle_this": True,
            "other_entry_register_promoted_to_argument_semantics": False,
            "memory_origin_promoted_to_HDVehicle_VDF_SDF_or_tire": False,
            "field_semantic_name_inferred_from_displacement": False,
            "owner_join_promoted_to_numeric_value": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actual_memory_load_provenance", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.actual_memory_load_provenance)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
