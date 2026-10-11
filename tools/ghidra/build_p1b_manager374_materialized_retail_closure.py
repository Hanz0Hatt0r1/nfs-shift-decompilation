#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / "evidence/p1b_manager374_materialized_retail_frontier.json"
FORMAT = "SHIFT.P1B.Manager374MaterializedRetailClosure/1"
EXPECTED_FRONTIER = "SHIFT.P1B.Manager374MaterializedRetailFrontier/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_PROBES = {
    "same_region": "SHIFT.P1B.Manager374MaterializedPlus374WriterProbe/1",
    "ebp_spill_reload": "SHIFT.P1B.Manager374MaterializedEbpSpillReloadProbe/1",
    "esp_spill_reload": "SHIFT.P1B.Manager374MaterializedESPSpillReloadProbe/1",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build() -> dict:
    data = json.loads(FRONTIER.read_text(encoding="utf-8"))
    require(data.get("format") == EXPECTED_FRONTIER, "frontier format drift")
    require(data.get("ready") is True, "frontier is not ready")
    authority = data.get("authority", {})
    require(authority.get("retail_executable_sha256") == RETAIL_SHA256, "retail SHA drift")
    require(authority.get("all_probe_outputs_same_authoritative_executable") is True,
            "probe outputs are not tied to one authoritative executable")
    require(data.get("inputs") == EXPECTED_PROBES, "probe contract set drift")

    surface = data.get("surface", {})
    per_probe = surface.get("candidate_record_count_by_probe")
    require(per_probe == {
        "same_region": 0,
        "ebp_spill_reload": 0,
        "esp_spill_reload": 0,
    }, "materialized retail candidate count changed")
    require(surface.get("probe_count") == 3, "probe count drift")
    require(surface.get("candidate_record_count") == 0, "candidate record frontier reopened")
    require(surface.get("candidate_records") == [], "candidate records frontier reopened")
    require(surface.get("unique_candidate_site_count") == 0, "unique candidate frontier reopened")
    require(surface.get("unique_candidate_sites") == [], "unique candidate sites frontier reopened")
    require(surface.get("candidate_site_sources") == [], "candidate source frontier reopened")
    require(surface.get("unadjudicated_candidate_site_count") == 0,
            "unadjudicated materialized candidate frontier reopened")
    require(surface.get("unadjudicated_candidate_sites") == [],
            "unadjudicated materialized sites frontier reopened")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "machine_execution_adjudicates": True,
        },
        "upstream_contract": EXPECTED_FRONTIER,
        "surface": {
            "probe_count": 3,
            "same_region_write_candidate_count": per_probe["same_region"],
            "ebp_spill_reload_write_candidate_count": per_probe["ebp_spill_reload"],
            "esp_spill_reload_write_candidate_count": per_probe["esp_spill_reload"],
            "candidate_record_count": 0,
            "unique_candidate_site_count": 0,
            "remaining_materialized_candidate_site_count": 0,
        },
        "adjudication": {
            "materialized_plus_374_same_region_retail_frontier_empty": True,
            "materialized_plus_374_ebp_spill_reload_retail_frontier_empty": True,
            "materialized_plus_374_esp_spill_reload_retail_frontier_empty": True,
            "materialized_plus_374_bounded_transport_surface_complete": True,
            "all_materialized_candidate_receivers_classified": True,
            "materialized_plus_374_bounded_transport_can_write_manager_374": False,
            "computed_address_manager_374_writer_surface_complete": False,
            "external_or_unknown_origin_outer_alias_surface_complete": False,
            "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete": False,
            "unrecognized_runtime_transform_root_origin_surface_complete": False,
            "memory_load_or_opaque_runtime_reconstruction_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the three merged materialized receiver+0x374 transport classes executed on authoritative retail: same-region GPR, EBP spill/reload and normalized ESP spill/reload.",
            "Indexed or arithmetic materialization, cross-control-flow carry, non-stack memory aliases, helper-returned materialized addresses and arbitrary runtime mutation remain outside this closure unless covered by separate contracts.",
            "An empty materialized frontier is not a proof over arbitrary external process memory and does not complete the final manager-root identity join.",
            "No identity is inferred from matching numeric offsets.",
        ],
        "next_step": "Compose this zero materialized frontier with already-closed computed-runtime/reconstruction classes, then reduce only surviving external-memory, unnamed opaque-helper and unrecognized-transform root origins before final manager+0x374 -> HDVehicle+0x4330 and slot2 adjudication.",
    }


def main() -> None:
    print(json.dumps(build(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
