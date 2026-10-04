#!/usr/bin/env python3
"""Run the BMW offset33b proof through owner/resource semantic frontiers.

This wrapper deliberately performs only one Ghidra instruction export, inherited
from ``run_bmw_offset33b_reduced_static_proof.py``.  It then consumes the exact
memory-LOAD worklist with the existing owner classifier and validates the
hash-locked BMW resource inputs.  It does not guess a field name from a
machine displacement and therefore keeps the numeric offset33b gate false until
pointer/owner provenance is sufficient for a later evaluator.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = _SCRIPT_DIR.parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_offset33b_field_owner_frontier as _owners
import run_bmw_offset33b_reduced_static_proof as _reduced
import validate_bmw_offset33b_resource_inputs as _resources

FORMAT = "SHIFT.BMWOffset33bSemanticStaticProofBundle/1"
OWNER_FILE = "06_bmw_offset33b_field_owner_frontier.json"
RESOURCE_VALIDATION_FILE = "07_bmw_offset33b_resource_inputs_validation.json"
BUNDLE_FILE = "bmw_offset33b_semantic_static_proof_bundle.json"
DEFAULT_RESOURCE_INPUTS = ROOT / "evidence" / "bmw_offset33b_resource_inputs.json"
DEFAULT_PHYSICS_MANIFEST = ROOT / "evidence" / "bmw_m3_vehicle_physics_manifest.json"
DEFAULT_BODY0_RESOURCE = ROOT / "evidence" / "bmw_body0_bind_resource_materialization.json"


def _write(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _handoff(report: Mapping[str, Any]) -> Mapping[str, Any]:
    value = report.get("handoff")
    return value if isinstance(value, Mapping) else {}


def _resource_mapping(resource_inputs_path: Path) -> dict[str, Any]:
    value = json.loads(resource_inputs_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != _resources.INPUT_FORMAT:
        raise ValueError(f"{resource_inputs_path}: expected {_resources.INPUT_FORMAT}")
    mapping = value.get("fun_0076b280_load_data_mapping")
    if not isinstance(mapping, Mapping):
        raise ValueError("offset33b resource input load-data mapping missing")
    return {
        "direct_CDF_fields": list(mapping.get("direct_fields") or []),
        "observed_but_not_directly_mapped": list(
            mapping.get("observed_but_not_directly_mapped_here") or []
        ),
        "derived_load_data_offsets_not_promoted": list(
            mapping.get("derived_load_data_offsets_not_promoted_from_resource_name") or []
        ),
    }


def _compose_bundle(
    *,
    reduced: Mapping[str, Any],
    owner: Mapping[str, Any] | None,
    resource_validation: Mapping[str, Any],
    resource_mapping: Mapping[str, Any],
    artifacts: Mapping[str, str],
) -> dict[str, Any]:
    reduced_handoff = _handoff(reduced)
    owner_handoff = _handoff(owner or {})
    resource_handoff = _handoff(resource_validation)

    exact_worklist = reduced_handoff.get("offset33b_exact_memory_field_worklist_ready") is True
    owner_ready = bool(owner is not None and owner.get("ready") is True)
    resources_ready = bool(
        resource_validation.get("ready") is True
        and resource_handoff.get("offset33b_resource_inputs_ready") is True
    )

    owner_analysis = owner.get("analysis") if isinstance(owner, Mapping) else {}
    if not isinstance(owner_analysis, Mapping):
        owner_analysis = {}

    if not exact_worklist:
        status = "blocked-before-semantic-frontier"
    elif not owner_ready or not resources_ready:
        status = "semantic-frontier-incomplete"
    elif owner_handoff.get("offset33b_all_field_owner_semantics_ready") is True:
        status = "owner-and-resource-frontiers-ready"
    else:
        status = "pointer-owner-join-frontier-ready"

    direct_hdvehicle = list(owner_analysis.get("direct_HDVehicle_fields") or [])
    indirect_slots = list(owner_analysis.get("indirect_owner_slots") or [])
    unresolved = list(owner_analysis.get("unresolved_owner_groups") or [])

    return {
        "format": FORMAT,
        "version": 1,
        "completed": True,
        "status": status,
        "artifacts": dict(artifacts),
        "frontier": {
            "direct_HDVehicle_fields": direct_hdvehicle,
            "indirect_owner_slots": indirect_slots,
            "unresolved_owner_groups": unresolved,
            "resource_mapping": dict(resource_mapping),
        },
        "handoff": {
            "offset33b_store_provenance_ready": bool(
                reduced_handoff.get("offset33b_store_provenance_ready") is True
            ),
            "offset33b_memory_LOAD_frontier_ready": bool(
                reduced_handoff.get("offset33b_memory_LOAD_frontier_ready") is True
            ),
            "offset33b_exact_memory_field_worklist_ready": exact_worklist,
            "offset33b_field_owner_frontier_ready": owner_ready,
            "offset33b_resource_inputs_ready": resources_ready,
            "offset33b_direct_CDF_load_data_mapping_ready": bool(
                resource_handoff.get("offset33b_direct_CDF_load_data_mapping_ready") is True
            ),
            "offset33b_all_field_owner_semantics_ready": bool(
                owner_handoff.get("offset33b_all_field_owner_semantics_ready") is True
            ),
            "offset33b_semantic_field_names_ready": False,
            "offset33b_memory_LOAD_semantic_join_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "next_proof": {
            "target": (
                "join only the reported indirect/unresolved base origins to concrete owners and "
                "match proven CDF load-data owner loads to the exact resource mapping"
            ),
            "direct_HDVehicle_field_references": [
                row.get("exact_owner_field_reference")
                for row in direct_hdvehicle
                if isinstance(row, Mapping) and row.get("exact_owner_field_reference")
            ],
            "indirect_owner_slots": [
                {
                    "origin_expression": row.get("indirect_owner_origin_expression"),
                    "displacement": row.get("displacement"),
                    "load_width": row.get("load_width"),
                    "feeds_offset33b_fields": row.get("feeds_offset33b_fields"),
                }
                for row in indirect_slots
                if isinstance(row, Mapping)
            ],
            "unresolved_owner_groups": unresolved,
            "resource_direct_CDF_fields": list(resource_mapping.get("direct_CDF_fields") or []),
            "derived_load_data_offsets_kept_unassigned": list(
                resource_mapping.get("derived_load_data_offsets_not_promoted") or []
            ),
        },
        "scope": {
            "targeted_Ghidra_export_count": 1,
            "targeted_Ghidra_function": "0x0076b280",
            "resource_semantics_inferred_from_displacement": False,
            "other_entry_register_promoted_to_argument_semantics": False,
            "memory_origin_promoted_to_CDF_SDF_or_tire_owner": False,
            "derived_load_data_0x338_promoted_to_CDF_field": False,
            "numeric_offset33b_claimed": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def run_bmw_offset33b_semantic_static_proof(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    output_dir: Path,
    *,
    program_name: str = _reduced._base._stores.PROGRAM,
    relation_path: Path = _reduced._base.DEFAULT_RELATION,
    resource_inputs_path: Path = DEFAULT_RESOURCE_INPUTS,
    physics_manifest_path: Path = DEFAULT_PHYSICS_MANIFEST,
    body0_resource_path: Path = DEFAULT_BODY0_RESOURCE,
    ghidra_home: Path | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    reduced = _reduced.run_bmw_offset33b_reduced_static_proof(
        project_dir,
        project_name,
        ghidra_export,
        output_dir,
        program_name=program_name,
        relation_path=relation_path,
        ghidra_home=ghidra_home,
        timeout_seconds=timeout_seconds,
    )

    load_path = output_dir / _reduced.LOAD_FILE
    owner_path = output_dir / OWNER_FILE
    resource_validation_path = output_dir / RESOURCE_VALIDATION_FILE
    bundle_path = output_dir / BUNDLE_FILE

    resource_validation = _resources.validate(
        resource_inputs_path,
        physics_manifest_path,
        body0_resource_path,
    )
    _write(resource_validation_path, resource_validation)
    resource_mapping = _resource_mapping(resource_inputs_path)

    reduced_handoff = _handoff(reduced)
    owner: dict[str, Any] | None = None
    if reduced_handoff.get("offset33b_exact_memory_field_worklist_ready") is True:
        owner = _owners.analyze_bmw_offset33b_field_owner_frontier(load_path)
        _write(owner_path, owner)

    artifacts = {
        "reduced_static_proof_bundle": str(output_dir / _reduced.BUNDLE_FILE),
        "instruction_export": str(output_dir / _reduced._base.INSTRUCTION_FILE),
        "store_provenance": str(output_dir / _reduced._base.PROVENANCE_FILE),
        "memory_load_provenance": str(load_path),
        "resource_inputs": str(resource_inputs_path),
        "resource_inputs_validation": str(resource_validation_path),
    }
    if owner is not None:
        artifacts["field_owner_frontier"] = str(owner_path)

    bundle = _compose_bundle(
        reduced=reduced,
        owner=owner,
        resource_validation=resource_validation,
        resource_mapping=resource_mapping,
        artifacts=artifacts,
    )
    _write(bundle_path, bundle)
    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("project_name")
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--program-name", default=_reduced._base._stores.PROGRAM)
    parser.add_argument("--relation", type=Path, default=_reduced._base.DEFAULT_RELATION)
    parser.add_argument("--resource-inputs", type=Path, default=DEFAULT_RESOURCE_INPUTS)
    parser.add_argument("--physics-manifest", type=Path, default=DEFAULT_PHYSICS_MANIFEST)
    parser.add_argument("--body0-resource", type=Path, default=DEFAULT_BODY0_RESOURCE)
    parser.add_argument("--ghidra-home", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args(argv)

    report = run_bmw_offset33b_semantic_static_proof(
        args.project_dir,
        args.project_name,
        args.ghidra_export,
        args.output_dir,
        program_name=args.program_name,
        relation_path=args.relation,
        resource_inputs_path=args.resource_inputs,
        physics_manifest_path=args.physics_manifest,
        body0_resource_path=args.body0_resource,
        ghidra_home=args.ghidra_home,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
