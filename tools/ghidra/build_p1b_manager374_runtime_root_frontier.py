#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

INPUTS = {
    "reconstruction": ROOT / "evidence/p1b_manager374_reconstruction_coverage.json",
    "static_interior": ROOT / "evidence/hdvehicle_64e8_manager_374_static_interior_relocation_surface.json",
    "vslot24": ROOT / "evidence/hdvehicle_64e8_manager_374_vslot24_eax_residue_surface.json",
    "vslot0c": ROOT / "evidence/hdvehicle_64e8_manager_374_vslot0c_dispatch_closure.json",
    "constructor_escape": ROOT / "evidence/hdvehicle_64e8_render_manager_constructor_exact_this_escape_closure.json",
}


def load(name):
    return json.loads(INPUTS[name].read_text())


def build():
    recon = load("reconstruction")
    interior = load("static_interior")
    slot24 = load("vslot24")
    slot0c = load("vslot0c")
    ctor = load("constructor_escape")

    assert recon["ready"] is True
    assert interior["adjudication"]["static_interior_pointer_surface_complete"] is True
    assert interior["adjudication"]["relocation_derived_surface_complete"] is True
    assert slot24["adjudication"]["vslot_24_can_export_exact_manager_root_to_its_observed_consumer"] is False
    assert slot0c["adjudication"]["fun_0045b130_alternate_manager_root_source_closed"] is True
    assert ctor["adjudication"]["pre_global_store_constructor_escape_surface_closed_negative"] is True

    return {
        "format": "SHIFT.P1B.Manager374RuntimeRootFrontier/1",
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "upstream_contracts": [
            recon["format"],
            interior["format"],
            slot24["format"],
            slot0c["format"],
            ctor["format"],
        ],
        "closed_runtime_root_classes": {
            "static_exact_or_interior_pointer_cells": True,
            "shipped_pe_base_relocations": True,
            "constant_same_or_multi_register_reconstruction": True,
            "exact_getter_persistence_and_stack_argument_aliases": True,
            "constructor_pre_global_store_exact_this_escape": True,
            "vslot24_opaque_eax_residue_export": True,
            "fun_0045b130_exact_global_first_hop_dispatch": True,
        },
        "observed_counts": {
            "static_interior_aligned_cells_in_manager_range": interior["static_cell_scan"]["aligned_cells_in_manager_range"],
            "vslot0c_exact_global_source_read_count": slot0c["exhaustive_exact_manager_first_hop"]["source_read_count"],
            "vslot0c_exact_global_source_function_count": slot0c["exhaustive_exact_manager_first_hop"]["source_function_count"],
            "vslot0c_proven_indirect_receiver_transfer_count": slot0c["exhaustive_exact_manager_first_hop"]["proven_indirect_receiver_transfer_count"],
            "vslot0c_target_dispatch_count": slot0c["exhaustive_exact_manager_first_hop"]["target_slot_plus_0x0c_dispatch_count"],
            "constructor_exact_this_memory_store_count": ctor["constructor"]["memory_stores_with_exact_this_as_value_count"],
            "constructor_exact_this_helper_transfer_count": ctor["constructor"]["helper_argument_transfers_of_exact_this_count"],
        },
        "surviving_frontier": {
            "runtime_created_or_copied_post_construction_outer_aliases": True,
            "external_or_unknown_origin_outer_alias_copies": True,
            "opaque_runtime_sources_not_rooted_in_closed_exact_global_first_hop": True,
        },
        "adjudication": {
            "bounded_runtime_root_classes_composed": True,
            "known_bounded_runtime_root_paths_can_create_manager_374_to_hdvehicle_4330_join": False,
            "runtime_created_or_copied_outer_alias_surface_complete": False,
            "memory_load_or_opaque_runtime_reconstruction_complete": False,
            "helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This is a composition of already-merged bounded machine-evidence contracts; it does not invent a global runtime alias absence proof.",
            "The remaining frontier is post-construction runtime-created/copied outer-object aliases plus external/unknown-origin opaque sources.",
            "No identity is inferred from matching offsets.",
        ],
        "next_step": "Close post-construction runtime-created/copied aliases of the outer object and external/unknown-origin opaque manager-root sources; then revisit the final manager+0x374 identity join and 0x004b86cf adjudication.",
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
