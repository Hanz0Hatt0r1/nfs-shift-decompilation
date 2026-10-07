from __future__ import annotations

from src.physics import native_vehicle_external_provider_frontier as legacy
from src.physics import native_vehicle_external_provider_frontier_current as current


def _joins(report: dict) -> dict[str, dict]:
    return {row["id"]: row for row in report["cross_chain_joins"]}


def _providers(report: dict) -> dict[str, dict]:
    return {row["id"]: row for row in report["providers"]}


def test_current_audit_closes_one_legacy_provider_and_narrows_effect_boundary() -> None:
    old = legacy.build_frontier()
    report = current.build_current_frontier()

    assert report["format"] == current.FORMAT
    assert report["upstream_frontier"] == legacy.FORMAT
    assert report["refresh_after_phase"] == 718
    assert report["refresh_label"] == "S6 PC effect inputs + x87 magnitude frontier"
    assert report["scheduler_refresh"] == (
        "S5 positive retail outer cadence + atomic explicit dispatch + exact "
        "selected-session 180 Hz rate + exact persistent 1/180 inner execution"
    )
    assert "positive exact outer->VHF numeric relation" in report["transform_refresh"]
    assert "x87 magnitude" in report["provider_refresh"]
    assert "FUN_007595d0 response parity" in report["provider_refresh"]
    assert old["external_provider_count"] == 9
    assert report["external_provider_count"] == 8
    providers = _providers(report)
    assert "fun_007682c0_delta_consumer" not in providers
    assert report["action_counts"][legacy.REQUEST_PROCESS1] == 8
    assert report["action_counts"][legacy.IMPLEMENT_NOW] == 0
    assert report["implement_now"] == []

    effect = providers["fun_007682c0_effect_provider"]
    assert effect["evidence_state"] == "source_inputs_and_machine_magnitude_positive"
    assert any(current.FUN_007682C0_EFFECT_FRONTIER_FORMAT in row for row in effect["evidence"])
    assert any(current.FUN_007682C0_MACHINE_MAGNITUDE_FORMAT in row for row in effect["evidence"])
    assert effect["blockers"] == [
        "FUN_007595d0 exact x87/f32 response machine parity remains unproven",
        "runtime wiring for the source-proven HDVehicle scalar fields +0x4068/+0x4054/+0x4084/+0x408c and load-factor numerator fields remains external",
    ]
    assert "std::sqrt" not in effect["additional_dependency"]

    audit = report["provider_audit"]
    assert audit["provider_inventory_changed"] is True
    assert audit["legacy_external_provider_count"] == 9
    assert audit["active_external_provider_count"] == 8
    assert audit["closed_provider_ids"] == ["fun_007682c0_delta_consumer"]
    assert audit["newly_positive_provider_or_owner_handoff_internalizable"] is True


def test_current_audit_consumes_transform_destination_inputs_and_magnitude() -> None:
    report = current.build_current_frontier()
    path = report["current_bind_path"]

    assert path["BODY0_construction_target_identity_ready"] is True
    assert path["BODY0_resource_values_ready"] is True
    assert path["BODY0_local_to_SDF_model_bind_pose_ready"] is True
    assert path["BODY0_to_outer_vehicle_root_numeric_matrix_ready"] is True
    assert path["canonical_BMW_VHF_resource_identity_ready"] is True
    assert path["outer_vehicle_render_snapshot_affine_bridge_ready"] is True
    assert path["outer_vehicle_render_root_delta_value_roots_ready"] is True
    assert path["canonical_BMW_VHF_hierarchy_root_frame_ready"] is True
    assert path["process2_exact_vhf_root_frame_stage_consumed"] is True
    assert path["process2_exact_vhf_root_frame_stage_contract"] == current.ROOT_STAGE_FORMAT
    assert path["outer_vehicle_root_to_VHF_numeric_contract"] == current.OUTER_VHF_NUMERIC_FORMAT
    assert path["outer_vehicle_root_to_VHF_vehicle_root_ready"] is True
    assert path["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is True
    assert path["BODY0_bind_frame_contract"] == current.BIND_PROOF_FORMAT
    assert path["BODY0_bind_frame_proof_ready"] is True
    assert path["persistent_world_transform_wiring_contract"] == current.WORLD_TRANSFORM_WIRING_FORMAT
    assert path["vehicle_world_transform_ready"] is True
    assert path["FUN_007682c0_delta_destination_contract"] == current.FUN_007682C0_DESTINATION_FORMAT
    assert path["FUN_007682c0_delta_destination_is_BODY0"] is True
    assert path["FUN_007682c0_effect_frontier_contract"] == current.FUN_007682C0_EFFECT_FRONTIER_FORMAT
    assert path["FUN_007682c0_source_input_provenance_ready"] is True
    assert path["FUN_007682c0_machine_magnitude_contract"] == current.FUN_007682C0_MACHINE_MAGNITUDE_FORMAT
    assert path["FUN_007682c0_machine_magnitude_ready"] is True
    assert path["FUN_007595d0_machine_response_parity_ready"] is False


def test_transform_join_stays_closed_while_s6_moves_inside_provider_boundary() -> None:
    transform = _joins(current.build_current_frontier())["body_pose_to_renderer_world_transform"]

    assert transform["state"] == "retail_proven_and_consumed"
    assert transform["process2_action"] == "closed"
    assert transform["blockers"] == []
    joined = " ".join(transform["evidence"])
    assert current.OUTER_VHF_NUMERIC_FORMAT in joined
    assert current.BIND_PROOF_FORMAT in joined
    assert current.WORLD_TRANSFORM_WIRING_FORMAT in joined
    assert "freshness-gated" in joined
    assert "eight provider" in transform["additional_dependency"]
    assert "std::sqrt" in transform["policy"]


def test_fun_007682c0_delta_and_magnitude_are_positive_but_response_remains_closed() -> None:
    report = current.build_current_frontier()
    audit = report["provider_audit"]
    guards = report["guards"]

    assert audit["fun_007682c0_runtime_body0_mutation_internalized"] is True
    assert audit["fun_007682c0_exact_source_destination_receiver_proven"] is True
    assert audit["fun_007682c0_destination_contract"] == current.FUN_007682C0_DESTINATION_FORMAT
    assert audit["fun_007682c0_legacy_delta_consumer_required"] is False
    assert audit["fun_007682c0_effect_frontier_contract"] == current.FUN_007682C0_EFFECT_FRONTIER_FORMAT
    assert audit["fun_007682c0_source_input_provenance_ready"] is True
    assert audit["fun_007682c0_machine_magnitude_contract"] == current.FUN_007682C0_MACHINE_MAGNITUDE_FORMAT
    assert audit["fun_007682c0_machine_magnitude_ready"] is True
    assert audit["fun_0075ada0_machine_planar_magnitude_ready"] is True
    assert audit["fun_007595d0_source_inputs_ready"] is True
    assert audit["fun_007595d0_machine_response_parity_ready"] is False
    assert audit["fun_007682c0_effect_production_ready"] is False
    assert audit["host_std_sqrt_used_for_retail_path"] is False

    assert guards["fun_007682c0_body0_delta_destination_ready"] is True
    assert guards["fun_007682c0_body0_delta_application_internal"] is True
    assert guards["fun_007682c0_source_input_provenance_ready"] is True
    assert guards["fun_007682c0_machine_magnitude_ready"] is True
    assert guards["fun_0075ada0_machine_planar_magnitude_ready"] is True
    assert guards["fun_007595d0_source_inputs_ready"] is True
    assert guards["fun_007595d0_machine_response_parity_ready"] is False
    assert guards["fun_007682c0_effect_production_ready"] is False
    assert guards["host_std_sqrt_used_for_retail_path"] is False

    closed = [
        row for row in report["closed_boundaries"]
        if row.get("provider_id") == "fun_007682c0_delta_consumer"
    ]
    assert len(closed) == 1
    assert closed[0]["proof"] == current.FUN_007682C0_DESTINATION_FORMAT
    assert closed[0]["destination"] == "BMW chassis BODY0 +0x50"
    assert closed[0]["active_external_provider_required"] is False


def test_current_audit_keeps_exact_inner_execution_and_eight_provider_frontier() -> None:
    report = current.build_current_frontier()
    scheduler = report["scheduler_authority"]
    guards = report["guards"]

    assert scheduler["contract"] == current.SCHEDULER_FORMAT
    assert scheduler["selected_rate_contract"] == current.SELECTED_RATE_FORMAT
    assert scheduler["selected_execution_contract"] == current.SELECTED_EXECUTION_FORMAT
    assert scheduler["authority_explicit"] is True
    assert scheduler["retail_cadence_admitted"] is True
    assert scheduler["retail_outer_dispatch_transaction_ready"] is True
    assert scheduler["loaded_inner_rate_admitted"] is True
    assert scheduler["selected_session_rate_hz"] == 180
    assert scheduler["inner_substep_seconds"] == 1 / 180
    assert scheduler["selected_session_normal_outer_substeps"] == 6
    assert scheduler["inner_substep_execution_admitted"] is True
    assert scheduler["provider_semantics_promoted"] is False
    assert scheduler["render_loop_equated_to_outer_dispatch"] is False
    assert scheduler["host_development_1_60_is_retail_evidence"] is False

    assert guards["scheduler_authority_explicit"] is True
    assert guards["retail_outer_cadence_ready"] is True
    assert guards["retail_outer_dispatch_transaction_ready"] is True
    assert guards["loaded_inner_rate_admitted"] is True
    assert guards["inner_substep_execution_admitted"] is True
    assert guards["provider_semantics_promoted"] is False
    assert guards["render_loop_equated_to_outer_dispatch"] is False
    assert guards["host_1_60_is_retail_evidence"] is False
    assert guards["outer_vehicle_to_vhf_root_relation_ready"] is True
    assert guards["body0_bind_frame_proof_ready"] is True
    assert guards["retail_vehicle_world_transform_ready"] is True

    contract = current.contract()
    assert contract["external_provider_count"] == 8
    assert contract["provider_inventory_changed"] is True
    assert contract["closed_provider_ids"] == ["fun_007682c0_delta_consumer"]
    assert contract["newly_positive_provider_or_owner_handoff_internalizable"] is True
    assert contract["FUN_007682c0_delta_destination_contract"] == current.FUN_007682C0_DESTINATION_FORMAT
    assert contract["FUN_007682c0_delta_destination_is_BODY0"] is True
    assert contract["FUN_007682c0_delta_application_internal"] is True
    assert contract["FUN_007682c0_legacy_delta_consumer_required"] is False
    assert contract["FUN_007682c0_effect_frontier_contract"] == current.FUN_007682C0_EFFECT_FRONTIER_FORMAT
    assert contract["FUN_007682c0_source_input_provenance_ready"] is True
    assert contract["FUN_007682c0_machine_magnitude_contract"] == current.FUN_007682C0_MACHINE_MAGNITUDE_FORMAT
    assert contract["FUN_007682c0_machine_magnitude_ready"] is True
    assert contract["FUN_007595d0_source_inputs_ready"] is True
    assert contract["FUN_007595d0_machine_response_parity_ready"] is False
    assert contract["FUN_007682c0_effect_production_ready"] is False
    assert contract["selected_rate_contract"] == current.SELECTED_RATE_FORMAT
    assert contract["selected_execution_contract"] == current.SELECTED_EXECUTION_FORMAT
    assert contract["retail_outer_cadence_admitted"] is True
    assert contract["retail_outer_dispatch_transaction_ready"] is True
    assert contract["loaded_inner_rate_admitted"] is True
    assert contract["selected_session_rate_hz"] == 180
    assert contract["selected_session_normal_outer_substeps"] == 6
    assert contract["inner_substep_execution_admitted"] is True
    assert contract["provider_semantics_promoted"] is False
    assert contract["render_loop_equated_to_outer_dispatch"] is False
    assert contract["host_1_60_is_retail_evidence"] is False
