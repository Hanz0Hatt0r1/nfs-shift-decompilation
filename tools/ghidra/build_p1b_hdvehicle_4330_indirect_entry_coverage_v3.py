#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/3"
EXPECTED_BASE = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/2"
EXPECTED_ENCODED = "SHIFT.P1B.HDVehicle4330ConstantEncodedSynthesis/1"
EXPECTED_PROVIDER_COUNT = 7


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(base_path: Path, encoded_path: Path) -> dict:
    base = load(base_path)
    encoded = load(encoded_path)
    if base.get("format") != EXPECTED_BASE or base.get("ready") is not True:
        raise ValueError("indirect-entry /2 input mismatch")
    if encoded.get("format") != EXPECTED_ENCODED or encoded.get("ready") is not True:
        raise ValueError("constant encoded input mismatch")
    for doc in (base, encoded):
        if doc["adjudication"]["external_provider_count"] != EXPECTED_PROVIDER_COUNT:
            raise ValueError("provider-count drift")
    if base["surface"]["bounded_exact_carrier_hit_count"] != 0:
        raise ValueError("base bounded exact-carrier hit reopened")
    if encoded["scan"]["exact_carrier_synthesis_hit_count"] != 0:
        raise ValueError("constant-only exact-carrier synthesis hit appeared")
    if encoded["adjudication"]["constant_only_encoded_carrier_synthesis_subset_complete"] is not True:
        raise ValueError("constant-only encoded subset incomplete")

    coverage = list(base["surface"]["coverage"])
    coverage.append({
        "class": "constant-only straight-line encoded carrier synthesis",
        "instruction_count": encoded["scan"]["instruction_count"],
        "constant_seed_count": encoded["scan"]["constant_seed_count"],
        "recognized_transition_count": encoded["scan"]["recognized_transition_count"],
        "exact_carrier_hit_count": 0,
    })

    return {
        "format": FORMAT,
        "version": 3,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "supersedes": EXPECTED_BASE,
        "upstream_contracts": [EXPECTED_BASE, EXPECTED_ENCODED],
        "surface": {
            "p1b_exact_carrier_count": base["surface"]["p1b_exact_carrier_count"],
            "composed_coverage_class_count": len(coverage),
            "bounded_exact_carrier_hit_count": 0,
            "coverage": coverage,
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "bsearch_closed_and_included": True,
            "exact_imagebase_plus_exact_rva_immediate_seed_subset_included": True,
            "constant_only_encoded_carrier_synthesis_subset_included": True,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
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
            "This supersedes /2 by adding the bounded constant-only straight-line encoded synthesis class.",
            "Memory/table-derived values, split/cross-block arithmetic, runtime-copied pointers, delayed module-base consumers, runtime patching, remaining callback families and opaque indirect dispatch remain open."
        ],
        "next_step": "Bound memory/table-derived and cross-block exact-carrier reconstruction, then classify runtime store/copy sinks before promoting global indirect-entry gates."
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("encoded", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(args.base, args.encoded)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
