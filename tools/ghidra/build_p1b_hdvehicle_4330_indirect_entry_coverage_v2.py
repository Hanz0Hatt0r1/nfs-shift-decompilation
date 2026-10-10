#!/usr/bin/env python3
"""Compose superseding bounded indirect-entry coverage for Process 1B."""
from __future__ import annotations
import argparse, json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/2"
EXPECTED_SEED = "SHIFT.P1B.HDVehicle4330CarrierSeedProvenanceCoverage/1"
EXPECTED_PROVIDER_COUNT = 7


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("ready") is not True:
        raise ValueError("seed provenance evidence not ready")
    return data


def build(seed_path: Path) -> dict:
    seed = load(seed_path)
    if seed.get("format") != EXPECTED_SEED:
        raise ValueError("seed provenance format drift")
    if seed["adjudication"]["external_provider_count"] != EXPECTED_PROVIDER_COUNT:
        raise ValueError("provider count drift")
    if seed["surface"]["exact_carrier_seed_hit_count"] != 0:
        raise ValueError("exact carrier seed appeared")
    return {
        "format": FORMAT,
        "version": 2,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "supersedes": "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/1",
        "upstream_contracts": [EXPECTED_SEED],
        "surface": {
            "composed_coverage_class_count": seed["surface"]["composed_seed_class_count"],
            "bounded_exact_carrier_hit_count": seed["surface"]["exact_carrier_seed_hit_count"],
            "p1b_exact_carrier_count": seed["surface"]["p1b_exact_carrier_count"],
            "coverage": seed["surface"]["classes"],
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "bsearch_closed_and_included": True,
            "exact_imagebase_plus_exact_rva_immediate_seed_subset_included": True,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "remaining_callback_api_families_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This supersedes /1 with the current four-class bounded seed provenance baseline.",
            "Runtime-generated/copied/encoded pointers, split/table-derived RVA arithmetic, runtime patching, remaining callback families and opaque indirect dispatch remain open."
        ],
        "next_step": "Bound split/table-derived/encoded and runtime-copied exact-carrier pointer flows before promoting global indirect-entry gates."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("seed", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    text = json.dumps(build(a.seed), indent=2, sort_keys=True) + "\n"
    if a.output: a.output.write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
