#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREV = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v7.json"
VTABLE = ROOT / "evidence" / "p1b_hdvehicle_4330_static_vtable_indirect_recovery.json"
FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/8"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict:
    prev = load(PREV)
    vtable = load(VTABLE)
    assert prev["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/7"
    assert vtable["format"] == "SHIFT.P1B.HDVehicle4330StaticVtableIndirectRecovery/1"
    ps = prev["surface"]
    vs = vtable["surface"]
    assert ps["composed_coverage_class_count"] == 11
    assert vs["static_vtable_slot_count"] == 22416
    assert vs["static_vtable_exact_carrier_target_hit_count"] == 0
    return {
        "format": FORMAT,
        "version": 8,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "supersedes": prev["format"],
        "upstream_contracts": [prev["format"], vtable["format"]],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "previous_bounded_coverage_class_count": 11,
            "composed_coverage_class_count": 12,
            "bounded_exact_carrier_hit_count": 0,
            "incoming_indirect_navigation_edge_count": ps["incoming_indirect_navigation_edge_count"],
            "incoming_indirect_unresolved_target_count": ps["incoming_indirect_unresolved_target_count"],
            "static_vtable_candidate_count": vs["static_vtable_candidate_count"],
            "static_vtable_slot_count": vs["static_vtable_slot_count"],
            "static_vtable_exact_carrier_target_hit_count": 0,
            "coverage_addition": {
                "class": "static vtable-backed indirect target recovery",
                "slot_count": vs["static_vtable_slot_count"],
                "exact_carrier_target_hit_count": 0,
            },
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "static_vtable_indirect_target_subset_included": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "remaining_incoming_entry_blocker_is_unresolved_nonstatic_indirect_target_recovery": True,
            "indirect_entry_into_carriers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "runtime_patching_or_generated_code_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This supersedes /7 by adding the static-vtable indirect-target recovery subset.",
            "Runtime-written vtables, callbacks, persistent function-pointer stores and opaque/runtime-generated targets remain open.",
        ],
        "next_step": "Recover callback-backed and persistent function-pointer-storage target subsets from the unresolved indirect navigation set.",
    }


def main() -> int:
    print(json.dumps(build(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
