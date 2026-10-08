"""Current P2.4 overlay for the active FUN_00765c40 provider frontier.

The older ``native_vehicle_external_provider_frontier_current`` module remains a
Phase726-era compatibility audit. This overlay consumes that report and records
only later positive P2.4 ownership changes so callers do not have to reinterpret
historical Phase725/726 claims as current state.
"""
from __future__ import annotations

from typing import Any

from . import native_vehicle_external_provider_frontier_current as phase726

FORMAT = "SHIFT.NativeVehicleExternalProviderFrontierP2_4Current/1"
EXTERNAL_PASS_RESULT_FORMAT = "SHIFT.Fun00765c40ExternalPassResult/5"
HISTORICAL_COLLISION_OUTPUT_RESULT_FORMAT = "SHIFT.Fun00765c40ExternalPassResult/4"
NATIVE_SELECTED_QUERY_INPUT_FORMAT = "SHIFT.Fun00765c40NativeSelectedQueryInput/1"
SESSION_QUERY_SNAPSHOT_FORMAT = "SHIFT.Fun00765c40SessionQuerySnapshot/1"
SELECTED_WORLD_POSITION_FORMAT = "SHIFT.Fun00765c40SelectedBMWWorldPosition/1"
SELECTED_QUERY_FALLBACK_FORMAT = "SHIFT.Fun00765c40SelectedBMWQueryFallback/1"
COLLISION_OUTPUT_HANDOFF_FORMAT = "SHIFT.Fun00765c40CollisionOutputHandoff/1"
COMPOSED_RESIDUAL_EXECUTOR_FORMAT = "SHIFT.Fun00765c40ComposedResidualExecutor/1"
RESIDUAL_PRODUCER_HANDOFF_FORMAT = "SHIFT.Fun00765c40ResidualProducerHandoff/2"
HISTORICAL_RESIDUAL_PRODUCER_HANDOFF_FORMAT = "SHIFT.Fun00765c40ResidualProducerHandoff/1"
RESIDUAL_PRODUCER_PROMOTION_GATE_FORMAT = "SHIFT.Fun00765c40ResidualProducerPromotionGate/1"
WHEEL_STATE_MACHINE_PROOF_FORMAT = "SHIFT.Fun00752fa0WheelStateMachineProof/1"
WHEEL_JOB_LOAD_STORE_SURFACE_FORMAT = "SHIFT.Fun0075cfb0LoadStoreSurface/1"

REMAINING_EXPLICIT_PRODUCERS = (
    "wheel_plane_producer_arithmetic",
    "wheel_state_source_HDVehicle_0x98_owner_lifetime",
    "wheel_job_formula_FUN_0075cfb0",
    "FUN_007584f0_computed_payloads",
    "wheel_pair_producer_arithmetic",
    "contact_array_producer_arithmetic",
    "contact_body_predicates_and_vectors",
    "bounded_state_tail_predicate_and_payloads",
    "optional_body_predicate_and_vectors",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_current_frontier() -> dict[str, Any]:
    upstream = phase726.build_current_frontier()
    _require(
        upstream.get("format") == phase726.FORMAT,
        "Phase726 compatibility frontier format drift",
    )
    _require(
        upstream.get("external_provider_count") == 7,
        "P2.4 overlay expects the seven-provider frontier",
    )

    providers = {
        str(row.get("id")): row for row in upstream.get("providers", [])
    }
    _require(
        "fun_00765c40_complete_anchor" in providers,
        "FUN_00765c40 provider missing from upstream frontier",
    )

    return {
        "format": FORMAT,
        "version": 1,
        "upstream_frontier": phase726.FORMAT,
        "external_provider_count": 7,
        "fun_00765c40": {
            "provider_id": "fun_00765c40_complete_anchor",
            "active_provider_required": True,
            "provider_removal_authorized_by_process1": True,
            "provider_removed": False,
            "external_pass_result_contract": EXTERNAL_PASS_RESULT_FORMAT,
            "historical_collision_output_result_contract": HISTORICAL_COLLISION_OUTPUT_RESULT_FORMAT,
            "native_selected_query_input_contract": NATIVE_SELECTED_QUERY_INPUT_FORMAT,
            "session_query_snapshot_contract": SESSION_QUERY_SNAPSHOT_FORMAT,
            "selected_world_position_contract": SELECTED_WORLD_POSITION_FORMAT,
            "selected_query_fallback_contract": SELECTED_QUERY_FALLBACK_FORMAT,
            "collision_output_handoff_contract": COLLISION_OUTPUT_HANDOFF_FORMAT,
            "composed_residual_executor_contract": COMPOSED_RESIDUAL_EXECUTOR_FORMAT,
            "residual_producer_handoff_contract": RESIDUAL_PRODUCER_HANDOFF_FORMAT,
            "historical_residual_producer_handoff_contract": HISTORICAL_RESIDUAL_PRODUCER_HANDOFF_FORMAT,
            "residual_producer_promotion_gate_contract": RESIDUAL_PRODUCER_PROMOTION_GATE_FORMAT,
            "residual_producer_handoff_present": True,
            "residual_producer_handoff_threaded_through_provider_result": True,
            "residual_producer_handoff_threaded_through_session_result": True,
            "residual_producer_handoff_authoritative": False,
            "residual_producer_handoff_selective_families": True,
            "residual_producer_handoff_legacy_all_families_compatible": True,
            "residual_producer_promotion_gate_present": True,
            "residual_producer_promotion_gate_session_wired": False,
            "residual_producer_promotion_authorized_family_count": 0,
            "residual_producer_presence_counts_as_proof": False,
            "wheel_state_machine_proof_contract": WHEEL_STATE_MACHINE_PROOF_FORMAT,
            "wheel_state_source_address": "HDVehicle+0x98",
            "wheel_state_source_address_proven": True,
            "wheel_state_source_owner_lifetime_native": False,
            "wheel_job_load_store_surface_contract": WHEEL_JOB_LOAD_STORE_SURFACE_FORMAT,
            "wheel_job_load_store_surface_native": True,
            "wheel_job_load_store_site_count": 3,
            "wheel_job_load_store_payload_bit_preserved": True,
            "wheel_job_formula_internalized": False,
            "wheel_job_branch_predicates_internalized": False,
            "selected_world_position_native": True,
            "selected_query_fallback_native": True,
            "selected_query_input_native": True,
            "provider_returned_selected_query_input_authoritative": False,
            "session_query_snapshot_native": True,
            "collision_output_typed": True,
            "lower_scene_query_provider_external": True,
            "lower_scene_query_provider_global": "0x00c133ac",
            "lower_scene_query_provider_vtable_slot": "0x1c0",
            "composed_residual_executor_present": True,
            "complete_internalization": False,
            "remaining_explicit_producers": list(REMAINING_EXPLICIT_PRODUCERS),
        },
        "guards": {
            "historical_phase726_audit_mutated": False,
            "historical_phase744_evidence_mutated": False,
            "external_provider_count_decremented": False,
            "lower_collision_semantics_invented": False,
            "unproven_producer_formula_invented": False,
            "wheel_state_source_owner_inferred_from_address": False,
            "producer_handoff_treated_as_native_computation": False,
            "absent_producer_family_default_overwrite_allowed": False,
            "producer_presence_treated_as_independent_proof": False,
            "producer_promotion_without_proof_allowed": False,
            "wheel_job_commit_surface_treated_as_formula_proof": False,
        },
    }


def contract() -> dict[str, Any]:
    report = build_current_frontier()
    fun = report["fun_00765c40"]
    return {
        "format": FORMAT,
        "upstream_frontier": report["upstream_frontier"],
        "external_provider_count": report["external_provider_count"],
        "external_pass_result_contract": fun["external_pass_result_contract"],
        "historical_collision_output_result_contract": fun[
            "historical_collision_output_result_contract"
        ],
        "native_selected_query_input_contract": fun["native_selected_query_input_contract"],
        "session_query_snapshot_contract": fun["session_query_snapshot_contract"],
        "collision_output_handoff_contract": fun["collision_output_handoff_contract"],
        "composed_residual_executor_contract": fun["composed_residual_executor_contract"],
        "residual_producer_handoff_contract": fun["residual_producer_handoff_contract"],
        "historical_residual_producer_handoff_contract": fun[
            "historical_residual_producer_handoff_contract"
        ],
        "residual_producer_promotion_gate_contract": fun[
            "residual_producer_promotion_gate_contract"
        ],
        "residual_producer_handoff_present": fun["residual_producer_handoff_present"],
        "residual_producer_handoff_threaded_through_provider_result": fun[
            "residual_producer_handoff_threaded_through_provider_result"
        ],
        "residual_producer_handoff_threaded_through_session_result": fun[
            "residual_producer_handoff_threaded_through_session_result"
        ],
        "residual_producer_handoff_authoritative": fun[
            "residual_producer_handoff_authoritative"
        ],
        "residual_producer_handoff_selective_families": fun[
            "residual_producer_handoff_selective_families"
        ],
        "residual_producer_handoff_legacy_all_families_compatible": fun[
            "residual_producer_handoff_legacy_all_families_compatible"
        ],
        "residual_producer_promotion_gate_present": fun[
            "residual_producer_promotion_gate_present"
        ],
        "residual_producer_promotion_gate_session_wired": fun[
            "residual_producer_promotion_gate_session_wired"
        ],
        "residual_producer_promotion_authorized_family_count": fun[
            "residual_producer_promotion_authorized_family_count"
        ],
        "residual_producer_presence_counts_as_proof": fun[
            "residual_producer_presence_counts_as_proof"
        ],
        "wheel_state_machine_proof_contract": fun["wheel_state_machine_proof_contract"],
        "wheel_state_source_address": fun["wheel_state_source_address"],
        "wheel_state_source_address_proven": fun["wheel_state_source_address_proven"],
        "wheel_state_source_owner_lifetime_native": fun[
            "wheel_state_source_owner_lifetime_native"
        ],
        "wheel_job_load_store_surface_contract": fun[
            "wheel_job_load_store_surface_contract"
        ],
        "wheel_job_load_store_surface_native": fun[
            "wheel_job_load_store_surface_native"
        ],
        "wheel_job_load_store_site_count": fun["wheel_job_load_store_site_count"],
        "wheel_job_formula_internalized": fun["wheel_job_formula_internalized"],
        "wheel_job_branch_predicates_internalized": fun[
            "wheel_job_branch_predicates_internalized"
        ],
        "selected_world_position_native": fun["selected_world_position_native"],
        "selected_query_fallback_native": fun["selected_query_fallback_native"],
        "selected_query_input_native": fun["selected_query_input_native"],
        "provider_returned_selected_query_input_authoritative": fun[
            "provider_returned_selected_query_input_authoritative"
        ],
        "lower_scene_query_provider_external": fun[
            "lower_scene_query_provider_external"
        ],
        "complete_internalization": fun["complete_internalization"],
        "provider_removed": fun["provider_removed"],
        "remaining_explicit_producers": fun["remaining_explicit_producers"],
    }


__all__ = [
    "FORMAT",
    "EXTERNAL_PASS_RESULT_FORMAT",
    "HISTORICAL_COLLISION_OUTPUT_RESULT_FORMAT",
    "NATIVE_SELECTED_QUERY_INPUT_FORMAT",
    "SESSION_QUERY_SNAPSHOT_FORMAT",
    "SELECTED_WORLD_POSITION_FORMAT",
    "SELECTED_QUERY_FALLBACK_FORMAT",
    "COLLISION_OUTPUT_HANDOFF_FORMAT",
    "COMPOSED_RESIDUAL_EXECUTOR_FORMAT",
    "RESIDUAL_PRODUCER_HANDOFF_FORMAT",
    "HISTORICAL_RESIDUAL_PRODUCER_HANDOFF_FORMAT",
    "RESIDUAL_PRODUCER_PROMOTION_GATE_FORMAT",
    "WHEEL_STATE_MACHINE_PROOF_FORMAT",
    "WHEEL_JOB_LOAD_STORE_SURFACE_FORMAT",
    "REMAINING_EXPLICIT_PRODUCERS",
    "build_current_frontier",
    "contract",
]
