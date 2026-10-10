#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/5"
EXPECTED_V4 = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/4"
EXPECTED_SEEDS = "SHIFT.P1B.HDVehicle4330BoundedRuntimePointerSeedCoverage/1"
EXPECTED_COPY = "SHIFT.P1B.HDVehicle4330KnownCarrierValueCopyOriginClosure/1"
EXPECTED_PROVIDER_COUNT = 7


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(v4_path: Path, seeds_path: Path, copy_path: Path) -> dict:
    v4 = load(v4_path)
    seeds = load(seeds_path)
    copy = load(copy_path)
    if v4["format"] != EXPECTED_V4:
        raise ValueError("unexpected v4 contract")
    if seeds["format"] != EXPECTED_SEEDS:
        raise ValueError("unexpected bounded seed contract")
    if copy["format"] != EXPECTED_COPY:
        raise ValueError("unexpected copy-origin contract")

    v4_surface = v4["surface"]
    seed_surface = seeds["surface"]
    copy_surface = copy["surface"]
    if v4_surface["p1b_exact_carrier_count"] != 15:
        raise ValueError("carrier count drift")
    if v4_surface["composed_coverage_class_count"] != 7:
        raise ValueError("v4 coverage count drift")
    if v4_surface["bounded_exact_carrier_hit_count"] != 0:
        raise ValueError("v4 exact carrier hit surfaced")
    if seed_surface["composed_bounded_seed_domain_count"] != 8:
        raise ValueError("seed domain count drift")
    if seed_surface["composed_bounded_exact_carrier_hit_count"] != 0:
        raise ValueError("bounded seed hit surfaced")
    if copy_surface["direct_known_carrier_value_copy_origin_count"] != 0:
        raise ValueError("known carrier copy origin surfaced")

    return {
        "format": FORMAT,
        "version": 5,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "supersedes": EXPECTED_V4,
        "upstream_contracts": [EXPECTED_V4, EXPECTED_SEEDS, EXPECTED_COPY],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "previous_bounded_coverage_class_count": 7,
            "composed_coverage_class_count": 9,
            "bounded_exact_carrier_hit_count": 0,
            "statically_reachable_getprocaddress_callsite_count": seed_surface["statically_reachable_getprocaddress_callsite_count"],
            "known_carrier_direct_copy_origin_count": copy_surface["direct_known_carrier_value_copy_origin_count"],
            "coverage_additions": [
                {
                    "class": "bounded statically reachable imported-GetProcAddress result storage",
                    "exact_carrier_hit_count": seed_surface["statically_reachable_getprocaddress_carrier_identity_hit_count"],
                    "physical_callsite_count": seed_surface["statically_reachable_getprocaddress_callsite_count"],
                },
                {
                    "class": "direct copy/store from already-materialized exact canonical carrier value",
                    "exact_carrier_origin_count": copy_surface["direct_known_carrier_value_copy_origin_count"],
                },
            ],
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "bounded_getprocaddress_storage_included": True,
            "known_exact_carrier_value_copy_origin_subset_included": True,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "memory_table_derived_carrier_pointers_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "runtime_patching_or_generated_code_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This supersedes /4 by adding bounded imported-GetProcAddress result-storage coverage and the known exact-carrier direct-copy-origin subset.",
            "Runtime-created/table-derived pointers, cross-block reconstruction, runtime patching, opaque/external pointer sources and unbounded generic stores/copies remain open.",
        ],
        "next_step": "Inventory unrelated runtime-populated function-pointer tables and cross-block/table-derived exact-carrier reconstruction before promoting global indirect-entry or store/copy gates.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("v4", type=Path)
    parser.add_argument("seeds", type=Path)
    parser.add_argument("copy", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(args.v4, args.seeds, args.copy)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
