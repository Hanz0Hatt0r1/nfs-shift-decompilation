#!/usr/bin/env python3
"""Compose the bounded on-disk/static exact-carrier seed surface for P1.3A."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13AStaticCarrierSeedHandoff/1"
STATIC_FORMAT = "SHIFT.P1A.P13ASlot01StaticCallbackTargetComposition/1"
ABS_FORMAT = "SHIFT.P1A.P13AExactCarrierWholeImagePointerLiteralClosure/1"
TEXT_RVA_FORMAT = "SHIFT.P1A.P13AExactCarrierTextRvaLiteralClosure/1"
RDATA_RVA_FORMAT = "SHIFT.P1A.P13AExactCarrierRdataRvaDiagnosticClosure/1"
RELOC_FORMAT = "SHIFT.P1A.P13APeBaseRelocationCarrierClosure/1"
INDIRECT_FORMAT = "SHIFT.P1A.P13AExactCarrierIncomingIndirectIndexFrontier/1"


def require(data: dict, fmt: str, label: str) -> dict:
    if data.get("format") != fmt or data.get("ready") is not True:
        raise ValueError(f"unexpected or incomplete {label}")
    return data.get("adjudication", {})


def build(static: dict, absolute: dict, text_rva: dict, rdata_rva: dict, reloc: dict, indirect: dict) -> dict:
    sa = require(static, STATIC_FORMAT, "static callback target composition")
    aa = require(absolute, ABS_FORMAT, "whole-image absolute literal closure")
    ta = require(text_rva, TEXT_RVA_FORMAT, "text RVA literal closure")
    ra = require(rdata_rva, RDATA_RVA_FORMAT, "rdata RVA diagnostic closure")
    pa = require(reloc, RELOC_FORMAT, "PE relocation closure")
    ia = require(indirect, INDIRECT_FORMAT, "incoming indirect index frontier")

    checks = [
        (sa.get("p13a_exact_carrier_callind_caller_subset_complete") is True, "carrier CALLIND-caller subset"),
        (sa.get("p13a_exact_carrier_vtable_target_subset_complete") is True, "vtable target subset"),
        (sa.get("p13a_exact_carrier_static_table_literal_pointer_subset_complete") is True, "static-table target subset"),
        (sa.get("p13a_exact_carrier_static_target_hit_found") is False, "static target hit"),
        (aa.get("p13a_whole_image_exact_carrier_absolute_va_literal_subset_complete") is True, "absolute VA literal subset"),
        (aa.get("p13a_whole_image_exact_carrier_absolute_va_literal_hit_found") is False, "absolute VA hit"),
        (ta.get("p13a_text_exact_carrier_rva_literal_subset_complete") is True, "text RVA subset"),
        (ta.get("p13a_text_exact_carrier_rva_literal_hit_found") is False, "text RVA hit"),
        (ra.get("p13a_whole_image_raw_exact_carrier_rva_match_subset_complete") is True, "whole-image raw RVA match subset"),
        (ra.get("p13a_whole_image_raw_exact_carrier_rva_semantic_pointer_hit_found") is False, "raw RVA semantic pointer hit"),
        (pa.get("p13a_standard_pe_base_relocation_subset_complete") is True, "PE relocation subset"),
        (pa.get("p13a_standard_pe_base_relocation_records_present") is False, "PE relocation presence"),
        (pa.get("p13a_pe_loader_base_relocation_carrier_pointer_path_ruled_out") is True, "PE loader relocation path"),
        (ia.get("p13a_incoming_indirect_index_frontier_captured") is True, "incoming indirect frontier"),
        (ia.get("p13a_incoming_indirect_index_has_resolved_target_coverage") is False, "incoming indirect resolved coverage"),
        (ia.get("p13a_index_can_prove_exact_carrier_incoming_indirect_absence") is False, "incoming indirect absence capability"),
    ]
    for ok, label in checks:
        if not ok:
            raise ValueError(f"upstream drift: {label}")

    if static.get("carrier_set", {}).get("count") != 16:
        raise ValueError("carrier count drift")
    if absolute.get("absolute_va_literal_scan", {}).get("hit_count") != 0:
        raise ValueError("absolute VA hit count drift")
    if rdata_rva.get("adjudication", {}).get("p13a_non_text_exact_carrier_rva_diagnostic_count") != 2:
        raise ValueError("rdata diagnostic count drift")
    if indirect.get("incoming_indirect_surface", {}).get("indirect_edge_count") != 19500:
        raise ValueError("incoming indirect edge count drift")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contracts": [STATIC_FORMAT, ABS_FORMAT, TEXT_RVA_FORMAT, RDATA_RVA_FORMAT, RELOC_FORMAT, INDIRECT_FORMAT],
        "carrier_set": static["carrier_set"],
        "bounded_static_seed_surface": {
            "exported_vtable_exact_carrier_hits": 0,
            "exported_static_table_exact_carrier_hits": 0,
            "whole_image_absolute_va_literal_hits": 0,
            "whole_image_raw_rva_matches": 2,
            "whole_image_raw_rva_semantic_pointer_hits": 0,
            "pe_base_relocation_records_present": False,
            "exact_carrier_callind_caller_edges": 0,
            "incoming_indirect_index_edges": 19500,
            "incoming_indirect_index_resolved_targets": 0,
        },
        "adjudication": {
            "p13a_bounded_on_disk_static_exact_carrier_seed_surface_complete": True,
            "p13a_bounded_on_disk_static_exact_carrier_seed_hit_found": False,
            "p13a_standard_pe_loader_relocation_seed_path_ruled_out": True,
            "p13a_incoming_indirect_index_capability_gap_explicit": True,
            "runtime_callback_registration_ruled_out": False,
            "incoming_indirect_entry_ruled_out": False,
            "manual_imagebase_plus_rva_pointer_construction_ruled_out": False,
            "encoded_or_reconstructed_carrier_pointers_ruled_out": False,
            "runtime_generated_or_copied_carrier_pointers_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "The complete flag is scoped to the explicitly composed on-disk/static classes: exported vtable/static tables, raw absolute-VA literals, raw RVA byte matches, and standard PE base relocations.",
            "The incoming-indirect SQLite result is a capability gap, not negative semantic evidence: all 19,500 indirect targets are unresolved.",
            "Manual arithmetic reconstruction, encoded pointers, runtime callback registration, incoming indirect entry, runtime copies/generated code pointers and selected-wheel data-pointer persistence remain open.",
            "No slot0/slot1, global stored-or-escaped-alias or aggregate P1.3 gate is promoted."
        ],
        "next_step": "Trace runtime/generated/encoded carrier pointer construction and callback registration/incoming dispatch, while continuing selected-wheel data-pointer persistence independently."
    }


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--static", type=Path, default=Path("evidence/p1a_p13a_slot01_static_callback_target_composition.json"))
    p.add_argument("--absolute", type=Path, default=Path("evidence/p1a_p13a_exact_carrier_whole_image_pointer_literal_closure.json"))
    p.add_argument("--text-rva", type=Path, default=Path("evidence/p1a_p13a_exact_carrier_text_rva_literal_closure.json"))
    p.add_argument("--rdata-rva", type=Path, default=Path("evidence/p1a_p13a_exact_carrier_rdata_rva_diagnostic_closure.json"))
    p.add_argument("--reloc", type=Path, default=Path("evidence/p1a_p13a_pe_base_relocation_carrier_closure.json"))
    p.add_argument("--indirect", type=Path, default=Path("evidence/p1a_p13a_exact_carrier_incoming_indirect_index_frontier.json"))
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    payload = build(load(args.static), load(args.absolute), load(args.text_rva), load(args.rdata_rva), load(args.reloc), load(args.indirect))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
