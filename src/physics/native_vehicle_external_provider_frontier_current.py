"""Current Process 2 audit overlay for the native vehicle provider frontier.

The Phase 699/708 frontier is intentionally retained as historical coordination
state.  This module overlays only proof states that have changed on the current
Silverstone + BMW bind/world-transform chain.  It does not reinterpret any of
the nine physics-provider semantics and therefore cannot turn a provider into
``implement_now`` merely because the bind path advanced.
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

    The overlay consumes only already-merged proof milestones.  The remaining
    transform blocker is narrowed to the exact outer Vehicle -> canonical BMW
    VHF root relation and the final positive bind proof derived from it.
    Physics-provider rows stay unchanged until a provider-specific producer or
    ownership proof is positive.
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
    report["deepest_native_chain"] = (
        "persistent retail BODY0 state -> fail-closed BODY0/VHF composition -> "
        "transactional fresh vehicle world-transform publication -> Process 3 live Vulkan sink; "
        "exact outer Vehicle/VHF root relation remains the transform-semantic blocker"
    )

    joins = {row["id"]: row for row in report["cross_chain_joins"]}
    transform = joins["body_pose_to_renderer_world_transform"]
    transform.update(
        {
            "state": "renderer_sink_ready_outer_vehicle_vhf_relation_pending",
            "process2_action": REQUEST_PROCESS1,
            "evidence": [
                "Process 1 PR #1265 proves the BMW construction origin/basis writer target is persistent chassis BODY0 via SHIFT.BMWBody0ConstructionTargetIdentity/1",
                "Process 1 PR #1268 admits exact BMW BODY0 resource values and exact BODY0-local -> SDF-model bind pose",
                "Process 1 PR #1277 binds the target Silverstone+BMW session and makes BODY0 -> outer Vehicle root numeric relation positive via SHIFT.BMWOffset33bNativeSessionSelection/1",
                "Process 1 PR #1315 proves canonical vehicles/bmw_m3_e36/bmw_m3_e36.vhf identity via SHIFT.BMWVehicleRenderModelResourceJoin/1",
                "Process 1 PR #1317 proves the outer Vehicle -> render snapshot affine bridge",
                "Process 1 PR #1322 provides exact FUN_00795d60 render-root delta value provenance",
                "Process 1 PR #1323 proves the exact canonical BMW VHF HIERARCHY Root frame, MatrixNumber, parent chain and affine matrices",
                "Process 2 PR #1326 consumes that exact VHF root frame through SHIFT.Process2BMWVHFHierarchyRootFrameStage/1",
                "Phases 704-706 keep composition, runtime handoff and transactional freshness fail-closed until final bind proof",
                "Process 3 Phase 649 keeps the live Vulkan sink freshness-gated",
            ],
            "blockers": [
                "positive source-backed outer Vehicle root -> exact canonical BMW VHF HIERARCHY root identity/fixed-affine relation is not committed",
                "positive SHIFT.BMWBody0BindFrameProof/1 derived from that relation is not committed",
            ],
            "additional_dependency": (
                "none on renderer transport; retail scheduler/cadence is a separate explicit authority gate "
                "under SHIFT.Process2RuntimeSchedulerAuthority/1"
            ),
            "policy": (
                "consume the next positive outer Vehicle/VHF relation immediately; do not reopen BODY0 construction/resource/session proofs, "
                "guess an affine relation, promote an identity-valued VHF root matrix, bypass final bind admission, or reuse host 1/60 as retail cadence"
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
        "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
        "BODY0_bind_frame_proof_ready": False,
        "vehicle_world_transform_ready": False,
    }

    report["provider_audit"] = {
        "provider_inventory_reused_from": LEGACY_FORMAT,
        "provider_inventory_changed": False,
        "newly_positive_provider_or_owner_handoff_internalizable": False,
        "reason": (
            "latest merged positive proofs advance BODY0/bind/render-frame identity and transport, "
            "but do not close any remaining provider-specific producer/ownership blocker"
        ),
        "fun_007682c0_runtime_body0_mutation_internalized": True,
        "fun_007682c0_exact_source_destination_receiver_proven": False,
        "semantic_source_receiver_must_not_be_inferred_from_runtime_body0_choice": True,
        "implement_now": [],
    }

    report["scheduler_authority"] = {
        "contract": SCHEDULER_FORMAT,
        "authority_explicit": True,
        "retail_cadence_admitted": False,
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
            "outer_vehicle_to_vhf_root_relation_ready": False,
            "body0_bind_frame_proof_ready": False,
            "retail_vehicle_world_transform_ready": False,
            "scheduler_authority_explicit": True,
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
        "outer_vehicle_to_vhf_root_relation_ready": False,
        "BODY0_bind_frame_proof_ready": False,
        "retail_vehicle_world_transform_ready": False,
        "scheduler_authority_contract": SCHEDULER_FORMAT,
        "host_1_60_is_retail_evidence": False,
    }


__all__ = ["FORMAT", "SCHEDULER_FORMAT", "ROOT_STAGE_FORMAT", "build_current_frontier", "contract"]
