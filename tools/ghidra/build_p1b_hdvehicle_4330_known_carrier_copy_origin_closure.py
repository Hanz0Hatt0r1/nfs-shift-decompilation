#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330KnownCarrierValueCopyOriginClosure/1"
EXPECTED_PROVIDER_COUNT = 7
EXPECTED_SOURCE = "SHIFT.P1B.HDVehicle4330SourceSymbolAddressTaking/1"
EXPECTED_SEEDS = "SHIFT.P1B.HDVehicle4330BoundedRuntimePointerSeedCoverage/1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(source_path: Path, seed_path: Path) -> dict:
    source = load(source_path)
    seeds = load(seed_path)
    if source["format"] != EXPECTED_SOURCE:
        raise ValueError("unexpected source-address-taking contract")
    if seeds["format"] != EXPECTED_SEEDS:
        raise ValueError("unexpected bounded seed contract")

    s = source["surface"]
    ss = seeds["surface"]
    if s["exact_carrier_symbol_count"] != 15:
        raise ValueError("canonical carrier count drift")
    if s["source_visible_address_taken_carrier_symbol_count"] != 0:
        raise ValueError("source-visible carrier address-taking is no longer negative")
    if s["source_visible_noncall_symbol_value_use_count"] != 0:
        raise ValueError("source-visible carrier value use is no longer negative")
    if ss["p1b_exact_carrier_count"] != 15:
        raise ValueError("bounded seed carrier count drift")
    if ss["composed_bounded_seed_domain_count"] != 8:
        raise ValueError("bounded seed domain count drift")
    if ss["composed_bounded_exact_carrier_hit_count"] != 0:
        raise ValueError("bounded seed domain now contains an exact carrier")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [EXPECTED_SOURCE, EXPECTED_SEEDS],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "source_exact_carrier_symbol_occurrence_count": s["total_exact_carrier_symbol_occurrence_count"],
            "source_address_taken_carrier_count": s["source_visible_address_taken_carrier_symbol_count"],
            "source_noncall_carrier_value_use_count": s["source_visible_noncall_symbol_value_use_count"],
            "bounded_seed_domain_count": ss["composed_bounded_seed_domain_count"],
            "bounded_seed_exact_carrier_hit_count": ss["composed_bounded_exact_carrier_hit_count"],
            "direct_known_carrier_value_copy_origin_count": 0,
        },
        "adjudication": {
            "known_exact_carrier_value_copy_origin_subset_complete": True,
            "known_exact_carrier_value_direct_store_or_copy_seed_found": False,
            "bounded_known_carrier_value_copy_path_can_seed_runtime_pointer_table": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This closes only direct copy/store origins that would require an already materialized exact canonical P1B carrier value.",
            "Reconstructed, table-derived, cross-block, runtime-created, patched, decoded, opaque-returned or externally supplied carrier-equivalent values remain open.",
            "The global runtime-generated/copied-function-pointer and generic store/copy gates remain fail-closed.",
        ],
        "next_step": "Inventory runtime-created/table-derived function-pointer values whose origins are not an already materialized exact carrier, then classify their stores and indirect-call consumers.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("seeds", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(args.source, args.seeds)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
