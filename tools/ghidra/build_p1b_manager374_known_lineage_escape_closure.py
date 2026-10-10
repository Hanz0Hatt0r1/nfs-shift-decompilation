#!/usr/bin/env python3
"""Compose known Participants Manager root-lineage escape coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.Manager374KnownLineageEscapeClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

INPUTS = {
    "origin": ROOT / "evidence/p1b_manager374_root_origin_coverage.json",
    "alias": ROOT / "evidence/p1b_manager374_exact_root_alias_closure.json",
    "direct": ROOT / "evidence/hdvehicle_64e8_manager_374_exact_root_direct_callee_surface.json",
    "setter": ROOT / "evidence/hdvehicle_64e8_manager_direct_setter_frontier.json",
    "participants": ROOT / "evidence/p1b_manager374_participants_lifecycle_closure.json",
}
EXPECTED = {
    "origin": "SHIFT.P1B.Manager374RootOriginCoverage/1",
    "alias": "SHIFT.P1B.Manager374ExactRootAliasClosure/1",
    "direct": "SHIFT.HDVehicle64e8Manager374ExactRootDirectCalleeSurface/1",
    "setter": "SHIFT.HDVehicle64e8ManagerDirectSetterFrontier/1",
    "participants": "SHIFT.P1B.Manager374ParticipantsLifecycleClosure/1",
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
    origin, alias, direct, setter, participants = (d[k] for k in ("origin", "alias", "direct", "setter", "participants"))

    require(origin["adjudication"]["bounded_manager_root_origin_classes_composed"] is True, "origin classes incomplete")
    require(alias["adjudication"]["exact_getter_root_alias_surface_complete"] is True, "getter alias surface incomplete")
    require(alias["adjudication"]["escaped_storage_paths_complete"] is True, "storage escape surface incomplete")
    require(alias["adjudication"]["stack_argument_alias_paths_complete"] is True, "stack argument surface incomplete")
    require(alias["surface"]["exact_root_object_or_global_store_count"] == 0, "exact root memory store appeared")
    require(alias["surface"]["immediate_push_eax_after_getter_count"] == 0, "exact root immediate push appeared")

    require(direct["adjudication"]["exact_root_direct_callee_surface_complete"] is True, "direct callee surface incomplete")
    require(direct["adjudication"]["direct_callee_count"] == 9, "direct callee count drift")
    require(all(0x00400000 <= int(row["target_address"], 16) < 0x00E00000 for row in direct["direct_callees"]), "non-retail direct target appeared")
    require(direct["adjudication"]["direct_exact_root_surface_places_hdvehicle_plus_0x4330_into_manager_374"] is False, "direct root surface now places HDVehicle+0x4330")

    require(setter["adjudication"]["direct_manager_receiver_method_setter_surface_exhausted"] is True, "direct setter surface incomplete")
    require(setter["adjudication"]["manager_vtable_direct_setter_surface_exhausted"] is True, "vtable setter surface incomplete")
    require(setter["adjudication"]["direct_manager_receiver_method_setter_found"] is False, "direct setter appeared")
    require(setter["adjudication"]["manager_vtable_direct_setter_found"] is False, "vtable setter appeared")

    padj = participants["adjudication"]
    require(padj["participants_lifecycle_helper_or_indirect_setter_surface_complete"] is True, "Participants indirect surface incomplete")
    require(padj["participants_lifecycle_nonzero_manager_374_writer_found"] is False, "Participants nonzero writer appeared")
    require(padj["external_provider_count"] == 7, "provider count changed")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": RETAIL_SHA256},
        "inputs": EXPECTED,
        "known_root_lineage": {
            "exact_getter_callsite_count": alias["surface"]["whole_image_direct_getter_callsite_count"],
            "exact_root_object_or_global_store_count": alias["surface"]["exact_root_object_or_global_store_count"],
            "exact_root_stack_save_count": alias["surface"]["exact_root_stack_save_count"],
            "exact_root_immediate_push_count": alias["surface"]["immediate_push_eax_after_getter_count"],
            "direct_exact_root_callee_count": direct["adjudication"]["direct_callee_count"],
            "direct_exact_root_callees_all_inside_retail_image": True,
        },
        "setter_surfaces": {
            "direct_manager_receiver_call_count": setter["direct_manager_receiver_calls"]["total_calls"],
            "direct_manager_receiver_unique_target_count": setter["direct_manager_receiver_calls"]["unique_targets"],
            "manager_vtable_slot_count": setter["manager_virtual_surface"]["slot_count"],
            "manager_vtable_unique_target_count": setter["manager_virtual_surface"]["unique_target_count"],
            "direct_or_vtable_manager_374_setter_found": False,
            "participants_lifecycle_indirect_call_count": participants["vtable_0x0c_indirect"]["indirect_call_count"],
            "participants_lifecycle_surface_reaches_manager_374": participants["vtable_0x0c_indirect"]["surface_reaches_manager_374"],
        },
        "adjudication": {
            "known_manager_root_lineage_escape_surface_complete": True,
            "known_manager_root_lineage_persists_into_object_or_global_memory": False,
            "known_manager_root_lineage_escapes_as_stack_argument": False,
            "known_manager_root_lineage_reaches_external_direct_callee": False,
            "known_manager_root_lineage_can_seed_external_memory_alias": False,
            "known_manager_root_lineage_helper_or_indirect_setter_surface_complete": True,
            "independent_opaque_or_external_runtime_root_synthesis_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "surviving_frontier": [
            "independent opaque helper return that synthesizes exact 0x00bc9fc0 from unrelated inputs",
            "externally initialized memory containing exact 0x00bc9fc0 without prior known-lineage escape",
            "unrecognized runtime transform outside merged reconstruction classes",
        ],
        "limits": [
            "This closes escape and reseeding from the known canonical Participants Manager root lineage, not arbitrary process memory.",
            "It does not prove that an unrelated opaque computation cannot independently synthesize the same absolute address.",
            "No identity is inferred from matching offsets."
        ],
        "next_step": "Reduce independent opaque/external exact-root synthesis to concrete machine candidates; only then perform final manager+0x374 identity and 0x004b86cf slot2 adjudication.",
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
