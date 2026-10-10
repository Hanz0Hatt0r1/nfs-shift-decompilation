#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/4"
EXPECTED_BASE = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/3"
EXPECTED_DIRECT_TABLE = "SHIFT.P1B.HDVehicle4330ImageBackedTableSeedClosure/1"
EXPECTED_TEXT_DELTA = "SHIFT.P1B.HDVehicle4330TextBaseDeltaTableSeedSurface/1"
EXPECTED_PROVIDER_COUNT = 7


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(base_path: Path, direct_table_path: Path, text_delta_path: Path) -> dict:
    base = load(base_path)
    direct_table = load(direct_table_path)
    text_delta = load(text_delta_path)

    if base.get("format") != EXPECTED_BASE or base.get("ready") is not True:
        raise ValueError("indirect-entry /3 input mismatch")
    if direct_table.get("format") != EXPECTED_DIRECT_TABLE or direct_table.get("ready") is not True:
        raise ValueError("direct image-backed table input mismatch")
    if text_delta.get("format") != EXPECTED_TEXT_DELTA or text_delta.get("ready") is not True:
        raise ValueError("text-base delta table input mismatch")
    for doc in (base, direct_table, text_delta):
        if doc["adjudication"]["external_provider_count"] != EXPECTED_PROVIDER_COUNT:
            raise ValueError("provider-count drift")

    if base["surface"]["bounded_exact_carrier_hit_count"] != 0:
        raise ValueError("base bounded exact-carrier hit reopened")
    if direct_table["adjudication"]["image_backed_direct_table_exact_carrier_seed_subset_complete"] is not True:
        raise ValueError("direct image-backed table subset incomplete")
    if direct_table["surface"]["direct_image_backed_exact_va_table_seed_count"] != 0:
        raise ValueError("direct image-backed exact-VA table seed appeared")
    if direct_table["surface"]["direct_image_backed_exact_rva_table_seed_count"] != 0:
        raise ValueError("direct image-backed exact-RVA table seed appeared")
    if text_delta["adjudication"]["image_backed_text_base_delta_table_seed_subset_complete"] is not True:
        raise ValueError("text-base delta table subset incomplete")
    if text_delta["scan"]["non_executable_section_exact_text_base_delta_hit_count"] != 0:
        raise ValueError("text-base delta data-table seed appeared")
    if text_delta["scan"]["unclassified_executable_diagnostic_count"] != 0:
        raise ValueError("text-base delta executable diagnostic reopened")

    coverage = list(base["surface"]["coverage"])
    coverage.append({
        "class": "direct image-backed exact VA/RVA table seeds",
        "whole_image_raw_bytes_scanned": direct_table["surface"]["whole_image_raw_bytes_scanned"],
        "static_table_record_count": direct_table["surface"]["static_table_record_count"],
        "exact_va_seed_count": direct_table["surface"]["direct_image_backed_exact_va_table_seed_count"],
        "exact_rva_seed_count": direct_table["surface"]["direct_image_backed_exact_rva_table_seed_count"],
        "exact_carrier_hit_count": 0,
    })
    coverage.append({
        "class": "image-backed .text-base delta table seeds",
        "raw_diagnostic_count": text_delta["scan"]["raw_exact_text_base_delta_hit_count"],
        "non_executable_table_seed_count": text_delta["scan"]["non_executable_section_exact_text_base_delta_hit_count"],
        "rel32_diagnostic_count": text_delta["scan"]["rel32_control_transfer_diagnostic_count"],
        "unclassified_executable_diagnostic_count": text_delta["scan"]["unclassified_executable_diagnostic_count"],
        "exact_carrier_hit_count": 0,
    })

    return {
        "format": FORMAT,
        "version": 4,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "supersedes": EXPECTED_BASE,
        "upstream_contracts": [EXPECTED_BASE, EXPECTED_DIRECT_TABLE, EXPECTED_TEXT_DELTA],
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
            "image_backed_direct_table_seed_subset_included": True,
            "image_backed_text_base_delta_table_seed_subset_included": True,
            "memory_table_derived_carrier_pointers_ruled_out": False,
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
            "This supersedes /3 by adding two bounded image-backed table seed classes.",
            "Direct exact VA/RVA table elements and direct .text-base-delta data-table elements are closed negative for the canonical 15 P1B carriers.",
            "Other transformed/delta chains, other section bases, runtime-populated tables, cross-block arithmetic, runtime-copied pointers, delayed module-base consumers, runtime patching, remaining callback families and opaque indirect dispatch remain open."
        ],
        "next_step": "Bound cross-block or runtime-populated memory/table-derived exact-carrier reconstruction and classify any positive pointer store/copy sinks before promoting global indirect-entry gates."
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("direct_table", type=Path)
    parser.add_argument("text_delta", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(args.base, args.direct_table, args.text_delta)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
