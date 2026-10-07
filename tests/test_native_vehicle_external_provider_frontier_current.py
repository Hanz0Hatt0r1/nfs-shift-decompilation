from __future__ import annotations

from src.physics import native_vehicle_external_provider_frontier as legacy
from src.physics import native_vehicle_external_provider_frontier_current as current


def _providers(report: dict) -> dict[str, dict]:
    return {row["id"]: row for row in report["providers"]}


def test_current_frontier_keeps_legacy_history_but_has_eight_active_boundaries() -> None:
    old = legacy.build_frontier()
    report = current.build_current_frontier()
    assert old["external_provider_count"] == 9
    assert report["format"] == current.FORMAT
    assert report["upstream_frontier"] == legacy.FORMAT
    assert report["refresh_after_phase"] == 722
    assert report["external_provider_count"] == 8
    assert report["provider_audit"]["legacy_external_provider_count"] == 9
    assert report["provider_audit"]["active_external_provider_count"] == 8
    assert report["provider_audit"]["closed_provider_ids"] == [
        "fun_007682c0_delta_consumer"
    ]


def test_fun_00765c40_remains_external_but_now_owns_typed_load_terms() -> None:
    report = current.build_current_frontier()
    contact = _providers(report)["fun_00765c40_complete_anchor"]
    assert contact["process2_action"] == legacy.REQUEST_PROCESS1
    assert contact["boundary_kind"] == "typed_output_provider_complete_anchor_external"
    assert "NativeVehicleContactFactorProvider" in contact["current_api"]
    assert "Fun00765c40LoadTerms" in contact["current_api"]
    joined = " ".join(contact["evidence"])
    assert current.FUN_00765C40_LOAD_TERMS_FORMAT in joined
    assert contact["blockers"]


def test_precomputed_effect_boundary_is_replaced_by_narrowed_raw_machine_inputs() -> None:
    report = current.build_current_frontier()
    providers = _providers(report)
    assert "fun_007682c0_effect_provider" not in providers
    assert "fun_007682c0_delta_consumer" not in providers
    raw = providers["fun_007682c0_machine_input_provider"]
    assert raw["boundary_kind"] == "typed_raw_machine_input_provider"
    assert "NativeVehicleMotionReadInputProvider" in raw["current_api"]
    assert "Fun007682c0ExternalMachineInput" in raw["current_api"]
    assert raw["process2_action"] == legacy.REQUEST_PROCESS1
    assert raw["blockers"]
    joined = " ".join(raw["evidence"])
    assert current.FUN_007682C0_DESTINATION_FORMAT in joined
    assert current.FUN_007682C0_EFFECT_FORMAT in joined
    assert current.FUN_007682C0_PROJECTION_FORMAT in joined
    assert current.FUN_007594E0_ANGLE_FORMAT in joined
    assert current.BMW_RESPONSE_4054_FORMAT in joined
    assert current.FUN_00765C40_LOAD_TERMS_FORMAT in joined
    blockers = " ".join(raw["blockers"])
    for closed in (
        "+0x4084",
        "+0x408c",
        "+0x4068",
        "+0x4054",
        "+0xb38",
        "+0x15b8",
        "+0x2038",
        "+0x2ab8",
    ):
        assert closed not in blockers
    assert "+0xe0" in blockers
    assert "DAT_00c128cc" in blockers


def test_effect_inputs_are_narrowed_to_gate_and_angle_mode() -> None:
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
    assert audit["fun_007682c0_external_precomputed_effect_required"] is False
    assert audit["fun_007682c0_external_delta_consumer_required"] is False
    assert audit["fun_007682c0_external_projection_fields_required"] is False
    assert audit["fun_007682c0_external_steering_required"] is False
    assert audit["fun_007682c0_external_response_4054_required"] is False
    assert audit["fun_007682c0_external_load_terms_required"] is False
    assert audit["fun_007682c0_raw_input_refresh_external"] is True
    assert audit["remaining_fun_007682c0_external_fields"] == [
        "HDVehicle+0xe0",
        "DAT_00c128cc",
    ]
    assert guards["fun_007682c0_body0_delta_destination_ready"] is True
    assert guards["fun_007682c0_body0_delta_application_internal"] is True
    assert guards["fun_007682c0_effect_production_ready"] is True
    assert guards["fun_007682c0_x87_fsqrt_ready"] is True
    assert guards["fun_007682c0_projection_state_ready"] is True
    assert guards["fun_007682c0_projection_fields_external"] is False
    assert guards["fun_007594e0_machine_angle_ready"] is True
    assert guards["fun_007682c0_steering_external"] is False
    assert guards["fun_007682c0_response_4054_ready"] is True
    assert guards["fun_007682c0_response_4054_external"] is False
    assert guards["fun_00765c40_load_term_ownership_ready"] is True
    assert guards["fun_007682c0_load_terms_external"] is False
    assert guards["fun_00765c40_complete_anchor_external"] is True
    assert guards["fun_007682c0_raw_input_refresh_ready"] is False


def test_positive_transform_and_selected_session_timing_remain_closed() -> None:
    report = current.build_current_frontier()
    path = report["current_bind_path"]
    scheduler = report["scheduler_authority"]
    assert path["BODY0_bind_frame_proof_ready"] is True
    assert path["vehicle_world_transform_ready"] is True
    assert path["FUN_007682c0_delta_destination_is_BODY0"] is True
    assert path["FUN_007682c0_effect_production_internal"] is True
    assert path["FUN_007682c0_projection_state_internal"] is True
    assert path["FUN_007682c0_projection_state_contract"] == current.FUN_007682C0_PROJECTION_FORMAT
    assert path["FUN_007594e0_steering_internal"] is True
    assert path["FUN_007594e0_machine_angle_contract"] == current.FUN_007594E0_ANGLE_FORMAT
    assert path["BMW_response_4054_contract"] == current.BMW_RESPONSE_4054_FORMAT
    assert path["BMW_response_4054_internal"] is True
    assert path["FUN_00765c40_load_terms_contract"] == current.FUN_00765C40_LOAD_TERMS_FORMAT
    assert path["FUN_00765c40_load_term_ownership_ready"] is True
    assert scheduler["retail_cadence_admitted"] is True
    assert scheduler["loaded_inner_rate_admitted"] is True
    assert scheduler["selected_session_rate_hz"] == 180
    assert scheduler["selected_session_normal_outer_substeps"] == 6
    assert scheduler["inner_substep_execution_admitted"] is True
    assert scheduler["host_development_1_60_is_retail_evidence"] is False


def test_contract_exposes_narrowed_boundary_without_promoting_contact_solver() -> None:
    payload = current.contract()
    assert payload["external_provider_count"] == 8
    assert payload["FUN_007682c0_machine_effect_contract"] == current.FUN_007682C0_EFFECT_FORMAT
    assert payload["FUN_007682c0_projection_state_contract"] == current.FUN_007682C0_PROJECTION_FORMAT
    assert payload["FUN_007594e0_machine_angle_contract"] == current.FUN_007594E0_ANGLE_FORMAT
    assert payload["BMW_response_4054_contract"] == current.BMW_RESPONSE_4054_FORMAT
    assert payload["FUN_00765c40_load_terms_contract"] == current.FUN_00765C40_LOAD_TERMS_FORMAT
    assert payload["FUN_007682c0_effect_production_internal"] is True
    assert payload["FUN_007682c0_x87_fsqrt_internal"] is True
    assert payload["FUN_007682c0_projection_state_internal"] is True
    assert payload["FUN_007682c0_external_projection_fields_required"] is False
    assert payload["FUN_007594e0_steering_internal"] is True
    assert payload["FUN_007682c0_external_steering_required"] is False
    assert payload["FUN_007682c0_response_4054_internal"] is True
    assert payload["FUN_007682c0_external_response_4054_required"] is False
    assert payload["FUN_00765c40_load_term_ownership_ready"] is True
    assert payload["FUN_00765c40_load_terms_typed_output"] is True
    assert payload["FUN_00765c40_complete_anchor_external"] is True
    assert payload["FUN_007682c0_external_load_terms_required"] is False
    assert payload["remaining_FUN_007682c0_external_fields"] == [
        "HDVehicle+0xe0",
        "DAT_00c128cc",
    ]
    assert payload["FUN_007682c0_raw_input_refresh_external"] is True
    assert payload["selected_session_rate_hz"] == 180
    assert payload["provider_semantics_promoted"] is False
    assert payload["render_loop_equated_to_outer_dispatch"] is False
    assert payload["host_1_60_is_retail_evidence"] is False
