#!/usr/bin/env python3
"""Compose P1B indirect-entry coverage v9 with bounded writable-data target recovery."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREV = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v8.json"
WRITABLE = ROOT / "evidence" / "p1b_hdvehicle_4330_direct_absolute_writable_indirect_recovery.json"
FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/9"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict:
    prev, writable = load(PREV), load(WRITABLE)
    assert prev["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/8"
    assert writable["format"] == "SHIFT.P1B.HDVehicle4330DirectAbsoluteWritableIndirectRecovery/1"
    assert prev["surface"]["composed_coverage_class_count"] == 12
    assert prev["surface"]["bounded_exact_carrier_hit_count"] == 0
    ws = writable["surface"]
    assert ws["direct_absolute_writable_transfer_count"] == 334
    assert ws["unique_writable_slot_count"] == 259
    assert ws["bounded_internal_or_static_candidate_value_count"] == 9
    assert ws["bounded_internal_or_static_exact_carrier_hit_count"] == 0
    assert writable["adjudication"]["bounded_internal_static_provider_subset_complete"] is True

    return {
        "format": FORMAT,
        "version": 9,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "supersedes": prev["format"],
        "upstream_contracts": [prev["format"], writable["format"]],
        "surface": {
            "p1b_exact_carrier_count": prev["surface"]["p1b_exact_carrier_count"],
            "previous_bounded_coverage_class_count": 12,
            "composed_coverage_class_count": 13,
            "bounded_exact_carrier_hit_count": 0,
            "incoming_indirect_navigation_edge_count": prev["surface"]["incoming_indirect_navigation_edge_count"],
            "incoming_indirect_unresolved_target_count": prev["surface"]["incoming_indirect_unresolved_target_count"],
            "direct_absolute_writable_transfer_count": ws["direct_absolute_writable_transfer_count"],
            "direct_absolute_writable_unique_slot_count": ws["unique_writable_slot_count"],
            "direct_absolute_writable_bounded_candidate_value_count": ws["bounded_internal_or_static_candidate_value_count"],
            "direct_absolute_writable_exact_carrier_hit_count": ws["bounded_internal_or_static_exact_carrier_hit_count"],
            "coverage_addition": {
                "class": "direct absolute writable .data indirect target recovery (bounded internal/static providers)",
                "transfer_count": ws["direct_absolute_writable_transfer_count"],
                "slot_count": ws["unique_writable_slot_count"],
                "bounded_candidate_value_count": ws["bounded_internal_or_static_candidate_value_count"],
                "exact_carrier_hit_count": 0,
            },
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "direct_absolute_writable_internal_static_target_subset_included": True,
            "remaining_incoming_entry_blocker_is_unresolved_nonstatic_indirect_target_recovery": True,
            "external_runtime_writable_target_providers_remain_open": True,
            "register_loaded_or_base_indexed_writable_targets_remain_open": True,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "runtime_patching_or_generated_code_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This supersedes /8 by adding bounded internal/static target provenance for the complete direct-absolute writable .data transfer inventory.",
            "The navigation index unresolved-target count remains 19,500 because that index does not map its unresolved edges onto the independently recovered writable-slot targets.",
            "External NVAPI results, alias/indirect writers, register-loaded/base-indexed writable pointers, runtime-written vtables and opaque/generated targets remain open.",
        ],
        "next_step": "Recover register-loaded/base-indexed writable target provenance and alias/indirect writers, then compose those subsets without treating the navigation-index unresolved count as a literal remainder counter.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
