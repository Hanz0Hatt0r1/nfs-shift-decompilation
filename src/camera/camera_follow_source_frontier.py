"""Machine-readable frontier for the first playable camera-follow source.

PC-retail proofs now close the mode-2 runtime argument, source-vtable identity,
and default/steady physics-before-camera update order.  The remaining semantic
join is narrower: retail target transform resolution reaches an entry-attached
runtime object at manager+0x2a0[target_id]+0x1e80, but that object's identity
with the selected HDVehicle/BODY0 current pose remains unproven.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.CameraFollowSourceFrontier/1"
WORLD_HANDOFF_FORMAT = "SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1"
PERSISTENT_TRANSFORM_FORMAT = "SHIFT.PersistentBMWVehicleWorldTransform/1"
REQUEST_PROCESS1 = "request_process1_static_proof"


def _vehicle_transform_state(world_handoff: Mapping[str, Any] | None) -> dict[str, Any]:
    if world_handoff is None:
        return {
            "evaluated": False,
            "format_valid": False,
            "current_retail_identity_ready": False,
            "current_retail_BODY0_bind_ready": False,
            "current_retail_world_matrix_ready": False,
            "persistent_vulkan_transport_available": False,
            "ready_for_camera_source_join": False,
            "blocking_reasons": ["camera-follow:retail-vehicle-world-matrix-handoff-not-supplied"],
        }

    blockers: list[str] = []
    format_valid = world_handoff.get("format") == WORLD_HANDOFF_FORMAT
    if not format_valid:
        blockers.append("camera-follow:vehicle-world-matrix-handoff-invalid-format")
    retail_identity_ready = world_handoff.get("current_retail_identity_ready") is True
    body0_bind_ready = world_handoff.get("current_retail_BODY0_bind_ready") is True
    world_ready = world_handoff.get("current_retail_world_matrix_ready") is True
    persistent_transport_available = world_handoff.get("phase649_persistent_vulkan_upload_available") is True
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


def build_camera_follow_source_frontier(world_handoff: Mapping[str, Any] | None = None) -> dict[str, Any]:
    transform_state = _vehicle_transform_state(world_handoff)

    source_lanes = [
        {"mode": 1, "source": "active_buffer+0x20", "activation": "FUN_0080de00 / FUN_0080dfd0", "classification": "buffer-selected-view-source", "playable_follow_candidate": False},
        {
            "mode": 2,
            "source": "active_buffer+0x1ca0",
            "source_stride": 0x460,
            "activation": "FUN_0080e0d0",
            "constructor": "FUN_0081fac0",
            "vtable": "0x00b16788",
            "preapply_virtual_call": {"offset": 0x90, "target": "FUN_0081f7c0", "argument": "selected camera object"},
            "internal_setter_virtual_call": {"offset": 0x5c, "target": "FUN_006bbf70"},
            "per_frame_virtual_call": {"offset": 0x60, "target": "FUN_008216a0", "ordering": "after admitted cPhysicsManager scheduler work"},
            "common_apply_virtual_call": {"offset": 0x64, "target": "FUN_00820a50", "manager_back_reference_offset": 0x44},
            "controller_apply": "FUN_0080d300",
            "classification": "tracking-source-lane",
            "playable_follow_candidate": True,
            "candidate_only": True,
            "runtime_argument_identity_resolved": True,
            "runtime_argument_is_selected_retail_vehicle": False,
            "source_vtable_identity_proven": True,
            "entry_attached_runtime_pose_dependency_proven": True,
            "vehicle_transform_dependency_proven": False,
            "retail_update_order_proven": True,
        },
        {"mode": 3, "source": "active_buffer+0x17a0", "source_stride": 0x280, "activation": "FUN_0080e140", "classification": "static-camera-source-lane", "playable_follow_candidate": False},
        {"mode": 4, "source": "caller-supplied external source", "activation": "FUN_0080d520", "preapply_helper": "FUN_0081b170", "classification": "external-source-lane", "playable_follow_candidate": False},
    ]

    proof_requests = [
        {"id": "mode2_runtime_argument_identity", "target": "FUN_0080e0d0", "status": "resolved-negative", "result": "source.vtable+0x90 receives the selected camera object, not the selected retail vehicle/world matrix", "required_for_native_follow": False},
        {"id": "mode2_source_vtable_identity", "target": "active_buffer+0x1ca0 source object", "status": "resolved", "result": "FUN_0081fac0 installs vtable 0x00b16788; +0x90=FUN_0081f7c0, +0x64=FUN_00820a50, +0x60=FUN_008216a0", "required_for_native_follow": False},
        {
            "id": "mode2_vehicle_pose_dependency",
            "target": "camera target service -> manager+0x2a0[target_id] -> entry+0x1e80 attached runtime",
            "status": "entry-attached-runtime-pose-bridge-proven-identity-open",
            "result": "direct manager-entry == HDVehicle identity is rejected; FUN_004810bf selectors consume state from entry+0x1e80",
            "request": "prove or reject entry+0x1e80 pose producer identity with the selected retail HDVehicle/BODY0 current pose",
            "required_for_native_follow": True,
        },
        {"id": "camera_follow_update_order", "target": "cPhysicsManager scheduler -> callback -> mode-2 source+0x60", "status": "resolved", "result": "admitted default/steady retail path runs FUN_0070f940/FUN_007155e0 physics before FUN_0070f890 callback -> FUN_00489f70 -> mode2 +0x60/FUN_008216a0", "required_for_native_follow": False},
    ]

    static_source_ready = False
    timing_ready = True
    native_follow_ready = static_source_ready and timing_ready and transform_state["ready_for_camera_source_join"]

    blockers = ["camera-follow:entry-attached-runtime-to-selected-vehicle-BODY0-identity-unproven"]
    blockers.extend(transform_state["blocking_reasons"])
    blockers = list(dict.fromkeys(blockers))

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if native_follow_ready else "static-proof-required",
        "ready": native_follow_ready,
        "native_camera_follow_ready": native_follow_ready,
        "process2_action": "implement_now" if native_follow_ready else REQUEST_PROCESS1,
        "candidate": {
            "mode": 2,
            "activation_function": "FUN_0080e0d0",
            "source": "active_buffer+0x1ca0",
            "source_stride": 0x460,
            "source_constructor": "FUN_0081fac0",
            "source_vtable": "0x00b16788",
            "preapply_vfunc_offset": 0x90,
            "preapply_vfunc_target": "FUN_0081f7c0",
            "per_frame_vfunc_offset": 0x60,
            "per_frame_vfunc_target": "FUN_008216a0",
            "controller_apply_function": "FUN_0080d300",
            "common_apply_vfunc_offset": 0x64,
            "common_apply_vfunc_target": "FUN_00820a50",
            "candidate_only": True,
        },
        "source_lanes": source_lanes,
        "vehicle_world_matrix_handoff": transform_state,
        "proof_state": {
            "mode2_runtime_argument_identity_resolved": True,
            "mode2_runtime_argument_is_selected_retail_vehicle": False,
            "mode2_source_vtable_identity_ready": True,
            "mode2_entry_attached_runtime_pose_dependency_ready": True,
            "mode2_vehicle_pose_dependency_ready": False,
            "camera_follow_update_order_ready": True,
            "retail_vehicle_world_matrix_ready": transform_state["ready_for_camera_source_join"],
        },
        "process1_requested_proof": proof_requests,
        "blocking_reasons": blockers,
        "native_admission": {
            "may_bind_vehicle_transform_to_camera_source": False,
            "may_schedule_camera_after_vehicle_update": False,
            "retail_physics_before_camera_order_proven": True,
            "may_serialize_opaque_word0_as_native_pointer": False,
            "required_positive_contracts": [
                "entry+0x1e80 attached runtime pose -> selected retail vehicle/BODY0 identity",
                WORLD_HANDOFF_FORMAT + " current retail world matrix",
                PERSISTENT_TRANSFORM_FORMAT + " freshness-checked transport",
            ],
        },
        "evidence": {
            "retail_executable_sha256": "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1",
            "mode2_activation_callsite": "FUN_0080e1b0@0x0080e236",
            "mode2_constructor": "FUN_0081fac0",
            "mode2_vtable": "0x00b16788",
            "camera_target_service": "CameraManager+0x574 = DAT_00bc185c+4",
            "camera_target_collection": "thunk_FUN_00444fcc()+0x2a0[target_id]",
            "manager_entry_is_HDVehicle_plus_0x4330": False,
            "entry_attached_runtime_field": "+0x1e80",
            "entry_attached_runtime_producer": "FUN_00481d46 -> FUN_0046c050",
            "entry_attached_runtime_update": "FUN_0046d7b0(entry+0x1e80, entry+0x1e84)",
            "target_dispatch_chain": "FUN_00481420 -> FUN_004810a0 -> FUN_004585e6 -> FUN_004810bf",
            "target_selector_2_lanes": ["+0x10", "+0x14", "+0x18"],
            "target_selector_5_lanes": ["+0x1c", "+0x20", "+0x24"],
            "retail_update_order": "physics scheduler -> cPhysicsManager+0x298 callback -> camera manager -> mode2 +0x60",
            "phase705_world_matrix_contract": WORLD_HANDOFF_FORMAT,
            "phase706_persistent_transport_contract": PERSISTENT_TRANSFORM_FORMAT,
        },
        "boundary": {
            "mode2_tracking_label_promoted_to_player_vehicle_follow_proof": False,
            "manager_entry_promoted_to_HDVehicle_identity": False,
            "entry_attached_runtime_promoted_to_HDVehicle_or_BODY0_identity": False,
            "camera_source_pointer_invented": False,
            "camera_source_vtable_invented": False,
            "native_vehicle_world_matrix_substituted_for_retail_source": False,
            "retail_update_cadence_inferred_from_native_fixed_step": False,
            "camera_math_inferred": False,
            "runtime_execution_claimed": False,
        },
    }
