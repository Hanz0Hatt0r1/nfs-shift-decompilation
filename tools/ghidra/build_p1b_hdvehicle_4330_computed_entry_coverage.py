#!/usr/bin/env python3
"""Compose bounded computed/loader entry surfaces for P1B exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330ComputedEntryCoverage/1"
EXPECTED = {
    "canonical": "SHIFT.P1B.HDVehicle4330CanonicalEipCaptureSurface/1",
    "x87": "SHIFT.P1B.HDVehicle4330X87EipCaptureSurface/1",
    "loader": "SHIFT.P1B.HDVehicle4330PeLoaderEntrySurface/1",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(canonical_path: Path, x87_path: Path, loader_path: Path) -> dict:
    docs = {
        "canonical": load(canonical_path),
        "x87": load(x87_path),
        "loader": load(loader_path),
    }
    for name, doc in docs.items():
        if doc.get("format") != EXPECTED[name]:
            raise ValueError(f"{name} format mismatch: {doc.get('format')!r}")
        if doc.get("ready") is not True:
            raise ValueError(f"{name} evidence is not ready")
        if doc.get("adjudication", {}).get("external_provider_count") != 7:
            raise ValueError(f"{name} provider-count drift")

    canonical, x87, loader = docs["canonical"], docs["x87"], docs["loader"]
    cg, xg, lg = canonical["adjudication"], x87["adjudication"], loader["adjudication"]

    if cg["canonical_call_next_pop_eip_capture_surface_complete"] is not True:
        raise ValueError("canonical EIP capture subset reopened")
    if cg["canonical_call_next_pop_can_derive_exact_carrier"] is not False:
        raise ValueError("canonical EIP capture gained exact-carrier derivation")
    if xg["x87_fstenv_eip_capture_surface_complete"] is not True or xg["x87_saved_eip_extraction_found"] is not False:
        raise ValueError("x87 EIP capture subset drift")
    for key in (
        "pe_published_loader_entry_subset_complete",
        "exact_carrier_export_surface_complete",
        "tls_callback_surface_complete",
        "load_config_published_handler_surface_complete",
    ):
        if lg[key] is not True:
            raise ValueError(f"loader subset reopened: {key}")
    if lg["exact_carrier_is_pe_entrypoint"] is not False or lg["exact_carrier_export_found"] is not False or lg["exact_carrier_tls_callback_found"] is not False:
        raise ValueError("loader surface gained exact-carrier entry")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [EXPECTED[k] for k in ("canonical", "x87", "loader")],
        "surface": {
            "closed_computed_or_loader_entry_class_count": 3,
            "exact_carrier_entry_hit_count": 0,
            "classes": [
                {
                    "class": "canonical CALL-next/POP EIP capture",
                    "candidate_count": cg["canonical_call_next_pop_candidate_count"],
                    "derived_value": canonical["canonical_call_next_pop_surface"]["derived_value"],
                    "derived_identity": canonical["canonical_call_next_pop_surface"]["derived_value_identity"],
                    "exact_carrier_hit_count": 0,
                },
                {
                    "class": "x87 FSTENV/FNSTENV saved-EIP extraction",
                    "decoded_site_count": xg["decoded_x87_env_site_count"],
                    "real_env_save_instruction_count": xg["real_x87_env_save_instruction_count"],
                    "saved_eip_extraction_found": False,
                    "exact_carrier_hit_count": 0,
                },
                {
                    "class": "PE loader-published entry surfaces",
                    "export_function_count": loader["export_surface"]["function_count"],
                    "tls_callback_count": loader["tls_surface"]["callback_count"],
                    "load_config_present": loader["load_config_surface"]["present"],
                    "entrypoint_va": loader["entrypoint"]["va"],
                    "exact_carrier_hit_count": 0,
                },
            ],
        },
        "adjudication": {
            "bounded_computed_and_loader_entry_coverage_composed": True,
            "bounded_computed_or_loader_exact_carrier_hit_found": False,
            "canonical_call_pop_eip_capture_complete": True,
            "x87_saved_eip_capture_complete": True,
            "pe_loader_published_entry_surface_complete": True,
            "noncanonical_nonx87_eip_capture_surface_complete": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This aggregate composes only canonical CALL-next/POP EIP capture, x87 FSTENV/FNSTENV saved-EIP extraction, and PE loader-published entry surfaces.",
            "Other noncanonical non-x87 address synthesis, transformed constants, copied/encoded pointers, runtime patching and opaque indirect dispatch remain open.",
            "The sole canonical CALL-next/POP candidate derives the .secu base, not an exact carrier pointer."
        ],
        "next_step": "Bound noncanonical non-x87 code-address synthesis and runtime copied/encoded exact-carrier pointer flows before promoting computed-pointer or indirect-entry gates."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("canonical", type=Path)
    p.add_argument("x87", type=Path)
    p.add_argument("loader", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = build(a.canonical, a.x87, a.loader)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
