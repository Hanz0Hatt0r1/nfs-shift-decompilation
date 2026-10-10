#!/usr/bin/env python3
"""Compose bounded carrier/callee/indirect evidence for P1.3A slot0/slot1.

This consumes merged P1A/P1D machine contracts without changing their ownership.
The result closes only already-bounded FUN_00765c40 derived/local-array lifetimes,
x86 string bulk opcodes in the 16 exact-root carriers and their immediate direct
callees, and the two call-through-IAT sites physically present in FUN_00770e80.
Runtime-generated/copied selected-wheel pointers and external callback/indirect
entry remain fail-closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01CarrierSurfaceComposition/1"
DERIVED_FORMAT = "SHIFT.P1A.P13ASlot01Fun00765c40DerivedAliasHandoff/1"
LOCAL_ARRAY_FORMAT = "SHIFT.P1A.P13AFun00765c40LocalArrayCalleeMachineClosure/1"
CARRIER_BULK_FORMAT = "SHIFT.P1D.Slot3SixteenCarrierBulkOpcodeClosure/1"
CALLEE_BULK_FORMAT = "SHIFT.P1D.Slot3DirectCalleeBulkOpcodeClosure/1"
CALL_TARGET_FORMAT = "SHIFT.P1D.Slot3CarrierCallTargetComposition/2"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INDEX_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"


def require_ready(data: dict, fmt: str, label: str) -> None:
    if data.get("format") != fmt:
        raise ValueError(f"unexpected {label} format: {data.get('format')!r}")
    if data.get("ready") is not True:
        raise ValueError(f"{label} evidence is not ready")


def require_retail(data: dict, label: str) -> None:
    actual = data.get("authority", {}).get("retail_executable_sha256")
    if actual != RETAIL_SHA256:
        raise ValueError(f"{label} retail SHA-256 drift: {actual!r}")


def build(derived: dict, local_arrays: dict, carrier_bulk: dict, callee_bulk: dict, call_targets: dict) -> dict:
    require_ready(derived, DERIVED_FORMAT, "FUN_00765c40 derived-alias handoff")
    require_ready(local_arrays, LOCAL_ARRAY_FORMAT, "FUN_00765c40 local-array closure")
    require_ready(carrier_bulk, CARRIER_BULK_FORMAT, "16-carrier bulk-opcode closure")
    require_ready(callee_bulk, CALLEE_BULK_FORMAT, "direct-callee bulk-opcode closure")
    require_ready(call_targets, CALL_TARGET_FORMAT, "carrier call-target composition")
    for label, payload in (
        ("derived", derived),
        ("local arrays", local_arrays),
        ("carrier bulk", carrier_bulk),
        ("callee bulk", callee_bulk),
    ):
        require_retail(payload, label)
    if callee_bulk.get("authority", {}).get("ghidra_sqlite_sha256") != INDEX_SHA256:
        raise ValueError("direct-callee Ghidra SQLite SHA-256 drift")

    da = derived.get("adjudication", {})
    if da.get("p13a_fun00765c40_wheel_678_alias_subset_complete") is not True:
        raise ValueError("FUN_00765c40 wheel+0x678 subset incomplete")
    if da.get("p13a_fun00765c40_wheel_7a8_alias_subset_complete") is not True:
        raise ValueError("FUN_00765c40 wheel+0x7a8 subset incomplete")
    if da.get("p13a_fun00765c40_post_derived_identity_inventory_complete") is not True:
        raise ValueError("FUN_00765c40 post-derived inventory incomplete")
    if da.get("p13a_fun00765c40_known_wheel_alias_target_writer_found") is not False:
        raise ValueError("known FUN_00765c40 wheel alias now writes selected target")
    if da.get("p13a_fun00765c40_known_wheel_alias_persistent_escape_found") is not False:
        raise ValueError("known FUN_00765c40 wheel alias now escapes")
    if da.get("p13a_fun00765c40_nonwheel_runtime_backpointer_store_found") is not True:
        raise ValueError("expected +0x6730 non-wheel runtime backpointer evidence missing")

    la = local_arrays.get("adjudication", {})
    if la.get("p13a_fun00765c40_local_array_callee_lifetimes_complete") is not True:
        raise ValueError("FUN_00765c40 local-array callee lifetimes incomplete")
    if la.get("p13a_fun00765c40_local_array_pointer_escape_found") is not False:
        raise ValueError("FUN_00765c40 local array gained pointer escape")
    if la.get("p13a_fun00765c40_local_array_selected_slot_writer_found") is not False:
        raise ValueError("FUN_00765c40 local array gained selected-slot writer")
    if la.get("p13a_fun00765c40_local_array_wheel_root_reconstruction_found") is not False:
        raise ValueError("FUN_00765c40 local array reconstructs wheel root")

    cb = carrier_bulk.get("adjudication", {})
    surface16 = carrier_bulk.get("direct_bulk_opcode_surface", {})
    scope16 = carrier_bulk.get("scope", {})
    if cb.get("machine_direct_bulk_opcode_16_carrier_subset_complete") is not True:
        raise ValueError("16-carrier direct bulk-opcode surface incomplete")
    if cb.get("machine_direct_bulk_opcode_found") is not False:
        raise ValueError("16-carrier direct bulk opcode now present")
    if scope16.get("carrier_count") != 16 or scope16.get("instruction_count") != 5178:
        raise ValueError("16-carrier scope drift")
    if surface16.get("hit_count") != 0 or surface16.get("rep_prefixed_or_x86_string_opcode_found") is not False:
        raise ValueError("16-carrier bulk-opcode hit surface drift")

    dc = callee_bulk.get("adjudication", {})
    dcs = callee_bulk.get("surface", {})
    if dc.get("first_direct_callee_bulk_opcode_surface_complete") is not True:
        raise ValueError("direct-callee bulk-opcode surface incomplete")
    if dc.get("first_direct_callee_bulk_opcode_found") is not False:
        raise ValueError("direct-callee bulk opcode now present")
    expected_direct = {
        "carrier_count": 16,
        "direct_callsite_count": 214,
        "unique_direct_callee_count": 82,
        "direct_callee_instruction_count": 9159,
        "bulk_opcode_hit_count": 0,
        "indirect_callsite_count": 2,
    }
    for key, value in expected_direct.items():
        if dcs.get(key) != value:
            raise ValueError(f"direct-callee surface drift: {key}")
    if [row.get("site") for row in dcs.get("indirect_callsites", [])] != ["0x00770ec4", "0x00770f41"]:
        raise ValueError("FUN_00770e80 indirect callsite set drift")

    cta = call_targets.get("adjudication", {})
    cts = call_targets.get("surface", {})
    if cta.get("sixteen_carrier_machine_call_target_surface_complete") is not True:
        raise ValueError("16-carrier machine call-target surface incomplete")
    if cta.get("sixteen_carrier_runtime_unknown_call_target_count") != 0:
        raise ValueError("runtime-unknown carrier call target introduced")
    if cta.get("sixteen_carrier_import_resolved_callsite_count") != 2:
        raise ValueError("import-resolved callsite count drift")
    if cts.get("immediate_direct_callsite_count") != 214 or cts.get("call_through_memory_site_count") != 2:
        raise ValueError("carrier callsite partition drift")
    if cts.get("total_machine_callsite_count") != 216:
        raise ValueError("carrier total machine callsite count drift")
    if cts.get("runtime_unknown_call_target_count_within_16_carrier_bodies") != 0:
        raise ValueError("carrier runtime-unknown target count drift")

    resolved = cts.get("resolved_call_through_memory_sites", [])
    expected_resolved = [
        ("0x00770ec4", "KERNEL32!InterlockedExchange", "HDVehicle+0x4020", 1),
        ("0x00770f41", "KERNEL32!InterlockedExchange", "HDVehicle+0x4020", 2),
    ]
    actual_resolved = [
        (row.get("site"), row.get("runtime_import"), row.get("target_argument"), row.get("value_argument"))
        for row in resolved
    ]
    if actual_resolved != expected_resolved:
        raise ValueError("FUN_00770e80 import-indirect resolution drift")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contracts": [
            DERIVED_FORMAT,
            LOCAL_ARRAY_FORMAT,
            CARRIER_BULK_FORMAT,
            CALLEE_BULK_FORMAT,
            CALL_TARGET_FORMAT,
        ],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "ghidra_sqlite_sha256": INDEX_SHA256,
            "cross_lane_machine_proofs_consumed_without_reowning": True,
        },
        "fun00765c40": {
            "known_wheel_derived_aliases_complete": True,
            "known_wheel_alias_target_writer_found": False,
            "known_wheel_alias_persistent_escape_found": False,
            "post_derived_identity_inventory_complete": True,
            "local_array_bases": [
                "HDVehicle+0x3430",
                "HDVehicle+0x35c8",
                "HDVehicle+0x35f8",
                "HDVehicle+0x36e0",
            ],
            "local_array_callee_lifetimes_complete": True,
            "local_array_pointer_escape_found": False,
            "local_array_wheel_root_reconstruction_found": False,
            "nonwheel_runtime_backpointer_family": "HDVehicle+0x6730",
            "nonwheel_runtime_backpointer_store_found": True,
        },
        "carrier_surface": {
            "carrier_count": 16,
            "carrier_instruction_count": 5178,
            "carrier_bulk_opcode_hit_count": 0,
            "immediate_direct_callsite_count": 214,
            "unique_immediate_direct_callee_count": 82,
            "direct_callee_instruction_count": 9159,
            "direct_callee_bulk_opcode_hit_count": 0,
            "call_through_memory_site_count": 2,
            "total_machine_callsite_count": 216,
            "runtime_unknown_call_target_count": 0,
            "resolved_call_through_memory_sites": resolved,
        },
        "adjudication": {
            "p13a_fun00765c40_known_derived_and_local_array_subset_complete": True,
            "p13a_fun00765c40_selected_slot_writer_found": False,
            "p13a_fun00765c40_selected_wheel_pointer_escape_found": False,
            "p13a_fun00765c40_nonwheel_runtime_backpointer_store_found": True,
            "p13a_sixteen_carrier_direct_bulk_opcode_subset_complete": True,
            "p13a_sixteen_carrier_direct_callee_bulk_opcode_subset_complete": True,
            "p13a_sixteen_carrier_call_target_surface_complete": True,
            "p13a_fun00770e80_aa60b4_import_indirect_subset_complete": True,
            "p13a_sixteen_carrier_runtime_unknown_call_target_found": False,
            "aggregate_or_bulk_alias_stores_ruled_out": False,
            "other_derived_aliases_ruled_out": False,
            "reconstructed_wheel_pointers_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "callbacks_and_indirect_entry_ruled_out": False,
            "other_indirect_entry_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only already-merged bounded machine surfaces; it adds no new physical-class identity claim.",
            "Zero x86 string-opcode hits cover the 16 exact-root carrier bodies and their 82 immediate direct callees only; hand-unrolled copies, deeper callees and aggregate stores remain open.",
            "The two FUN_00770e80 call-through-memory sites are resolved PE imports to KERNEL32!InterlockedExchange on HDVehicle+0x4020, not selected-wheel callbacks.",
            "The positive HDVehicle+0x6730 runtime-created-node backpointers remain explicit evidence for a distinct non-wheel subobject and prevent any global runtime-pointer gate from closing.",
            "Callbacks/indirect entry outside the bounded carrier callsites, reconstructed pointers and runtime-generated/copied selected-wheel aliases remain open."
        ],
        "next_step": (
            "Trace runtime-generated/copied selected-wheel pointers and callback/indirect-entry surfaces outside the bounded 16-carrier callsites; "
            "promote no global stored-or-escaped-alias or slot gate until those surfaces are exhausted."
        ),
    }


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--derived", type=Path, default=Path("evidence/p1a_p13a_slot01_fun00765c40_derived_alias_handoff.json"))
    parser.add_argument("--local-arrays", type=Path, default=Path("evidence/p1a_p13a_fun00765c40_local_array_callee_machine_closure.json"))
    parser.add_argument("--carrier-bulk", type=Path, default=Path("evidence/p1d_slot3_16carrier_bulk_opcode_closure.json"))
    parser.add_argument("--callee-bulk", type=Path, default=Path("evidence/p1d_slot3_direct_callee_bulk_opcode_closure.json"))
    parser.add_argument("--call-targets", type=Path, default=Path("evidence/p1d_slot3_carrier_call_target_composition.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build(
        load(args.derived),
        load(args.local_arrays),
        load(args.carrier_bulk),
        load(args.callee_bulk),
        load(args.call_targets),
    )
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
