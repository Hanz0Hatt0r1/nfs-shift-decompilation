#!/usr/bin/env python3
"""Compose the bounded Participants Manager lifecycle/helper closure for manager+0x374."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.Manager374ParticipantsLifecycleClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

INPUTS = {
    "lifecycle": ROOT / "evidence/hdvehicle_64e8_manager_374_participants_lifecycle_zero_writers.json",
    "active": ROOT / "evidence/hdvehicle_64e8_manager_374_participants_active_dispatch_nested_frontier.json",
    "root_descendant": ROOT / "evidence/hdvehicle_64e8_manager_374_root_descendant_frontier.json",
    "vtable0c": ROOT / "evidence/hdvehicle_64e8_manager_374_participants_vtable0c_indirect_frontier.json",
    "computed": ROOT / "evidence/p1b_manager374_computed_runtime_closure.json",
    "exact_alias": ROOT / "evidence/p1b_manager374_exact_root_alias_closure.json",
}

EXPECTED_FORMATS = {
    "lifecycle": "SHIFT.HDVehicle64e8Manager374ParticipantsLifecycleZeroWriters/1",
    "active": "SHIFT.HDVehicle64e8Manager374ParticipantsActiveDispatchNestedFrontier/1",
    "root_descendant": "SHIFT.HDVehicle64e8Manager374RootDescendantFrontier/1",
    "vtable0c": "SHIFT.HDVehicle64e8Manager374ParticipantsVtable0cIndirectFrontier/1",
    "computed": "SHIFT.P1B.Manager374ComputedRuntimeClosure/1",
    "exact_alias": "SHIFT.P1B.Manager374ExactRootAliasClosure/1",
}


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not data.get("ready"):
        raise ValueError(f"upstream contract not ready: {path}")
    return data


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build() -> dict:
    data = {name: _load(path) for name, path in INPUTS.items()}
    for name, expected in EXPECTED_FORMATS.items():
        _require(data[name].get("format") == expected, f"{name}: format drift")

    lifecycle = data["lifecycle"]
    active = data["active"]
    root_desc = data["root_descendant"]
    vtable0c = data["vtable0c"]
    computed = data["computed"]
    exact_alias = data["exact_alias"]

    for name in ("lifecycle", "active", "root_descendant", "vtable0c"):
        _require(data[name]["authority"]["retail_executable_sha256"] == RETAIL_SHA256, f"{name}: retail hash drift")

    _require(lifecycle["constructor_vptr"]["vptr"] == "0x00ab916c", "Participants Manager vptr drift")
    _require(lifecycle["receiver"]["normalized_target"] == "manager+0x374", "normalized target drift")
    _require(len(lifecycle["exact_target_writers"]) == 2, "lifecycle target writer count drift")
    _require(all(row["written_value"] == 0 for row in lifecycle["exact_target_writers"]), "nonzero lifecycle writer appeared")
    _require(lifecycle["adjudication"]["participants_lifecycle_direct_target_writers_are_zero_only"] is True,
             "direct lifecycle target writers no longer zero-only")

    _require(active["adjudication"]["active_dispatch_direct_nested_surface_complete"] is True,
             "active-dispatch direct nested surface incomplete")
    _require(active["adjudication"]["active_dispatch_root_forwarder_direct_body_reaches_manager_374"] is False,
             "active-dispatch root forwarder reaches manager+0x374")
    _require(root_desc["adjudication"]["active_dispatch_receiver_preserving_root_descendant_surface_complete"] is True,
             "root descendant surface incomplete")
    _require(root_desc["adjudication"]["FUN_00489b00_exact_root_receiver_direct_descendant_reaches_manager_374"] is False,
             "FUN_00489b00 descendant reaches manager+0x374")
    _require(root_desc["adjudication"]["FUN_00d610c0_preserves_manager_root_to_descendants"] is False,
             "FUN_00d610c0 unexpectedly preserves manager root")

    _require(vtable0c["adjudication"]["participants_vtable_0x0c_indirect_receiver_inventory_complete"] is True,
             "Participants vtable +0x0c indirect inventory incomplete")
    _require(vtable0c["participants_callback"]["indirect_call_count"] == 6,
             "Participants vtable +0x0c indirect call count drift")
    _require(vtable0c["adjudication"]["participants_vtable_0x0c_indirect_surface_reaches_manager_374"] is False,
             "Participants vtable +0x0c indirect surface reaches manager+0x374")
    _require(vtable0c["adjudication"]["heap_helper_indirect_target_surface_complete"] is True,
             "heap-helper indirect surface incomplete")
    _require(vtable0c["adjudication"]["manager_438_deeper_same_receiver_surface_complete"] is True,
             "manager+0x438 descendant surface incomplete")
    _require(vtable0c["adjudication"]["manager_438_foreign_receiver_callback_surface_complete"] is True,
             "manager+0x438 foreign callback surface incomplete")

    _require(computed["surface"]["remaining_computed_runtime_path_count"] == 0,
             "computed runtime manager+0x374 paths reopened")
    _require(computed["adjudication"]["computed_runtime_paths_complete"] is True,
             "computed runtime closure incomplete")
    _require(exact_alias["adjudication"]["escaped_storage_paths_complete"] is True,
             "exact manager-root escaped storage reopened")
    _require(exact_alias["adjudication"]["stack_argument_alias_paths_complete"] is True,
             "exact manager-root stack argument aliases reopened")
    _require(exact_alias["adjudication"]["external_provider_count"] == 7,
             "provider count changed without Process 2 proof")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
        },
        "inputs": {name: EXPECTED_FORMATS[name] for name in EXPECTED_FORMATS},
        "participants_manager": {
            "manager_getter": lifecycle["receiver"]["manager_getter"],
            "manager_singleton": lifecycle["receiver"]["manager_singleton"],
            "subobject": lifecycle["receiver"]["participants_subobject"],
            "vptr": lifecycle["constructor_vptr"]["vptr"],
            "target": lifecycle["receiver"]["normalized_target"],
        },
        "lifecycle_writers": {
            "exact_target_writer_count": len(lifecycle["exact_target_writers"]),
            "nonzero_writer_count": sum(1 for row in lifecycle["exact_target_writers"] if row["written_value"] != 0),
            "writers": [
                {
                    "function": row["function"],
                    "vtable_slot": row["vtable_slot"],
                    "written_value": row["written_value"],
                }
                for row in lifecycle["exact_target_writers"]
            ],
        },
        "active_dispatch": {
            "default_target": active["bmanager_dispatch"]["default_target"],
            "alternate_target": active["bmanager_dispatch"]["alternate_target"],
            "exact_root_forwarder_count": active["adjudication"]["active_dispatch_exact_root_forwarder_count"],
            "exact_root_forwarder": active["root_forwarding"]["only_exact_manager_root_forwarder_from_active_dispatch_callbacks"],
            "root_forwarder_direct_body_reaches_manager_374": active["adjudication"]["active_dispatch_root_forwarder_direct_body_reaches_manager_374"],
            "exact_root_direct_descendant_count": root_desc["adjudication"]["FUN_00489b00_exact_root_receiver_direct_descendant_count"],
            "exact_root_direct_descendant_reaches_manager_374": root_desc["adjudication"]["FUN_00489b00_exact_root_receiver_direct_descendant_reaches_manager_374"],
            "descendant_preserves_manager_root_further": root_desc["adjudication"]["FUN_00d610c0_preserves_manager_root_to_descendants"],
        },
        "vtable_0x0c_indirect": {
            "callback": vtable0c["participants_callback"]["function"],
            "indirect_call_count": vtable0c["participants_callback"]["indirect_call_count"],
            "heap_helper_call_count": len(vtable0c["indirect_receiver_domains"]["heap_helper_calls"]),
            "manager_derived_call_count": len(vtable0c["indirect_receiver_domains"]["manager_derived_calls"]),
            "manager_derived_receiver": vtable0c["indirect_receiver_domains"]["manager_derived_receiver"],
            "manager_438_target": vtable0c["manager_438_object"]["resolved_target"],
            "manager_438_parent_recovery_found": vtable0c["resolved_target_body"]["parent_recovery_from_manager_438_observed"],
            "manager_438_direct_manager_374_store_found": vtable0c["resolved_target_body"]["direct_manager_plus_0x374_store_observed"],
            "surface_reaches_manager_374": vtable0c["adjudication"]["participants_vtable_0x0c_indirect_surface_reaches_manager_374"],
        },
        "already_closed_parallel_surfaces": {
            "computed_runtime_remaining_path_count": computed["surface"]["remaining_computed_runtime_path_count"],
            "exact_getter_escaped_storage_paths_complete": exact_alias["adjudication"]["escaped_storage_paths_complete"],
            "exact_getter_stack_argument_alias_paths_complete": exact_alias["adjudication"]["stack_argument_alias_paths_complete"],
        },
        "adjudication": {
            "participants_lifecycle_nested_writer_surface_complete": True,
            "participants_lifecycle_nonzero_manager_374_writer_found": False,
            "participants_lifecycle_helper_or_indirect_setter_surface_complete": True,
            "participants_lifecycle_can_place_fixed_hdvehicle_4330_into_manager_374": False,
            "computed_runtime_paths_complete": True,
            "exact_getter_alias_storage_and_stack_paths_complete": True,
            "unrelated_manager_alias_or_unknown_root_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes the exact Participants Manager lifecycle vtable surface, its active-dispatch receiver-preserving descendants, and the six indirect calls in vtable +0x0c.",
            "It does not claim that an unrelated reconstructed/unknown manager root cannot reach another helper or indirect setter outside the audited Participants lifecycle lineage.",
            "The manager+0x2a0 selection writer remains a separate allocator-owned object domain and is not promoted to HDVehicle+0x4330.",
            "No identity is inferred from matching numeric offsets.",
        ],
        "next_step": "Bound unrelated/unknown Participants Manager root aliases outside the lifecycle lineage; if none can reach an additional manager+0x374 writer, perform the final manager+0x374 identity rejection and 0x004b86cf slot2 adjudication.",
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
