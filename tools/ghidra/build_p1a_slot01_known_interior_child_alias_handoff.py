#!/usr/bin/env python3
"""Compose the known slot0/slot1 interior/child alias closures for P1.3A.

The semantic/machine conclusions are consumed from merged P1D contracts, while
slot0/slot1 wheel identity is supplied by the merged P1A wheel-root handoff.
This closes only three already-bounded alias families: wheel+0x80,
wheel+0x7c8, and child=[wheel+0x420].
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01KnownInteriorChildAliasHandoff/1"
WHEEL_FORMAT = "SHIFT.P1A.P13ASlot01WheelRootMaterializationPersistenceHandoff/1"
PRIMARY_FORMAT = "SHIFT.P1D.P13DSlot3PrimaryAliasEscape/1"
INTERIOR80_FORMAT = "SHIFT.P1D.Slot3Fun007555b0InteriorAliasClosure/1"
DIRECT_FORMAT = "SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1"
INTERIOR7C8_FORMAT = "SHIFT.P1D.Slot3Fun00755a60RegisterAliasClosure/1"
CHILD420_FORMAT = "SHIFT.P1D.Slot3Wheel420ChildCalleeMachineClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

SLOT_ROWS = [
    {
        "slot": 0,
        "wheel_receiver": "HDVehicle+0x400",
        "absolute_target": "HDVehicle+0x938..+0x93f",
        "wheel_80_receiver": "HDVehicle+0x480",
        "wheel_7c8_receiver": "HDVehicle+0xbc8",
    },
    {
        "slot": 1,
        "wheel_receiver": "HDVehicle+0xe80",
        "absolute_target": "HDVehicle+0x13b8..+0x13bf",
        "wheel_80_receiver": "HDVehicle+0xf00",
        "wheel_7c8_receiver": "HDVehicle+0x1648",
    },
]


def require(data: dict, fmt: str, label: str) -> None:
    if data.get("format") != fmt:
        raise ValueError(f"unexpected {label} format: {data.get('format')!r}")
    if data.get("ready") is not True:
        raise ValueError(f"{label} evidence is not ready")
    if data.get("authority", {}).get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError(f"{label} retail SHA-256 drift")


def build(wheel: dict, primary: dict, interior80: dict, direct: dict, interior7c8: dict, child420: dict) -> dict:
    require(wheel, WHEEL_FORMAT, "P1A wheel-root")
    require(primary, PRIMARY_FORMAT, "primary alias")
    require(interior80, INTERIOR80_FORMAT, "wheel+0x80")
    require(direct, DIRECT_FORMAT, "direct wheel carrier")
    require(interior7c8, INTERIOR7C8_FORMAT, "wheel+0x7c8")
    require(child420, CHILD420_FORMAT, "wheel+0x420 child")

    wheel_slots = wheel.get("slot01", [])
    if [(r.get("slot"), r.get("wheel_receiver"), r.get("absolute_target")) for r in wheel_slots] != [
        (0, "HDVehicle+0x400", "HDVehicle+0x938..+0x93f"),
        (1, "HDVehicle+0xe80", "HDVehicle+0x13b8..+0x13bf"),
    ]:
        raise ValueError("P1A slot0/slot1 wheel identity drift")
    wheel_adj = wheel.get("adjudication", {})
    if wheel_adj.get("p13a_slot01_known_wheel_root_materialization_subset_complete") is not True:
        raise ValueError("P1A wheel-root materialization prerequisite is incomplete")

    p = primary.get("primary_loop", {})
    if p.get("selected_wheel_materialization") != "0x00758ccf ECX=ESI-0x448=HDVehicle+0x400+slot*0xa80":
        raise ValueError("primary four-wheel materialization drift")
    if p.get("selected_wheel_direct_call") != "0x00758d6b -> FUN_00755950":
        raise ValueError("primary FUN_00755950 call drift")
    c = primary.get("consumer", {})
    if c.get("function") != "FUN_00755950" or c.get("callee_receiver") != "0x00755964 ECX=EDX+0x80":
        raise ValueError("FUN_00755950 wheel+0x80 forwarding drift")
    if c.get("writes_overlap_target_0x538_0x53f") is not False:
        raise ValueError("FUN_00755950 now overlaps wheel+0x538")
    if c.get("only_direct_callee") != "0x00755983 -> FUN_007555b0":
        raise ValueError("FUN_00755950 callee drift")

    i80_path = interior80.get("path", {})
    i80_callee = interior80.get("callee", {})
    i80_adj = interior80.get("adjudication", {})
    if i80_path.get("caller") != "FUN_00755950" or i80_path.get("callee") != "FUN_007555b0":
        raise ValueError("wheel+0x80 path drift")
    if i80_path.get("callee_receiver") != "selected wheel+0x80":
        raise ValueError("wheel+0x80 receiver drift")
    if i80_path.get("selected_target_from_callee_receiver") != "+0x4b8":
        raise ValueError("wheel+0x80 target normalization drift")
    if i80_callee.get("receiver_relative_write_offsets") != ["+0x248", "+0x250", "+0x258", "+0x260"]:
        raise ValueError("FUN_007555b0 write surface drift")
    if i80_callee.get("selected_target_relative_offset_observed") is not False:
        raise ValueError("FUN_007555b0 now observes target-relative +0x4b8")
    if i80_callee.get("direct_call_count") != 0 or i80_callee.get("receiver_value_reconstruction_or_mutation_count") != 0:
        raise ValueError("FUN_007555b0 gained forwarding/root reconstruction")
    if i80_adj.get("fun007555b0_selected_slot3_target_writer_found") is not False:
        raise ValueError("upstream wheel+0x80 writer premise changed")

    d55 = direct.get("paths", {}).get("fun00755a60", {})
    if d55.get("receiver") != "HDVehicle+0x400+slot*0xa80":
        raise ValueError("FUN_00755a60 generic wheel receiver drift")
    if d55.get("target_overlap") is not False:
        raise ValueError("FUN_00755a60 direct surface now overlaps target")

    i7 = interior7c8.get("fun00755a60", {})
    leaf7 = interior7c8.get("fun00753620", {})
    i7_adj = interior7c8.get("adjudication", {})
    if i7.get("derived_subfield_alias") != "0x00755c04 ECX=ESI+0x7c8":
        raise ValueError("wheel+0x7c8 alias materialization drift")
    if i7.get("derived_subfield_alias_persists_to_call") != "0x00755dae FUN_00753620":
        raise ValueError("wheel+0x7c8 consumer drift")
    if leaf7 != {
        "absolute_selected_wheel_write_offsets": ["+0x7c8"],
        "direct_call_count": 0,
        "receiver": "selected wheel+0x7c8",
        "selected_target_overlap": False,
        "write_offsets": ["+0x0"],
    }:
        raise ValueError("FUN_00753620 bounded leaf drift")
    if i7_adj.get("fun00753620_selected_target_writer_found") is not False:
        raise ValueError("upstream wheel+0x7c8 writer premise changed")

    child_adj = child420.get("adjudication", {})
    child_effects = child420.get("child_effects", {})
    entries = child420.get("entry_paths", [])
    expected_entries = [
        ("FUN_00760b50", "FUN_007ba860", "child=[wheel+0x420]"),
        ("FUN_00755f80", "FUN_007af0a0", "child+0xd4"),
        ("FUN_00755f80", "FUN_007af010", "child+0xd4"),
    ]
    if [(r.get("caller"), r.get("callee"), r.get("receiver_identity")) for r in entries] != expected_entries:
        raise ValueError("wheel+0x420 child entry surface drift")
    if child_adj.get("known_wheel_420_child_callee_subset_complete") is not True:
        raise ValueError("wheel+0x420 child subset incomplete")
    for key in (
        "known_wheel_420_child_back_pointer_recovery_found",
        "known_wheel_420_child_pointer_persistence_found",
        "known_wheel_420_child_selected_target_writer_found",
    ):
        if child_adj.get(key) is not False:
            raise ValueError(f"child alias premise changed: {key}")
    if child_effects.get("back_pointer_or_wheel_root_recovery_found") is not False:
        raise ValueError("child chain gained wheel-root recovery")
    if child_effects.get("child_pointer_persistence_found") is not False:
        raise ValueError("child chain gained pointer persistence")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contracts": [
            WHEEL_FORMAT,
            PRIMARY_FORMAT,
            INTERIOR80_FORMAT,
            DIRECT_FORMAT,
            INTERIOR7C8_FORMAT,
            CHILD420_FORMAT,
        ],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "machine_bytes_adjudicate_upstream": True,
            "cross_lane_machine_proofs_consumed_without_reowning": True,
        },
        "slot01": SLOT_ROWS,
        "wheel_80_alias": {
            "source": "FUN_00758b50 per-wheel loop -> FUN_00755950",
            "interior_materialization": "FUN_00755950 ECX=wheel+0x80",
            "callee": "FUN_007555b0",
            "target_relative_to_callee": "+0x4b8",
            "callee_receiver_write_offsets": ["+0x248", "+0x250", "+0x258", "+0x260"],
            "wheel_relative_write_offsets": ["+0x2c8", "+0x2d0", "+0x2d8", "+0x2e0"],
            "target_writer_found": False,
            "reconstructs_wheel_root": False,
            "forwards_to_direct_callee": False,
        },
        "wheel_7c8_alias": {
            "source": "FUN_00755a60 exact wheel receiver",
            "materialization": "0x00755c04 ECX=wheel+0x7c8",
            "callee_call": "0x00755dae -> FUN_00753620",
            "callee": "FUN_00753620",
            "callee_write_offsets": ["+0x0"],
            "wheel_relative_write_offsets": ["+0x7c8"],
            "callee_direct_call_count": 0,
            "target_writer_found": False,
        },
        "wheel_420_child_alias": {
            "source": "child=[wheel+0x420]",
            "bounded_callers": ["FUN_00760b50", "FUN_00755f80"],
            "bounded_callees": ["FUN_007ba860", "FUN_007af0a0", "FUN_007af010", "FUN_007ba7e0", "FUN_007aefb0"],
            "back_pointer_or_wheel_root_recovery_found": False,
            "child_pointer_persistence_found": False,
            "selected_target_writer_found": False,
            "persistent_child_scalar_writes": child_effects.get("FUN_007ba860_writes", []),
        },
        "adjudication": {
            "p13a_slot01_wheel_80_interior_alias_subset_complete": True,
            "p13a_slot01_wheel_7c8_interior_alias_subset_complete": True,
            "p13a_slot01_wheel_420_child_alias_subset_complete": True,
            "p13a_slot01_known_interior_child_alias_target_writer_found": False,
            "p13a_slot01_known_interior_child_alias_root_reconstruction_found": False,
            "p13a_slot01_known_interior_child_alias_pointer_persistence_found": False,
            "other_derived_or_child_aliases_ruled_out": False,
            "reconstructed_wheel_pointers_ruled_out": False,
            "runtime_generated_or_copied_pointer_stores_ruled_out": False,
            "callbacks_and_indirect_entry_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only the already-machine-bounded wheel+0x80, wheel+0x7c8 and [wheel+0x420] child alias families for slot0/slot1.",
            "Slot0/slot1 object identity is supplied by the merged P1A wheel-root handoff; P1D contracts contribute machine body/callee semantics without ownership transfer.",
            "Other derived aliases, reconstructed pointers, aggregate copies, runtime-generated/copied pointers, callbacks and indirect entry remain open.",
            "No global stored-or-escaped-alias, slot-completion or aggregate P1.3 gate is promoted by this bounded composition."
        ],
        "next_step": (
            "Consume remaining four-wheel interior alias families (including FUN_00765c40 wheel+0x678/+0x7a8 where slot-agnostic), "
            "then trace reconstructed/runtime-generated pointers and callback/indirect-entry carriers."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, default=Path("evidence/p1a_p13a_slot01_wheel_root_materialization_persistence_handoff.json"))
    parser.add_argument("--primary", type=Path, default=Path("evidence/p1d_slot3_primary_alias_escape.json"))
    parser.add_argument("--interior80", type=Path, default=Path("evidence/p1d_slot3_fun007555b0_interior_alias_closure.json"))
    parser.add_argument("--direct", type=Path, default=Path("evidence/p1d_slot3_exact_wheel_direct_carrier_closure.json"))
    parser.add_argument("--interior7c8", type=Path, default=Path("evidence/p1d_slot3_fun00755a60_register_alias_closure.json"))
    parser.add_argument("--child420", type=Path, default=Path("evidence/p1d_slot3_wheel420_child_callee_machine_closure.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build(*[
        json.loads(path.read_text(encoding="utf-8")) for path in (
            args.wheel, args.primary, args.interior80, args.direct, args.interior7c8, args.child420
        )
    ])
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
