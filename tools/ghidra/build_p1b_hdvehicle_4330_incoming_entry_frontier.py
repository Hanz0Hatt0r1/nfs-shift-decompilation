#!/usr/bin/env python3
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IncomingEntryFrontier/1"
DIRECT = "SHIFT.P1B.HDVehicle4330IncomingDirectCallFrontier/1"
FINAL = "SHIFT.P1B.HDVehicle4330ExternalCallerFinalTranche/1"
INDEX = "SHIFT.P1A.P13AExactCarrierIncomingIndirectIndexFrontier/1"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build(direct_path: Path, final_path: Path, index_path: Path):
    direct, final, index = map(load, [direct_path, final_path, index_path])
    assert direct["format"] == DIRECT and direct["ready"]
    assert final["format"] == FINAL and final["ready"]
    assert index["format"] == INDEX and index["ready"]
    ds = direct["incoming_direct_surface"]
    fa = final["adjudication"]
    ins = index["incoming_indirect_surface"]
    assert direct["carrier_set"]["count"] == 15
    assert (ds["callsite_count"], ds["exact_carrier_internal_callsite_count"], ds["external_callsite_count"], ds["external_caller_count"]) == (25, 14, 11, 7)
    assert fa["external_direct_incoming_receiver_provenance_complete"] is True
    assert fa["remaining_external_caller_count"] == 0
    assert fa["external_direct_incoming_preexisting_4330_alias_found"] is False
    assert (ins["indirect_edge_count"], ins["resolved_indirect_target_count"], ins["unresolved_indirect_target_count"]) == (19500, 0, 19500)
    return {
        "format": FORMAT, "version": 1, "ready": True, "owner": "Process 1B / P1.3B",
        "upstream_contracts": [DIRECT, FINAL, INDEX],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "incoming_direct_callsite_count": 25,
            "incoming_direct_internal_callsite_count": 14,
            "incoming_direct_external_callsite_count": 11,
            "incoming_direct_external_caller_count": 7,
            "incoming_direct_remaining_unresolved_external_caller_count": 0,
            "navigation_index_indirect_edge_count": 19500,
            "navigation_index_resolved_indirect_target_count": 0,
            "navigation_index_unresolved_indirect_target_count": 19500,
        },
        "adjudication": {
            "incoming_direct_entry_surface_complete": True,
            "incoming_direct_external_receiver_provenance_complete": True,
            "incoming_direct_preexisting_4330_alias_found": False,
            "incoming_indirect_index_capability_captured": True,
            "incoming_indirect_index_has_resolved_target_coverage": False,
            "remaining_incoming_entry_blocker_is_unresolved_indirect_target_recovery": True,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Direct incoming entry is fully adjudicated; the remaining incoming-entry uncertainty is indirect target recovery.",
            "The shared SQLite navigation index contains 19,500 indirect edges but resolves none to concrete targets, so zero carrier hits is not an absence proof.",
            "The P1A contract is consumed only for shared-index capability counts; P1A carrier semantics are not imported into P1B.",
        ],
        "next_step": "Recover bounded indirect targets from vtable/callback/function-pointer storage provenance and compare them with the canonical 15 P1B carrier addresses.",
    }


def main():
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("direct"); p.add_argument("final"); p.add_argument("index"); p.add_argument("--output", required=True)
    a = p.parse_args(); out = build(Path(a.direct), Path(a.final), Path(a.index))
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__": main()
