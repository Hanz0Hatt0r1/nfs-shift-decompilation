from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_bmw_offset33b_semantic_static_proof.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_offset33b_semantic", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reduced(*, exact: bool = True) -> dict:
    return {
        "completed": True,
        "handoff": {
            "offset33b_store_provenance_ready": True,
            "offset33b_memory_LOAD_frontier_ready": True,
            "offset33b_exact_memory_field_worklist_ready": exact,
        },
    }


def _owner(*, all_ready: bool = False) -> dict:
    return {
        "ready": True,
        "analysis": {
            "direct_HDVehicle_fields": [
                {"exact_owner_field_reference": "HDVehicle+0x33a8"}
            ],
            "indirect_owner_slots": [
                {
                    "indirect_owner_origin_expression": "memory:[esi+0x20]",
                    "displacement": 48,
                    "load_width": 8,
                    "feeds_offset33b_fields": ["offset33b.x"],
                }
            ],
            "unresolved_owner_groups": [],
        },
        "handoff": {
            "offset33b_all_field_owner_semantics_ready": all_ready,
        },
    }


def _resources() -> dict:
    return {
        "ready": True,
        "handoff": {
            "offset33b_resource_inputs_ready": True,
            "offset33b_direct_CDF_load_data_mapping_ready": True,
        },
    }


def _mapping() -> dict:
    return {
        "direct_CDF_fields": [
            {
                "semantic_field": "CDF.GENERAL.Mass",
                "load_data_offsets": [0x24],
                "value": 1460.0,
            }
        ],
        "observed_but_not_directly_mapped": [],
        "derived_load_data_offsets_not_promoted": [0x338],
    }


def test_compose_exposes_exact_remaining_pointer_frontier() -> None:
    m = _module()
    report = m._compose_bundle(
        reduced=_reduced(),
        owner=_owner(),
        resource_validation=_resources(),
        resource_mapping=_mapping(),
        artifacts={},
    )
    assert report["status"] == "pointer-owner-join-frontier-ready"
    assert report["handoff"]["offset33b_resource_inputs_ready"] is True
    assert report["handoff"]["offset33b_field_owner_frontier_ready"] is True
    assert report["handoff"]["offset33b_memory_LOAD_semantic_join_ready"] is False
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["next_proof"]["direct_HDVehicle_field_references"] == [
        "HDVehicle+0x33a8"
    ]
    assert report["next_proof"]["derived_load_data_offsets_kept_unassigned"] == [0x338]


def test_incomplete_machine_worklist_blocks_owner_frontier() -> None:
    m = _module()
    report = m._compose_bundle(
        reduced=_reduced(exact=False),
        owner=None,
        resource_validation=_resources(),
        resource_mapping=_mapping(),
        artifacts={},
    )
    assert report["status"] == "blocked-before-semantic-frontier"
    assert report["handoff"]["offset33b_field_owner_frontier_ready"] is False
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False


def test_even_all_owner_domains_do_not_preclaim_numeric_offset() -> None:
    m = _module()
    report = m._compose_bundle(
        reduced=_reduced(),
        owner=_owner(all_ready=True),
        resource_validation=_resources(),
        resource_mapping=_mapping(),
        artifacts={},
    )
    assert report["status"] == "owner-and-resource-frontiers-ready"
    assert report["handoff"]["offset33b_all_field_owner_semantics_ready"] is True
    assert report["handoff"]["offset33b_semantic_field_names_ready"] is False
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
