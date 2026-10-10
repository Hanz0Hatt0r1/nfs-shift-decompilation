#!/usr/bin/env python3
"""Compose _bsearch into the bounded P1B runtime-callback coverage baseline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/4"
SUPERSEDES = "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/3"
OLD = "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/3"
BSEARCH = "SHIFT.P1B.HDVehicle4330BsearchCallbackClosure/1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(old_path: Path, bsearch_path: Path) -> dict:
    old, bs = load(old_path), load(bsearch_path)
    if old.get("format") != OLD or old.get("ready") is not True:
        raise ValueError("runtime callback /3 baseline drift")
    if bs.get("format") != BSEARCH or bs.get("ready") is not True:
        raise ValueError("_bsearch callback contract drift")
    if old["adjudication"]["external_provider_count"] != 7 or bs["adjudication"]["external_provider_count"] != 7:
        raise ValueError("provider count drift")
    if old["surface"]["closed_surface_count"] != 7 or old["surface"]["bounded_callback_capable_callsite_count"] != 49:
        raise ValueError("runtime callback /3 count drift")
    if old["surface"]["unique_possible_callback_entrypoint_count"] != 34:
        raise ValueError("runtime callback /3 entrypoint drift")
    if old["surface"]["exact_4330_carrier_entrypoint_hit_count"] != 0:
        raise ValueError("old aggregate carrier hit appeared")
    ba = bs["adjudication"]
    if ba["bsearch_physical_callsite_surface_complete"] is not True or ba["bsearch_comparator_provenance_complete"] is not True:
        raise ValueError("_bsearch surface incomplete")
    if ba["bsearch_physical_callsite_count"] != 2 or ba["bsearch_exact_p1b_carrier_hit_count"] != 0:
        raise ValueError("_bsearch count/carrier drift")

    entrypoints = set(old["surface"]["possible_entrypoints"])
    entrypoints.update(row["comparator"] for row in bs["registrations"])
    if len(entrypoints) != 36:
        raise ValueError(f"unexpected unique entrypoint count: {len(entrypoints)}")
    coverage = list(old["surface"]["coverage"])
    coverage.append({
        "surface": "CRT _bsearch comparators",
        "physical_callsite_count": 2,
        "possible_entrypoint_count": 2,
        "exact_4330_carrier_hit_count": 0,
    })
    return {
        "format": FORMAT,
        "version": 4,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "supersedes": SUPERSEDES,
        "upstream_contracts": [OLD, BSEARCH],
        "surface": {
            "closed_surface_count": 8,
            "bounded_callback_capable_callsite_count": 51,
            "unique_possible_callback_entrypoint_count": 36,
            "exact_4330_carrier_entrypoint_hit_count": 0,
            "coverage": coverage,
            "possible_entrypoints": sorted(entrypoints),
        },
        "adjudication": {
            "bounded_runtime_callback_coverage_composed": True,
            "bsearch_included_in_runtime_callback_baseline": True,
            "bounded_runtime_callback_exact_4330_carrier_hit_found": False,
            "runtime_callback_registration_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "remaining_callback_api_families_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes eight bounded callback/indirect-entry surfaces, now including both retail _bsearch comparators.",
            "It does not claim that all callback-capable APIs or application-owned wrappers are inventoried.",
            "Generic/runtime-generated/copied/encoded function-pointer paths and opaque indirect dispatch remain open."
        ],
        "next_step": "Use /4 as the no-duplication callback baseline; inventory remaining callback families and generic/runtime-generated function-pointer paths before promoting global indirect-entry gates.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("old", type=Path)
    p.add_argument("bsearch", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = build(args.old, args.bsearch)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
