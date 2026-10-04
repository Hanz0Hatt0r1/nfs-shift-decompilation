from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_field_owner_frontier.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_field_owner_frontier", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _group(
    origins: list[str],
    displacement: int,
    *,
    width: int = 4,
    fields: tuple[str, ...] = ("offset33b.x",),
    index: int = 0,
) -> dict:
    return {
        "base_origin_expression_set": origins,
        "displacement": displacement,
        "displacement_hex": (
            f"0x{displacement:x}" if displacement >= 0 else f"-0x{-displacement:x}"
        ),
        "load_width": width,
        "load_node_ids": [f"0x0076b2{80 + index * 4:02x}:0"],
        "load_instructions": [f"0x0076b2{80 + index * 4:02x}"],
        "feeds_offset33b_fields": list(fields),
        "semantic_owner_or_resource": None,
        "semantic_field_name": None,
        "semantic_join_ready": False,
    }


def _report(
    tmp_path: Path,
    groups: list[dict],
    *,
    exact_ready: bool = True,
    numeric_preclaim: bool = False,
    machine_mass_join: bool = False,
) -> Path:
    report = {
        "format": MODULE.INPUT_FORMAT,
        "version": 1,
        "ready": True,
        "producer": {
            "function": MODULE.PRODUCER,
            "mnemonic_sha256": MODULE.PRODUCER_MNEMONIC_SHA256,
        },
        "known_semantic_reductions": {
            "additional_mass_first_bootstrap": {
                "semantic_name": "additional participant mass term",
                "value": 0.0,
                "numeric_value_proven": True,
                "term_elidable_for_first_bootstrap": True,
            }
        },
        "analysis": {"exact_object_field_worklist": groups},
        "handoff": {
            "offset33b_store_provenance_ready": True,
            "offset33b_memory_LOAD_frontier_ready": True,
            "offset33b_exact_memory_field_worklist_ready": exact_ready,
            "offset33b_additional_mass_machine_LOAD_join_ready": machine_mass_join,
            "BMW_numeric_offset33b_ready": numeric_preclaim,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }
    path = tmp_path / "memory_loads.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_entry_ecx_is_promoted_only_to_exact_HDVehicle_field_owner(tmp_path):
    report = MODULE.analyze_bmw_offset33b_field_owner_frontier(
        _report(tmp_path, [_group(["entry:ECX"], 0x120)])
    )

    assert report["format"] == MODULE.FORMAT
    assert report["status"] == "all-owner-semantics-ready"
    assert report["ready"] is True
    assert report["producer_semantics"]["entry_ECX_is_HDVehicle_this"] is True
    assert report["analysis"]["direct_HDVehicle_field_count"] == 1
    assert report["analysis"]["indirect_owner_slot_count"] == 0
    assert report["analysis"]["unresolved_owner_group_count"] == 0

    row = report["analysis"]["direct_HDVehicle_fields"][0]
    assert row["owner_class"] == "direct-HDVehicle-this"
    assert row["semantic_owner_domain"] == "HDVehicle"
    assert row["owner_join_ready"] is True
    assert row["exact_owner_field_reference"] == "HDVehicle+0x120"
    assert row["semantic_field_name"] is None
    assert row["semantic_field_value_ready"] is False
    assert row["numeric_loaded_value_proven"] is False
    assert report["handoff"]["offset33b_direct_HDVehicle_field_owner_joins_ready"] is True
    assert report["handoff"]["offset33b_all_field_owner_semantics_ready"] is True
    assert report["handoff"]["offset33b_semantic_field_names_ready"] is False
    assert report["handoff"]["BMW_numeric_offset33b_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False


def test_memory_derived_base_remains_typed_less_indirect_owner_slot(tmp_path):
    report = MODULE.analyze_bmw_offset33b_field_owner_frontier(
        _report(tmp_path, [_group(["memory:[esi+0x20]"], 0x30)])
    )

    assert report["status"] == "owner-domain-frontier-ready"
    row = report["analysis"]["indirect_owner_slots"][0]
    assert row["owner_class"] == "indirect-owner-slot"
    assert row["semantic_owner_domain"] is None
    assert row["owner_join_ready"] is False
    assert row["exact_owner_field_reference"] is None
    assert row["indirect_owner_origin_expression"] == "memory:[esi+0x20]"
    assert row["candidate_owner_types"] == []
    assert row["VDF_SDF_tire_identity_assumed"] is False
    assert report["handoff"]["offset33b_all_LOAD_owner_domains_classified"] is True
    assert report["handoff"]["offset33b_all_field_owner_semantics_ready"] is False
    assert any(
        blocker["id"] == "offset33b-indirect-owner-slot-semantics-unproven"
        for blocker in report["blockers"]
    )


def test_other_entry_register_is_not_promoted_to_argument_semantics(tmp_path):
    report = MODULE.analyze_bmw_offset33b_field_owner_frontier(
        _report(tmp_path, [_group(["entry:EAX"], 0x44)])
    )

    row = report["analysis"]["unresolved_owner_groups"][0]
    assert row["owner_class"] == "other-entry-register"
    assert row["semantic_owner_domain"] is None
    assert row["owner_join_ready"] is False
    assert report["handoff"]["offset33b_all_LOAD_owner_domains_classified"] is False
    assert report["scope"]["other_entry_register_promoted_to_argument_semantics"] is False


def test_multiple_origins_remain_unresolved(tmp_path):
    report = MODULE.analyze_bmw_offset33b_field_owner_frontier(
        _report(
            tmp_path,
            [_group(["entry:ECX", "memory:[esi+0x20]"], 0x48)],
        )
    )

    row = report["analysis"]["unresolved_owner_groups"][0]
    assert row["owner_class"] == "multi-origin-unresolved"
    assert row["owner_join_ready"] is False
    assert report["analysis"]["direct_HDVehicle_field_count"] == 0
    assert any(
        blocker["id"] == "offset33b-field-owner-origin-unresolved"
        for blocker in report["blockers"]
    )


def test_mixed_direct_and_indirect_groups_preserve_only_safe_promotion(tmp_path):
    report = MODULE.analyze_bmw_offset33b_field_owner_frontier(
        _report(
            tmp_path,
            [
                _group(["entry:ECX"], 0x120, index=0),
                _group(
                    ["memory:[esi+0x20]"],
                    0x30,
                    fields=("offset33b.y", "offset33b.z"),
                    index=1,
                ),
            ],
        )
    )

    assert report["analysis"]["direct_HDVehicle_field_count"] == 1
    assert report["analysis"]["indirect_owner_slot_count"] == 1
    assert report["analysis"]["unresolved_owner_group_count"] == 0
    assert report["handoff"]["offset33b_direct_HDVehicle_field_owner_joins_ready"] is True
    assert report["handoff"]["offset33b_all_LOAD_owner_domains_classified"] is True
    assert report["handoff"]["offset33b_all_field_owner_semantics_ready"] is False
    assert report["next_proof"]["direct_HDVehicle_fields_ready_for_field_semantic_lookup"] == [
        "HDVehicle+0x120"
    ]
    assert report["next_proof"]["indirect_owner_slots_requiring_pointer_join"] == [
        {
            "origin_expression": "memory:[esi+0x20]",
            "displacement": 0x30,
            "load_width": 4,
            "feeds_offset33b_fields": ["offset33b.y", "offset33b.z"],
        }
    ]


def test_additional_mass_zero_requires_upstream_machine_pointer_join(tmp_path):
    no_join = MODULE.analyze_bmw_offset33b_field_owner_frontier(
        _report(tmp_path, [_group(["entry:ECX"], 0x860)], machine_mass_join=False)
    )
    reduction = no_join["known_semantic_reductions"]
    assert reduction["additional_mass_first_bootstrap_zero_ready"] is True
    assert reduction["additional_mass_machine_LOAD_join_ready"] is False
    assert reduction["additional_mass_zero_available_for_numeric_evaluator"] is False
    assert reduction["additional_mass_zero_applied_by_this_stage"] is False

    joined = MODULE.analyze_bmw_offset33b_field_owner_frontier(
        _report(tmp_path, [_group(["entry:ECX"], 0x860)], machine_mass_join=True)
    )
    reduction2 = joined["known_semantic_reductions"]
    assert reduction2["additional_mass_machine_LOAD_join_ready"] is True
    assert reduction2["additional_mass_zero_available_for_numeric_evaluator"] is True
    assert reduction2["additional_mass_zero_applied_by_this_stage"] is False
    assert joined["scope"]["additional_mass_zero_reapplied_by_this_stage"] is False


def test_exact_memory_field_worklist_gate_is_required(tmp_path):
    with pytest.raises(ValueError, match="exact memory-field worklist is not ready"):
        MODULE.analyze_bmw_offset33b_field_owner_frontier(
            _report(
                tmp_path,
                [_group(["entry:ECX"], 0x120)],
                exact_ready=False,
            )
        )


def test_empty_exact_worklist_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="must not be empty"):
        MODULE.analyze_bmw_offset33b_field_owner_frontier(
            _report(tmp_path, [])
        )


def test_upstream_numeric_preclaim_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unexpectedly preclaims numeric offset33b"):
        MODULE.analyze_bmw_offset33b_field_owner_frontier(
            _report(
                tmp_path,
                [_group(["entry:ECX"], 0x120)],
                numeric_preclaim=True,
            )
        )


def test_existing_semantic_owner_preclaim_in_worklist_is_rejected(tmp_path):
    group = _group(["entry:ECX"], 0x120)
    group["semantic_owner_or_resource"] = "guessed-VDF"
    with pytest.raises(ValueError, match="unexpectedly preclaims semantic owner"):
        MODULE.analyze_bmw_offset33b_field_owner_frontier(
            _report(tmp_path, [group])
        )
