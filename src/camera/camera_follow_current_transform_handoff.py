"""Compose the closed P1.4 camera proof with the production vehicle transform.

This adapter intentionally does not revive the historical Phase705 boolean gate.
It consumes the current production S4 world-transform wiring contract and the
camera proof surface independently, then exposes a fail-closed Process 1D ->
Process 2 handoff.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.CameraFollowP14CurrentVehicleTransformHandoff/1"
CAMERA_FRONTIER_FORMAT = "SHIFT.CameraFollowSourceFrontier/1"
WORLD_WIRING_FORMAT = "SHIFT.BMWPersistentWorldTransformRuntimeWiring/1"
BODY0_BIND_PROOF_FORMAT = "SHIFT.BMWBody0BindFrameProof/1"
BODY0_BIND_ADMISSION_FORMAT = "SHIFT.NativeBMWBody0BindFrameRuntimeAdmission/1"
PERSISTENT_WORLD_TRANSFORM_FORMAT = "SHIFT.PersistentBMWVehicleWorldTransform/1"


def build_handoff(
    camera_frontier: Mapping[str, Any],
    world_wiring: Mapping[str, Any],
) -> dict[str, Any]:
    camera_format_valid = camera_frontier.get("format") == CAMERA_FRONTIER_FORMAT
    camera_state = camera_frontier.get("proof_state")
    if not isinstance(camera_state, Mapping):
        camera_state = {}

    selected_player_ready = (
        camera_state.get("mode2_playable_target_entity_value_ready") is True
        and camera_state.get("mode2_selected_player_target_identity_ready") is True
    )
    pose_dependency_ready = camera_state.get("mode2_vehicle_pose_dependency_ready") is True
    retail_order_ready = camera_state.get("camera_follow_update_order_ready") is True

    world_format_valid = world_wiring.get("format") == WORLD_WIRING_FORMAT
    world_ready = world_wiring.get("ready") is True

    inputs = world_wiring.get("INPUT")
    if not isinstance(inputs, Mapping):
        inputs = {}
    output = world_wiring.get("OUTPUT")
    if not isinstance(output, Mapping):
        output = {}
    provenance = world_wiring.get("provenance")
    if not isinstance(provenance, Mapping):
        provenance = {}
    persistent_commit = provenance.get("persistent_commit")
    if not isinstance(persistent_commit, Mapping):
        persistent_commit = {}

    body0_bind_proof_ready = inputs.get("body0_bind_proof") == BODY0_BIND_PROOF_FORMAT
    body0_bind_admission_ready = (
        inputs.get("body0_bind_runtime_admission") == BODY0_BIND_ADMISSION_FORMAT
    )
    persistent_world_transform_ready = (
        inputs.get("persistent_world_transform") == PERSISTENT_WORLD_TRANSFORM_FORMAT
        and output.get("vehicle_world_transform_ready") is True
    )
    body0_index_ready = provenance.get("body_index") == 0
    same_fixed_step_publish_ready = (
        persistent_commit.get("function") == "commit_retail_bmw_vehicle_world_transform"
        and persistent_commit.get("publication")
        == "publish_persistent_bmw_vehicle_world_transform_for_render"
        and persistent_commit.get("same_fixed_step_continuation_before_phase715") is True
    )

    ready = all(
        (
            camera_format_valid,
            selected_player_ready,
            pose_dependency_ready,
            retail_order_ready,
            world_format_valid,
            world_ready,
            body0_bind_proof_ready,
            body0_bind_admission_ready,
            persistent_world_transform_ready,
            body0_index_ready,
            same_fixed_step_publish_ready,
        )
    )

    blockers: list[str] = []
    if not camera_format_valid:
        blockers.append("camera-follow-handoff:camera-frontier-invalid-format")
    if not selected_player_ready:
        blockers.append("camera-follow-handoff:selected-player-target-identity-not-ready")
    if not pose_dependency_ready:
        blockers.append("camera-follow-handoff:vehicle-pose-dependency-not-ready")
    if not retail_order_ready:
        blockers.append("camera-follow-handoff:retail-update-order-not-ready")
    if not world_format_valid:
        blockers.append("camera-follow-handoff:world-wiring-invalid-format")
    if not world_ready:
        blockers.append("camera-follow-handoff:world-wiring-not-ready")
    if not body0_bind_proof_ready:
        blockers.append("camera-follow-handoff:BODY0-bind-proof-not-ready")
    if not body0_bind_admission_ready:
        blockers.append("camera-follow-handoff:BODY0-bind-admission-not-ready")
    if not persistent_world_transform_ready:
        blockers.append("camera-follow-handoff:persistent-world-transform-not-ready")
    if not body0_index_ready:
        blockers.append("camera-follow-handoff:selected-BODY0-index-not-ready")
    if not same_fixed_step_publish_ready:
        blockers.append("camera-follow-handoff:same-fixed-step-publication-not-ready")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": ready,
        "status": "ready-for-process2-camera-feed" if ready else "blocked",
        "process2_action": "implement_camera_feed" if ready else "hold",
        "camera": {
            "frontier_format": CAMERA_FRONTIER_FORMAT,
            "selected_player_target_identity_ready": selected_player_ready,
            "vehicle_pose_dependency_ready": pose_dependency_ready,
            "retail_physics_before_camera_order_ready": retail_order_ready,
            "mode2_source": "active_buffer+0x1ca0",
            "mode2_per_frame_target": "FUN_008216a0",
        },
        "vehicle_transform": {
            "wiring_format": WORLD_WIRING_FORMAT,
            "production_wiring_ready": world_ready,
            "body_index": provenance.get("body_index"),
            "BODY0_bind_proof_ready": body0_bind_proof_ready,
            "BODY0_bind_runtime_admission_ready": body0_bind_admission_ready,
            "persistent_world_transform_ready": persistent_world_transform_ready,
            "same_fixed_step_commit_publish_ready": same_fixed_step_publish_ready,
            "commit_function": persistent_commit.get("function"),
            "publication_function": persistent_commit.get("publication"),
        },
        "blocking_reasons": blockers,
        "adjudication": {
            "p1_4_retail_camera_follow_proof_complete": ready,
            "process2_camera_feed_handoff_ready": ready,
            "process3_p3_5_camera_semantics_handoff_ready": ready,
            "camera_runtime_feed_implemented": False,
            "retail_control_chain_complete": False,
            "external_provider_count": 7,
        },
        "boundary": {
            "historical_phase705_false_boolean_promoted": False,
            "world_transform_readiness_inferred_from_host_frequency": False,
            "camera_target_identity_inferred_from_numeric_offset": False,
            "camera_runtime_execution_claimed": False,
            "provider_removed": False,
        },
    }
