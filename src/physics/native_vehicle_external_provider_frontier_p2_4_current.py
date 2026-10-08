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
EXTERNAL_PASS_RESULT_FORMAT = "SHIFT.Fun00765c40ExternalPassResult/4"
NATIVE_SELECTED_QUERY_INPUT_FORMAT = "SHIFT.Fun00765c40NativeSelectedQueryInput/1"
SESSION_QUERY_SNAPSHOT_FORMAT = "SHIFT.Fun00765c40SessionQuerySnapshot/1"
SELECTED_WORLD_POSITION_FORMAT = "SHIFT.Fun00765c40SelectedBMWWorldPosition/1"
SELECTED_QUERY_FALLBACK_FORMAT = "SHIFT.Fun00765c40SelectedBMWQueryFallback/1"
COLLISION_OUTPUT_HANDOFF_FORMAT = "SHIFT.Fun00765c40CollisionOutputHandoff/1"
COMPOSED_RESIDUAL_EXECUTOR_FORMAT = "SHIFT.Fun00765c40ComposedResidualExecutor/1"
WHEEL_STATE_MACHINE_PROOF_FORMAT = "SHIFT.Fun00752fa0WheelStateMachineProof/1"

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
            "native_selected_query_input_contract": NATIVE_SELECTED_QUERY_INPUT_FORMAT,
            "session_query_snapshot_contract": SESSION_QUERY_SNAPSHOT_FORMAT,
            "selected_world_position_contract": SELECTED_WORLD_POSITION_FORMAT,
            "selected_query_fallback_contract": SELECTED_QUERY_FALLBACK_FORMAT,
            "collision_output_handoff_contract": COLLISION_OUTPUT_HANDOFF_FORMAT,
            "composed_residual_executor_contract": COMPOSED_RESIDUAL_EXECUTOR_FORMAT,
            "wheel_state_machine_proof_contract": WHEEL_STATE_MACHINE_PROOF_FORMAT,
            "wheel_state_source_address": "HDVehicle+0x98",
            "wheel_state_source_address_proven": True,
            "wheel_state_source_owner_lifetime_native": False,
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
            "external_provider_count_decremented": False,
            "lower_collision_semantics_invented": False,
            "unproven_producer_formula_invented": False,
            "wheel_state_source_owner_inferred_from_address": False,
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
        "native_selected_query_input_contract": fun["native_selected_query_input_contract"],
        "session_query_snapshot_contract": fun["session_query_snapshot_contract"],
        "collision_output_handoff_contract": fun["collision_output_handoff_contract"],
        "composed_residual_executor_contract": fun["composed_residual_executor_contract"],
        "wheel_state_machine_proof_contract": fun["wheel_state_machine_proof_contract"],
        "wheel_state_source_address": fun["wheel_state_source_address"],
        "wheel_state_source_address_proven": fun["wheel_state_source_address_proven"],
        "wheel_state_source_owner_lifetime_native": fun[
            "wheel_state_source_owner_lifetime_native"
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
    "NATIVE_SELECTED_QUERY_INPUT_FORMAT",
    "SESSION_QUERY_SNAPSHOT_FORMAT",
    "SELECTED_WORLD_POSITION_FORMAT",
    "SELECTED_QUERY_FALLBACK_FORMAT",
    "COLLISION_OUTPUT_HANDOFF_FORMAT",
    "COMPOSED_RESIDUAL_EXECUTOR_FORMAT",
    "WHEEL_STATE_MACHINE_PROOF_FORMAT",
    "REMAINING_EXPLICIT_PRODUCERS",
    "build_current_frontier",
    "contract",
]
