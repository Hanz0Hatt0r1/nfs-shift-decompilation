from __future__ import annotations

from src.physics import native_vehicle_external_provider_frontier as legacy
from src.physics import native_vehicle_external_provider_frontier_current as current


def _providers(report: dict) -> dict[str, dict]:
    return {row["id"]: row for row in report["providers"]}


def test_current_frontier_keeps_legacy_history_but_has_seven_active_boundaries() -> None:
    old = legacy.build_frontier()
    report = current.build_current_frontier()
    assert old["external_provider_count"] == 9
    assert report["format"] == current.FORMAT
    assert report["upstream_frontier"] == legacy.FORMAT
    assert report["refresh_after_phase"] == 742
    assert report["external_provider_count"] == 7
    assert report["provider_audit"]["legacy_external_provider_count"] == 9
    assert report["provider_audit"]["active_external_provider_count"] == 7
    assert report["provider_audit"]["closed_provider_ids"] == [
        "fun_007682c0_delta_consumer",
        "fun_007682c0_effect_provider",
    ]
    assert report["provider_audit"]["narrowed_provider_ids"] == {
        "fun_00765c40_complete_anchor": (
            "selected BMW query world position/cache/fallback and typed collision output are now "
            "source-owned or exposed; collision-provider execution and residual pass side effects remain external"
        )
    }


def test_fun_00765c40_remains_external_but_selected_query_io_is_narrowed() -> None:
    report = current.build_current_frontier()
    provider = _providers(report)["fun_00765c40_complete_anchor"]
    assert provider["process2_action"] == legacy.REQUEST_PROCESS1
    assert provider["boundary_kind"] == (
        "typed_external_pass_result_with_selected_collision_output_complete_anchor_external"
    )
    assert "NativeVehicleFun00765c40Provider" in provider["current_api"]
    assert "Fun00765c40ExternalPassInput/2" in provider["current_api"]
    assert "Fun00765c40ExternalPassResult" in provider["current_api"]
    assert "Fun00765c40LoadTerms" in provider["current_api"]
    assert "Fun00765c40QueryInputBoundary" in provider["current_api"]
    assert "CollisionQueryOutput" in provider["current_api"]
    assert "NativeVehicleContactFactorProvider" not in provider["current_api"]
    joined = " ".join(provider["evidence"])
    assert current.FUN_00765C40_LOAD_TERMS_FORMAT in joined
    assert current.FUN_00765C40_EXTERNAL_PASS_RESULT_HISTORY_FORMAT in joined
    assert current.FUN_00765C40_EXTERNAL_PASS_RESULT_FORMAT in joined
    assert current.FUN_00765C40_QUERY_INPUT_FORMAT in joined
    assert current.FUN_00765C40_SELECTED_WORLD_POSITION_FORMAT in joined
    assert current.FUN_00765C40_QUERY_CACHE_LIFETIME_FORMAT in joined
    assert current.FUN_00765C40_SELECTED_FALLBACK_FORMAT in joined
    assert current.FUN_00765C40_COLLISION_OUTPUT_HANDOFF_FORMAT in joined
    assert current.FUN_00766510_QUERY_SCALAR_HANDOFF_FORMAT in joined
    assert "Phase 742" not in joined or "CollisionQueryOutput" in joined
    assert provider["blockers"]

    audit = report["provider_audit"]
    guards = report["guards"]
    assert audit["fun_00765c40_session_contact_factor_alias_removed"] is True
    assert audit["fun_00765c40_query_input_capture_ready"] is True
    assert audit["fun_00765c40_query_record_materialization_native"] is True
    assert audit["fun_00765c40_query_input_capture_count_per_explicit_step"] == 2
    assert audit["fun_00765c40_complete_anchor_external"] is True
    assert audit["fun_00765c40_world_position_producer_internalized"] is True
    assert audit["fun_00765c40_world_position_coordinate_provenance_inferred"] is False
    assert audit["fun_00765c40_renderer_transform_reused_as_query_transform"] is False
    assert audit["fun_00765c40_query_cache_state_internalized"] is True
    assert audit["fun_00765c40_selected_fallback_internalized"] is True
    assert audit["fun_00765c40_selected_collision_output_required"] is True
    assert audit["fun_00765c40_collision_output_typed"] is True
    assert audit["fun_00765c40_collision_provider_internalized"] is False
    assert audit["fun_00766510_query_scalar_handoff_native"] is True
    assert audit["fun_00766510_query_scalar_handoff_session_wired"] is False
    assert guards["fun_00765c40_external_pass_result_ready"] is True
    assert guards["fun_00765c40_query_input_ready"] is True
    assert guards["fun_00765c40_query_input_capture_ready"] is True
    assert guards["fun_00765c40_query_record_materialization_native"] is True
    assert guards["fun_00765c40_world_position_producer_ready"] is True
    assert guards["fun_00765c40_query_cache_state_ready"] is True
    assert guards["fun_00765c40_selected_fallback_ready"] is True
    assert guards["fun_00765c40_selected_collision_output_ready"] is True
    assert guards["fun_00765c40_collision_provider_ready"] is False
    assert guards["fun_00765c40_renderer_transform_is_query_producer"] is False
    assert guards["fun_00766510_query_scalar_handoff_ready"] is True
    assert guards["fun_00766510_query_scalar_handoff_session_wired"] is False


def test_fun_007682c0_external_provider_is_fully_closed_for_selected_session() -> None:
    report = current.build_current_frontier()
    providers = _providers(report)
    assert "fun_007682c0_effect_provider" not in providers
    assert "fun_007682c0_delta_consumer" not in providers
    assert "fun_007682c0_machine_input_provider" not in providers

    audit = report["provider_audit"]
    guards = report["guards"]
    assert audit["fun_007682c0_runtime_body0_mutation_internalized"] is True
    assert audit["fun_007682c0_effect_arithmetic_internalized"] is True
    assert audit["fun_007682c0_x87_fsqrt_internalized"] is True
    assert audit["fun_007682c0_projection_fields_internalized"] is True
    assert audit["fun_007594e0_body0_basis_angle_internalized"] is True
    assert audit["fun_007682c0_response_4054_internalized"] is True
    assert audit["fun_00765c40_load_term_ownership_proven"] is True
    assert audit["fun_007560c0_gate_setup_ownership_proven"] is True
    assert audit["dat_00c128cc_retail_mapping_proven"] is True
    assert audit["dat_00c128cc_selected_session_value_native"] is True
    assert audit["selected_player_difficulty"] == 1
    assert audit["retail_player_difficulty_default_used_as_proof"] is False
    assert audit["fun_007682c0_external_precomputed_effect_required"] is False
    assert audit["fun_007682c0_external_delta_consumer_required"] is False
    assert audit["fun_007682c0_external_projection_fields_required"] is False
    assert audit["fun_007682c0_external_steering_required"] is False
    assert audit["fun_007682c0_external_response_4054_required"] is False
    assert audit["fun_007682c0_external_load_terms_required"] is False
    assert audit["fun_007682c0_external_gate_required_per_pass"] is False
    assert audit["fun_007682c0_raw_input_refresh_external"] is False
    assert audit["remaining_fun_007682c0_external_fields"] == []
    assert guards["dat_00c128cc_selected_session_ready"] is True
    assert guards["fun_007682c0_raw_input_refresh_ready"] is True


def test_dat_00c128cc_closed_boundary_keeps_native_policy_distinct_from_retail_default() -> None:
    report = current.build_current_frontier()
    closed = next(
        row
        for row in report["closed_boundaries"]
        if row["boundary"].startswith("DAT_00c128cc")
    )
    assert closed["proof"] == current.BMW_NATIVE_DIFFICULTY_FORMAT
    assert closed["retail_source_field"] == "RaceModeInfo+0x6c"
    assert closed["selected_session_value"] == 1
    assert closed["valid_retail_domain"] == [0, 1, 2]
    assert closed["retail_default_used_as_proof"] is False
    assert closed["active_late_motion_read_provider_required"] is False


def test_renderer_transform_stays_closed_and_separate_from_wheel_query_producer() -> None:
    report = current.build_current_frontier()
    path = report["current_bind_path"]
    scheduler = report["scheduler_authority"]
    assert path["BODY0_bind_frame_proof_ready"] is True
    assert path["vehicle_world_transform_ready"] is True
    assert path["FUN_007682c0_delta_destination_is_BODY0"] is True
    assert path["FUN_007682c0_effect_production_internal"] is True
    assert path["FUN_007682c0_projection_state_internal"] is True
    assert path["FUN_007594e0_steering_internal"] is True
    assert path["BMW_response_4054_internal"] is True
    assert path["FUN_00765c40_load_term_ownership_ready"] is True
    assert path["FUN_00765c40_external_pass_result_history_contract"] == (
        current.FUN_00765C40_EXTERNAL_PASS_RESULT_HISTORY_FORMAT
    )
    assert path["FUN_00765c40_external_pass_result_contract"] == (
        current.FUN_00765C40_EXTERNAL_PASS_RESULT_FORMAT
    )
    assert path["FUN_00765c40_external_pass_input_contract"] == (
        current.FUN_00765C40_EXTERNAL_PASS_INPUT_FORMAT
    )
    assert path["FUN_00765c40_query_input_contract"] == current.FUN_00765C40_QUERY_INPUT_FORMAT
    assert path["FUN_00765c40_query_input_capture_ready"] is True
    assert path["FUN_00765c40_query_record_materialization_native"] is True
    assert path["FUN_00765c40_selected_world_position_contract"] == (
        current.FUN_00765C40_SELECTED_WORLD_POSITION_FORMAT
    )
    assert path["FUN_00765c40_world_position_producer_internal"] is True
    assert path["FUN_00765c40_query_cache_state_internal"] is True
    assert path["FUN_00765c40_selected_fallback_internal"] is True
    assert path["FUN_00765c40_collision_output_handoff_contract"] == (
        current.FUN_00765C40_COLLISION_OUTPUT_HANDOFF_FORMAT
    )
    assert path["FUN_00765c40_selected_collision_output_required"] is True
    assert path["FUN_00766510_query_scalar_handoff_contract"] == (
        current.FUN_00766510_QUERY_SCALAR_HANDOFF_FORMAT
    )
    assert path["FUN_00766510_query_scalar_handoff_native"] is True
    assert path["FUN_00766510_query_scalar_handoff_session_wired"] is False
    assert path["FUN_00765c40_collision_provider_internal"] is False
    assert path["FUN_00765c40_renderer_transform_used_as_query_producer"] is False
    assert path["FUN_00765c40_session_boundary_exact"] is True
    assert path["FUN_007560c0_gate_setup_owned"] is True
    assert path["BMW_native_player_difficulty_contract"] == current.BMW_NATIVE_DIFFICULTY_FORMAT
    assert path["BMW_native_player_difficulty"] == 1
    assert path["DAT_00c128cc_selected_session_internal"] is True
    assert scheduler["retail_cadence_admitted"] is True
    assert scheduler["loaded_inner_rate_admitted"] is True
    assert scheduler["selected_session_rate_hz"] == 180
    assert scheduler["selected_session_normal_outer_substeps"] == 6
    assert scheduler["inner_substep_execution_admitted"] is True
    assert scheduler["host_development_1_60_is_retail_evidence"] is False


def test_contract_exposes_collision_output_narrowing_and_no_fun_007682c0_raw_fields() -> None:
    payload = current.contract()
    assert payload["external_provider_count"] == 7
    assert payload["closed_provider_ids"] == [
        "fun_007682c0_delta_consumer",
        "fun_007682c0_effect_provider",
    ]
    assert payload["narrowed_provider_ids"] == {
        "fun_00765c40_complete_anchor": (
            "selected BMW query world position/cache/fallback and typed collision output are now "
            "source-owned or exposed; collision-provider execution and residual pass side effects remain external"
        )
    }
    assert payload["FUN_00765c40_external_pass_result_history_contract"] == (
        current.FUN_00765C40_EXTERNAL_PASS_RESULT_HISTORY_FORMAT
    )
    assert payload["FUN_00765c40_external_pass_result_contract"] == (
        current.FUN_00765C40_EXTERNAL_PASS_RESULT_FORMAT
    )
    assert payload["FUN_00765c40_external_pass_input_contract"] == (
        current.FUN_00765C40_EXTERNAL_PASS_INPUT_FORMAT
    )
    assert payload["FUN_00765c40_query_input_contract"] == current.FUN_00765C40_QUERY_INPUT_FORMAT
    assert payload["FUN_00765c40_collision_output_handoff_contract"] == (
        current.FUN_00765C40_COLLISION_OUTPUT_HANDOFF_FORMAT
    )
    assert payload["FUN_00766510_query_scalar_handoff_contract"] == (
        current.FUN_00766510_QUERY_SCALAR_HANDOFF_FORMAT
    )
    assert payload["FUN_00765c40_external_pass_result_ready"] is True
    assert payload["FUN_00765c40_query_input_ready"] is True
    assert payload["FUN_00765c40_query_input_capture_ready"] is True
    assert payload["FUN_00765c40_query_record_materialization_native"] is True
    assert payload["FUN_00765c40_query_input_capture_count_per_explicit_step"] == 2
    assert payload["FUN_00765c40_session_contact_factor_alias_removed"] is True
    assert payload["FUN_00765c40_complete_anchor_external"] is True
    assert payload["FUN_00765c40_world_position_producer_internal"] is True
    assert payload["FUN_00765c40_world_position_coordinate_provenance_inferred"] is False
    assert payload["FUN_00765c40_renderer_transform_reused_as_query_transform"] is False
    assert payload["FUN_00765c40_query_cache_state_internal"] is True
    assert payload["FUN_00765c40_selected_fallback_internal"] is True
    assert payload["FUN_00765c40_selected_collision_output_required"] is True
    assert payload["FUN_00765c40_collision_provider_internal"] is False
    assert payload["FUN_00766510_query_scalar_handoff_native"] is True
    assert payload["FUN_00766510_query_scalar_handoff_session_wired"] is False
    assert payload["BMW_native_player_difficulty_contract"] == current.BMW_NATIVE_DIFFICULTY_FORMAT
    assert payload["DAT_00c128cc_selected_session_internal"] is True
    assert payload["selected_player_difficulty"] == 1
    assert payload["retail_player_difficulty_default_used_as_proof"] is False
    assert payload["remaining_FUN_007682c0_external_fields"] == []
    assert payload["FUN_007682c0_raw_input_refresh_external"] is False
    assert payload["selected_session_rate_hz"] == 180
    assert payload["provider_semantics_promoted"] is False
    assert payload["render_loop_equated_to_outer_dispatch"] is False
    assert payload["host_1_60_is_retail_evidence"] is False
