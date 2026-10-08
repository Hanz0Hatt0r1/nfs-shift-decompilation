from __future__ import annotations

from pathlib import Path

from src.physics import native_vehicle_external_provider_frontier_p2_4_current as p2_4

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_RESULT = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
NATIVE_QUERY_EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_native_selected_query_input.json"
SESSION_QUERY_EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_session_query_snapshot.json"
WHEEL_STATE_EVIDENCE = ROOT / "evidence/fun_00752fa0_wheel_state_machine_proof.json"
COMPOSED_EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_composed_residual_executor.json"
COMPOSED_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_composed_residual_executor.hpp"
HANDOFF_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_residual_producer_handoff.hpp"
PROMOTION_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_residual_producer_promotion_gate.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_p2_4_overlay_currentizes_fun_00765c40_without_rewriting_history() -> None:
    report = p2_4.build_current_frontier()
    assert report["format"] == p2_4.FORMAT
    assert report["external_provider_count"] == 7
    fun = report["fun_00765c40"]
    assert fun["active_provider_required"] is True
    assert fun["provider_removal_authorized_by_process1"] is True
    assert fun["provider_removed"] is False
    assert fun["external_pass_result_contract"] == "SHIFT.Fun00765c40ExternalPassResult/5"
    assert fun["historical_collision_output_result_contract"] == "SHIFT.Fun00765c40ExternalPassResult/4"
    assert fun["residual_producer_handoff_contract"] == "SHIFT.Fun00765c40ResidualProducerHandoff/2"
    assert fun["historical_residual_producer_handoff_contract"] == "SHIFT.Fun00765c40ResidualProducerHandoff/1"
    assert fun["residual_producer_promotion_gate_contract"] == "SHIFT.Fun00765c40ResidualProducerPromotionGate/1"
    assert fun["residual_producer_handoff_present"] is True
    assert fun["residual_producer_handoff_threaded_through_provider_result"] is True
    assert fun["residual_producer_handoff_threaded_through_session_result"] is True
    assert fun["residual_producer_handoff_authoritative"] is False
    assert fun["residual_producer_handoff_selective_families"] is True
    assert fun["residual_producer_handoff_legacy_all_families_compatible"] is True
    assert fun["residual_producer_promotion_gate_present"] is True
    assert fun["residual_producer_promotion_gate_session_wired"] is False
    assert fun["residual_producer_promotion_authorized_family_count"] == 0
    assert fun["residual_producer_presence_counts_as_proof"] is False
    assert fun["selected_world_position_native"] is True
    assert fun["selected_query_fallback_native"] is True
    assert fun["selected_query_input_native"] is True
    assert fun["provider_returned_selected_query_input_authoritative"] is False
    assert fun["session_query_snapshot_native"] is True
    assert fun["collision_output_typed"] is True
    assert fun["wheel_state_machine_proof_contract"] == p2_4.WHEEL_STATE_MACHINE_PROOF_FORMAT
    assert fun["wheel_state_source_address"] == "HDVehicle+0x98"
    assert fun["wheel_state_source_address_proven"] is True
    assert fun["wheel_state_source_owner_lifetime_native"] is False
    assert fun["lower_scene_query_provider_external"] is True
    assert fun["lower_scene_query_provider_global"] == "0x00c133ac"
    assert fun["lower_scene_query_provider_vtable_slot"] == "0x1c0"
    assert fun["composed_residual_executor_present"] is True
    assert fun["complete_internalization"] is False
    assert tuple(fun["remaining_explicit_producers"]) == p2_4.REMAINING_EXPLICIT_PRODUCERS
    assert report["guards"]["historical_phase726_audit_mutated"] is False
    assert report["guards"]["historical_phase744_evidence_mutated"] is False
    assert report["guards"]["external_provider_count_decremented"] is False
    assert report["guards"]["wheel_state_source_owner_inferred_from_address"] is False
    assert report["guards"]["producer_handoff_treated_as_native_computation"] is False
    assert report["guards"]["absent_producer_family_default_overwrite_allowed"] is False
    assert report["guards"]["producer_presence_treated_as_independent_proof"] is False
    assert report["guards"]["producer_promotion_without_proof_allowed"] is False


def test_overlay_matches_active_runtime_contracts() -> None:
    result_header = EXTERNAL_RESULT.read_text(encoding="utf-8")
    native_query_evidence = NATIVE_QUERY_EVIDENCE.read_text(encoding="utf-8")
    session_query_evidence = SESSION_QUERY_EVIDENCE.read_text(encoding="utf-8")
    wheel_state_evidence = WHEEL_STATE_EVIDENCE.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")
    composed = COMPOSED_EVIDENCE.read_text(encoding="utf-8")
    composed_header = COMPOSED_HEADER.read_text(encoding="utf-8")
    handoff_header = HANDOFF_HEADER.read_text(encoding="utf-8")
    promotion_header = PROMOTION_HEADER.read_text(encoding="utf-8")

    assert p2_4.EXTERNAL_PASS_RESULT_FORMAT in result_header
    assert p2_4.HISTORICAL_COLLISION_OUTPUT_RESULT_FORMAT in result_header
    assert p2_4.RESIDUAL_PRODUCER_HANDOFF_FORMAT in handoff_header
    assert p2_4.HISTORICAL_RESIDUAL_PRODUCER_HANDOFF_FORMAT in handoff_header
    assert p2_4.RESIDUAL_PRODUCER_PROMOTION_GATE_FORMAT in promotion_header
    assert "family_presence_explicit = false" in handoff_header
    assert "family_present{}" in handoff_header
    assert "independently_proven{}" in promotion_header
    assert "present without independent proof authorization" in promotion_header
    assert "std::optional<CollisionQueryOutput> query_output" in result_header
    assert "std::optional<Fun00765c40ResidualProducerHandoff> residual_producer_handoff" in result_header
    assert p2_4.NATIVE_SELECTED_QUERY_INPUT_FORMAT in native_query_evidence
    assert p2_4.SESSION_QUERY_SNAPSHOT_FORMAT in session_query_evidence
    assert p2_4.WHEEL_STATE_MACHINE_PROOF_FORMAT in wheel_state_evidence
    assert '"qword_argument_source": "HDVehicle+0x98"' in wheel_state_evidence
    assert "std::uint64_t wheel_state_source_bits = 0u" in composed_header
    assert "fun_00765c40_residual_producer_family_is_present" in composed_header
    assert "materialize_fun_00765c40_session_query_snapshot" in session_source
    assert "query_inputs[pass_index] = session_query_input" in session_source
    assert "fun_00765c40_residual_producer_handoffs" in session_header
    assert "fun_00765c40_residual_producer_handoff_capture_count" in session_header
    assert "if (result.residual_producer_handoff.has_value())" in session_source
    assert "residual_producer_handoffs[pass_index] =" in session_source
    assert "result.fun_00765c40_residual_producer_handoffs =" in session_source
    assert "execute_fun_00765c40_composed_residual_pass" not in session_source
    assert "apply_proven_fun_00765c40_residual_producer_handoff" not in session_source
    assert p2_4.COMPOSED_RESIDUAL_EXECUTOR_FORMAT in composed
    assert '"complete_FUN_00765c40_internalized": false' in composed
    assert '"external_provider_count_after": 7' in composed


def test_contract_is_fail_closed_on_remaining_producers() -> None:
    payload = p2_4.contract()
    assert payload["external_provider_count"] == 7
    assert payload["external_pass_result_contract"] == "SHIFT.Fun00765c40ExternalPassResult/5"
    assert payload["historical_collision_output_result_contract"] == "SHIFT.Fun00765c40ExternalPassResult/4"
    assert payload["residual_producer_handoff_contract"] == "SHIFT.Fun00765c40ResidualProducerHandoff/2"
    assert payload["historical_residual_producer_handoff_contract"] == "SHIFT.Fun00765c40ResidualProducerHandoff/1"
    assert payload["residual_producer_promotion_gate_contract"] == "SHIFT.Fun00765c40ResidualProducerPromotionGate/1"
    assert payload["residual_producer_handoff_threaded_through_provider_result"] is True
    assert payload["residual_producer_handoff_threaded_through_session_result"] is True
    assert payload["residual_producer_handoff_authoritative"] is False
    assert payload["residual_producer_handoff_selective_families"] is True
    assert payload["residual_producer_handoff_legacy_all_families_compatible"] is True
    assert payload["residual_producer_promotion_gate_present"] is True
    assert payload["residual_producer_promotion_gate_session_wired"] is False
    assert payload["residual_producer_promotion_authorized_family_count"] == 0
    assert payload["residual_producer_presence_counts_as_proof"] is False
    assert payload["provider_returned_selected_query_input_authoritative"] is False
    assert payload["wheel_state_source_address"] == "HDVehicle+0x98"
    assert payload["wheel_state_source_address_proven"] is True
    assert payload["wheel_state_source_owner_lifetime_native"] is False
    assert payload["lower_scene_query_provider_external"] is True
    assert payload["complete_internalization"] is False
    assert payload["provider_removed"] is False
    assert payload["remaining_explicit_producers"] == list(p2_4.REMAINING_EXPLICIT_PRODUCERS)
    assert "wheel_state_source_HDVehicle_0x98_owner_lifetime" in payload["remaining_explicit_producers"]
    assert "wheel_job_formula_FUN_0075cfb0" in payload["remaining_explicit_producers"]
    assert "FUN_007584f0_computed_payloads" in payload["remaining_explicit_producers"]
