#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330ImageBackedTableSeedClosure/1"
EXPECTED_WHOLE = "SHIFT.P1B.HDVehicle4330WholeImageLiteralPointerSurface/1"
EXPECTED_STATIC = "SHIFT.P1B.HDVehicle4330ExactCarrierStaticTableSurface/1"
EXPECTED_PROVIDER_COUNT = 7


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(whole_path: Path, static_path: Path) -> dict:
    whole = load(whole_path)
    static = load(static_path)
    if whole.get("format") != EXPECTED_WHOLE or whole.get("ready") is not True:
        raise ValueError("whole-image literal-pointer input mismatch")
    if static.get("format") != EXPECTED_STATIC or static.get("ready") is not True:
        raise ValueError("static-table input mismatch")
    for doc in (whole, static):
        if doc["adjudication"]["external_provider_count"] != EXPECTED_PROVIDER_COUNT:
            raise ValueError("provider-count drift")

    ws = whole["whole_image_surface"]
    ss = static["static_table_surface"]
    if whole["carrier_set"]["count"] != 15 or static["carrier_set"]["count"] != 15:
        raise ValueError("canonical carrier count drift")
    if ws["absolute_va_hit_count"] != 0 or ws["rva_hit_count"] != 0:
        raise ValueError("whole-image exact carrier VA/RVA seed reopened")
    if ss["exact_carrier_pointer_hit_count"] != 0:
        raise ValueError("static-table exact carrier VA seed reopened")
    if whole["adjudication"]["whole_image_exact_carrier_absolute_va_literal_surface_complete"] is not True:
        raise ValueError("whole-image absolute-VA surface incomplete")
    if whole["adjudication"]["whole_image_exact_carrier_rva_literal_surface_complete"] is not True:
        raise ValueError("whole-image RVA surface incomplete")
    if static["adjudication"]["exact_4330_carrier_static_table_literal_pointer_subset_complete"] is not True:
        raise ValueError("static-table literal pointer surface incomplete")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [EXPECTED_WHOLE, EXPECTED_STATIC],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "retail_file_size": whole["authority"]["retail_file_size"],
            "whole_image_raw_bytes_scanned": whole["authority"]["whole_file_raw_bytes_scanned"],
            "whole_image_exact_carrier_absolute_va_hit_count": ws["absolute_va_hit_count"],
            "whole_image_exact_carrier_rva_hit_count": ws["rva_hit_count"],
            "static_table_record_count": ss["record_count"],
            "static_table_raw_bytes_scanned": ss["raw_hex_bytes_total"],
            "static_table_exact_carrier_absolute_va_hit_count": ss["exact_carrier_pointer_hit_count"],
            "direct_image_backed_exact_va_table_seed_count": 0,
            "direct_image_backed_exact_rva_table_seed_count": 0,
        },
        "adjudication": {
            "image_backed_direct_table_exact_carrier_seed_subset_complete": True,
            "image_backed_exact_carrier_va_table_seed_found": False,
            "image_backed_exact_carrier_rva_table_seed_found": False,
            "direct_imagebase_plus_image_table_exact_rva_seed_path_ruled_out": True,
            "memory_table_derived_carrier_pointers_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This closes only direct image-backed table elements that already contain an exact carrier absolute VA or exact carrier RVA.",
            "The exhaustive retail-byte scan has zero exact P1B carrier VA and RVA encodings, so a direct load of such an image-backed element cannot seed an exact carrier pointer, including preferred-imagebase + exact-table-RVA.",
            "Runtime-populated tables, transformed/delta/encoded entries, split or cross-block arithmetic, opaque helper returns, runtime patching and copied pointers remain open.",
            "The Ghidra static-table export is a finite navigation cross-check; retail whole-image bytes are the authority for the zero direct VA/RVA seed claim."
        ],
        "next_step": "Bound transformed/delta table entries and cross-block memory-derived carrier reconstruction, then classify any positive runtime store/copy sinks."
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("whole", type=Path)
    parser.add_argument("static", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(args.whole, args.static)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
