#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VTABLE = ROOT / "evidence" / "p1b_hdvehicle_4330_exact_carrier_vtable_surface.json"
FRONTIER = ROOT / "evidence" / "p1b_hdvehicle_4330_incoming_entry_frontier.json"
FORMAT = "SHIFT.P1B.HDVehicle4330StaticVtableIndirectRecovery/1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict:
    vtable = load(VTABLE)
    frontier = load(FRONTIER)
    assert vtable["format"] == "SHIFT.P1B.HDVehicle4330ExactCarrierVtableSurface/1"
    assert frontier["format"] == "SHIFT.P1B.HDVehicle4330IncomingEntryFrontier/1"
    vs = vtable["vtable_surface"]
    fs = frontier["surface"]
    assert vtable["carrier_set"]["count"] == 15
    assert vs["slot_count"] == 22416
    assert vs["exact_carrier_target_hit_count"] == 0
    assert fs["incoming_indirect_unresolved_target_count"] == 19500
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [vtable["format"], frontier["format"]],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "static_vtable_candidate_count": vs["candidate_table_count"],
            "static_vtable_slot_count": vs["slot_count"],
            "static_vtable_exact_carrier_target_hit_count": vs["exact_carrier_target_hit_count"],
            "incoming_indirect_navigation_edge_count": fs["incoming_indirect_navigation_edge_count"],
            "incoming_indirect_unresolved_target_count": fs["incoming_indirect_unresolved_target_count"],
        },
        "adjudication": {
            "static_vtable_indirect_target_subset_complete": True,
            "static_vtable_can_target_exact_p1b_carrier": False,
            "remaining_incoming_indirect_blocker_requires_nonstatic_vtable_or_other_runtime_target_provenance": True,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only indirect targets backed by the pinned static vtable candidate inventory.",
            "Runtime-written vtables, callback tables, copied/generated pointers and opaque memory remain open.",
        ],
        "next_step": "Recover callback-backed and persistent function-pointer-storage targets from the unresolved indirect navigation set.",
    }


def main() -> int:
    print(json.dumps(build(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
