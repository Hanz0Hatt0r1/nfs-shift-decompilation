"""Current Process 2 audit overlay for the native vehicle provider frontier.

The Phase 699/708 frontier is retained as coordination history. This module
overlays proof states that have changed on the current Silverstone + BMW chain.
It does not reinterpret any of the nine physics-provider semantics and therefore
cannot turn a provider into ``implement_now`` merely because bind, render or
scheduler infrastructure advanced.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .native_vehicle_external_provider_frontier import (
    FORMAT as LEGACY_FORMAT,
    IMPLEMENT_NOW,
    REQUEST_PROCESS1,
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
SELECTED_RATE_HZ = 180
SELECTED_NORMAL_OUTER_SUBSTEPS = 6

_EXPECTED_PROVIDER_IDS = (
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


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_current_frontier() -> dict[str, Any]:
    """Return the current fail-closed provider/frontier audit.

    The overlay consumes only already-merged proof milestones. The BODY0 ->
    canonical BMW VHF relation, bind proof and freshness-gated persistent world
    transform are positive. S5 retail outer cadence, the exact hash-verified
    selected-session PhysicsTweaker rate (180 Hz), and the persistent 1/180 BODY
    inner-batch timing path are also positive. Provider rows stay unchanged until
    provider-specific producer or ownership proofs become positive.
    """

    legacy = build_legacy_frontier()
    _require(legacy.get("format") == LEGACY_FORMAT, "legacy provider frontier format drift")
    providers = legacy.get("providers")
    _require(isinstance(providers, list), "legacy provider list missing")
    ids = tuple(str(row.get("id")) for row in providers)
    _require(ids == _EXPECTED_PROVIDER_IDS, "legacy provider inventory drift")
    _require(
        all(row.get("process2_action") == REQUEST_PROCESS1 for row in providers),
        "provider-specific proof state changed; current audit must be re-adjudicated",
    )
    _require(not legacy.get("implement_now"), "legacy frontier unexpectedly exposes implement-now work")

    report = deepcopy(legacy)
    report["format"] = FORMAT
    report["version"] = 1
    report["upstream_frontier"] = LEGACY_FORMAT
    report["refresh_after_phase"] = 716
    report["refresh_label"] = "Process 2 Phase 717 current-chain proof audit"
    report["scheduler_refresh"] = (
        "S5 positive retail outer cadence + atomic explicit dispatch + exact "
        "selected-session 180 Hz rate + exact persistent 1/180 inner execution"
    )
    report["transform_refresh"] = (
        "positive exact outer->VHF numeric relation + positive BODY0 bind proof + "
        "freshness-gated persistent BMW world-transform runtime wiring"
    )
    report["deepest_native_chain"] = (
        "persistent retail BODY0 state -> positive BODY0/VHF bind proof -> "
        "freshness-gated persistent BMW vehicle world-transform publication -> "
        "Process 3 live Vulkan sink; S5 provides positive RetailEvidence outer cadence, "
        "atomic explicit dispatch, exact resource-proven selected-session 180 Hz rate, "
        "and exact persistent 1/180 inner execution, while the nine provider-specific "
        "producer/ownership rows remain blocked"
    )

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    transform = joins["body_pose_to_renderer_world_transform"]
    transform.update(
        {
            "state": "retail_proven_and_consumed",
            "process2_action": "closed",
            "evidence": [
                "SHIFT.BMWOuterVHFNumericRelation/1 is ready for Silverstone+BMW_M3_E36 with exact delta_local=(0,0,0), finite invertible outer Vehicle -> canonical BMW VHF matrix and no runtime capture",
                "SHIFT.BMWBody0BindFrameProof/1 is ready/proven-static and publishes the exact BODY0-local -> VHF-vehicle-root row matrix for chassis BODY0",
                "SHIFT.BMWPersistentWorldTransformRuntimeWiring/1 is ready and commits/publishes a fresh current BMW vehicle world transform from current BODY0 pose after each admitted fixed step",
                "Process 3 Phase 649 remains the freshness-gated live Vulkan consumer",
            ],
            "blockers": [],
            "additional_dependency": (
                "none for BODY0 -> vehicle world-transform transport or selected-session timing; the current shortest independent gate is provider-specific producer/ownership provenance"
            ),
            "policy": (
                "reuse the positive numeric relation, bind proof, persistent freshness-gated runtime wiring and exact selected-session timing; "
                "do not reopen already-proven transform/timing work, do not substitute host 1/60, and do not promote fixture provider callbacks into retail semantics"
            ),
        }
    )

    report["current_bind_path"] = {
        "BODY0_construction_target_identity_ready": True,
        "BODY0_resource_values_ready": True,
        "BODY0_local_to_SDF_model_bind_pose_ready": True,
        "BODY0_to_outer_vehicle_root_numeric_matrix_ready": True,
        "canonical_BMW_VHF_resource_identity_ready": True,
        "outer_vehicle_render_snapshot_affine_bridge_ready": True,
        "outer_vehicle_render_root_delta_value_roots_ready": True,
        "canonical_BMW_VHF_hierarchy_root_frame_ready": True,
        "process2_exact_vhf_root_frame_stage_consumed": True,
        "process2_exact_vhf_root_frame_stage_contract": ROOT_STAGE_FORMAT,
        "outer_vehicle_root_to_VHF_numeric_contract": OUTER_VHF_NUMERIC_FORMAT,
        "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
        "BODY0_bind_frame_contract": BIND_PROOF_FORMAT,
        "BODY0_bind_frame_proof_ready": True,
        "persistent_world_transform_wiring_contract": WORLD_TRANSFORM_WIRING_FORMAT,
        "vehicle_world_transform_ready": True,
    }

    report["provider_audit"] = {
        "provider_inventory_reused_from": LEGACY_FORMAT,
        "provider_inventory_changed": False,
        "newly_positive_provider_or_owner_handoff_internalizable": False,
        "reason": (
            "merged positive proofs close the BODY0/VHF bind, persistent world-transform transport, retail scheduling/rate and exact inner-execution timing gates, "
            "but do not close any remaining provider-specific producer/ownership blocker"
        ),
        "fun_007682c0_runtime_body0_mutation_internalized": True,
        "fun_007682c0_exact_source_destination_receiver_proven": False,
        "semantic_source_receiver_must_not_be_inferred_from_runtime_body0_choice": True,
        "implement_now": [],
    }

    report["scheduler_authority"] = {
        "contract": SCHEDULER_FORMAT,
        "selected_rate_contract": SELECTED_RATE_FORMAT,
        "selected_execution_contract": SELECTED_EXECUTION_FORMAT,
        "authority_explicit": True,
        "retail_cadence_admitted": True,
        "retail_outer_dispatch_transaction_ready": True,
        "loaded_inner_rate_admitted": True,
        "selected_session_rate_hz": SELECTED_RATE_HZ,
        "inner_substep_seconds": 1.0 / SELECTED_RATE_HZ,
        "selected_session_normal_outer_substeps": SELECTED_NORMAL_OUTER_SUBSTEPS,
        "inner_substep_execution_admitted": True,
        "provider_semantics_promoted": False,
        "render_loop_equated_to_outer_dispatch": False,
        "host_development_1_60_is_retail_evidence": False,
    }

    report["guards"].update(
        {
            "body0_construction_target_identity_ready": True,
            "body0_local_to_SDF_bind_ready": True,
            "body0_to_outer_vehicle_root_numeric_ready": True,
            "canonical_bmw_vhf_resource_identity_ready": True,
            "outer_vehicle_render_snapshot_affine_bridge_ready": True,
            "outer_vehicle_render_root_delta_value_roots_ready": True,
            "canonical_bmw_vhf_hierarchy_root_frame_ready": True,
            "process2_exact_vhf_root_frame_stage_consumed": True,
            "outer_vehicle_to_vhf_root_relation_ready": True,
            "body0_bind_frame_proof_ready": True,
            "retail_vehicle_world_transform_ready": True,
            "scheduler_authority_explicit": True,
            "retail_outer_cadence_ready": True,
            "retail_outer_dispatch_transaction_ready": True,
            "loaded_inner_rate_admitted": True,
            "inner_substep_execution_admitted": True,
            "provider_semantics_promoted": False,
            "render_loop_equated_to_outer_dispatch": False,
            "host_1_60_is_retail_evidence": False,
        }
    )

    _require(report["action_counts"][IMPLEMENT_NOW] == 0, "audit must not invent provider implementation work")
    _require(report["implement_now"] == [], "audit must keep provider admission fail-closed")
    return report


def contract() -> dict[str, Any]:
    report = build_current_frontier()
    transform = next(
        row for row in report["cross_chain_joins"] if row["id"] == "body_pose_to_renderer_world_transform"
    )
    return {
        "format": FORMAT,
        "version": 1,
        "upstream_frontier": LEGACY_FORMAT,
        "external_provider_count": report["external_provider_count"],
        "provider_inventory_changed": report["provider_audit"]["provider_inventory_changed"],
        "newly_positive_provider_or_owner_handoff_internalizable": report["provider_audit"][
            "newly_positive_provider_or_owner_handoff_internalizable"
        ],
        "current_transform_state": transform["state"],
        "outer_vehicle_to_vhf_root_relation_ready": True,
        "BODY0_bind_frame_proof_ready": True,
        "retail_vehicle_world_transform_ready": True,
        "outer_vehicle_to_vhf_root_contract": OUTER_VHF_NUMERIC_FORMAT,
        "BODY0_bind_frame_contract": BIND_PROOF_FORMAT,
        "persistent_world_transform_wiring_contract": WORLD_TRANSFORM_WIRING_FORMAT,
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
    "SELECTED_RATE_HZ",
    "SELECTED_NORMAL_OUTER_SUBSTEPS",
    "build_current_frontier",
    "contract",
]
