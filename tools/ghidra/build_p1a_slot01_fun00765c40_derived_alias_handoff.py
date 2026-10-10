#!/usr/bin/env python3
"""Compose bounded FUN_00765c40 derived-pointer evidence for P1.3A slot0/slot1.

Consumes merged machine evidence without changing its ownership.  The claim is
limited to two four-wheel interior aliases (+0x678/+0x7a8) and the post-derived
identity inventory.  Callee-facing lifetimes of the HDVehicle-local arrays,
runtime/generated pointers, callbacks and indirect entry remain fail-closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01Fun00765c40DerivedAliasHandoff/1"
WHEEL_FORMAT = "SHIFT.P1A.P13ASlot01WheelRootMaterializationPersistenceHandoff/1"
WHEEL678_FORMAT = "SHIFT.P1D.Slot3Fun00765c40WheelInteriorAliasClosure/1"
WHEEL7A8_FORMAT = "SHIFT.P1D.Slot3Fun00765c40Wheel7a8AliasClosure/1"
POST_FORMAT = "SHIFT.P1D.Slot3Fun00765c40PostDerivedInventory/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

SLOT_ROWS = [
    {
        "slot": 0,
        "wheel_receiver": "HDVehicle+0x400",
        "absolute_target": "HDVehicle+0x938..+0x93f",
        "wheel_678_receiver": "HDVehicle+0xa78",
        "wheel_678_writes": ["HDVehicle+0xa70 qword", "HDVehicle+0xa78 qword"],
        "wheel_7a8_receiver": "HDVehicle+0xba8",
        "wheel_7a8_writes": ["HDVehicle+0xba0 qword", "HDVehicle+0xba8 qword"],
    },
    {
        "slot": 1,
        "wheel_receiver": "HDVehicle+0xe80",
        "absolute_target": "HDVehicle+0x13b8..+0x13bf",
        "wheel_678_receiver": "HDVehicle+0x14f8",
        "wheel_678_writes": ["HDVehicle+0x14f0 qword", "HDVehicle+0x14f8 qword"],
        "wheel_7a8_receiver": "HDVehicle+0x1628",
        "wheel_7a8_writes": ["HDVehicle+0x1620 qword", "HDVehicle+0x1628 qword"],
    },
]


def require(data: dict, fmt: str, label: str) -> None:
    if data.get("format") != fmt:
        raise ValueError(f"unexpected {label} format: {data.get('format')!r}")
    if data.get("ready") is not True:
        raise ValueError(f"{label} evidence is not ready")
    if data.get("authority", {}).get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError(f"{label} retail SHA-256 drift")


def build(wheel: dict, wheel678: dict, wheel7a8: dict, post: dict) -> dict:
    require(wheel, WHEEL_FORMAT, "P1A wheel-root")
    require(wheel678, WHEEL678_FORMAT, "wheel+0x678")
    require(wheel7a8, WHEEL7A8_FORMAT, "wheel+0x7a8")
    require(post, POST_FORMAT, "post-derived inventory")

    wheel_slots = wheel.get("slot01", [])
    if [(r.get("slot"), r.get("wheel_receiver"), r.get("absolute_target")) for r in wheel_slots] != [
        (0, "HDVehicle+0x400", "HDVehicle+0x938..+0x93f"),
        (1, "HDVehicle+0xe80", "HDVehicle+0x13b8..+0x13bf"),
    ]:
        raise ValueError("P1A slot0/slot1 wheel identity drift")
    if wheel.get("adjudication", {}).get("p13a_slot01_known_wheel_root_materialization_subset_complete") is not True:
        raise ValueError("P1A wheel-root materialization prerequisite incomplete")

    a678 = wheel678.get("wheel_interior_alias", {})
    if a678.get("per_wheel_offset") != "+0x678":
        raise ValueError("wheel+0x678 offset drift")
    if a678.get("vehicle_relative_offsets") != ["+0x0a78", "+0x14f8", "+0x1f78", "+0x29f8"]:
        raise ValueError("wheel+0x678 four-wheel sequence drift")
    if a678.get("persistent_or_nonlocal_pointer_store_found") is not False:
        raise ValueError("wheel+0x678 gained persistent pointer store")
    if a678.get("selected_target_overlap") is not False:
        raise ValueError("wheel+0x678 write surface now overlaps target")
    if a678.get("selected_slot3_write_offsets") != [
        "HDVehicle+0x29f0 = wheel+0x670 qword",
        "HDVehicle+0x29f8 = wheel+0x678 qword",
    ]:
        raise ValueError("wheel+0x678 write normalization drift")

    child = wheel678.get("child_pointer_load", {})
    if child.get("expression") != "[wheel+0x678-0x258] = [wheel+0x420]":
        raise ValueError("wheel+0x678 child expression drift")
    if child.get("child_pointer_forward_to_call_found") is not False or child.get("child_pointer_store_found") is not False:
        raise ValueError("wheel+0x678 child pointer gained escape")

    transient = wheel678.get("transient_stack_alias", {})
    if transient.get("site") != "0x00765da4" or transient.get("overwrite_site") != "0x00765dc9":
        raise ValueError("wheel+0x678 transient stack alias drift")
    if transient.get("persistent_escape") is not False or transient.get("pointer_reaches_callee_stack_argument") is not False:
        raise ValueError("transient wheel+0x678 stack pointer now escapes")
    scalar = wheel678.get("scalar_call_ecx", {})
    if scalar.get("callee") != "FUN_00758ad0" or scalar.get("callee_incoming_ecx_read_before_overwrite") is not False:
        raise ValueError("FUN_00758ad0 incoming ECX premise drift")
    if scalar.get("hdvehicle_pointer_consumed_as_object_receiver") is not False:
        raise ValueError("FUN_00758ad0 now consumes HDVehicle receiver")

    a7 = wheel7a8.get("wheel_alias", {})
    if a7.get("per_wheel_offset") != "+0x7a8":
        raise ValueError("wheel+0x7a8 offset drift")
    if a7.get("vehicle_relative_aliases") != ["+0x0ba8", "+0x1628", "+0x20a8", "+0x2b28"]:
        raise ValueError("wheel+0x7a8 four-wheel sequence drift")
    if a7.get("pointer_store_found") is not False or a7.get("pointer_push_found") is not False:
        raise ValueError("wheel+0x7a8 gained pointer persistence")
    if a7.get("direct_call_count") != 0:
        raise ValueError("wheel+0x7a8 gained direct call")
    writes7 = wheel7a8.get("writes", {})
    if writes7.get("per_wheel_offsets") != ["+0x7a0 qword", "+0x7a8 qword"]:
        raise ValueError("wheel+0x7a8 write normalization drift")
    if writes7.get("selected_target_overlap") is not False:
        raise ValueError("wheel+0x7a8 write surface now overlaps target")

    families = post.get("families", {})
    manager = families.get("hdvehicle_6730", {})
    if manager.get("identity") != "HDVehicle+0x6730 local manager/subobject; not a wheel root or wheel-relative alias":
        raise ValueError("HDVehicle+0x6730 identity drift")
    if manager.get("runtime_created_node_backpointer_stores") != [
        "0x00a62a20 [node+0x24]=HDVehicle+0x6730",
        "0x00a62a63 [node+0x34]=HDVehicle+0x6730",
    ]:
        raise ValueError("HDVehicle+0x6730 runtime backpointer surface drift")
    if manager.get("selected_slot3_pointer_identity") is not False:
        raise ValueError("HDVehicle+0x6730 was promoted to selected wheel identity")
    if manager.get("fun00a628a0_receiver_value_store_or_push_found") is not False:
        raise ValueError("FUN_00a628a0 gained receiver persistence")

    arrays12 = families.get("hdvehicle_local_arrays_12", {})
    if arrays12.get("bases") != ["HDVehicle+0x3430", "HDVehicle+0x35c8", "HDVehicle+0x35f8"]:
        raise ValueError("12-iteration local-array identity drift")
    if arrays12.get("selected_slot3_pointer_identity") is not False:
        raise ValueError("12-iteration local array promoted to wheel identity")
    if arrays12.get("callee_lifetime_fully_closed") is not False:
        raise ValueError("unexpected closure of 12-iteration array callee lifetime")
    array4 = families.get("hdvehicle_local_array_4", {})
    if array4.get("base") != "HDVehicle+0x36e0" or array4.get("selected_slot3_pointer_identity") is not False:
        raise ValueError("4-iteration local-array identity drift")
    if array4.get("callee_lifetime_fully_closed") is not False:
        raise ValueError("unexpected closure of 4-iteration array callee lifetime")

    post_adj = post.get("adjudication", {})
    if post_adj.get("fun00765c40_post_derived_family_inventory_complete") is not True:
        raise ValueError("post-derived inventory incomplete")
    if post_adj.get("fun00765c40_post_derived_selected_slot3_alias_found") is not False:
        raise ValueError("post-derived inventory found selected wheel alias")
    if post_adj.get("fun00765c40_hdvehicle_6730_runtime_backpointer_store_found") is not True:
        raise ValueError("expected non-wheel +0x6730 runtime backpointer evidence missing")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contracts": [WHEEL_FORMAT, WHEEL678_FORMAT, WHEEL7A8_FORMAT, POST_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "machine_bytes_adjudicate_upstream": True,
            "cross_lane_machine_proofs_consumed_without_reowning": True,
        },
        "slot01": SLOT_ROWS,
        "wheel_678_alias": {
            "per_wheel_offset": "+0x678",
            "write_offsets": ["+0x670 qword", "+0x678 qword"],
            "persistent_or_nonlocal_pointer_store_found": False,
            "child_source": "[wheel+0x420]",
            "child_pointer_forward_or_store_found": False,
            "transient_stack_pointer_site": "0x00765da4",
            "transient_stack_pointer_overwrite_site": "0x00765dc9",
            "transient_stack_pointer_reaches_callee": False,
            "target_overlap": False,
        },
        "wheel_7a8_alias": {
            "per_wheel_offset": "+0x7a8",
            "write_offsets": ["+0x7a0 qword", "+0x7a8 qword"],
            "pointer_store_found": False,
            "pointer_push_found": False,
            "direct_call_count": 0,
            "target_overlap": False,
        },
        "post_derived_identity_inventory": {
            "selected_wheel_alias_found": False,
            "nonwheel_runtime_backpointer_family": "HDVehicle+0x6730",
            "nonwheel_runtime_backpointer_stores": manager["runtime_created_node_backpointer_stores"],
            "hdvehicle_local_array_bases": [
                "HDVehicle+0x3430",
                "HDVehicle+0x35c8",
                "HDVehicle+0x35f8",
                "HDVehicle+0x36e0",
            ],
            "local_array_callee_lifetimes_complete": False,
        },
        "adjudication": {
            "p13a_fun00765c40_wheel_678_alias_subset_complete": True,
            "p13a_fun00765c40_wheel_7a8_alias_subset_complete": True,
            "p13a_fun00765c40_post_derived_identity_inventory_complete": True,
            "p13a_fun00765c40_known_wheel_alias_target_writer_found": False,
            "p13a_fun00765c40_known_wheel_alias_persistent_escape_found": False,
            "p13a_fun00765c40_post_derived_selected_wheel_alias_found": False,
            "p13a_fun00765c40_nonwheel_runtime_backpointer_store_found": True,
            "p13a_fun00765c40_local_array_callee_lifetimes_complete": False,
            "other_derived_aliases_ruled_out": False,
            "reconstructed_wheel_pointers_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "callbacks_and_indirect_entry_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only the bounded FUN_00765c40 wheel+0x678 and wheel+0x7a8 four-wheel aliases plus the post-derived identity inventory.",
            "The proven HDVehicle+0x6730 runtime-created-node backpointers are retained as positive pointer persistence for a distinct non-wheel manager/subobject; they are not silently discarded and do not close runtime/generated pointer stores globally.",
            "HDVehicle+0x3430/+0x35c8/+0x35f8/+0x36e0 are classified as non-wheel local arrays, but their callee-facing lifetimes remain open.",
            "Reconstructed selected-wheel pointers, aggregate copies, callbacks, indirect entry and other derived families remain open; no slot or aggregate P1.3 gate is promoted."
        ],
        "next_step": (
            "Trace the callee-facing lifetimes of the HDVehicle-local array cursors through "
            "FUN_007afd20/FUN_007baa70/FUN_00747b90/FUN_007aefb0; separately consume the direct 16-carrier bulk-opcode "
            "absence and continue runtime-generated/copied selected-wheel pointer plus callback/indirect-entry surfaces."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, default=Path("evidence/p1a_p13a_slot01_wheel_root_materialization_persistence_handoff.json"))
    parser.add_argument("--wheel678", type=Path, default=Path("evidence/p1d_slot3_fun00765c40_wheel_interior_alias_closure.json"))
    parser.add_argument("--wheel7a8", type=Path, default=Path("evidence/p1d_slot3_fun00765c40_wheel_7a8_alias_closure.json"))
    parser.add_argument("--post", type=Path, default=Path("evidence/p1d_slot3_fun00765c40_post_derived_inventory.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build(*[json.loads(p.read_text(encoding="utf-8")) for p in (args.wheel, args.wheel678, args.wheel7a8, args.post)])
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
