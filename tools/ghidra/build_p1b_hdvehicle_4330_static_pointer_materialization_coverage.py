#!/usr/bin/env python3
"""Compose static/source-visible exact-carrier function-pointer materialization negatives for P1B."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330StaticFunctionPointerMaterializationCoverage/1"
EXPECTED = {
    "vtable": "SHIFT.P1B.HDVehicle4330ExactCarrierVtableSurface/1",
    "static": "SHIFT.P1B.HDVehicle4330ExactCarrierStaticTableSurface/1",
    "literal": "SHIFT.P1B.HDVehicle4330WholeImageLiteralPointerSurface/1",
    "source": "SHIFT.P1B.HDVehicle4330SourceSymbolAddressTaking/1",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(vtable_path: Path, static_path: Path, literal_path: Path, source_path: Path) -> dict:
    docs = {
        "vtable": load(vtable_path), "static": load(static_path),
        "literal": load(literal_path), "source": load(source_path),
    }
    for key, doc in docs.items():
        if doc.get("format") != EXPECTED[key]:
            raise ValueError(f"{key} format mismatch: {doc.get('format')!r}")
        if doc.get("ready") is not True:
            raise ValueError(f"{key} evidence is not ready")
        if doc.get("adjudication", {}).get("external_provider_count") != 7:
            raise ValueError(f"{key} provider-count drift")

    vtable, static, literal, source = docs["vtable"], docs["static"], docs["literal"], docs["source"]
    if vtable["carrier_set"]["count"] != 15 or static["carrier_set"]["count"] != 15 or literal["carrier_set"]["count"] != 15:
        raise ValueError("canonical carrier count drift")
    if source["surface"]["exact_carrier_symbol_count"] != 15:
        raise ValueError("source carrier count drift")

    if vtable["vtable_surface"]["exact_carrier_target_hit_count"] != 0:
        raise ValueError("exact carrier vtable target appeared")
    if static["static_table_surface"]["exact_carrier_pointer_hit_count"] != 0:
        raise ValueError("exact carrier static-table pointer appeared")
    if literal["whole_image_surface"]["absolute_va_hit_count"] != 0 or literal["whole_image_surface"]["rva_hit_count"] != 0:
        raise ValueError("exact carrier whole-image literal appeared")
    if source["surface"]["source_visible_noncall_symbol_value_use_count"] != 0 or source["surface"]["source_visible_address_taken_carrier_symbol_count"] != 0:
        raise ValueError("source-visible exact carrier symbol materialization appeared")

    required_true = [
        vtable["adjudication"]["exact_4330_carrier_vtable_target_subset_complete"],
        static["adjudication"]["exact_4330_carrier_static_table_literal_pointer_subset_complete"],
        literal["adjudication"]["whole_image_exact_carrier_absolute_va_literal_surface_complete"],
        literal["adjudication"]["whole_image_exact_carrier_rva_literal_surface_complete"],
        source["adjudication"]["source_visible_exact_carrier_symbol_reference_surface_complete"],
    ]
    if any(v is not True for v in required_true):
        raise ValueError("upstream static/source-visible subset reopened")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [EXPECTED[k] for k in ("vtable", "static", "literal", "source")],
        "surface": {
            "exact_carrier_count": 15,
            "closed_materialization_class_count": 4,
            "exact_carrier_materialization_hit_count": 0,
            "classes": [
                {
                    "class": "vtable candidate targets",
                    "bounded_unit_count": vtable["vtable_surface"]["slot_count"],
                    "bounded_unit": "vtable slots",
                    "exact_carrier_hit_count": 0,
                },
                {
                    "class": "static-table absolute pointers",
                    "bounded_unit_count": static["static_table_surface"]["record_count"],
                    "bounded_unit": "static-table records",
                    "scanned_raw_byte_count": static["static_table_surface"]["raw_hex_bytes_total"],
                    "exact_carrier_hit_count": 0,
                },
                {
                    "class": "whole-image absolute VA/RVA literals",
                    "bounded_unit_count": literal["authority"]["whole_file_raw_bytes_scanned"],
                    "bounded_unit": "retail file bytes",
                    "absolute_va_hit_count": 0,
                    "rva_hit_count": 0,
                    "exact_carrier_hit_count": 0,
                },
                {
                    "class": "Ghidra C exact-symbol references",
                    "bounded_unit_count": source["surface"]["total_exact_carrier_symbol_occurrence_count"],
                    "bounded_unit": "exact carrier symbol occurrences",
                    "noncall_symbol_value_use_count": 0,
                    "address_taken_symbol_count": 0,
                    "exact_carrier_hit_count": 0,
                },
            ],
        },
        "adjudication": {
            "static_and_source_visible_exact_carrier_pointer_materialization_coverage_composed": True,
            "bounded_static_pointer_materialization_exact_carrier_hit_found": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This aggregate composes four already-bounded static/source-visible function-pointer materialization classes only.",
            "It does not rule out runtime-generated, copied, encoded, reconstructed, code-relative/EIP-derived, heap/global-written or otherwise decompiler-opaque function pointers.",
            "Zero hits in these bounded classes does not by itself prove global indirect entry into exact carriers impossible."
        ],
        "next_step": "Continue machine-level runtime-generated/copied/reconstructed exact-carrier pointer creation and stores; keep global indirect-entry and manager identity gates fail-closed."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("vtable", type=Path); p.add_argument("static", type=Path)
    p.add_argument("literal", type=Path); p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = build(a.vtable, a.static, a.literal, a.source)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output: a.output.write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
