#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREV = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v10.json"
ADD = ROOT / "evidence" / "p1a_p13a_fun005ffc50_base_indexed_data_stack_spill_reload.json"
FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/11"


def build() -> dict:
    previous = json.loads(PREV.read_text(encoding="utf-8"))
    spill = json.loads(ADD.read_text(encoding="utf-8"))

    assert previous["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/10"
    assert spill["format"] == "SHIFT.P1A.P13AFun005ffc50BaseIndexedDataStackSpillReload/1"
    assert previous["surface"]["composed_coverage_class_count"] == 14
    assert spill["inventory"]["base_indexed_data_load_count"] == 63
    assert spill["inventory"]["spilled_load_count"] == 2
    assert spill["inventory"]["stack_reload_event_count"] == 0
    assert spill["inventory"]["reload_derived_indirect_transfer_count"] == 0
    assert spill["inventory"]["tainted_register_indirect_transfer_count"] == 0

    return {
        "format": FORMAT,
        "version": 11,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "supersedes": previous["format"],
        "upstream_contracts": [previous["format"], spill["format"]],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "previous_bounded_coverage_class_count": 14,
            "composed_coverage_class_count": 15,
            "bounded_exact_carrier_hit_count": 0,
            "incoming_indirect_navigation_edge_count": 19500,
            "incoming_indirect_unresolved_target_count": 19500,
            "base_indexed_writable_data_load_count": 63,
            "base_indexed_stack_spill_event_count": 2,
            "base_indexed_stack_reload_event_count": 0,
            "base_indexed_reload_derived_indirect_transfer_count": 0,
            "base_indexed_tainted_register_indirect_transfer_count": 0,
            "coverage_addition": {
                "class": "base/index-addressed writable .data exact mov stack spill/reload propagation",
                "spill_event_count": 2,
                "reload_event_count": 0,
                "reload_derived_indirect_transfer_count": 0,
                "exact_carrier_hit_count": 0,
            },
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "base_indexed_writable_same_register_near_transfer_subset_included": True,
            "base_indexed_exact_mov_stack_spill_reload_subset_included": True,
            "base_indexed_copy_transform_spill_subset_bounded": True,
            "base_indexed_implicit_or_normalized_stack_carriers_remain_open": True,
            "base_indexed_inter_block_carry_remains_open": True,
            "remaining_incoming_entry_blocker_is_unresolved_nonstatic_indirect_target_recovery": True,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "runtime_patching_or_generated_code_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This supersedes /10 by composing only the exact mov-based EBP/ESP stack spill/reload propagation subset recovered from the shared P1.3A machine scan.",
            "The two observed spills produce zero exact reloads and zero reload-derived or surviving-taint indirect transfers in the bounded window.",
            "Implicit push/pop, normalized ESP-delta carriers, inter-block/phi carry, aliases, runtime mutation and other indirect target classes remain open.",
            "The 19,500 navigation-index unresolved edges remain a capability metric, not a decrementing remainder counter.",
        ],
        "next_step": "Bound implicit/normalized stack carriers and inter-block carry for base/index-derived writable values before promoting any global indirect-entry gate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
