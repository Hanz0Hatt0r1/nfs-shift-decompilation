#!/usr/bin/env python3
"""Classify exact BMW offset33b LOAD groups into safe owner domains.

``SHIFT.BMWOffset33bMemoryLoadProvenance/1`` turns anonymous p-code memory roots
into exact ``(base-origin expression set, displacement, width)`` groups.  This
pass performs only the semantic promotion already justified by the producer ABI:

* ``FUN_0076b280`` is source-backed as an HDVehicle ``__thiscall`` producer;
* a LOAD whose all-path base origin is exactly ``entry:ECX`` is therefore an
  exact ``HDVehicle+offset`` field reference;
* a deterministic ``memory:[...]`` base remains only an indirect owner slot;
* any other entry register, multi-origin, derived, or unknown base remains
  unresolved.

The input must come from the repaired canonical LOAD pipeline merged in #1262.
It must explicitly consume ``SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1``
and reject the retracted manager-record zero contract.  This stage never assigns
VDF/SDF/tire names by displacement and never applies the +0.0f reduction unless
an upstream machine-LOAD pointer join has already proved that exact identity.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWOffset33bFieldOwnerFrontier/1"
INPUT_FORMAT = "SHIFT.BMWOffset33bMemoryLoadProvenance/1"
ACTUAL_ZERO_FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1"
PRODUCER = "0x0076b280"
PRODUCER_NAME = "FUN_0076b280"
PRODUCER_ROLE = "HDVehicle offset33b producer"
PRODUCER_MNEMONIC_SHA256 = "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6"

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


def _string_list(value: Any, *, field: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field}: expected list of strings")
    result = [str(item) for item in value if isinstance(item, str) and item]
    if len(result) != len(value):
        raise ValueError(f"{field}: expected only non-empty strings")
    if not result and not allow_empty:
        raise ValueError(f"{field}: list must not be empty")
    return result


def _validate_input(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report = _read_json(path)
    if report.get("format") != INPUT_FORMAT:
        raise ValueError(f"{path}: expected {INPUT_FORMAT}")
    if report.get("ready") is not True:
        raise ValueError("offset33b memory-LOAD provenance is not ready")

    producer = report.get("producer")
    if not isinstance(producer, Mapping):
        raise ValueError("memory-LOAD producer identity missing")
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
    for field in (
        "BMW_numeric_offset33b_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        if handoff.get(field) is not False:
            raise ValueError(f"memory-LOAD report unexpectedly preclaims {field}")

    scope = report.get("scope")
    if not isinstance(scope, Mapping):
        raise ValueError("memory-LOAD scope missing")
    if scope.get("retracted_manager_record_zero_contract_accepted") is not False:
        raise ValueError("retracted manager-record zero contract was accepted")
    if scope.get("additional_mass_zero_promoted_to_unjoined_machine_LOAD") is not False:
        raise ValueError("unjoined additional-mass zero was promoted")

    reductions = report.get("known_semantic_reductions")
    additional = (
        reductions.get("additional_mass_first_bootstrap")
        if isinstance(reductions, Mapping)
        else None
    )
    if not isinstance(additional, Mapping):
        raise ValueError("actual additional-mass reduction missing")
    if additional.get("proof_format") != ACTUAL_ZERO_FORMAT:
        raise ValueError("additional-mass reduction proof format drift")
    if additional.get("retracted_manager_record_zero_claim_reused") is not False:
        raise ValueError("retracted manager-record zero reduction was reused")
    if additional.get("numeric_value_proven") is not True:
        raise ValueError("actual additional-mass reduction is not numeric")
    if float(additional.get("value", 1.0)) != 0.0:
        raise ValueError("actual additional-mass reduction is not exact zero")
    if additional.get("term_elidable_for_first_bootstrap") is not True:
        raise ValueError("actual additional-mass reduction is not first-bootstrap elidable")
    if additional.get("machine_LOAD_pointer_identity_joined") is not False:
        raise ValueError("additional-mass machine pointer identity was unexpectedly prejoined")

    analysis = report.get("analysis")
    if not isinstance(analysis, Mapping):
        raise ValueError("memory-LOAD analysis missing")
    raw_worklist = analysis.get("exact_object_field_worklist")
    if not isinstance(raw_worklist, list):
        raise ValueError("exact_object_field_worklist missing")
    if not raw_worklist:
        raise ValueError("exact_object_field_worklist must not be empty")

    rows: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, ...], int, int]] = set()
    for index, raw in enumerate(raw_worklist):
        if not isinstance(raw, Mapping):
            raise ValueError(f"exact_object_field_worklist[{index}] must be an object")
        origins = _string_list(
            raw.get("base_origin_expression_set"),
            field=f"exact_object_field_worklist[{index}].base_origin_expression_set",
        )
        displacement = raw.get("displacement")
        width = raw.get("load_width")
        if not isinstance(displacement, int):
            raise ValueError(f"exact_object_field_worklist[{index}].displacement invalid")
        if not isinstance(width, int) or width <= 0:
            raise ValueError(f"exact_object_field_worklist[{index}].load_width invalid")
        fields = _string_list(
            raw.get("feeds_offset33b_fields"),
            field=f"exact_object_field_worklist[{index}].feeds_offset33b_fields",
        )
        if raw.get("semantic_join_ready") is not False:
            raise ValueError(
                f"exact_object_field_worklist[{index}] unexpectedly preclaims semantic join"
            )
        if raw.get("semantic_owner_or_resource") is not None:
            raise ValueError(
                f"exact_object_field_worklist[{index}] unexpectedly preclaims semantic owner"
            )
        if raw.get("semantic_field_name") is not None:
            raise ValueError(
                f"exact_object_field_worklist[{index}] unexpectedly preclaims semantic field"
            )
        key = (tuple(origins), displacement, width)
        if key in seen:
            raise ValueError(f"duplicate exact object-field group {key!r}")
        seen.add(key)
        rows.append(
            {
                **raw,
                "base_origin_expression_set": origins,
                "displacement": displacement,
                "load_width": width,
                "feeds_offset33b_fields": fields,
            }
        )
    return report, rows


def _classify_origins(origins: list[str]) -> tuple[str, str | None]:
    if origins == ["entry:ECX"]:
        return "direct-HDVehicle-this", "HDVehicle"
    if len(origins) == 1:
        origin = origins[0]
        if _ENTRY_ORIGIN.fullmatch(origin) is not None:
            return "other-entry-register", None
        if _MEMORY_ORIGIN.fullmatch(origin) is not None:
            return "indirect-owner-slot", None
        return "single-unresolved-origin", None
    return "multi-origin-unresolved", None


def _field_ref(owner: str, displacement: int) -> str:
    sign = "+" if displacement >= 0 else "-"
    return f"{owner}{sign}0x{abs(displacement):x}"


def analyze_bmw_offset33b_field_owner_frontier(memory_load_path: Path) -> dict[str, Any]:
    report, worklist = _validate_input(memory_load_path)

    direct_hdvehicle: list[dict[str, Any]] = []
    indirect_slots: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    classified: list[dict[str, Any]] = []

    for index, row in enumerate(worklist):
        origins = list(row["base_origin_expression_set"])
        owner_class, semantic_owner = _classify_origins(origins)
        common = {
            "source_worklist_index": index,
            "base_origin_expression_set": origins,
            "displacement": row["displacement"],
            "displacement_hex": row.get("displacement_hex")
            or (
                f"0x{row['displacement']:x}"
                if row["displacement"] >= 0
                else f"-0x{-row['displacement']:x}"
            ),
            "load_width": row["load_width"],
            "load_node_ids": list(row.get("load_node_ids") or []),
            "load_instructions": list(row.get("load_instructions") or []),
            "feeds_offset33b_fields": list(row["feeds_offset33b_fields"]),
            "owner_class": owner_class,
            "semantic_owner_domain": semantic_owner,
            "semantic_field_name": None,
            "semantic_field_value_ready": False,
            "numeric_loaded_value_proven": False,
        }
        if owner_class == "direct-HDVehicle-this":
            promoted = {
                **common,
                "owner_join_ready": True,
                "exact_owner_field_reference": _field_ref(
                    "HDVehicle", int(row["displacement"])
                ),
                "producer_this_identity_basis": {
                    "function": PRODUCER,
                    "name": PRODUCER_NAME,
                    "role": PRODUCER_ROLE,
                    "calling_convention": "__thiscall",
                    "entry_receiver_register": "ECX",
                    "exact_this_origin": "entry:ECX",
                },
            }
            direct_hdvehicle.append(promoted)
            classified.append(promoted)
        elif owner_class == "indirect-owner-slot":
            promoted = {
                **common,
                "owner_join_ready": False,
                "exact_owner_field_reference": None,
                "indirect_owner_origin_expression": origins[0],
                "candidate_owner_types": [],
                "VDF_SDF_tire_identity_assumed": False,
            }
            indirect_slots.append(promoted)
            classified.append(promoted)
        else:
            blocked = {
                **common,
                "owner_join_ready": False,
                "exact_owner_field_reference": None,
                "required_evidence": (
                    "resolve this base-origin expression to one concrete object before "
                    "assigning HDV/VDF/SDF/tire semantics"
                ),
            }
            unresolved.append(blocked)
            classified.append(blocked)

    reductions = report["known_semantic_reductions"]
    additional = reductions["additional_mass_first_bootstrap"]
    handoff = report["handoff"]
    additional_machine_join_ready = bool(
        handoff.get("offset33b_additional_mass_machine_LOAD_join_ready") is True
    )
    additional_zero_ready = bool(
        additional.get("proof_format") == ACTUAL_ZERO_FORMAT
        and additional.get("numeric_value_proven") is True
        and float(additional.get("value", 1.0)) == 0.0
        and additional.get("term_elidable_for_first_bootstrap") is True
        and additional.get("retracted_manager_record_zero_claim_reused") is False
    )
    additional_zero_available = additional_zero_ready and additional_machine_join_ready

    direct_ready = bool(direct_hdvehicle)
    all_owner_domains_classified = len(unresolved) == 0
    all_semantic_owners_ready = bool(classified) and all(
        row["owner_join_ready"] is True for row in classified
    )

    blockers: list[dict[str, Any]] = []
    if indirect_slots:
        blockers.append(
            {
                "id": "offset33b-indirect-owner-slot-semantics-unproven",
                "count": len(indirect_slots),
                "origin_expressions": sorted(
                    {row["indirect_owner_origin_expression"] for row in indirect_slots}
                ),
                "required_evidence": (
                    "join each indirect memory-derived base expression to the exact "
                    "HDV/VDF/SDF/tire owner pointer before assigning semantic fields"
                ),
            }
        )
    if unresolved:
        blockers.append(
            {
                "id": "offset33b-field-owner-origin-unresolved",
                "count": len(unresolved),
                "required_evidence": (
                    "resolve non-ECX entry/multi/derived origins before resource-field joining"
                ),
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "all-owner-semantics-ready"
            if all_semantic_owners_ready
            else "owner-domain-frontier-ready"
        ),
        "ready": True,
        "inputs": {"memory_load_provenance": str(memory_load_path)},
        "producer_semantics": {
            "function": PRODUCER,
            "name": PRODUCER_NAME,
            "role": PRODUCER_ROLE,
            "mnemonic_sha256": PRODUCER_MNEMONIC_SHA256,
            "calling_convention": "__thiscall",
            "entry_ECX_is_HDVehicle_this": True,
        },
        "analysis": {
            "input_field_group_count": len(worklist),
            "classified_field_group_count": len(classified),
            "direct_HDVehicle_field_count": len(direct_hdvehicle),
            "indirect_owner_slot_count": len(indirect_slots),
            "unresolved_owner_group_count": len(unresolved),
            "classified_groups": classified,
            "direct_HDVehicle_fields": direct_hdvehicle,
            "indirect_owner_slots": indirect_slots,
            "unresolved_owner_groups": unresolved,
        },
        "known_semantic_reductions": {
            "additional_mass_first_bootstrap_zero_ready": additional_zero_ready,
            "additional_mass_proof_format": additional.get("proof_format"),
            "additional_mass_machine_LOAD_join_ready": additional_machine_join_ready,
            "additional_mass_zero_available_for_numeric_evaluator": additional_zero_available,
            "additional_mass_zero_applied_by_this_stage": False,
            "retracted_manager_record_zero_claim_used": False,
        },
        "handoff": {
            "offset33b_memory_LOAD_frontier_ready": True,
            "offset33b_exact_memory_field_worklist_ready": True,
            "offset33b_direct_HDVehicle_field_owner_joins_ready": direct_ready,
            "offset33b_all_LOAD_owner_domains_classified": all_owner_domains_classified,
            "offset33b_all_field_owner_semantics_ready": all_semantic_owners_ready,
            "offset33b_semantic_field_names_ready": False,
            "offset33b_additional_mass_machine_LOAD_join_ready": additional_machine_join_ready,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "next_proof": {
            "target": (
                "resolve only indirect/unresolved owner bases, then map exact owner+offset "
                "references to semantic HDV/VDF/SDF/tire fields"
            ),
            "direct_HDVehicle_fields_ready_for_field_semantic_lookup": [
                row["exact_owner_field_reference"] for row in direct_hdvehicle
            ],
            "indirect_owner_slots_requiring_pointer_join": [
                {
                    "origin_expression": row["indirect_owner_origin_expression"],
                    "displacement": row["displacement"],
                    "load_width": row["load_width"],
                    "feeds_offset33b_fields": row["feeds_offset33b_fields"],
                }
                for row in indirect_slots
            ],
            "unresolved_owner_groups_requiring_provenance": [
                {
                    "base_origin_expression_set": row["base_origin_expression_set"],
                    "displacement": row["displacement"],
                    "load_width": row["load_width"],
                    "feeds_offset33b_fields": row["feeds_offset33b_fields"],
                }
                for row in unresolved
            ],
        },
        "scope": {
            "actual_object_additional_mass_proof_consumed": True,
            "retracted_manager_record_zero_contract_accepted": False,
            "FUN_0076b280_entry_ECX_promoted_to_HDVehicle_this": True,
            "other_entry_register_promoted_to_argument_semantics": False,
            "memory_origin_promoted_to_HDVehicle_VDF_SDF_or_tire": False,
            "field_semantic_name_inferred_from_displacement": False,
            "owner_join_promoted_to_numeric_value": False,
            "additional_mass_zero_reapplied_by_this_stage": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("memory_load_provenance", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze_bmw_offset33b_field_owner_frontier(args.memory_load_provenance)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
