#!/usr/bin/env python3
"""Compose the complete PC-retail literal manager+0x374 writer surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.Manager374LiteralWriterClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INPUTS = {
    "inventory": ROOT / "evidence/hdvehicle_64e8_manager_374_literal_store_inventory.json",
    "vptr": ROOT / "evidence/hdvehicle_64e8_manager_374_vptr_receiver_rejections.json",
    "precluster": ROOT / "evidence/hdvehicle_64e8_manager_374_final_precluster_rejections.json",
    "fmod": ROOT / "evidence/hdvehicle_64e8_manager_374_fmod_codec_cluster_rejection.json",
}
EXPECTED = {
    "inventory": "SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1",
    "vptr": "SHIFT.HDVehicle64e8Manager374VptrReceiverRejections/1",
    "precluster": "SHIFT.HDVehicle64e8Manager374FinalPreclusterRejections/2",
    "fmod": "SHIFT.HDVehicle64e8Manager374FmodCodecClusterRejection/1",
}


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("ready"):
        raise ValueError(f"upstream contract not ready: {path}")
    return data


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def vptr_rejection_sites(vptr: dict) -> set[str]:
    """Flatten the structured vptr/owner rejection contract into exact sites."""
    require(vptr["adjudication"]["rejected_site_count"] == 15, "vptr rejected-site count drift")
    require(vptr["adjudication"]["rejections_use_exact_receiver_owner_vptr_or_address_identity"] is True,
            "vptr rejection authority drift")
    require(vptr["adjudication"]["numeric_plus_0x374_equality_used_as_identity"] is False,
            "numeric offset equality became identity")

    sites: set[str] = set()

    for row in vptr["same_body_vptr_rejections"]:
        require(row["equals_manager_root_vptr"] is False, f"same-body vptr site reopened: {row['site']}")
        sites.add(row["site"])

    dispatch = vptr["unique_vtable_dispatch_rejection"]
    require(dispatch["owning_vtable_equals_manager_root_vptr"] is False, "vtable dispatch owner reopened")
    sites.update(dispatch["target_sites"])

    for row in vptr["owner_child_vptr_rejections"]:
        require(row["equals_manager_root_vptr"] is False, f"owner-child vptr site reopened: {row['site']}")
        sites.add(row["site"])

    embedded = vptr["embedded_owner_address_rejections"]
    for row in embedded["embedded_targets"]:
        require(row["equals_manager_singleton_root"] is False, f"embedded owner site reopened: {row['site']}")
        sites.add(row["site"])

    copied = vptr["embedded_copy_receiver_rejection"]
    require(copied["equals_manager_singleton_root"] is False, "embedded copy receiver reopened")
    sites.add(copied["site"])

    fresh = vptr["fresh_allocation_receiver_rejection"]
    require(fresh["all_receivers_are_fresh_allocation_results"] is True, "fresh allocation provenance drift")
    require(fresh["equals_fixed_manager_singleton_root"] is False, "fresh allocation receiver reopened")
    sites.add(fresh["site"])

    require(len(sites) == 15, f"flattened vptr rejection set drift: {len(sites)}")
    return sites


def build() -> dict:
    data = {name: load(path) for name, path in INPUTS.items()}
    for name, expected in EXPECTED.items():
        require(data[name].get("format") == expected, f"{name}: format drift")
        require(data[name]["authority"]["retail_executable_sha256"] == RETAIL_SHA256, f"{name}: retail hash drift")

    inventory = data["inventory"]
    vptr = data["vptr"]
    precluster = data["precluster"]
    fmod = data["fmod"]

    all_sites = {row["site"] for row in inventory["inventory"]["sites"]}
    require(len(all_sites) == 25, "literal inventory must contain exactly 25 unique sites")
    require(inventory["inventory"]["literal_write_site_count"] == 25, "literal site count drift")

    manager_sites = {row["site"] for row in inventory["proven_manager_domain_sites"]}
    inherited = {row["site"] for row in inventory["inherited_closed_negative_sites"]}
    vptr_sites = vptr_rejection_sites(vptr)
    precluster_sites = {row["site"] for row in precluster["rejections"]}
    fmod_sites = set(fmod["target"]["sites"])

    partitions = [manager_sites, inherited, vptr_sites, precluster_sites, fmod_sites]
    labels = ["manager", "inherited", "vptr", "precluster", "fmod"]
    for index, left in enumerate(partitions):
        for right_index in range(index + 1, len(partitions)):
            overlap = left & partitions[right_index]
            require(not overlap, f"partition overlap {labels[index]}/{labels[right_index]}: {sorted(overlap)}")

    closed = set().union(*partitions)
    require(closed == all_sites, f"literal closure mismatch: missing={sorted(all_sites-closed)} extra={sorted(closed-all_sites)}")
    require(len(manager_sites) == 2, "manager-domain site count drift")
    require(len(inherited) == 3, "inherited negative site count drift")
    require(len(vptr_sites) == 15, "vptr rejection count drift")
    require(len(precluster_sites) == 2, "corrected precluster count drift")
    require(len(fmod_sites) == 3, "FMOD rejection count drift")

    for row in inventory["proven_manager_domain_sites"]:
        negative = row.get("can_place_hdvehicle_plus_0x4330") is False or row.get("can_place_fixed_hdvehicle_plus_0x4330") is False
        require(negative, f"manager-domain site not closed: {row['site']}")
    for row in inventory["inherited_closed_negative_sites"]:
        require(row.get("status") == "closed-negative", f"inherited site reopened: {row['site']}")
    for row in precluster["rejections"]:
        require(row.get("can_place_hdvehicle_plus_0x4330_into_manager_plus_0x374") is False, f"precluster site reopened: {row['site']}")
    require(fmod["identity_adjudication"]["listed_sites_can_write_manager_plus_0x374"] is False, "FMOD cluster reopened")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": RETAIL_SHA256},
        "inputs": EXPECTED,
        "surface": {
            "literal_write_site_count": 25,
            "unique_literal_write_site_count": len(all_sites),
            "partition_counts": {
                "proven_manager_domain": len(manager_sites),
                "inherited_closed_negative": len(inherited),
                "vptr_receiver_rejections": len(vptr_sites),
                "corrected_precluster_rejections": len(precluster_sites),
                "fmod_codec_rejections": len(fmod_sites),
            },
            "closed_site_count": len(closed),
            "remaining_literal_site_count": 0,
            "remaining_literal_sites": [],
        },
        "adjudication": {
            "literal_plus_0x374_writer_surface_complete": True,
            "literal_manager_374_receiver_provenance_complete": True,
            "literal_plus_0x374_site_can_place_fixed_hdvehicle_4330": False,
            "computed_address_manager_374_writer_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only machine instructions whose memory destination itself carries literal +0x374.",
            "Computed/materialized +0x374 addresses, helper-mediated setters, runtime aliases and arbitrary process-memory mutation remain separate fail-closed surfaces.",
            "The final 0x004b86cf/slot2 adjudication is not promoted by literal writer closure alone."
        ],
        "next_step": "Run the already-merged materialized/computed +0x374 probes on authoritative PC retail 1.02 SHIFT.exe and classify only their positive candidates before revisiting the final manager identity join."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = build()
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
