#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREV = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v11.json"
ADD = ROOT / "evidence" / "p1b_hdvehicle_4330_base_indexed_implicit_stack_carriers.json"
FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/12"


def build() -> dict:
    previous = json.loads(PREV.read_text(encoding="utf-8"))
    implicit = json.loads(ADD.read_text(encoding="utf-8"))

    assert previous["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/11"
    assert implicit["format"] == "SHIFT.P1B.HDVehicle4330BaseIndexedImplicitStackCarrierSurface/1"
    assert previous["surface"]["composed_coverage_class_count"] == 15
    assert implicit["inventory"]["base_indexed_data_load_count"] == 63
    assert implicit["inventory"]["implicit_push_event_count"] == 5
    assert implicit["inventory"]["implicit_pop_reload_event_count"] == 0
    assert implicit["inventory"]["normalized_esp_adjust_event_count"] == 0
    assert implicit["inventory"]["tainted_register_indirect_transfer_count"] == 0
    assert implicit["inventory"]["direct_call_argument_escape_count"] == 5

    return {
        "format": FORMAT,
        "version": 12,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "supersedes": previous["format"],
        "upstream_contracts": [previous["format"], implicit["format"]],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "previous_bounded_coverage_class_count": 15,
            "composed_coverage_class_count": 16,
            "bounded_exact_carrier_hit_count": 0,
            "incoming_indirect_navigation_edge_count": 19500,
            "incoming_indirect_unresolved_target_count": 19500,
            "base_indexed_writable_data_load_count": 63,
            "base_indexed_implicit_push_event_count": 5,
            "base_indexed_implicit_pop_reload_event_count": 0,
            "base_indexed_normalized_esp_adjust_event_count": 0,
            "base_indexed_tainted_indirect_transfer_count": 0,
            "base_indexed_direct_call_argument_escape_count": 5,
            "base_indexed_direct_call_argument_escape_unique_callee_count": 4,
            "coverage_addition": {
                "class": "base/index-addressed writable .data implicit stack carrier surface",
                "implicit_push_event_count": 5,
                "implicit_pop_reload_event_count": 0,
                "normalized_esp_adjust_event_count": 0,
                "tainted_indirect_transfer_count": 0,
                "direct_call_argument_escape_count": 5,
                "exact_carrier_hit_count": 0
            }
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "base_indexed_exact_mov_stack_spill_reload_subset_included": True,
            "base_indexed_implicit_stack_carrier_surface_included": True,
            "base_indexed_direct_call_argument_escapes_require_callee_provenance": True,
            "base_indexed_inter_block_carry_remains_open": True,
            "remaining_incoming_entry_blocker_is_unresolved_nonstatic_indirect_target_recovery": True,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "runtime_patching_or_generated_code_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7
        },
        "limits": [
            "This supersedes /11 by composing the bounded implicit push/pop and normalized ESP carrier scan over the same 63 base/index-addressed writable .data loads.",
            "Five tainted values escape as arguments to direct callees; those callee-side flows are an explicit open provenance frontier rather than a negative closure.",
            "No implicit pop reload, normalized ESP-delta event, or tainted indirect CALL/JMP occurs before same-block termination.",
            "Interprocedural callee flow, inter-block/phi carry, aliases, runtime mutation and other indirect target classes remain open.",
            "The 19,500 navigation-index unresolved edges remain a capability metric, not a decrementing remainder counter."
        ],
        "next_step": "Classify the four unique direct callees receiving five base/index-derived argument escapes, then bound inter-block carry before promoting any global indirect-entry gate."
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
