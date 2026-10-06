from __future__ import annotations

from src.physics import native_vehicle_external_provider_frontier as legacy
from src.physics import native_vehicle_external_provider_frontier_current as current


def _joins(report: dict) -> dict[str, dict]:
    return {row["id"]: row for row in report["cross_chain_joins"]}


def _providers(report: dict) -> dict[str, dict]:
    return {row["id"]: row for row in report["providers"]}


def test_current_audit_preserves_provider_inventory_and_admission() -> None:
    old = legacy.build_frontier()
    report = current.build_current_frontier()

    assert report["format"] == current.FORMAT
    assert report["upstream_frontier"] == legacy.FORMAT
    assert report["refresh_after_phase"] == 716
    assert report["refresh_label"] == "Process 2 Phase 717 current-chain proof audit"
    assert report["scheduler_refresh"] == (
        "S5 positive retail outer cadence + atomic explicit dispatch + exact "
        "selected-session 180 Hz rate; persistent inner execution remains blocked"
    )
    assert "positive exact outer->VHF numeric relation" in report["transform_refresh"]
    assert report["external_provider_count"] == old["external_provider_count"] == 9
    assert [row["id"] for row in report["providers"]] == [
        row["id"] for row in old["providers"]
    ]
    assert report["providers"] == old["providers"]
    assert report["action_counts"] == old["action_counts"]
    assert report["implement_now"] == []
    assert report["provider_audit"]["provider_inventory_changed"] is False
    assert report["provider_audit"]["newly_positive_provider_or_owner_handoff_internalizable"] is False


def test_current_audit_consumes_positive_transform_chain() -> None:
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


def test_transform_join_is_closed_by_positive_bind_and_runtime_wiring() -> None:
    transform = _joins(current.build_current_frontier())["body_pose_to_renderer_world_transform"]

    assert transform["state"] == "retail_proven_and_consumed"
    assert transform["process2_action"] == "closed"
    assert transform["blockers"] == []
    joined = " ".join(transform["evidence"])
    assert current.OUTER_VHF_NUMERIC_FORMAT in joined
    assert current.BIND_PROOF_FORMAT in joined
    assert current.WORLD_TRANSFORM_WIRING_FORMAT in joined
    assert "freshness-gated" in joined
    assert "none for BODY0 -> vehicle world-transform transport" in transform[
        "additional_dependency"
    ]
    assert "selected-session 180 Hz handoff" in transform[
        "additional_dependency"
    ]
    assert "do not reopen already-proven transform" in transform["policy"]


def test_provider_audit_does_not_confuse_runtime_body0_choice_with_source_truth() -> None:
    report = current.build_current_frontier()
    audit = report["provider_audit"]
    delta = _providers(report)["fun_007682c0_delta_consumer"]

    assert audit["fun_007682c0_runtime_body0_mutation_internalized"] is True
    assert audit["fun_007682c0_exact_source_destination_receiver_proven"] is False
    assert audit["semantic_source_receiver_must_not_be_inferred_from_runtime_body0_choice"] is True
    assert delta["process2_action"] == legacy.REQUEST_PROCESS1
    assert delta["blockers"]
    assert "exact BODY pointer/record" in delta["blockers"][0]


def test_current_audit_admits_transform_outer_scheduler_and_exact_rate_but_keeps_execution_closed() -> None:
    report = current.build_current_frontier()
    scheduler = report["scheduler_authority"]
    guards = report["guards"]

    assert scheduler["contract"] == current.SCHEDULER_FORMAT
    assert scheduler["selected_rate_contract"] == current.SELECTED_RATE_FORMAT
    assert scheduler["authority_explicit"] is True
    assert scheduler["retail_cadence_admitted"] is True
    assert scheduler["retail_outer_dispatch_transaction_ready"] is True
    assert scheduler["loaded_inner_rate_admitted"] is True
    assert scheduler["selected_session_rate_hz"] == 180
    assert scheduler["inner_substep_seconds"] == 1 / 180
    assert scheduler["inner_substep_execution_admitted"] is False
    assert scheduler["render_loop_equated_to_outer_dispatch"] is False
    assert scheduler["host_development_1_60_is_retail_evidence"] is False

    assert guards["scheduler_authority_explicit"] is True
    assert guards["retail_outer_cadence_ready"] is True
    assert guards["retail_outer_dispatch_transaction_ready"] is True
    assert guards["loaded_inner_rate_admitted"] is True
    assert guards["inner_substep_execution_admitted"] is False
    assert guards["render_loop_equated_to_outer_dispatch"] is False
    assert guards["host_1_60_is_retail_evidence"] is False
    assert guards["outer_vehicle_to_vhf_root_relation_ready"] is True
    assert guards["body0_bind_frame_proof_ready"] is True
    assert guards["retail_vehicle_world_transform_ready"] is True

    contract = current.contract()
    assert contract["newly_positive_provider_or_owner_handoff_internalizable"] is False
    assert contract["outer_vehicle_to_vhf_root_relation_ready"] is True
    assert contract["BODY0_bind_frame_proof_ready"] is True
    assert contract["retail_vehicle_world_transform_ready"] is True
    assert contract["outer_vehicle_to_vhf_root_contract"] == current.OUTER_VHF_NUMERIC_FORMAT
    assert contract["BODY0_bind_frame_contract"] == current.BIND_PROOF_FORMAT
    assert contract["persistent_world_transform_wiring_contract"] == current.WORLD_TRANSFORM_WIRING_FORMAT
    assert contract["scheduler_authority_contract"] == current.SCHEDULER_FORMAT
    assert contract["selected_rate_contract"] == current.SELECTED_RATE_FORMAT
    assert contract["retail_outer_cadence_admitted"] is True
    assert contract["retail_outer_dispatch_transaction_ready"] is True
    assert contract["loaded_inner_rate_admitted"] is True
    assert contract["selected_session_rate_hz"] == 180
    assert contract["inner_substep_execution_admitted"] is False
    assert contract["render_loop_equated_to_outer_dispatch"] is False
    assert contract["host_1_60_is_retail_evidence"] is False
