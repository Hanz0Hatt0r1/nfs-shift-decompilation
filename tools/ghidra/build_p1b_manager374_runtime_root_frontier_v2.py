#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.Manager374RuntimeRootFrontier/2"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

INPUTS = {
    "frontier_v1": ROOT / "evidence/p1b_manager374_runtime_root_frontier.json",
    "constructor": ROOT / "evidence/hdvehicle_64e8_render_manager_constructor_exact_this_escape_closure.json",
    "canonical": ROOT / "evidence/p1b_render_manager_canonical_access_closure.json",
    "copy_return": ROOT / "evidence/p1b_render_manager_copy_return_closure.json",
    "derived": ROOT / "evidence/p1b_render_manager_derived_subobject_closure.json",
    "live_call": ROOT / "evidence/p1b_render_manager_live_call_boundary_closure.json",
    "named_opaque": ROOT / "evidence/p1b_manager374_named_opaque_candidate_closure.json",
}

EXPECTED = {
    "frontier_v1": "SHIFT.P1B.Manager374RuntimeRootFrontier/1",
    "constructor": "SHIFT.HDVehicle64e8RenderManagerConstructorExactThisEscapeClosure/1",
    "canonical": "SHIFT.P1B.RenderManagerCanonicalAccessClosure/1",
    "copy_return": "SHIFT.P1B.RenderManagerCopyReturnClosure/1",
    "derived": "SHIFT.P1B.RenderManagerDerivedSubobjectClosure/1",
    "live_call": "SHIFT.P1B.RenderManagerLiveCallBoundaryClosure/1",
    "named_opaque": "SHIFT.P1B.Manager374NamedOpaqueCandidateClosure/1",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(name: str) -> dict:
    data = json.loads(INPUTS[name].read_text(encoding="utf-8"))
    require(data.get("format") == EXPECTED[name], f"{name}: format drift")
    require(data.get("ready") is True, f"{name}: contract not ready")
    authority = data.get("authority")
    if isinstance(authority, dict) and "retail_executable_sha256" in authority:
        require(authority["retail_executable_sha256"] == RETAIL_SHA256, f"{name}: retail SHA drift")
    return data


def build() -> dict:
    v1 = load("frontier_v1")
    ctor = load("constructor")
    canonical = load("canonical")
    copy_return = load("copy_return")
    derived = load("derived")
    live = load("live_call")
    opaque = load("named_opaque")

    require(v1["adjudication"]["bounded_runtime_root_classes_composed"] is True,
            "v1 bounded runtime-root composition reopened")

    require(ctor["adjudication"]["pre_global_store_constructor_escape_surface_closed_negative"] is True,
            "constructor pre-global escape reopened")
    require(ctor["constructor"]["memory_stores_with_exact_this_as_value_count"] == 0,
            "constructor exact-this memory store found")
    require(ctor["constructor"]["helper_argument_transfers_of_exact_this_count"] == 0,
            "constructor exact-this helper transfer found")

    cadj = canonical["adjudication"]
    require(cadj["candidate_global_non_null_origin_unique"] is True,
            "canonical non-null origin no longer unique")
    require(cadj["candidate_global_writer_surface_complete"] is True,
            "canonical writer surface reopened")
    require(cadj["canonical_raw_slot_occurrence_partition_complete"] is True,
            "canonical raw slot partition incomplete")
    require(cadj["canonical_render_manager_slot_access_surface_complete"] is True,
            "canonical slot access surface incomplete")
    require(cadj["canonical_direct_propagation_escape_found"] is False,
            "canonical direct propagation escape found")
    require(canonical["raw_occurrence_partition"] == {
        "direct_load_count": 112,
        "direct_store_count": 2,
        "partition_complete": True,
        "slot_address_literal_materialization_count": 1,
        "slot_address_literal_site": "0x004fb9af",
        "whole_image_little_endian_occurrence_count": 115,
    }, "canonical raw occurrence partition drift")
    require(canonical["origin_and_propagation"]["direct_exact_global_memory_store_count"] == 0,
            "post-load exact-root memory store found")
    require(canonical["origin_and_propagation"]["direct_exact_global_push_count"] == 0,
            "post-load exact-root push found")
    require(canonical["origin_and_propagation"]["bounded_direct_target_remaining_count"] == 0,
            "canonical direct callee target reopened")

    cradj = copy_return["adjudication"]
    require(cradj["direct_exact_global_postconstruction_copy_surface_complete"] is True,
            "postconstruction copy surface incomplete")
    require(cradj["direct_exact_global_postconstruction_copy_surface_closed_negative"] is True,
            "postconstruction copy surface no longer negative")
    require(cradj["known_returned_root_consumer_surface_complete"] is True,
            "returned-root consumer surface incomplete")
    require(cradj["known_returned_root_can_persist_or_dispatch_exact_root"] is False,
            "returned root can persist or dispatch")
    require(copy_return["machine_cfg"]["exact_root_memory_store_count"] == 0,
            "machine-CFG exact-root store found")
    require(copy_return["machine_cfg"]["exact_root_push_count"] == 0,
            "machine-CFG exact-root push found")
    require(copy_return["machine_cfg"]["unmodelled_exact_alias_transfer_count"] == 0,
            "machine-CFG unmodelled exact alias transfer found")

    dadj = derived["adjudication"]
    require(dadj["derived_subobject_alias_surface_complete"] is True,
            "derived subobject surface incomplete")
    require(dadj["derived_subobject_can_reconstruct_exact_outer_root"] is False,
            "derived subobject can reconstruct outer root")
    require(dadj["derived_subobject_transition_count"] == 3,
            "derived transition count drift")

    ladj = live["adjudication"]
    require(ladj["canonical_lineage_live_call_boundary_surface_complete"] is True,
            "live call-boundary surface incomplete")
    require(ladj["bounded_direct_callee_alias_surface_complete"] is True,
            "bounded direct callee alias surface incomplete")
    require(ladj["all_live_exact_root_indirect_calls_classified"] is True,
            "live exact-root indirect calls incomplete")
    require(ladj["canonical_lineage_live_exact_root_non_vtable_indirect_setter_surface_complete"] is True,
            "canonical non-vtable setter surface incomplete")
    require(ladj["canonical_lineage_live_exact_root_non_vtable_indirect_setter_found"] is False,
            "canonical non-vtable setter found")
    require(live["direct_exact_root_callees"]["remaining_target_count"] == 0,
            "direct exact-root callee remains")
    require(live["indirect_exact_root_calls"]["count"] == 3,
            "indirect exact-root call count drift")
    require(live["indirect_exact_root_calls"]["non_vtable_indirect_call_count"] == 0,
            "non-vtable indirect exact-root call found")

    oadj = opaque["adjudication"]
    require(oadj["named_opaque_manager_root_candidate_surface_complete"] is True,
            "named opaque candidate surface incomplete")
    require(oadj["named_opaque_manager_root_candidate_count"] == 2,
            "named opaque candidate count drift")
    require(oadj["named_opaque_manager_root_exportable_candidate_count"] == 0,
            "named opaque exportable candidate found")
    require(oadj["known_named_opaque_helpers_can_create_independent_manager_root_alias"] is False,
            "known named opaque helper can create independent root alias")

    return {
        "format": FORMAT,
        "version": 2,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
        },
        "upstream_contracts": [EXPECTED[name] for name in INPUTS],
        "canonical_outer_root": {
            "slot": canonical["canonical_slot"],
            "constructor": canonical["origin_and_propagation"]["non_null_global_origin_unique_constructor"],
            "non_null_origin_unique": True,
        },
        "program_internal_exact_root_surface": {
            "pre_global_exact_this_memory_store_count": ctor["constructor"]["memory_stores_with_exact_this_as_value_count"],
            "pre_global_exact_this_helper_transfer_count": ctor["constructor"]["helper_argument_transfers_of_exact_this_count"],
            "canonical_direct_load_count": canonical["raw_occurrence_partition"]["direct_load_count"],
            "postconstruction_exact_root_memory_store_count": copy_return["machine_cfg"]["exact_root_memory_store_count"],
            "postconstruction_exact_root_push_count": copy_return["machine_cfg"]["exact_root_push_count"],
            "postconstruction_unmodelled_exact_alias_transfer_count": copy_return["machine_cfg"]["unmodelled_exact_alias_transfer_count"],
            "derived_subobject_transition_count": derived["adjudication"]["derived_subobject_transition_count"],
            "derived_subobject_reconstructs_exact_outer_root": derived["adjudication"]["derived_subobject_can_reconstruct_exact_outer_root"],
            "conditional_exact_eax_return_function_count": copy_return["returned_root"]["conditional_exact_eax_return_function_count"],
            "direct_return_callsite_count": copy_return["returned_root"]["direct_return_callsite_count"],
            "returned_root_consumer_can_persist_or_dispatch": copy_return["adjudication"]["known_returned_root_can_persist_or_dispatch_exact_root"],
            "live_call_boundary_observation_count": live["live_call_boundary_inventory"]["call_boundary_observation_count"],
            "live_call_boundary_unique_callsite_count": live["live_call_boundary_inventory"]["unique_callsite_count"],
            "bounded_direct_callee_target_count": live["direct_exact_root_callees"]["bounded_target_count"],
            "bounded_direct_callee_remaining_count": live["direct_exact_root_callees"]["remaining_target_count"],
            "indirect_exact_root_call_count": live["indirect_exact_root_calls"]["count"],
            "non_vtable_indirect_exact_root_call_count": live["indirect_exact_root_calls"]["non_vtable_indirect_call_count"],
        },
        "named_opaque_surface": {
            "candidate_count": oadj["named_opaque_manager_root_candidate_count"],
            "exportable_candidate_count": oadj["named_opaque_manager_root_exportable_candidate_count"],
        },
        "surviving_frontier": [
            "externally or unknown-origin initialized memory containing the exact outer root without a canonical program-internal producer",
            "previously unidentified opaque helper return that synthesizes the exact outer root from unrelated unknown input",
            "unrecognized runtime transform outside the merged bounded reconstruction classes",
        ],
        "adjudication": {
            "bounded_runtime_root_classes_composed": True,
            "program_internal_canonical_lineage_runtime_alias_surface_complete": True,
            "program_internal_canonical_lineage_runtime_alias_found": False,
            "canonical_lineage_pre_global_escape_surface_complete": True,
            "canonical_lineage_postconstruction_copy_surface_complete": True,
            "canonical_lineage_returned_root_consumer_surface_complete": True,
            "canonical_lineage_derived_subobject_surface_complete": True,
            "canonical_lineage_live_call_boundary_surface_complete": True,
            "named_opaque_manager_root_candidate_surface_complete": True,
            "known_named_opaque_manager_root_exportable_candidate_count": 0,
            "external_or_unknown_origin_outer_alias_surface_complete": False,
            "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete": False,
            "unrecognized_runtime_transform_root_origin_surface_complete": False,
            "memory_load_or_opaque_runtime_reconstruction_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This supersedes the v1 runtime-root frontier only for program-internal canonical-lineage creation, copies, returns, derived aliases and live call boundaries.",
            "It does not claim that arbitrary external process writes or unrelated unknown memory cannot contain the same runtime pointer.",
            "It does not claim that an as-yet-unidentified opaque helper cannot synthesize the runtime pointer from unrelated inputs.",
            "No object identity is inferred from equal numeric offsets.",
        ],
        "next_step": "Reduce only the three surviving external/unnamed-opaque/unrecognized-transform origin classes; do not reopen canonical-lineage postconstruction copies before final manager+0x374 -> HDVehicle+0x4330 and slot2 adjudication.",
    }


def main() -> None:
    print(json.dumps(build(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
