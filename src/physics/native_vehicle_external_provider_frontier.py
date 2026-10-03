"""Machine-readable frontier for external providers in the deepest native vehicle chain.

Phase 699 is coordination infrastructure, not a physics implementation. It
freezes the providers still injected into the Phase 697 persistent outer-update
path and classifies each boundary using the Process 2 policy:

* already-proven producer -> implement now;
* static frontier available -> request an exact Process 1 proof;
* runtime-only evidence -> remain blocked.

The report deliberately keeps an empty ``implement_now`` set when no additional
producer is proven strongly enough for a native substitution.
"""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.NativeVehicleExternalProviderFrontier/1"
IMPLEMENT_NOW = "implement_now"
REQUEST_PROCESS1 = "request_process1_static_proof"
RUNTIME_ONLY_BLOCKED = "remain_blocked_runtime_only"


def _provider(
    identifier: str,
    *,
    retail_boundary: str,
    current_api: str,
    boundary_kind: str,
    evidence: list[str],
    blockers: list[str],
    requested_proof: list[str],
    additional_dependency: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": identifier,
        "retail_boundary": retail_boundary,
        "current_api": current_api,
        "boundary_kind": boundary_kind,
        "evidence_state": "static_frontier_available",
        "process2_action": REQUEST_PROCESS1,
        "evidence": evidence,
        "blockers": blockers,
        "process1_requested_proof": requested_proof,
    }
    if additional_dependency is not None:
        row["additional_dependency"] = additional_dependency
    return row


def build_frontier() -> dict[str, Any]:
    providers = [
        _provider(
            "fun_00765c40_complete_anchor",
            retail_boundary="FUN_00765c40",
            current_api="Fun0076d100MotionReadEffectProviderCallbacks.contact_factor",
            boundary_kind="generic_callback",
            evidence=[
                "Phases 665-667 provide native factor/query/response subpaths",
                "Phase 693 keeps the complete Phase 684 anchor external",
            ],
            blockers=[
                "complete local work and side-effect ordering are not proven",
                "query world-position production is not proven",
                "collision-provider ownership/execution is not proven",
            ],
            requested_proof=[
                "prove a complete or separable FUN_00765c40 source/machine boundary without dropping residual work",
                "prove exact world-position producer and collision-provider ownership",
            ],
            additional_dependency="Process 3 track/surface resources after collision-provider identity is proven",
        ),
        _provider(
            "fun_00758b50_wheel_update",
            retail_boundary="FUN_00758b50",
            current_api="Fun0076d100MotionReadEffectProviderCallbacks.wheel_update",
            boundary_kind="generic_callback",
            evidence=["Phase 684 freezes this anchor's relative pass order"],
            blockers=[
                "complete caller-visible inputs/writes/nested work are not closed",
                "wheel/control state ownership is not proven",
            ],
            requested_proof=[
                "freeze complete FUN_00758b50 producer inputs, writes and nested calls",
                "prove concrete vehicle/wheel/control-state ownership at the callsite",
            ],
        ),
        _provider(
            "fun_00766510_contact_response",
            retail_boundary="FUN_00766510",
            current_api="Fun0076d100MotionReadEffectProviderCallbacks.contact_response",
            boundary_kind="generic_callback",
            evidence=[
                "Phase 663/371 response arithmetic is native",
                "Phase 667 joins the query scalar into native response arithmetic",
            ],
            blockers=[
                "primary response-vector application into FUN_007baa70 is not frozen",
                "caller state production/ownership is incomplete",
            ],
            requested_proof=[
                "prove the exact primary response application transform and destination ownership",
                "prove all caller-state producers required by this anchor",
            ],
        ),
        _provider(
            "fun_007675f0_input_provider",
            retail_boundary="FUN_007675f0",
            current_api="Fun007675f0ContactOuterInputProvider",
            boundary_kind="typed_input_provider",
            evidence=[
                "Phase 662 native arithmetic",
                "Phase 693/697 execute it inside the persistent composed chain",
            ],
            blockers=["the ten ContactOuterKernelInput field producers remain external"],
            requested_proof=[
                "map every typed input field to exact caller storage/producer operations",
                "prove refresh timing and ownership across both passes",
            ],
        ),
        _provider(
            "fun_007682c0_effect_provider",
            retail_boundary="FUN_007682c0",
            current_api="Fun007682c0EffectProvider",
            boundary_kind="typed_effect_provider",
            evidence=[
                "Phase 380 source/machine arithmetic frontier",
                "Phase 696/697 narrow and persist gate_open plus accumulator delta",
            ],
            blockers=[
                "exact magnitude machine production and x87 boundaries are incomplete",
                "complete FUN_007595d0 producer inputs are incomplete",
            ],
            requested_proof=[
                "prove exact retail magnitude production including x87/store-reload boundaries",
                "prove complete FUN_007595d0 inputs and resulting accumulator delta production",
            ],
        ),
        _provider(
            "fun_007682c0_delta_consumer",
            retail_boundary="FUN_007682c0 BODY +0x50 application",
            current_api="Fun007682c0AccumulatorDeltaConsumer",
            boundary_kind="typed_effect_consumer",
            evidence=[
                "Phase 380 proves the visible BODY +0x50 effect lane",
                "Phase 696 narrows application to one finite scalar delta",
                "Phase 698 provides fail-closed future BODY-index pose selection infrastructure",
                "Process 1 PR #1183 proves nine named BMW BODY field roles and narrows the chassis candidate frontier",
            ],
            blockers=[
                "main/chassis BODY semantic selection is not proven",
                "update-child to vehicle solver-base continuity is not proven",
                "concrete retail selected BODY index remains null",
            ],
            requested_proof=[
                "prove the exact main/chassis SDF BODY row/index from the remaining named topology frontier",
                "prove update-child to vehicle solver-base continuity through FUN_007615c0",
            ],
        ),
        _provider(
            "fun_007afdd0_scalar_provider",
            retail_boundary="FUN_007afdd0 machine scalar production",
            current_api="Fun007afdd0ScalarProvider",
            boundary_kind="typed_scalar_provider",
            evidence=[
                "Phase 691 source-core outer-chain join",
                "Phase 692 static machine-scalar provenance frontier",
            ],
            blockers=[
                "four scalar store-role mapping is incomplete",
                "sqrt/trig return provenance and floating-control state are incomplete",
            ],
            requested_proof=[
                "join all four scalar roles to exact machine stores/returns",
                "prove sqrt/trig return paths plus inherited x87/MXCSR boundaries",
            ],
        ),
        _provider(
            "fun_007b8810_post_half_step",
            retail_boundary="FUN_007b8810",
            current_api="Fun007b8810PostHalfStepCallback",
            boundary_kind="generic_callback",
            evidence=["Phase 683/689 prove its required position after each half-step"],
            blockers=["complete refresh semantics and producer ownership are not proven"],
            requested_proof=[
                "freeze FUN_007b8810 reads/writes/nested producer work",
                "prove which refreshed state feeds the following pass",
            ],
        ),
        _provider(
            "fun_00765470_half_step_refresh_bundle",
            retail_boundary="FUN_00765470 per-half-step producer refresh",
            current_api="Fun00765470MachineScalarHalfStepProvider",
            boundary_kind="typed_composite_provider",
            evidence=[
                "Phases 688/689/691 consume native machine/constraint/solver/projection inputs",
                "each half-step remains independently refreshable",
            ],
            blockers=[
                "retail ownership and refresh schedule are not proven",
                "reuse versus recomputation between half-steps is not proven",
            ],
            requested_proof=[
                "prove retail producer and source order for every composite-provider field",
                "prove whether each producer refreshes before pass 0, pass 1, both, or another exact boundary",
            ],
        ),
    ]

    closed = [
        {"boundary": "FUN_007675f0 arithmetic", "state": "native_in_deepest_chain", "phase": 693},
        {
            "boundary": "FUN_007682c0 broad arbitrary callback",
            "state": "replaced_by_typed_effect_provider_consumer",
            "phase": 696,
        },
        {
            "boundary": "persistent BODY bytes across explicit outer updates",
            "state": "runtime_owned_persistent",
            "phase": 697,
        },
        {
            "boundary": "persistent BODY origin/basis decode",
            "state": "runtime_owned_typed_snapshots",
            "phase": 695,
        },
        {
            "boundary": "proven BODY-index -> persistent pose selection transport",
            "state": "fail_closed_infrastructure_ready",
            "phase": 698,
            "retail_identity_ready": False,
        },
        {
            "boundary": "BMW named BODY field topology",
            "state": "process1_named_roles_ready_chassis_unselected",
            "proof": "SHIFT.VehicleNamedBodyTopologyFrontier/1",
            "selected_BODY_index": None,
        },
        {
            "boundary": "renderer prepared native scene path",
            "state": "process3_resource_side_ready_or_fail_closed",
            "phase": 641,
        },
    ]

    joins = [
        {
            "id": "outer_update_cadence_owner",
            "state": "static_frontier_available",
            "process2_action": REQUEST_PROCESS1,
            "blockers": [
                "source gate is narrowed but exact committed retail machine-callsite mapping remains evidence-gated",
                "dynamic execution multiplicity is not proven",
                "runtime cadence owner is not proven",
            ],
            "policy": "explicit outer update only; fixed_step auto-schedule forbidden",
        },
        {
            "id": "body_to_vehicle_identity",
            "state": "static_frontier_available",
            "process2_action": REQUEST_PROCESS1,
            "blockers": [
                "Process 1 PR #1183 keeps main_chassis_BODY_selected false",
                "selected_BODY_index remains null",
                "update-child -> vehicle solver-base continuity is not proven",
                "vehicle/world transform mapping from selected BODY pose is not proven",
            ],
            "policy": "Phase 698 selector remains fail-closed until exact retail chassis BODY identity is proven",
        },
        {
            "id": "body_pose_to_renderer_object_identity",
            "state": "cross_process_identity_blocked",
            "process2_action": REQUEST_PROCESS1,
            "blockers": ["BODY/vehicle -> prepared scene child identity is not proven"],
            "additional_dependency": "Process 3 Phase 641 renderer/resource side",
            "policy": "do not rewrite SVWT, scene state or camera without identity/mapping proof",
        },
        {
            "id": "retail_resource_to_initial_body_state",
            "state": "static_frontier_available",
            "process2_action": REQUEST_PROCESS1,
            "blockers": [
                "retail vehicle physics resources -> concrete initial 0x170 BODY records are not proven end-to-end"
            ],
            "additional_dependency": "Process 3 vehicle resource graph/bootstrap",
            "policy": "Phase 697 initialization continues to require exact admitted BODY bytes",
        },
    ]

    action_counts = {
        IMPLEMENT_NOW: sum(row["process2_action"] == IMPLEMENT_NOW for row in providers),
        REQUEST_PROCESS1: sum(row["process2_action"] == REQUEST_PROCESS1 for row in providers),
        RUNTIME_ONLY_BLOCKED: sum(row["process2_action"] == RUNTIME_ONLY_BLOCKED for row in providers),
    }

    return {
        "format": FORMAT,
        "version": 1,
        "phase": 699,
        "deepest_native_chain": "Phase 697 persistent FUN_00770e80 outer-update path",
        "external_provider_count": len(providers),
        "providers": providers,
        "action_counts": action_counts,
        "implement_now": [row["id"] for row in providers if row["process2_action"] == IMPLEMENT_NOW],
        "process1_handoff_requests": [
            row["id"] for row in providers if row["process2_action"] == REQUEST_PROCESS1
        ],
        "runtime_only_blocked": [
            row["id"] for row in providers if row["process2_action"] == RUNTIME_ONLY_BLOCKED
        ],
        "closed_boundaries": closed,
        "cross_chain_joins": joins,
        "guards": {
            "two_half_steps_preserved": True,
            "persistent_body_state_preserved": True,
            "participant_admission_preserved": True,
            "missing_provider_fails_closed": True,
            "fixed_step_auto_schedule_allowed": False,
            "host_sqrt_substitution_allowed": False,
            "host_sin_substitution_allowed": False,
            "host_cos_substitution_allowed": False,
            "body_pose_to_vehicle_transform_promotion_allowed": False,
            "original_game_execution_required": False,
            "new_runtime_capture_required": False,
        },
    }


__all__ = [
    "FORMAT",
    "IMPLEMENT_NOW",
    "REQUEST_PROCESS1",
    "RUNTIME_ONLY_BLOCKED",
    "build_frontier",
]
