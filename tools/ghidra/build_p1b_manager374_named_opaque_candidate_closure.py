#!/usr/bin/env python3
"""Compose the finite named opaque Participants Manager root candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.Manager374NamedOpaqueCandidateClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

INPUTS = {
    "vslot24": ROOT / "evidence/hdvehicle_64e8_manager_374_vslot24_eax_residue_surface.json",
    "vslot0c": ROOT / "evidence/hdvehicle_64e8_manager_374_vslot0c_dispatch_closure.json",
    "root_origin": ROOT / "evidence/p1b_manager374_root_origin_coverage.json",
    "known_escape": ROOT / "evidence/p1b_manager374_known_lineage_escape_closure.json",
}
EXPECTED = {
    "vslot24": "SHIFT.HDVehicle64e8Manager374VSlot24EaxResidueSurface/1",
    "vslot0c": "SHIFT.HDVehicle64e8Manager374VSlot0cDispatchClosure/1",
    "root_origin": "SHIFT.P1B.Manager374RootOriginCoverage/1",
    "known_escape": "SHIFT.P1B.Manager374KnownLineageEscapeClosure/1",
}


def load(name: str) -> dict:
    with INPUTS[name].open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("format") != EXPECTED[name] or not data.get("ready"):
        raise ValueError(f"{name}: upstream contract drift")
    authority = data.get("authority", {})
    if authority.get("retail_executable_sha256") not in (None, RETAIL_SHA256):
        raise ValueError(f"{name}: retail hash drift")
    return data


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def build() -> dict:
    d = {name: load(name) for name in INPUTS}
    v24, v0c, origin, escape = d["vslot24"], d["vslot0c"], d["root_origin"], d["known_escape"]

    require(v24["adjudication"]["vslot_24_identity_closed"] is True, "vslot24 identity reopened")
    require(v24["adjudication"]["slot_body_can_leave_manager_root_in_eax"] is True, "vslot24 candidate shape drift")
    require(v24["adjudication"]["vslot_24_can_export_exact_manager_root_to_its_observed_consumer"] is False, "vslot24 now exports manager root")
    require(v24["exact_dispatch"]["exact_manager_root_preserved_after_dispatch"] is False, "vslot24 consumer preserves root")

    require(v0c["adjudication"]["exact_manager_first_hop_indirect_surface_complete"] is True, "vslot0c first-hop surface incomplete")
    require(v0c["adjudication"]["target_vslot_plus_0x0c_reached_by_exact_manager"] is False, "vslot0c became reachable")
    require(v0c["adjudication"]["fun_0045b130_alternate_manager_root_source_closed"] is True, "FUN_0045b130 source reopened")
    require(v0c["exhaustive_exact_manager_first_hop"]["target_slot_plus_0x0c_dispatch_count"] == 0, "vslot0c dispatch appeared")

    require(origin["adjudication"]["bounded_manager_root_origin_classes_composed"] is True, "root origin coverage incomplete")
    require(escape["adjudication"]["known_manager_root_lineage_escape_surface_complete"] is True, "known root escape closure incomplete")
    require(escape["adjudication"]["known_manager_root_lineage_can_seed_external_memory_alias"] is False, "known lineage now seeds external memory")
    require(escape["adjudication"]["external_provider_count"] == 7, "provider count changed")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": RETAIL_SHA256},
        "inputs": EXPECTED,
        "named_opaque_candidates": [
            {
                "id": "render-child-vslot24-eax-residue",
                "function": v24["slot_body"]["function"],
                "vtable": v24["object_identity"]["vtable"],
                "slot": v24["object_identity"]["slot_offset"],
                "can_materialize_exact_manager_root_in_eax": True,
                "exportable_to_observed_consumer": False,
                "reason": v24["exact_dispatch"]["post_call_clobber"],
            },
            {
                "id": "render-manager-vslot0c",
                "function": v0c["vslot"]["target"],
                "vtable": v0c["vslot"]["primary_vtable"],
                "slot": v0c["vslot"]["target_slot_offset"],
                "direct_call_count": v0c["vslot"]["direct_call_count"],
                "exact_lineage_dispatch_count": v0c["exhaustive_exact_manager_first_hop"]["target_slot_plus_0x0c_dispatch_count"],
                "exportable_to_observed_consumer": False,
            },
        ],
        "summary": {
            "named_candidate_count": 2,
            "named_candidate_exportable_count": 0,
            "vslot24_observed_dispatch_preserves_root": False,
            "vslot0c_exact_lineage_dispatch_count": 0,
        },
        "adjudication": {
            "named_opaque_manager_root_candidate_surface_complete": True,
            "named_opaque_manager_root_candidate_count": 2,
            "named_opaque_manager_root_exportable_candidate_count": 0,
            "known_named_opaque_helpers_can_create_independent_manager_root_alias": False,
            "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "surviving_frontier": [
            "previously unobserved opaque helper return that independently synthesizes exact 0x00bc9fc0",
            "externally initialized memory containing exact 0x00bc9fc0 without known-lineage seeding",
            "unrecognized runtime transform outside merged reconstruction classes",
        ],
        "limits": [
            "This contract closes the two named opaque manager-root candidates present in merged Process 1B evidence; it is not a proof that no as-yet-unidentified opaque helper exists.",
            "The vslot0c rejection is scoped to the exhaustive exact render-manager lineage; runtime-created outer aliases remain a separate global concern.",
            "No identity is inferred from matching offsets."
        ],
        "next_step": "Search specifically for any additional unnamed opaque helper/memory-load producer of exact 0x00bc9fc0; if none is present in the retail machine surface, promote the final manager-root origin closure before slot2 adjudication.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
