#!/usr/bin/env python3
"""Compose bounded exact-carrier seed provenance coverage for Process 1B."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330CarrierSeedProvenanceCoverage/1"
EXPECTED_PROVIDER_COUNT = 7
EXPECTED = {
    "static": "SHIFT.P1B.HDVehicle4330StaticFunctionPointerMaterializationCoverage/1",
    "computed": "SHIFT.P1B.HDVehicle4330ComputedEntryCoverage/1",
    "callbacks": "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/4",
    "imagebase": "SHIFT.P1A.P13AExactImagebaseRvaImmediateConstructionClosure/1",
}


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("ready") is not True:
        raise ValueError(f"upstream contract not ready: {path}")
    return data


def build(static_path: Path, computed_path: Path, callbacks_path: Path, imagebase_path: Path) -> dict:
    data = {
        "static": load(static_path),
        "computed": load(computed_path),
        "callbacks": load(callbacks_path),
        "imagebase": load(imagebase_path),
    }
    for name, expected in EXPECTED.items():
        if data[name].get("format") != expected:
            raise ValueError(f"{name} format drift: {data[name].get('format')!r}")
        if data[name].get("adjudication", {}).get("external_provider_count") != EXPECTED_PROVIDER_COUNT:
            raise ValueError(f"{name} provider-count drift")

    static = data["static"]
    computed = data["computed"]
    callbacks = data["callbacks"]
    imagebase = data["imagebase"]

    if static["surface"]["exact_carrier_count"] != 15:
        raise ValueError("P1B carrier count drift")
    if static["surface"]["exact_carrier_materialization_hit_count"] != 0:
        raise ValueError("static exact-carrier seed appeared")
    if computed["surface"]["exact_carrier_entry_hit_count"] != 0:
        raise ValueError("computed/loader exact-carrier seed appeared")
    if callbacks["surface"]["exact_4330_carrier_entrypoint_hit_count"] != 0:
        raise ValueError("runtime callback exact-carrier seed appeared")
    if imagebase["scan"]["exact_carrier_rva_scalar_use_count"] != 0:
        raise ValueError("exact carrier RVA scalar appeared")
    if imagebase["scan"]["same_function_exact_imagebase_plus_carrier_rva_candidate_count"] != 0:
        raise ValueError("exact imagebase+RVA construction candidate appeared")

    classes = [
        {
            "class": "static/source-visible exact carrier materialization",
            "subclass_count": static["surface"]["closed_materialization_class_count"],
            "exact_carrier_hit_count": static["surface"]["exact_carrier_materialization_hit_count"],
        },
        {
            "class": "canonical computed/loader entry publication",
            "subclass_count": computed["surface"]["closed_computed_or_loader_entry_class_count"],
            "exact_carrier_hit_count": computed["surface"]["exact_carrier_entry_hit_count"],
        },
        {
            "class": "bounded runtime callback registration",
            "subclass_count": callbacks["surface"]["closed_surface_count"],
            "physical_callsite_count": callbacks["surface"]["bounded_callback_capable_callsite_count"],
            "possible_entrypoint_count": callbacks["surface"]["unique_possible_callback_entrypoint_count"],
            "exact_carrier_hit_count": callbacks["surface"]["exact_4330_carrier_entrypoint_hit_count"],
        },
        {
            "class": "exact preferred-imagebase + exact carrier-RVA immediate synthesis",
            "carrier_superset_count": imagebase["scope"]["carrier_count"],
            "disassembled_instruction_count": imagebase["scan"]["disassembled_instruction_count"],
            "exact_carrier_rva_scalar_use_count": imagebase["scan"]["exact_carrier_rva_scalar_use_count"],
            "exact_carrier_hit_count": imagebase["scan"]["same_function_exact_imagebase_plus_carrier_rva_candidate_count"],
        },
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [EXPECTED[k] for k in ("static", "computed", "callbacks", "imagebase")],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "composed_seed_class_count": len(classes),
            "exact_carrier_seed_hit_count": 0,
            "classes": classes,
        },
        "adjudication": {
            "bounded_known_carrier_seed_provenance_composed": True,
            "static_source_visible_seed_classes_complete": True,
            "canonical_computed_loader_seed_classes_complete": True,
            "bounded_runtime_callback_seed_classes_complete": True,
            "exact_imagebase_plus_exact_rva_immediate_seed_subset_complete": True,
            "known_bounded_seed_exact_carrier_hit_found": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This composes only already-bounded exact-carrier seed classes.",
            "Split/table-derived RVAs, delayed module-base consumers, encoded/XORed arithmetic, runtime-generated/copied pointers, runtime patching and opaque indirect dispatch remain open.",
            "The P1A imagebase+RVA input covers a 16-carrier superset and reports zero exact carrier-RVA scalar uses, so it is a valid negative bound for the 15-carrier P1B subset.",
        ],
        "next_step": "Trace split/table-derived/encoded carrier reconstruction and delayed runtime module-base consumers, then classify any resulting exact-carrier pointer stores/copies before promoting global indirect-entry gates.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("static", type=Path)
    p.add_argument("computed", type=Path)
    p.add_argument("callbacks", type=Path)
    p.add_argument("imagebase", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = build(args.static, args.computed, args.callbacks, args.imagebase)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
