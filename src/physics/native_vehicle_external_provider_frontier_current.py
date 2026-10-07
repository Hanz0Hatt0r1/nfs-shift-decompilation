"""Current single-process audit for the deepest native vehicle provider frontier.

The Phase 699 nine-provider table remains immutable coordination history. This
module consumes later positive proofs and describes the executable frontier used
by the current Silverstone + BMW slice.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .native_vehicle_external_provider_frontier import (
    FORMAT as LEGACY_FORMAT,
    IMPLEMENT_NOW,
    REQUEST_PROCESS1,
    RUNTIME_ONLY_BLOCKED,
    build_frontier as build_legacy_frontier,
)

FORMAT = "SHIFT.NativeVehicleExternalProviderFrontierCurrent/1"
SCHEDULER_FORMAT = "SHIFT.Process2RuntimeSchedulerAuthority/1"
ROOT_STAGE_FORMAT = "SHIFT.Process2BMWVHFHierarchyRootFrameStage/1"
OUTER_VHF_NUMERIC_FORMAT = "SHIFT.BMWOuterVHFNumericRelation/1"
BIND_PROOF_FORMAT = "SHIFT.BMWBody0BindFrameProof/1"
WORLD_TRANSFORM_WIRING_FORMAT = "SHIFT.BMWPersistentWorldTransformRuntimeWiring/1"
SELECTED_RATE_FORMAT = "SHIFT.SelectedSessionPhysicsTweakerRate/1"
SELECTED_EXECUTION_FORMAT = "SHIFT.SelectedSessionRetailVehicleExecution/1"
SELECTED_RACE_MODE_FORMAT = "SHIFT.BMWOffset33bNativeSessionSelection/1"
FUN_007682C0_DESTINATION_FORMAT = "SHIFT.Fun007682c0Body0DeltaDestination/1"
FUN_007682C0_EFFECT_FORMAT = "SHIFT.Fun007682c0MachineEffectProduction/1"
FUN_007682C0_PROJECTION_FORMAT = "SHIFT.Fun007682c0DerivedProjectionState/1"
FUN_007594E0_ANGLE_FORMAT = "SHIFT.Fun007594e0MachineAngle/1"
BMW_RESPONSE_4054_FORMAT = "SHIFT.BMWM3E36ResponseField4054/1"
FUN_00765C40_LOAD_TERMS_FORMAT = "SHIFT.Fun00765c40LoadTerms/1"
FUN_007560C0_GATE_SETUP_FORMAT = "SHIFT.Fun007560c0MotionReadGateSetup/1"
DAT_00C128CC_DIFFICULTY_FORMAT = "SHIFT.DAT00c128ccPlayerDifficultyOwnership/1"
SELECTED_RATE_HZ = 180
SELECTED_PLAYER_DIFFICULTY = 1
SELECTED_NORMAL_OUTER_SUBSTEPS = 6

_EXPECTED_LEGACY_PROVIDER_IDS = (
    "fun_00765c40_complete_anchor",
    "fun_00758b50_wheel_update",
    "fun_00766510_contact_response",
    "fun_007675f0_input_provider",
    "fun_007682c0_effect_provider",
    "fun_007682c0_delta_consumer",
    "fun_007afdd0_scalar_provider",
    "fun_007b8810_post_half_step",
    "fun_00765470_half_step_refresh_bundle",
)
_CLOSED_DELTA_ID = "fun_007682c0_delta_consumer"
_CLOSED_EFFECT_ID = "fun_007682c0_effect_provider"
_HISTORICAL_RAW_INPUT_ID = "fun_007682c0_machine_input_provider"
_CONTACT_FACTOR_ID = "fun_00765c40_complete_anchor"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _build_active_providers(legacy_providers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Phase 724 closes both legacy FUN_007682c0 top-level boundaries. The effect
    # arithmetic/destination are native and every raw machine input now has an
    # earlier proven owner, so no synthetic replacement raw-input provider remains.
    active = [
        deepcopy(row)
        for row in legacy_providers
        if row.get("id") not in {_CLOSED_DELTA_ID, _CLOSED_EFFECT_ID}
    ]

    contact = next(row for row in active if row.get("id") == _CONTACT_FACTOR_ID)
    contact.update(
        {
            "current_api": "NativeVehicleContactFactorProvider / Fun00765c40LoadTerms",
            "boundary_kind": "typed_output_provider_complete_anchor_external",
            "evidence_state": "complete_anchor_external_load_term_output_ownership_proven",
        }
    )
    contact["evidence"].extend(
        [
            f"{FUN_00765C40_LOAD_TERMS_FORMAT} proves the four HDVehicle load terms are wheel+0x738 outputs owned by FUN_00765c40",
            "Phase 722 preserves complete FUN_00765c40 as external while typing its per-pass four-value output for the later FUN_00769ef0 read",
        ]
    )
    contact["process1_requested_proof"].append(
        "preserve the proven four-value load-term output contract while closing residual FUN_00765c40 contact/collision work"
    )
    _require(len(active) == 7, "current provider count drift")
    return active


def build_current_frontier() -> dict[str, Any]:
    legacy = build_legacy_frontier()
    _require(legacy.get("format") == LEGACY_FORMAT, "legacy provider frontier format drift")
    legacy_providers = legacy.get("providers")
    _require(isinstance(legacy_providers, list), "legacy provider list missing")
    ids = tuple(str(row.get("id")) for row in legacy_providers)
    _require(ids == _EXPECTED_LEGACY_PROVIDER_IDS, "legacy provider inventory drift")
    _require(
        all(row.get("process2_action") == REQUEST_PROCESS1 for row in legacy_providers),
        "legacy provider proof state changed; current audit must be re-adjudicated",
    )

    active = _build_active_providers(legacy_providers)
    closed_delta = next(row for row in legacy_providers if row["id"] == _CLOSED_DELTA_ID)
    closed_effect = next(row for row in legacy_providers if row["id"] == _CLOSED_EFFECT_ID)

    report = deepcopy(legacy)
    report.update(
        {
            "format": FORMAT,
            "version": 1,
            "upstream_frontier": LEGACY_FORMAT,
            "refresh_after_phase": 724,
            "refresh_label": "S6 DAT_00c128cc RaceModeInfo Player Difficulty ownership closure",
            "scheduler_refresh": (
                "positive retail outer cadence + exact selected-session 180 Hz rate + "
                "selected native RaceModeInfo Player Difficulty policy"
            ),
            "transform_refresh": (
                "positive exact outer->VHF numeric relation + positive BODY0 bind proof + "
                "freshness-gated persistent BMW world-transform runtime wiring"
            ),
            "provider_refresh": (
                "all FUN_007682c0 effect inputs now have explicit earlier owners: FUN_007560c0 setup gate, "
                "FUN_007594e0 steering, FUN_00765c40 load outputs, selected-BMW +0x4054, previous-outer "
                "projection state, and RaceModeInfo+0x6c Player Difficulty published to DAT_00c128cc; "
                "the late raw-input provider is removed"
            ),
            "deepest_native_chain": (
                "external FUN_00765c40 contact work + typed four-wheel load output -> session-owned FUN_007560c0 "
                "gate setup + session-owned RaceModeInfo Player Difficulty + current-BODY0 FUN_007594e0 steering + "
                "selected-BMW setup +0x4054 + previous-outer projection state -> native PC FUN_007682c0 machine "
                "effect -> persistent BMW BODY0 +0x50 application -> half-step BODY integration -> post-outer "
                "projection refresh -> positive BODY0/VHF bind -> fresh BMW world transform -> live Vulkan sink; "
                "seven top-level provider boundaries remain external"
            ),
            "providers": active,
            "external_provider_count": len(active),
        }
    )
    report["action_counts"] = {
        IMPLEMENT_NOW: sum(row["process2_action"] == IMPLEMENT_NOW for row in active),
        REQUEST_PROCESS1: sum(row["process2_action"] == REQUEST_PROCESS1 for row in active),
        RUNTIME_ONLY_BLOCKED: sum(row["process2_action"] == RUNTIME_ONLY_BLOCKED for row in active),
    }
    report["implement_now"] = [row["id"] for row in active if row["process2_action"] == IMPLEMENT_NOW]
    report["process1_handoff_requests"] = [
        row["id"] for row in active if row["process2_action"] == REQUEST_PROCESS1
    ]
    report["runtime_only_blocked"] = [
        row["id"] for row in active if row["process2_action"] == RUNTIME_ONLY_BLOCKED
    ]

    report["closed_boundaries"].extend(
        [
            {
                "boundary": closed_delta["retail_boundary"],
                "provider_id": _CLOSED_DELTA_ID,
                "state": "retail_pc_source_proven_and_native_consumed",
                "proof": FUN_007682C0_DESTINATION_FORMAT,
                "destination": "BMW chassis BODY0 +0x50",
                "legacy_api": closed_delta["current_api"],
                "active_external_provider_required": False,
            },
            {
                "boundary": closed_effect["retail_boundary"],
                "provider_id": _CLOSED_EFFECT_ID,
                "state": "retail_pc_machine_arithmetic_and_all_inputs_owned",
                "proof": FUN_007682C0_EFFECT_FORMAT,
                "historical_narrowed_boundary": _HISTORICAL_RAW_INPUT_ID,
                "active_precomputed_effect_provider_required": False,
                "active_late_raw_input_provider_required": False,
            },
            {
                "boundary": "HDVehicle+0x4084/+0x408c FUN_007682c0 projection inputs",
                "state": "retail_pc_derived_persistent_state_native",
                "proof": FUN_007682C0_PROJECTION_FORMAT,
                "active_external_provider_required": False,
            },
            {
                "boundary": "HDVehicle+0x4068 FUN_007682c0 steering input",
                "state": "retail_pc_body0_machine_angle_native",
                "proof": FUN_007594E0_ANGLE_FORMAT,
                "active_external_provider_required": False,
            },
            {
                "boundary": "HDVehicle+0x4054 FUN_007595d0 response input",
                "state": "selected_bmw_setup_fixed_native",
                "proof": BMW_RESPONSE_4054_FORMAT,
                "active_external_provider_required": False,
            },
            {
                "boundary": "HDVehicle+0xb38/+0x15b8/+0x2038/+0x2ab8 late motion-read ownership",
                "state": "retail_pc_owner_reassigned_to_existing_external_fun_00765c40",
                "proof": FUN_00765C40_LOAD_TERMS_FORMAT,
                "active_late_motion_read_provider_required": False,
                "active_FUN_00765c40_provider_required": True,
            },
            {
                "boundary": "HDVehicle+0xe0 FUN_007682c0 caller gate",
                "state": "retail_pc_vehicle_setup_ownership_proven_selected_value_explicit",
                "proof": FUN_007560C0_GATE_SETUP_FORMAT,
                "active_late_motion_read_provider_required": False,
                "session_setup_state_required": True,
                "selected_setup_value_derived_natively": False,
            },
            {
                "boundary": "DAT_00c128cc FUN_007682c0 angle mode",
                "state": "retail_pc_race_mode_owner_proven_selected_native_session_bound",
                "proof": DAT_00C128CC_DIFFICULTY_FORMAT,
                "selected_session_contract": SELECTED_RACE_MODE_FORMAT,
                "race_mode_field": "RaceModeInfo+0x6c Player Difficulty",
                "selected_player_difficulty": SELECTED_PLAYER_DIFFICULTY,
                "active_late_motion_read_provider_required": False,
                "retail_live_session_selector_inferred": False,
            },
        ]
    )

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    transform = joins["body_pose_to_renderer_world_transform"]
    transform.update(
        {
            "state": "retail_proven_and_consumed",
            "process2_action": "closed",
            "evidence": [
                "SHIFT.BMWOuterVHFNumericRelation/1 is positive for the selected Silverstone+BMW chain",
                "SHIFT.BMWBody0BindFrameProof/1 publishes the exact BODY0-local -> VHF root relation",
                "SHIFT.BMWPersistentWorldTransformRuntimeWiring/1 publishes fresh current transforms",
            ],
            "blockers": [],
            "additional_dependency": (
                "none for FUN_007682c0 raw-input ownership; remaining external work is in the seven upstream provider boundaries"
            ),
            "policy": "do not reopen positive transform/timing/FUN_007682c0 ownership work",
        }
    )

    report["current_bind_path"] = {
        "BODY0_construction_target_identity_ready": True,
        "BODY0_resource_values_ready": True,
        "BODY0_local_to_SDF_model_bind_pose_ready": True,
        "BODY0_to_outer_vehicle_root_numeric_matrix_ready": True,
        "canonical_BMW_VHF_resource_identity_ready": True,
        "canonical_BMW_VHF_hierarchy_root_frame_ready": True,
        "process2_exact_vhf_root_frame_stage_consumed": True,
        "process2_exact_vhf_root_frame_stage_contract": ROOT_STAGE_FORMAT,
        "outer_vehicle_root_to_VHF_numeric_contract": OUTER_VHF_NUMERIC_FORMAT,
        "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
        "BODY0_bind_frame_contract": BIND_PROOF_FORMAT,
        "BODY0_bind_frame_proof_ready": True,
        "persistent_world_transform_wiring_contract": WORLD_TRANSFORM_WIRING_FORMAT,
        "vehicle_world_transform_ready": True,
        "FUN_007682c0_delta_destination_contract": FUN_007682C0_DESTINATION_FORMAT,
        "FUN_007682c0_delta_destination_is_BODY0": True,
        "FUN_007682c0_machine_effect_contract": FUN_007682C0_EFFECT_FORMAT,
        "FUN_007682c0_effect_production_internal": True,
        "FUN_007682c0_projection_state_contract": FUN_007682C0_PROJECTION_FORMAT,
        "FUN_007682c0_projection_state_internal": True,
        "FUN_007594e0_machine_angle_contract": FUN_007594E0_ANGLE_FORMAT,
        "FUN_007594e0_steering_internal": True,
        "BMW_response_4054_contract": BMW_RESPONSE_4054_FORMAT,
        "BMW_response_4054_internal": True,
        "FUN_00765c40_load_terms_contract": FUN_00765C40_LOAD_TERMS_FORMAT,
        "FUN_00765c40_load_term_ownership_ready": True,
        "FUN_007560c0_gate_setup_contract": FUN_007560C0_GATE_SETUP_FORMAT,
        "FUN_007560c0_gate_setup_owned": True,
        "DAT_00c128cc_player_difficulty_contract": DAT_00C128CC_DIFFICULTY_FORMAT,
        "selected_race_mode_contract": SELECTED_RACE_MODE_FORMAT,
        "selected_player_difficulty": SELECTED_PLAYER_DIFFICULTY,
        "FUN_007682c0_angle_mode_session_owned": True,
    }

    report["provider_audit"] = {
        "provider_inventory_reused_from": LEGACY_FORMAT,
        "legacy_external_provider_count": len(legacy_providers),
        "active_external_provider_count": len(active),
        "provider_inventory_changed": True,
        "closed_provider_ids": [_CLOSED_DELTA_ID, _CLOSED_EFFECT_ID],
        "narrowed_provider_ids": {_CLOSED_EFFECT_ID: _HISTORICAL_RAW_INPUT_ID},
        "historical_narrowed_provider_is_still_active": False,
        "newly_positive_provider_or_owner_handoff_internalizable": True,
        "fun_007682c0_destination_contract": FUN_007682C0_DESTINATION_FORMAT,
        "fun_007682c0_machine_effect_contract": FUN_007682C0_EFFECT_FORMAT,
        "fun_007682c0_projection_state_contract": FUN_007682C0_PROJECTION_FORMAT,
        "fun_007594e0_machine_angle_contract": FUN_007594E0_ANGLE_FORMAT,
        "bmw_response_4054_contract": BMW_RESPONSE_4054_FORMAT,
        "fun_00765c40_load_terms_contract": FUN_00765C40_LOAD_TERMS_FORMAT,
        "fun_007560c0_gate_setup_contract": FUN_007560C0_GATE_SETUP_FORMAT,
        "dat_00c128cc_player_difficulty_contract": DAT_00C128CC_DIFFICULTY_FORMAT,
        "selected_race_mode_contract": SELECTED_RACE_MODE_FORMAT,
        "fun_007682c0_runtime_body0_mutation_internalized": True,
        "fun_007682c0_effect_arithmetic_internalized": True,
        "fun_007682c0_x87_fsqrt_internalized": True,
        "fun_007682c0_projection_fields_internalized": True,
        "fun_007682c0_projection_refresh_after_both_passes": True,
        "fun_007594e0_body0_basis_angle_internalized": True,
        "fun_007594e0_x87_fpatan_internalized": True,
        "fun_007594e0_refresh_before_both_passes": True,
        "fun_007682c0_response_4054_internalized": True,
        "fun_00765c40_load_term_ownership_proven": True,
        "fun_00765c40_load_terms_typed_output": True,
        "fun_00765c40_complete_anchor_external": True,
        "fun_007560c0_gate_setup_ownership_proven": True,
        "fun_007560c0_selected_gate_value_native": False,
        "dat_00c128cc_race_mode_ownership_proven": True,
        "fun_007682c0_angle_mode_session_owned": True,
        "selected_player_difficulty": SELECTED_PLAYER_DIFFICULTY,
        "selected_player_difficulty_is_retail_observation": False,
        "fun_007682c0_external_precomputed_effect_required": False,
        "fun_007682c0_external_delta_consumer_required": False,
        "fun_007682c0_external_projection_fields_required": False,
        "fun_007682c0_external_steering_required": False,
        "fun_007682c0_external_response_4054_required": False,
        "fun_007682c0_external_load_terms_required": False,
        "fun_007682c0_external_gate_required_per_pass": False,
        "fun_007682c0_external_angle_mode_required": False,
        "fun_007682c0_raw_input_refresh_external": False,
        "remaining_fun_007682c0_external_fields": [],
        "implement_now": [],
    }

    report["scheduler_authority"] = {
        "contract": SCHEDULER_FORMAT,
        "selected_rate_contract": SELECTED_RATE_FORMAT,
        "selected_execution_contract": SELECTED_EXECUTION_FORMAT,
        "selected_race_mode_contract": SELECTED_RACE_MODE_FORMAT,
        "authority_explicit": True,
        "retail_cadence_admitted": True,
        "retail_outer_dispatch_transaction_ready": True,
        "loaded_inner_rate_admitted": True,
        "selected_session_rate_hz": SELECTED_RATE_HZ,
        "selected_session_player_difficulty": SELECTED_PLAYER_DIFFICULTY,
        "inner_substep_seconds": 1.0 / SELECTED_RATE_HZ,
        "selected_session_normal_outer_substeps": SELECTED_NORMAL_OUTER_SUBSTEPS,
        "inner_substep_execution_admitted": True,
        "provider_semantics_promoted": False,
        "render_loop_equated_to_outer_dispatch": False,
        "host_development_1_60_is_retail_evidence": False,
    }

    report["guards"].update(
        {
            "outer_vehicle_to_vhf_root_relation_ready": True,
            "body0_bind_frame_proof_ready": True,
            "retail_vehicle_world_transform_ready": True,
            "scheduler_authority_explicit": True,
            "retail_outer_cadence_ready": True,
            "retail_outer_dispatch_transaction_ready": True,
            "loaded_inner_rate_admitted": True,
            "inner_substep_execution_admitted": True,
            "fun_007682c0_body0_delta_destination_ready": True,
            "fun_007682c0_body0_delta_application_internal": True,
            "fun_007682c0_effect_production_ready": True,
            "fun_007682c0_x87_fsqrt_ready": True,
            "fun_007682c0_projection_state_ready": True,
            "fun_007682c0_projection_fields_external": False,
            "fun_007594e0_machine_angle_ready": True,
            "fun_007682c0_steering_external": False,
            "fun_007682c0_response_4054_ready": True,
            "fun_007682c0_response_4054_external": False,
            "fun_00765c40_load_term_ownership_ready": True,
            "fun_007682c0_load_terms_external": False,
            "fun_00765c40_complete_anchor_external": True,
            "fun_007560c0_gate_setup_ownership_ready": True,
            "fun_007682c0_gate_external_per_pass": False,
            "fun_007560c0_selected_gate_value_native": False,
            "dat_00c128cc_player_difficulty_ownership_ready": True,
            "fun_007682c0_angle_mode_external": False,
            "fun_007682c0_raw_input_refresh_ready": True,
            "fun_007682c0_raw_input_provider_required": False,
            "provider_semantics_promoted": False,
            "render_loop_equated_to_outer_dispatch": False,
            "host_1_60_is_retail_evidence": False,
        }
    )

    _require(report["external_provider_count"] == 7, "S6 must leave seven external providers")
    _require(report["action_counts"][IMPLEMENT_NOW] == 0, "audit must not invent implementation work")
    return report


def contract() -> dict[str, Any]:
    report = build_current_frontier()
    return {
        "format": FORMAT,
        "version": 1,
        "upstream_frontier": LEGACY_FORMAT,
        "external_provider_count": report["external_provider_count"],
        "provider_inventory_changed": True,
        "closed_provider_ids": report["provider_audit"]["closed_provider_ids"],
        "narrowed_provider_ids": report["provider_audit"]["narrowed_provider_ids"],
        "FUN_007682c0_delta_destination_contract": FUN_007682C0_DESTINATION_FORMAT,
        "FUN_007682c0_machine_effect_contract": FUN_007682C0_EFFECT_FORMAT,
        "FUN_007682c0_projection_state_contract": FUN_007682C0_PROJECTION_FORMAT,
        "FUN_007594e0_machine_angle_contract": FUN_007594E0_ANGLE_FORMAT,
        "BMW_response_4054_contract": BMW_RESPONSE_4054_FORMAT,
        "FUN_00765c40_load_terms_contract": FUN_00765C40_LOAD_TERMS_FORMAT,
        "FUN_007560c0_gate_setup_contract": FUN_007560C0_GATE_SETUP_FORMAT,
        "DAT_00c128cc_player_difficulty_contract": DAT_00C128CC_DIFFICULTY_FORMAT,
        "selected_race_mode_contract": SELECTED_RACE_MODE_FORMAT,
        "FUN_007682c0_delta_destination_is_BODY0": True,
        "FUN_007682c0_delta_application_internal": True,
        "FUN_007682c0_effect_production_internal": True,
        "FUN_007682c0_x87_fsqrt_internal": True,
        "FUN_007682c0_projection_state_internal": True,
        "FUN_007682c0_external_projection_fields_required": False,
        "FUN_007594e0_steering_internal": True,
        "FUN_007682c0_external_steering_required": False,
        "FUN_007682c0_response_4054_internal": True,
        "FUN_007682c0_external_response_4054_required": False,
        "FUN_00765c40_load_term_ownership_ready": True,
        "FUN_00765c40_load_terms_typed_output": True,
        "FUN_00765c40_complete_anchor_external": True,
        "FUN_007682c0_external_load_terms_required": False,
        "FUN_007560c0_gate_setup_owned": True,
        "FUN_007560c0_selected_gate_value_native": False,
        "FUN_007682c0_external_gate_required_per_pass": False,
        "DAT_00c128cc_player_difficulty_owned": True,
        "selected_session_player_difficulty": SELECTED_PLAYER_DIFFICULTY,
        "selected_player_difficulty_is_retail_observation": False,
        "FUN_007682c0_external_angle_mode_required": False,
        "remaining_FUN_007682c0_external_fields": [],
        "FUN_007682c0_raw_input_refresh_external": False,
        "FUN_007682c0_raw_input_provider_required": False,
        "outer_vehicle_to_vhf_root_relation_ready": True,
        "BODY0_bind_frame_proof_ready": True,
        "retail_vehicle_world_transform_ready": True,
        "scheduler_authority_contract": SCHEDULER_FORMAT,
        "selected_rate_contract": SELECTED_RATE_FORMAT,
        "selected_execution_contract": SELECTED_EXECUTION_FORMAT,
        "retail_outer_cadence_admitted": True,
        "retail_outer_dispatch_transaction_ready": True,
        "loaded_inner_rate_admitted": True,
        "selected_session_rate_hz": SELECTED_RATE_HZ,
        "selected_session_normal_outer_substeps": SELECTED_NORMAL_OUTER_SUBSTEPS,
        "inner_substep_execution_admitted": True,
        "provider_semantics_promoted": False,
        "render_loop_equated_to_outer_dispatch": False,
        "host_1_60_is_retail_evidence": False,
    }


__all__ = [
    "FORMAT",
    "SCHEDULER_FORMAT",
    "ROOT_STAGE_FORMAT",
    "OUTER_VHF_NUMERIC_FORMAT",
    "BIND_PROOF_FORMAT",
    "WORLD_TRANSFORM_WIRING_FORMAT",
    "SELECTED_RATE_FORMAT",
    "SELECTED_EXECUTION_FORMAT",
    "SELECTED_RACE_MODE_FORMAT",
    "FUN_007682C0_DESTINATION_FORMAT",
    "FUN_007682C0_EFFECT_FORMAT",
    "FUN_007682C0_PROJECTION_FORMAT",
    "FUN_007594E0_ANGLE_FORMAT",
    "BMW_RESPONSE_4054_FORMAT",
    "FUN_00765C40_LOAD_TERMS_FORMAT",
    "FUN_007560C0_GATE_SETUP_FORMAT",
    "DAT_00C128CC_DIFFICULTY_FORMAT",
    "SELECTED_RATE_HZ",
    "SELECTED_PLAYER_DIFFICULTY",
    "SELECTED_NORMAL_OUTER_SUBSTEPS",
    "build_current_frontier",
    "contract",
]
