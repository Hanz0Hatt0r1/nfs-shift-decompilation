#!/usr/bin/env python3
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/7"
PREV = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/6"
INCOMING = "SHIFT.P1B.HDVehicle4330IncomingEntryFrontier/1"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build(prev_path: Path, incoming_path: Path):
    prev = load(prev_path)
    incoming = load(incoming_path)
    assert prev["format"] == PREV and prev["ready"]
    assert incoming["format"] == INCOMING and incoming["ready"]
    ps = prev["surface"]
    ins = incoming["surface"]
    assert ps["composed_coverage_class_count"] == 10
    assert ps["bounded_exact_carrier_hit_count"] == 0
    assert ins["incoming_direct_remaining_unresolved_external_caller_count"] == 0
    assert ins["navigation_index_indirect_edge_count"] == 19500
    assert ins["navigation_index_resolved_indirect_target_count"] == 0
    assert ins["navigation_index_unresolved_indirect_target_count"] == 19500
    assert incoming["adjudication"]["remaining_incoming_entry_blocker_is_unresolved_indirect_target_recovery"] is True
    return {
        "format": FORMAT,
        "version": 7,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "supersedes": PREV,
        "upstream_contracts": [PREV, INCOMING],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "previous_bounded_coverage_class_count": 10,
            "composed_coverage_class_count": 11,
            "bounded_exact_carrier_hit_count": 0,
            "incoming_direct_callsite_count": 25,
            "incoming_direct_remaining_unresolved_external_caller_count": 0,
            "incoming_indirect_navigation_edge_count": 19500,
            "incoming_indirect_resolved_target_count": 0,
            "incoming_indirect_unresolved_target_count": 19500,
            "coverage_addition": {
                "class": "incoming-entry frontier isolation",
                "direct_remaining_unresolved_external_caller_count": 0,
                "unresolved_indirect_target_count": 19500,
            },
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "incoming_entry_frontier_subset_included": True,
            "incoming_direct_entry_surface_complete": True,
            "remaining_incoming_entry_blocker_is_unresolved_indirect_target_recovery": True,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "memory_table_derived_carrier_pointers_ruled_out": False,
            "runtime_patching_or_generated_code_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This supersedes /6 by adding the incoming-entry frontier isolation contract.",
            "Direct incoming entry is complete; the unresolved incoming-entry class is now specifically indirect target recovery from the shared navigation index.",
            "Unrelated runtime-populated tables, cross-block/table-derived reconstruction, runtime patching and opaque/external pointer sources remain open."
        ],
        "next_step": "Recover bounded subsets of unresolved indirect targets from vtable/callback/function-pointer storage provenance before promoting global indirect-entry/store-copy gates."
    }


def main():
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("previous"); p.add_argument("incoming"); p.add_argument("--output", required=True)
    a = p.parse_args(); out = build(Path(a.previous), Path(a.incoming))
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__": main()
