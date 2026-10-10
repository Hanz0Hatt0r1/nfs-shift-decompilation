#!/usr/bin/env python3
"""Compose bounded P1B HDVehicle+0x4330 indirect-entry coverage contracts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/1"
EXPECTED = {
    "callbacks": "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/3",
    "static": "SHIFT.P1B.HDVehicle4330StaticFunctionPointerMaterializationCoverage/1",
    "computed": "SHIFT.P1B.HDVehicle4330ComputedEntryCoverage/1",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(contract: dict, name: str) -> None:
    if contract.get("format") != EXPECTED[name]:
        raise ValueError(f"{name} format drift: {contract.get('format')!r}")
    if contract.get("ready") is not True:
        raise ValueError(f"{name} contract is not ready")
    adjudication = contract.get("adjudication") or {}
    if adjudication.get("external_provider_count") != 7:
        raise ValueError(f"{name} external provider count drift")
    for gate in (
        "indirect_entry_into_carriers_ruled_out",
        "manager_374_join_to_hdvehicle_4330_complete",
        "last_literal_0x004b86cf_rejected",
        "p1_3_control_producer_complete",
    ):
        if adjudication.get(gate) is not False:
            raise ValueError(f"{name} promoted global gate {gate}")


def build(callbacks: dict, static: dict, computed: dict) -> dict:
    _require(callbacks, "callbacks")
    _require(static, "static")
    _require(computed, "computed")

    cb_adj = callbacks["adjudication"]
    st_adj = static["adjudication"]
    cp_adj = computed["adjudication"]
    if cb_adj.get("bounded_runtime_callback_exact_4330_carrier_hit_found") is not False:
        raise ValueError("callback exact-carrier hit drift")
    if st_adj.get("bounded_static_pointer_materialization_exact_carrier_hit_found") is not False:
        raise ValueError("static exact-carrier hit drift")
    if cp_adj.get("bounded_computed_or_loader_exact_carrier_hit_found") is not False:
        raise ValueError("computed/loader exact-carrier hit drift")

    cb_surface = callbacks["surface"]
    st_surface = static["surface"]
    cp_surface = computed["surface"]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [EXPECTED["callbacks"], EXPECTED["static"], EXPECTED["computed"]],
        "surface": {
            "composed_coverage_class_count": 3,
            "coverage": [
                {
                    "class": "bounded runtime callback registrations",
                    "closed_surface_count": cb_surface["closed_surface_count"],
                    "bounded_callback_capable_callsite_count": cb_surface["bounded_callback_capable_callsite_count"],
                    "unique_possible_callback_entrypoint_count": cb_surface["unique_possible_callback_entrypoint_count"],
                    "exact_carrier_hit_count": cb_surface["exact_4330_carrier_entrypoint_hit_count"],
                },
                {
                    "class": "static/source-visible function-pointer materialization",
                    "closed_materialization_class_count": st_surface["closed_materialization_class_count"],
                    "exact_carrier_count": st_surface["exact_carrier_count"],
                    "exact_carrier_hit_count": st_surface["exact_carrier_materialization_hit_count"],
                },
                {
                    "class": "computed/loader entry materialization",
                    "closed_computed_or_loader_entry_class_count": cp_surface["closed_computed_or_loader_entry_class_count"],
                    "exact_carrier_hit_count": cp_surface["exact_carrier_entry_hit_count"],
                },
            ],
            "bounded_exact_carrier_hit_count": 0,
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "runtime_callback_registration_ruled_out": False,
            "remaining_callback_api_families_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This composes only three already-bounded classes: known callback registrations, static/source-visible pointer materialization, and canonical/x87/loader computed-entry coverage.",
            "It does not rule out unresolved callback APIs such as _bsearch, application-owned wrappers, runtime-generated/copied/encoded/reconstructed pointers, runtime patching, arbitrary pointer stores, noncanonical code-address synthesis, or opaque indirect dispatch.",
            "Zero exact-carrier hits in these bounded classes is not global proof that indirect entry into the 15 exact HDVehicle+0x4330 carriers is impossible.",
        ],
        "next_step": "Close the unresolved _bsearch comparator with machine evidence, then bound runtime-generated/copied/encoded exact-carrier pointer stores and noncanonical code-address synthesis before promoting any global indirect-entry gate.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("callbacks", type=Path)
    p.add_argument("static", type=Path)
    p.add_argument("computed", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = build(load(a.callbacks), load(a.static), load(a.computed))
    except ValueError as exc:
        p.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
