#!/usr/bin/env python3
"""Compose bounded Participants Manager root-origin coverage for Process 1B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.Manager374RootOriginCoverage/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

INPUTS = {
    "literal": ROOT / "evidence/hdvehicle_64e8_manager_374_direct_singleton_reference_surface.json",
    "static": ROOT / "evidence/hdvehicle_64e8_manager_374_static_pointer_occurrence_surface.json",
    "interior": ROOT / "evidence/hdvehicle_64e8_manager_374_static_interior_relocation_surface.json",
    "reconstruction": ROOT / "evidence/p1b_manager374_reconstruction_coverage.json",
    "exact_alias": ROOT / "evidence/p1b_manager374_exact_root_alias_closure.json",
    "computed": ROOT / "evidence/p1b_manager374_computed_runtime_closure.json",
    "participants": ROOT / "evidence/p1b_manager374_participants_lifecycle_closure.json",
}

EXPECTED = {
    "literal": "SHIFT.HDVehicle64e8Manager374DirectSingletonReferenceSurface/1",
    "static": "SHIFT.HDVehicle64e8Manager374StaticPointerOccurrenceSurface/1",
    "interior": "SHIFT.HDVehicle64e8Manager374StaticInteriorRelocationSurface/1",
    "reconstruction": "SHIFT.P1B.Manager374ReconstructionCoverage/1",
    "exact_alias": "SHIFT.P1B.Manager374ExactRootAliasClosure/1",
    "computed": "SHIFT.P1B.Manager374ComputedRuntimeClosure/1",
    "participants": "SHIFT.P1B.Manager374ParticipantsLifecycleClosure/1",
}


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not data.get("ready"):
        raise ValueError(f"upstream contract not ready: {path}")
    return data


def _require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def build() -> dict:
    data = {name: _load(path) for name, path in INPUTS.items()}
    for name, expected in EXPECTED.items():
        _require(data[name].get("format") == expected, f"{name}: format drift")

    for name in ("literal", "static", "interior", "reconstruction", "exact_alias", "participants"):
        _require(data[name]["authority"]["retail_executable_sha256"] == RETAIL_SHA256, f"{name}: retail hash drift")

    literal = data["literal"]
    static = data["static"]
    interior = data["interior"]
    recon = data["reconstruction"]
    alias = data["exact_alias"]
    computed = data["computed"]
    participants = data["participants"]

    _require(literal["manager_singleton"]["address"] == "0x00bc9fc0", "manager singleton drift")
    _require(literal["whole_image_immediate_reference_surface"]["reference_count"] == 3, "literal reference count drift")
    _require(literal["adjudication"]["independent_runtime_singleton_reconstruction_site_count"] == 0, "independent literal root appeared")

    _require(static["adjudication"]["static_exact_pointer_cell_surface_complete"] is True, "static pointer surface incomplete")
    _require(static["adjudication"]["static_exact_pointer_cell_count"] == 0, "static exact pointer cell appeared")
    _require(static["adjudication"]["table_or_global_load_of_preinitialized_exact_manager_root_possible"] is False, "preinitialized exact manager root became possible")

    _require(interior["static_cell_scan"]["aligned_cells_in_manager_range"] == 0, "static interior manager pointer appeared")
    _require(interior["adjudication"]["static_interior_pointer_surface_complete"] is True, "static interior surface incomplete")
    _require(interior["adjudication"]["relocation_derived_surface_complete"] is True, "relocation surface incomplete")
    _require(interior["relocation_surface"]["base_relocation_entries_available"] is False, "base relocation entries appeared")

    _require(recon["adjudication"]["simple_immediate_arithmetic_reconstruction_complete"] is True, "simple reconstruction incomplete")
    _require(recon["adjudication"]["constant_only_multi_register_reconstruction_complete"] is True, "multi-register reconstruction incomplete")
    _require(recon["adjudication"]["bounded_non_literal_manager_root_reconstruction_count"] == 0, "bounded non-literal root appeared")

    _require(alias["adjudication"]["exact_getter_root_alias_surface_complete"] is True, "getter alias surface incomplete")
    _require(alias["adjudication"]["escaped_storage_paths_complete"] is True, "getter storage escape reopened")
    _require(alias["adjudication"]["stack_argument_alias_paths_complete"] is True, "getter stack argument escape reopened")
    _require(alias["surface"]["exact_root_object_or_global_store_count"] == 0, "getter root object/global store appeared")

    _require(computed["adjudication"]["computed_runtime_paths_complete"] is True, "computed runtime paths incomplete")
    _require(computed["surface"]["remaining_computed_runtime_path_count"] == 0, "computed runtime path reopened")

    padj = participants["adjudication"]
    _require(padj["participants_lifecycle_nested_writer_surface_complete"] is True, "Participants lifecycle nested writer surface incomplete")
    _require(padj["participants_lifecycle_helper_or_indirect_setter_surface_complete"] is True, "Participants lifecycle helper surface incomplete")
    _require(padj["participants_lifecycle_nonzero_manager_374_writer_found"] is False, "Participants lifecycle nonzero writer appeared")
    _require(padj["external_provider_count"] == 7, "provider count changed without Process 2 proof")

    refs = literal["whole_image_immediate_reference_surface"]["references"]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": RETAIL_SHA256},
        "inputs": {name: EXPECTED[name] for name in EXPECTED},
        "manager_root": "0x00bc9fc0",
        "manager_target": "manager+0x374",
        "known_literal_origins": {
            "count": len(refs),
            "sites": [row["instruction_address"] for row in refs],
            "independent_runtime_producer_count": literal["adjudication"]["independent_runtime_singleton_reconstruction_site_count"],
        },
        "static_and_loader_origins": {
            "whole_file_exact_occurrence_count": static["occurrences"]["whole_file_count"],
            "non_text_exact_pointer_occurrence_count": static["occurrences"]["non_text_count"],
            "static_exact_pointer_cell_count": static["adjudication"]["static_exact_pointer_cell_count"],
            "aligned_static_interior_cell_count": interior["static_cell_scan"]["aligned_cells_in_manager_range"],
            "base_relocation_entries_available": interior["relocation_surface"]["base_relocation_entries_available"],
        },
        "bounded_reconstruction": {
            "simple_mov_immediate_seed_count": recon["surface"]["simple_mov_immediate_seed_count"],
            "simple_arithmetic_transition_count": recon["surface"]["simple_arithmetic_transition_count"],
            "constant_multi_register_transition_count": recon["surface"]["constant_multi_register_transition_count"],
            "non_literal_exact_root_count": recon["adjudication"]["bounded_non_literal_manager_root_reconstruction_count"],
        },
        "exact_getter_aliases": {
            "direct_getter_callsite_count": alias["surface"]["whole_image_direct_getter_callsite_count"],
            "object_or_global_store_count": alias["surface"]["exact_root_object_or_global_store_count"],
            "stack_save_count": alias["surface"]["exact_root_stack_save_count"],
            "immediate_push_eax_count": alias["surface"]["immediate_push_eax_after_getter_count"],
            "escaped_storage_complete": alias["adjudication"]["escaped_storage_paths_complete"],
            "stack_argument_aliases_complete": alias["adjudication"]["stack_argument_alias_paths_complete"],
        },
        "writer_and_helper_surfaces": {
            "computed_runtime_remaining_path_count": computed["surface"]["remaining_computed_runtime_path_count"],
            "participants_lifecycle_nonzero_writer_found": padj["participants_lifecycle_nonzero_manager_374_writer_found"],
            "participants_lifecycle_helper_or_indirect_setter_surface_complete": padj["participants_lifecycle_helper_or_indirect_setter_surface_complete"],
            "participants_lifecycle_can_place_fixed_hdvehicle_4330_into_manager_374": padj["participants_lifecycle_can_place_fixed_hdvehicle_4330_into_manager_374"],
        },
        "adjudication": {
            "bounded_manager_root_origin_classes_composed": True,
            "known_literal_static_loader_constant_reconstruction_origins_complete": True,
            "known_bounded_origin_classes_create_unrelated_manager_root": False,
            "exact_getter_alias_persistence_complete": True,
            "computed_runtime_writer_paths_complete": True,
            "participants_lifecycle_helper_writer_surface_complete": True,
            "opaque_helper_or_external_memory_root_origin_surface_complete": False,
            "unrecognized_runtime_transform_root_origin_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "surviving_frontier": [
            "opaque helper-returned exact manager roots synthesized from unrelated inputs",
            "externally/runtime initialized memory containing the exact manager root without a canonical getter lineage",
            "unrecognized runtime transforms outside the bounded arithmetic/multi-register classes",
        ],
        "limits": [
            "This is a composition of bounded retail machine-evidence contracts, not a proof over arbitrary process memory.",
            "The final manager+0x374 identity join remains fail-closed until the surviving opaque/external runtime-origin class is closed or shown unable to reach another target writer.",
            "No identity is inferred from matching numeric offsets."
        ],
        "next_step": "Reduce the remaining opaque/external manager-root origin class to concrete machine candidates; only then decide the final manager+0x374 -> HDVehicle+0x4330 rejection and 0x004b86cf slot2 adjudication.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = build()
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
