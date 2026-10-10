#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DIRECT = ROOT / "evidence/hdvehicle_64e8_manager_374_exact_root_direct_callee_surface.json"
COMPUTED = ROOT / "evidence/p1b_manager374_computed_runtime_closure.json"
BULK = ROOT / "evidence/hdvehicle_64e8_manager_374_bulkcopy_camera_rejection.json"
OUT = ROOT / "evidence/p1b_manager374_writer_coverage.json"


def load(path):
    return json.loads(path.read_text())


def build():
    direct = load(DIRECT)
    computed = load(COMPUTED)
    bulk = load(BULK)
    assert direct["format"] == "SHIFT.HDVehicle64e8Manager374ExactRootDirectCalleeSurface/1"
    assert computed["format"] == "SHIFT.P1B.Manager374ComputedRuntimeClosure/1"
    assert bulk["format"] == "SHIFT.HDVehicle64e8Manager374BulkCopyCameraRejection/1"
    return {
        "format": "SHIFT.P1B.Manager374WriterCoverage/1",
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [direct["format"], computed["format"], bulk["format"]],
        "surface": {
            "exact_root_direct_callee_count": direct["adjudication"]["direct_callee_count"],
            "exact_root_direct_manager_374_writer_count": direct["adjudication"]["direct_callees_writing_manager_374_count"],
            "only_direct_nonzero_writer": direct["adjudication"]["only_direct_nonzero_writer"],
            "only_direct_nonzero_writer_value_domain": direct["adjudication"]["only_direct_nonzero_writer_value_domain"],
            "computed_runtime_original_path_count": computed["surface"]["original_computed_runtime_path_count"],
            "computed_runtime_remaining_path_count": computed["surface"]["remaining_computed_runtime_path_count"],
            "direct_bulk_copy_literal_writer_surface_complete": bulk["bulk_copy_surface"]["direct_bulk_copy_literal_writer_surface_complete"],
            "manager_374_literal_writer_surface_complete": bulk["adjudication"]["manager_374_literal_writer_surface_complete"],
        },
        "adjudication": {
            "direct_exact_root_writer_surface_complete": direct["adjudication"]["exact_root_direct_callee_surface_complete"],
            "computed_address_manager_374_writer_surface_complete": computed["adjudication"]["computed_address_manager_374_writer_surface_complete"],
            "literal_and_direct_bulk_copy_writer_surface_complete": bulk["adjudication"]["manager_374_literal_writer_surface_complete"],
            "bounded_manager_374_writer_classes_complete": True,
            "bounded_writer_classes_place_fixed_hdvehicle_4330_into_manager_374": False,
            "escaped_storage_paths_complete": False,
            "stack_argument_alias_paths_complete": False,
            "helper_alias_or_non_vtable_indirect_setter_still_possible": True,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes direct exact-root, computed-address, literal-store and direct bulk-copy writer classes only.",
            "Escaped manager-root aliases, stack-argument aliases, helper-mediated stores and non-vtable indirect setters remain open.",
            "No identity is inferred from matching numeric offsets."
        ],
        "next_step": "Close escaped-storage and stack-argument manager-root aliases plus helper/non-vtable indirect setters, then perform the final manager+0x374 -> HDVehicle+0x4330 identity join and 0x004b86cf adjudication."
    }


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n")
