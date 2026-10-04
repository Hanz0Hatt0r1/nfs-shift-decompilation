"""Machine-readable frontier for the first playable camera-follow source.

This contract composes only already-recovered CameraManager control-flow facts.
It deliberately does not identify any camera source object as the BMW/player
vehicle follow camera. Instead it narrows that remaining proof to the exact
mode-2 source lane and the two source virtual-call boundaries that must be joined
to a proven retail vehicle identity/transform before native camera-follow wiring
can be admitted.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.CameraFollowSourceFrontier/1"
WORLD_HANDOFF_FORMAT = "SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1"
PERSISTENT_TRANSFORM_FORMAT = "SHIFT.PersistentBMWVehicleWorldTransform/1"
REQUEST_PROCESS1 = "request_process1_static_proof"


def _vehicle_transform_state(
    world_handoff: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate only the existing Phase 705 semantic world-matrix contract.

    Freshness remains a separate camera scheduling proof.  Phase 706/649 already
    provide the persistent/freshness-checked renderer transport infrastructure,
    but this frontier must not manufacture a current retail matrix from it while
    Phase 705 still reports the BODY0 bind gate open.
    """
    if world_handoff is None:
        return {
            "evaluated": False,
            "format_valid": False,
            "current_retail_identity_ready": False,
            "current_retail_BODY0_bind_ready": False,
            "current_retail_world_matrix_ready": False,
            "persistent_vulkan_transport_available": False,
            "ready_for_camera_source_join": False,
            "blocking_reasons": [
                "camera-follow:retail-vehicle-world-matrix-handoff-not-supplied"
            ],
        }

    blockers: list[str] = []
    format_valid = world_handoff.get("format") == WORLD_HANDOFF_FORMAT
    if not format_valid:
        blockers.append("camera-follow:vehicle-world-matrix-handoff-invalid-format")

    retail_identity_ready = world_handoff.get("current_retail_identity_ready") is True
    body0_bind_ready = world_handoff.get("current_retail_BODY0_bind_ready") is True
    world_ready = world_handoff.get("current_retail_world_matrix_ready") is True
    persistent_transport_available = (
        world_handoff.get("phase649_persistent_vulkan_upload_available") is True
    )

    if not retail_identity_ready:
        blockers.append("camera-follow:retail-vehicle-identity-not-ready")
    if not body0_bind_ready:
        blockers.append("camera-follow:retail-BODY0-bind-not-ready")
    if not world_ready:
        blockers.append("camera-follow:retail-vehicle-world-matrix-not-ready")
    if not persistent_transport_available:
        blockers.append("camera-follow:persistent-world-transform-transport-not-ready")

    return {
        "evaluated": True,
        "format_valid": format_valid,
        "current_retail_identity_ready": retail_identity_ready,
        "current_retail_BODY0_bind_ready": body0_bind_ready,
        "current_retail_world_matrix_ready": world_ready,
        "persistent_vulkan_transport_available": persistent_transport_available,
        "ready_for_camera_source_join": not blockers,
        "blocking_reasons": blockers,
    }


def build_camera_follow_source_frontier(
    world_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the strongest currently justified camera-follow source frontier."""
    transform_state = _vehicle_transform_state(world_handoff)

    source_lanes = [
        {
            "mode": 1,
            "source": "active_buffer+0x20",
            "activation": "FUN_0080de00 / FUN_0080dfd0",
            "classification": "buffer-selected-view-source",
            "playable_follow_candidate": False,
            "reason": "source-backed static/sub-view selection lane",
        },
        {
            "mode": 2,
            "source": "active_buffer+0x1ca0",
            "source_stride": 0x460,
            "activation": "FUN_0080e0d0",
            "preapply_virtual_call": {
                "offset": 0x90,
                "argument": "runtime_argument",
            },
            "controller_apply": "FUN_0080d300",
            "common_apply_virtual_call": {
                "offset": 0x64,
                "manager_back_reference_offset": 0x44,
            },
            "classification": "tracking-source-lane",
            "playable_follow_candidate": True,
            "candidate_only": True,
            "retail_vehicle_identity_proven": False,
            "vehicle_transform_dependency_proven": False,
        },
        {
            "mode": 3,
            "source": "active_buffer+0x17a0",
            "source_stride": 0x280,
            "activation": "FUN_0080e140",
            "classification": "static-camera-source-lane",
            "playable_follow_candidate": False,
        },
        {
            "mode": 4,
            "source": "caller-supplied external source",
            "activation": "FUN_0080d520",
            "preapply_helper": "FUN_0081b170",
            "classification": "external-source-lane",
            "playable_follow_candidate": False,
            "reason": "caller identity remains external and mode-4 semantics are not vehicle-follow proof",
        },
    ]

    proof_requests = [
        {
            "id": "mode2_runtime_argument_identity",
            "target": "FUN_0080e0d0",
            "request": (
                "trace every retail callsite/runtime_argument producer entering "
                "the mode-2 activation and prove or reject equality/ownership "
                "with the selected retail player vehicle"
            ),
            "required_for_native_follow": True,
        },
        {
            "id": "mode2_source_vtable_identity",
            "target": "active_buffer+0x1ca0 source object",
            "request": (
                "prove the concrete retail vtable/object type installed in the "
                "mode-2 source lane and resolve its +0x90 and +0x64 entries"
            ),
            "required_for_native_follow": True,
        },
        {
            "id": "mode2_vehicle_pose_dependency",
            "target": "resolved mode-2 vtable+0x90 and vtable+0x64 callees",
            "request": (
                "prove the exact reads/derived values by which the selected "
                "vehicle or its current world pose reaches camera source state; "
                "do not substitute the native VehicleWorldMatrix by similarity"
            ),
            "required_for_native_follow": True,
        },
        {
            "id": "camera_follow_update_order",
            "target": "retail caller/scheduler around FUN_0080e0d0/FUN_0080d300",
            "request": (
                "prove the update ordering/freshness relation between the retail "
                "vehicle update and the mode-2 camera-source update"
            ),
            "required_for_native_follow": True,
        },
    ]

    # None of these source semantics is positive yet.  Keeping the booleans
    # literal makes accidental admission impossible even if a caller supplies a
    # future-positive Phase 705 world-matrix contract before Process 1 closes the
    # camera source identity itself.
    static_source_ready = False
    timing_ready = False
    native_follow_ready = (
        static_source_ready
        and timing_ready
        and transform_state["ready_for_camera_source_join"]
    )

    blockers = [
        "camera-follow:mode2-runtime-argument-vehicle-identity-unproven",
        "camera-follow:mode2-source-vtable-identity-unproven",
        "camera-follow:mode2-vehicle-pose-dependency-unproven",
        "camera-follow:retail-update-order-unproven",
    ]
    blockers.extend(transform_state["blocking_reasons"])
    blockers = list(dict.fromkeys(blockers))

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if native_follow_ready else "static-proof-required",
        "ready": native_follow_ready,
        "native_camera_follow_ready": native_follow_ready,
        "process2_action": (
            "implement_now" if native_follow_ready else REQUEST_PROCESS1
        ),
        "candidate": {
            "mode": 2,
            "activation_function": "FUN_0080e0d0",
            "source": "active_buffer+0x1ca0",
            "source_stride": 0x460,
            "preapply_vfunc_offset": 0x90,
            "controller_apply_function": "FUN_0080d300",
            "common_apply_vfunc_offset": 0x64,
            "source_manager_back_reference_offset": 0x44,
            "candidate_only": True,
        },
        "source_lanes": source_lanes,
        "vehicle_world_matrix_handoff": transform_state,
        "proof_state": {
            "mode2_runtime_argument_vehicle_identity_ready": False,
            "mode2_source_vtable_identity_ready": False,
            "mode2_vehicle_pose_dependency_ready": False,
            "camera_follow_update_order_ready": False,
            "retail_vehicle_world_matrix_ready": transform_state[
                "ready_for_camera_source_join"
            ],
        },
        "process1_requested_proof": proof_requests,
        "blocking_reasons": blockers,
        "native_admission": {
            "may_bind_vehicle_transform_to_camera_source": False,
            "may_schedule_camera_after_vehicle_update": False,
            "may_serialize_opaque_word0_as_native_pointer": False,
            "required_positive_contracts": [
                "mode-2 runtime_argument -> selected retail vehicle identity",
                "mode-2 concrete source vtable identity (+0x90/+0x64)",
                "mode-2 source -> retail vehicle pose dependency",
                "retail vehicle update -> camera update ordering/freshness",
                WORLD_HANDOFF_FORMAT + " current retail world matrix",
                PERSISTENT_TRANSFORM_FORMAT + " freshness-checked transport",
            ],
        },
        "evidence": {
            "camera_snapshot_source_field": "CameraManager+0x2568",
            "camera_snapshot_function": "FUN_0080e040",
            "mode2_activation": "FUN_0080e0d0",
            "mode2_source": "active_buffer+0x1ca0 stride 0x460",
            "mode2_preapply_vfunc": "+0x90(runtime_argument)",
            "controller_apply": "FUN_0080d300",
            "controller_source_store": "CameraManager+0x2568",
            "source_manager_back_reference": "camera_source+0x44 = manager",
            "controller_source_vfunc": "+0x64()",
            "phase705_world_matrix_contract": WORLD_HANDOFF_FORMAT,
            "phase706_persistent_transport_contract": PERSISTENT_TRANSFORM_FORMAT,
        },
        "boundary": {
            "mode2_tracking_label_promoted_to_player_vehicle_follow_proof": False,
            "camera_source_pointer_invented": False,
            "camera_source_vtable_invented": False,
            "native_vehicle_world_matrix_substituted_for_retail_source": False,
            "phase706_transport_promoted_to_camera_timing_proof": False,
            "retail_update_cadence_inferred_from_native_fixed_step": False,
            "camera_math_inferred": False,
            "runtime_execution_claimed": False,
        },
    }
