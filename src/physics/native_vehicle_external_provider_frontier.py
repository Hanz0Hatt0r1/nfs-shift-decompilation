"""Machine-readable frontier for external providers in the deepest native vehicle chain.

Phase 699 is coordination infrastructure, not a physics implementation. This
Phase 708 refresh consumes Process 1 PRs #1208 and #1210, Process 2 Phase 707,
and Process 3 Phases 647-649. It removes already-closed BODY-owner identity and
renderer-transport blockers without promoting any still-unproven physics
producer, BODY0 bind witness, or retail cadence owner.
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
                "Process 1 PR #1208 commits positive SHIFT.GlobalVehicleBodyOwnerIdentity/1 for retail BMW chassis BODY 0",
                "Phase 707 exposes SHIFT.NativeRetailGlobalVehicleBodyOwnerIdentity/1 and removes caller-injected identity from the retail transform path",
            ],
            blockers=[
                "the exact BODY pointer/record receiving the FUN_007682c0 +0x50 application is not yet proven to be the retail BMW chassis BODY 0 record",
            ],
            requested_proof=[
                "prove exact FUN_007682c0 accumulator destination pointer/record provenance at the application site and join that destination to the proven retail BODY 0 identity",
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
                "Process 1 PR #1208 closes FUN_00765470 BODY-owner receiver provenance inside positive SHIFT.GlobalVehicleBodyOwnerIdentity/1",
                "Phase 707 consumes that positive retail identity without changing producer refresh scheduling",
            ],
            blockers=[
                "producer field ownership and exact refresh schedule remain unproven",
                "reuse versus recomputation between half-steps is not proven",
            ],
            requested_proof=[
                "prove retail producer/source order for every composite-provider field",
                "prove whether each producer refreshes before pass 0, pass 1, both, or another exact boundary",
            ],
        ),
    ]

    closed = [
        {"boundary": "FUN_007675f0 arithmetic", "state": "native_in_deepest_chain", "phase": 693},
        {"boundary": "FUN_007682c0 broad arbitrary callback", "state": "replaced_by_typed_effect_provider_consumer", "phase": 696},
        {"boundary": "persistent BODY bytes across explicit outer updates", "state": "runtime_owned_persistent", "phase": 697},
        {"boundary": "persistent BODY origin/basis decode", "state": "runtime_owned_typed_snapshots", "phase": 695},
        {"boundary": "BODY-index -> persistent pose selector", "state": "fail_closed_infrastructure_ready", "phase": 698},
        {"boundary": "NativeRuntimeState -> selected BODY pose handoff", "state": "read_only_transport_ready", "phase": 700},
        {
            "boundary": "BMW main/chassis BODY semantic identity",
            "state": "process1_structurally_proven",
            "proof": "SHIFT.BMWChassisBodyIdentityFrontier/1",
            "selected_BODY_index": 0,
        },
        {
            "boundary": "global vehicle/BODY-owner identity composition contract",
            "state": "retail_proven",
            "proof": "SHIFT.GlobalVehicleBodyOwnerIdentity/1 / Process 1 PR #1208",
            "selected_BODY_index": 0,
            "retail_identity_ready": True,
            "global_vehicle_address": "0x00c13700",
            "BODY_owner_pointer_field_offset": "0x339c",
            "BODY_array_owner_is_global_vehicle_base": False,
            "update_child_pointer_equality_required": False,
        },
        {
            "boundary": "native composed BODY-owner identity consumer",
            "state": "phase703_positive_retail_consumer_ready",
            "phase": 703,
            "proof": "SHIFT.NativeGlobalVehicleBodyOwnerSelection/1",
            "retail_identity_ready": True,
            "selected_BODY_index": 0,
        },
        {
            "boundary": "native retail BODY-owner identity producer",
            "state": "phase707_retail_producer_ready",
            "phase": 707,
            "proof": "SHIFT.NativeRetailGlobalVehicleBodyOwnerIdentity/1",
            "retail_identity_ready": True,
            "selected_BODY_index": 0,
            "caller_injected_identity_required": False,
        },
        {
            "boundary": "BODY0/VHF bind-frame composition contract",
            "state": "composition_formula_proven_bind_witness_pending",
            "proof": "SHIFT.BMWBody0VHFBindFrameFrontier/1 / Process 1 PR #1199",
            "BODY0_bind_frame_proven": False,
        },
        {
            "boundary": "BODY0 bind initialization static frontier",
            "state": "bounded_static_worklist_ready_bind_matrix_pending",
            "proof": "SHIFT.BMWBody0BindInitializationFrontier/1 / Process 1 PR #1200",
            "BODY0_bind_matrix_proven": False,
        },
        {
            "boundary": "BODY0 bind pose-writer physical ABI",
            "state": "physical_abi_ready_semantic_roles_pending",
            "proof": "SHIFT.BMWBody0BindPoseWriterABI/1 / Process 1 PR #1210",
            "BODY0_pointer_proven": False,
            "BODY0_bind_origin_proven": False,
            "BODY0_bind_basis_proven": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        {
            "boundary": "native BODY0/VHF world-matrix composition",
            "state": "phase704_fail_closed_composition_ready",
            "phase": 704,
            "proof": "SHIFT.NativeBMWBody0VHFWorldMatrixComposition/1",
            "current_retail_world_matrix_ready": False,
        },
        {
            "boundary": "NativeRuntimeState -> BMW vehicle world-matrix handoff",
            "state": "phase705_retail_identity_ready_bind_witness_pending",
            "phase": 705,
            "proof": "SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1",
            "current_retail_identity_ready": True,
            "current_retail_world_matrix_ready": False,
        },
        {
            "boundary": "persistent BMW vehicle world transform",
            "state": "phase706_transactional_freshness_checked_state_ready",
            "phase": 706,
            "proof": "SHIFT.PersistentBMWVehicleWorldTransform/1",
            "current_retail_identity_ready": True,
            "current_retail_world_matrix_ready": False,
        },
        {
            "boundary": "resource-driven Silverstone+BMW playable scene bootstrap",
            "state": "process3_one_command_bootstrap_ready",
            "phase": 644,
            "proof": "SHIFT.NativePlayableSceneBootstrap/1 / Process 3 PR #1191",
        },
        {
            "boundary": "canonical BMW VHF static bind transform",
            "state": "process3_static_bind_transform_ready_not_dynamic_pose",
            "phase": 645,
            "proof": "SHIFT.BMWVHFBodyWorldTransform/1",
        },
        {
            "boundary": "dynamic vehicle world-transform transport core",
            "state": "process3_transport_core_ready",
            "phase": 646,
            "proof": "SHIFT.NativeVehicleWorldTransformScript/1 + native transform core / Process 3 PR #1197",
        },
        {
            "boundary": "live vehicle Vulkan vertex upload",
            "state": "process3_real_vulkan_upload_ready",
            "phase": 647,
            "proof": "SHIFT.LiveVehicleVertexBufferUpload/1 / Process 3 PR #1207",
        },
        {
            "boundary": "shift_runtime vehicle Vulkan frame wiring",
            "state": "process3_explicit_regression_transport_ready",
            "phase": 648,
            "proof": "Process 3 Phase 648 runtime vehicle Vulkan wiring",
            "retail_transform_producer_claimed": False,
        },
        {
            "boundary": "persistent Phase706 transform -> live Vulkan upload",
            "state": "process3_freshness_gated_renderer_sink_ready",
            "phase": 649,
            "proof": "SHIFT.PersistentVehicleVulkanUpload/1",
            "stale_transform_rejected_before_gpu_access": True,
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
            "state": "retail_proven_and_consumed",
            "process2_action": "closed",
            "evidence": [
                "Process 1 PR #1208 commits positive SHIFT.GlobalVehicleBodyOwnerIdentity/1",
                "global vehicle base 0x00c13700 loads the BODY-array owner pointer from +0x339c without asserting owner==base",
                "retail BMW chassis BODY 0 is selected and Phase 698/700 admission is positive",
                "Phase 707 exposes the native retail producer and removes caller-injected identity from the Phase 705/706 retail wrappers",
            ],
            "blockers": [],
            "policy": "reuse Phase 707/703/698/700; do not reintroduce update-child pointer equality or collapse BODY owner pointer into the global vehicle base",
        },
        {
            "id": "body_pose_to_renderer_world_transform",
            "state": "renderer_sink_ready_retail_bind_witness_pending",
            "process2_action": REQUEST_PROCESS1,
            "evidence": [
                "Process 1 PR #1199 proves exact row-vector composition M_vhf_bind * inverse(M_BODY0_bind) * M_BODY0_runtime",
                "Process 1 PR #1200 narrows BODY0 bind initialization to a finite static caller/callsite worklist",
                "Process 1 PR #1210 proves the physical FUN_007b7840 pose-writer ABI while keeping BODY0 pointer/origin/basis semantics unresolved",
                "Phase 707 makes the retail BODY0 identity input positive",
                "Phases 704-706 implement composition, runtime handoff and persistent freshness checks",
                "Process 3 Phases 647-649 provide the live Vulkan upload and freshness-gated renderer sink",
            ],
            "blockers": [
                "positive SHIFT.BMWBody0BindFrameProof/1 with source-backed BODY0 pointer, bind origin and bind basis semantics is not committed",
            ],
            "additional_dependency": "none on renderer transport: Phase 649 already consumes a current Phase 706 matrix; the remaining transform dependency is semantic BODY0 bind proof plus an explicit proven commit schedule",
            "policy": "do not synthesize the BODY0 bind matrix, infer pose-writer parameter semantics from physical ABI alone, or bypass Phase 704-706/649 freshness gates",
        },
        {
            "id": "retail_resource_to_initial_body_state",
            "state": "static_frontier_available",
            "process2_action": REQUEST_PROCESS1,
            "blockers": [
                "retail vehicle physics resources -> concrete initial 0x170 BODY records are not proven end-to-end"
            ],
            "additional_dependency": "Process 3 can select/compose BMW resources, but concrete physics BODY initialization remains a separate producer proof",
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
        "refresh_after_phase": 707,
        "refresh_label": "Process 2 Phase 708 coordination refresh",
        "deepest_native_chain": "Phase 697 persistent FUN_00770e80 outer-update path wrapped by Phase 701 persistent provider session; Phase 707 supplies retail BODY0 identity, Phase 706 persists admitted world transforms, and Process 3 Phase 649 is the live freshness-gated Vulkan sink",
        "external_provider_count": len(providers),
        "providers": providers,
        "action_counts": action_counts,
        "implement_now": [row["id"] for row in providers if row["process2_action"] == IMPLEMENT_NOW],
        "process1_handoff_requests": [row["id"] for row in providers if row["process2_action"] == REQUEST_PROCESS1],
        "runtime_only_blocked": [row["id"] for row in providers if row["process2_action"] == RUNTIME_ONLY_BLOCKED],
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
            "update_child_pointer_equality_required": False,
            "retail_body_owner_identity_ready": True,
            "retail_identity_injected_by_caller": False,
            "body_pose_to_vehicle_transform_promotion_allowed": False,
            "phase645_static_bind_transform_is_dynamic_pose": False,
            "phase646_transport_core_is_body_frame_proof": False,
            "phase704_composition_contract_is_retail_bind_proof": False,
            "phase706_persistent_transform_is_renderer_mutation": False,
            "phase649_renderer_sink_ready": True,
            "phase649_renderer_sink_is_retail_transform_producer": False,
            "body0_pose_writer_physical_abi_implies_semantic_bind_roles": False,
            "original_game_execution_required": False,
            "new_runtime_capture_required": False,
        },
    }


__all__ = ["FORMAT", "IMPLEMENT_NOW", "REQUEST_PROCESS1", "RUNTIME_ONLY_BLOCKED", "build_frontier"]
