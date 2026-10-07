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
    assert report["refresh_after_phase"] == 724
    assert report["external_provider_count"] == 7
    audit = report["provider_audit"]
    assert audit["legacy_external_provider_count"] == 9
    assert audit["active_external_provider_count"] == 7
    assert audit["closed_provider_ids"] == [
        "fun_007682c0_delta_consumer",
        "fun_007682c0_effect_provider",
    ]


def test_fun_00765c40_remains_external_but_owns_typed_load_terms() -> None:
    report = current.build_current_frontier()
    contact = _providers(report)["fun_00765c40_complete_anchor"]
    assert contact["process2_action"] == legacy.REQUEST_PROCESS1
    assert contact["boundary_kind"] == "typed_output_provider_complete_anchor_external"
    assert "NativeVehicleContactFactorProvider" in contact["current_api"]
    assert "Fun00765c40LoadTerms" in contact["current_api"]
    assert current.FUN_00765C40_LOAD_TERMS_FORMAT in " ".join(contact["evidence"])
    assert contact["blockers"]


def test_fun_007682c0_top_level_boundaries_are_closed() -> None:
    report = current.build_current_frontier()
    providers = _providers(report)
    assert "fun_007682c0_effect_provider" not in providers
    assert "fun_007682c0_delta_consumer" not in providers
    assert "fun_007682c0_machine_input_provider" not in providers
    closed = report["closed_boundaries"]
    difficulty = next(
        row for row in closed if row.get("boundary") == "DAT_00c128cc FUN_007682c0 angle mode"
    )
    assert difficulty["proof"] == current.DAT_00C128CC_DIFFICULTY_FORMAT
    assert difficulty["selected_session_contract"] == current.SELECTED_RACE_MODE_FORMAT
    assert difficulty["selected_player_difficulty"] == 1
    assert difficulty["active_late_motion_read_provider_required"] is False
    assert difficulty["retail_live_session_selector_inferred"] is False


def test_all_fun_007682c0_inputs_have_explicit_owners() -> None:
    report = current.build_current_frontier()
    audit = report["provider_audit"]
    guards = report["guards"]
    assert audit["fun_007682c0_runtime_body0_mutation_internalized"] is True
    assert audit["fun_007682c0_effect_arithmetic_internalized"] is True
    assert audit["fun_007682c0_x87_fsqrt_internalized"] is True
    assert audit["fun_007682c0_projection_fields_internalized"] is True
    assert audit["fun_007682c0_projection_refresh_after_both_passes"] is True
    assert audit["fun_007594e0_body0_basis_angle_internalized"] is True
    assert audit["fun_007594e0_x87_fpatan_internalized"] is True
    assert audit["fun_007594e0_refresh_before_both_passes"] is True
    assert audit["fun_007682c0_response_4054_internalized"] is True
    assert audit["fun_00765c40_load_term_ownership_proven"] is True
    assert audit["fun_00765c40_load_terms_typed_output"] is True
    assert audit["fun_00765c40_complete_anchor_external"] is True
    assert audit["fun_007560c0_gate_setup_ownership_proven"] is True
    assert audit["fun_007560c0_selected_gate_value_native"] is False
    assert audit["dat_00c128cc_race_mode_ownership_proven"] is True
    assert audit["fun_007682c0_angle_mode_session_owned"] is True
    assert audit["selected_player_difficulty"] == 1
    assert audit["selected_player_difficulty_is_retail_observation"] is False
    assert audit["fun_007682c0_external_precomputed_effect_required"] is False
    assert audit["fun_007682c0_external_delta_consumer_required"] is False
    assert audit["fun_007682c0_external_projection_fields_required"] is False
    assert audit["fun_007682c0_external_steering_required"] is False
    assert audit["fun_007682c0_external_response_4054_required"] is False
    assert audit["fun_007682c0_external_load_terms_required"] is False
    assert audit["fun_007682c0_external_gate_required_per_pass"] is False
    assert audit["fun_007682c0_external_angle_mode_required"] is False
    assert audit["fun_007682c0_raw_input_refresh_external"] is False
    assert audit["remaining_fun_007682c0_external_fields"] == []
    assert guards["fun_007682c0_body0_delta_destination_ready"] is True
    assert guards["fun_007682c0_effect_production_ready"] is True
    assert guards["fun_00765c40_complete_anchor_external"] is True
    assert guards["fun_007560c0_gate_setup_ownership_ready"] is True
    assert guards["dat_00c128cc_player_difficulty_ownership_ready"] is True
    assert guards["fun_007682c0_angle_mode_external"] is False
    assert guards["fun_007682c0_raw_input_refresh_ready"] is True
    assert guards["fun_007682c0_raw_input_provider_required"] is False


def test_positive_transform_timing_and_race_mode_selection_are_joined() -> None:
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
    assert path["FUN_007560c0_gate_setup_owned"] is True
    assert path["DAT_00c128cc_player_difficulty_contract"] == current.DAT_00C128CC_DIFFICULTY_FORMAT
    assert path["selected_race_mode_contract"] == current.SELECTED_RACE_MODE_FORMAT
    assert path["selected_player_difficulty"] == 1
    assert path["FUN_007682c0_angle_mode_session_owned"] is True
    assert scheduler["retail_cadence_admitted"] is True
    assert scheduler["loaded_inner_rate_admitted"] is True
    assert scheduler["selected_session_rate_hz"] == 180
    assert scheduler["selected_session_player_difficulty"] == 1
    assert scheduler["selected_session_normal_outer_substeps"] == 6
    assert scheduler["inner_substep_execution_admitted"] is True
    assert scheduler["host_development_1_60_is_retail_evidence"] is False


def test_contract_exposes_no_late_fun_007682c0_fields() -> None:
    payload = current.contract()
    assert payload["external_provider_count"] == 7
    assert payload["FUN_007682c0_machine_effect_contract"] == current.FUN_007682C0_EFFECT_FORMAT
    assert payload["FUN_007682c0_projection_state_contract"] == current.FUN_007682C0_PROJECTION_FORMAT
    assert payload["FUN_007594e0_machine_angle_contract"] == current.FUN_007594E0_ANGLE_FORMAT
    assert payload["BMW_response_4054_contract"] == current.BMW_RESPONSE_4054_FORMAT
    assert payload["FUN_00765c40_load_terms_contract"] == current.FUN_00765C40_LOAD_TERMS_FORMAT
    assert payload["FUN_007560c0_gate_setup_contract"] == current.FUN_007560C0_GATE_SETUP_FORMAT
    assert payload["DAT_00c128cc_player_difficulty_contract"] == current.DAT_00C128CC_DIFFICULTY_FORMAT
    assert payload["selected_race_mode_contract"] == current.SELECTED_RACE_MODE_FORMAT
    assert payload["FUN_007682c0_effect_production_internal"] is True
    assert payload["FUN_007682c0_projection_state_internal"] is True
    assert payload["FUN_007594e0_steering_internal"] is True
    assert payload["FUN_007682c0_response_4054_internal"] is True
    assert payload["FUN_00765c40_load_term_ownership_ready"] is True
    assert payload["FUN_00765c40_complete_anchor_external"] is True
    assert payload["FUN_007560c0_gate_setup_owned"] is True
    assert payload["FUN_007560c0_selected_gate_value_native"] is False
    assert payload["DAT_00c128cc_player_difficulty_owned"] is True
    assert payload["selected_session_player_difficulty"] == 1
    assert payload["selected_player_difficulty_is_retail_observation"] is False
    assert payload["FUN_007682c0_external_angle_mode_required"] is False
    assert payload["remaining_FUN_007682c0_external_fields"] == []
    assert payload["FUN_007682c0_raw_input_refresh_external"] is False
    assert payload["FUN_007682c0_raw_input_provider_required"] is False
    assert payload["selected_session_rate_hz"] == 180
    assert payload["provider_semantics_promoted"] is False
    assert payload["render_loop_equated_to_outer_dispatch"] is False
    assert payload["host_1_60_is_retail_evidence"] is False
