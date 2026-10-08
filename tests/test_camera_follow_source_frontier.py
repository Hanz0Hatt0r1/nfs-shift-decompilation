from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMERA = ROOT / "src" / "camera"
if str(CAMERA) not in sys.path:
    sys.path.insert(0, str(CAMERA))

from camera_follow_source_frontier import (  # noqa: E402
    FORMAT,
    REQUEST_PROCESS1,
    WORLD_HANDOFF_FORMAT,
    build_camera_follow_source_frontier,
)


def _world_handoff(*, ready: bool) -> dict:
    return {
        "format": WORLD_HANDOFF_FORMAT,
        "current_retail_identity_ready": True,
        "retail_identity_injected_by_caller": False,
        "current_retail_BODY0_bind_ready": ready,
        "current_retail_world_matrix_ready": ready,
        "phase649_persistent_vulkan_upload_available": True,
    }


def test_default_frontier_freezes_resolved_pose_path_but_keeps_target_identity_closed() -> None:
    report = build_camera_follow_source_frontier()
    assert report["format"] == FORMAT
    assert report["ready"] is False
    assert report["native_camera_follow_ready"] is False
    assert report["process2_action"] == REQUEST_PROCESS1

    candidate = report["candidate"]
    assert candidate["source"] == "active_buffer+0x1ca0"
    assert candidate["source_constructor"] == "FUN_0081fac0"
    assert candidate["source_vtable"] == "0x00b16788"
    assert candidate["preapply_vfunc_target"] == "FUN_0081f7c0"
    assert candidate["per_frame_vfunc_target"] == "FUN_008216a0"
    assert candidate["common_apply_vfunc_target"] == "FUN_00820a50"

    state = report["proof_state"]
    assert state["mode2_runtime_argument_identity_resolved"] is True
    assert state["mode2_runtime_argument_is_selected_retail_vehicle"] is False
    assert state["mode2_source_vtable_identity_ready"] is True
    assert state["mode2_entry_attached_runtime_local_target_dependency_ready"] is True
    assert state["mode2_target_vehicle_snapshot_affine_dependency_ready"] is True
    assert state["mode2_tracking_data_target_field_ready"] is True
    assert state["mode2_override_path_rejected_as_vehicle_target"] is True
    assert state["mode2_selected_player_target_identity_ready"] is False
    assert state["mode2_vehicle_pose_dependency_ready"] is False
    assert state["camera_follow_update_order_ready"] is True

    assert "camera-follow:tracking-data-target-to-selected-player-bmw-entry-unproven" in report["blocking_reasons"]
    assert "camera-follow:retail-update-order-unproven" not in report["blocking_reasons"]
    assert report["native_admission"]["retail_physics_before_camera_order_proven"] is True
    assert report["native_admission"]["target_vehicle_snapshot_affine_proven"] is True
    assert report["native_admission"]["tracking_data_target_field_identified"] is True
    assert report["native_admission"]["tracking_override_path_rejected_as_vehicle_target"] is True


def test_current_phase705_contract_still_keeps_bind_and_world_matrix_blocked() -> None:
    report = build_camera_follow_source_frontier(_world_handoff(ready=False))
    state = report["vehicle_world_matrix_handoff"]
    assert state["format_valid"] is True
    assert state["current_retail_identity_ready"] is True
    assert state["current_retail_BODY0_bind_ready"] is False
    assert state["current_retail_world_matrix_ready"] is False
    assert state["persistent_vulkan_transport_available"] is True
    assert state["ready_for_camera_source_join"] is False
    assert "camera-follow:retail-BODY0-bind-not-ready" in report["blocking_reasons"]
    assert "camera-follow:retail-vehicle-world-matrix-not-ready" in report["blocking_reasons"]


def test_future_positive_world_matrix_does_not_bypass_tracking_target_identity() -> None:
    report = build_camera_follow_source_frontier(_world_handoff(ready=True))
    assert report["vehicle_world_matrix_handoff"]["ready_for_camera_source_join"] is True
    assert report["ready"] is False
    assert report["process2_action"] == REQUEST_PROCESS1
    assert report["native_admission"]["may_bind_vehicle_transform_to_camera_source"] is False
    assert report["native_admission"]["may_schedule_camera_after_vehicle_update"] is False
    assert report["proof_state"]["mode2_target_vehicle_snapshot_affine_dependency_ready"] is True
    assert report["proof_state"]["mode2_selected_player_target_identity_ready"] is False


def test_mode2_lane_records_snapshot_affine_target_field_and_retail_order() -> None:
    report = build_camera_follow_source_frontier()
    lanes = {row["mode"]: row for row in report["source_lanes"]}
    assert sorted(lanes) == [1, 2, 3, 4]
    lane = lanes[2]
    assert lane["constructor"] == "FUN_0081fac0"
    assert lane["vtable"] == "0x00b16788"
    assert lane["preapply_virtual_call"] == {
        "offset": 0x90,
        "target": "FUN_0081f7c0",
        "argument": "selected camera object",
    }
    assert lane["per_frame_virtual_call"]["target"] == "FUN_008216a0"
    assert lane["entry_attached_runtime_local_target_dependency_proven"] is True
    assert lane["target_vehicle_snapshot_affine_dependency_proven"] is True
    assert lane["tracking_data_target_field_identified"] is True
    assert lane["tracking_override_path_rejected_as_vehicle_target"] is True
    assert lane["selected_player_target_identity_proven"] is False
    assert lane["vehicle_transform_dependency_proven"] is True
    assert lane["retail_update_order_proven"] is True


def test_process1_worklist_points_to_actual_target_field_and_service_join() -> None:
    report = build_camera_follow_source_frontier()
    rows = {row["id"]: row for row in report["process1_requested_proof"]}
    assert rows["mode2_runtime_argument_identity"]["status"] == "resolved-negative"
    assert rows["mode2_source_vtable_identity"]["status"] == "resolved"
    assert rows["camera_follow_update_order"]["status"] == "resolved"
    request3 = rows["mode2_vehicle_pose_dependency"]
    assert request3["status"] == "vehicle-snapshot-affine-proven-target-field-identified-selected-target-identity-open"
    assert "Target byte +0x78" in request3["target"]
    assert "FUN_008140c0" in request3["request"]
    assert "CameraManager+0x574" in request3["request"]

    evidence = report["evidence"]
    assert evidence["tracking_data_target_field"] == "CTrackingCamData byte +0x78 ('Target')"
    assert evidence["tracking_data_override_field"] == "CTrackingCamData byte +0xd4 ('OverridedBy')"
    assert evidence["tracking_override_not_vehicle_target_proof"] is True
    assert evidence["manager_entry_is_HDVehicle_plus_0x4330"] is False
    assert evidence["entry_attached_runtime_classification"] == "local target/offset runtime state, not world pose"
    assert "FUN_00485290" in evidence["entry_numeric_vehicle_index_source"]
    assert evidence["vehicle_snapshot_slot_formula"] == "DAT_00c10b20 + entry[+0xfc] * 0x1fa0"
    assert "FUN_00481e20" in evidence["vehicle_snapshot_copy"]
    assert evidence["outer_vehicle_snapshot_contract"] == "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
    assert report["boundary"]["tracking_override_linkage_promoted_to_vehicle_target_proof"] is False
    assert report["boundary"]["tracking_target_field_promoted_to_selected_player_without_service_join"] is False
    assert report["boundary"]["manager_entry_promoted_to_HDVehicle_identity"] is False
    assert report["boundary"]["entry_attached_runtime_promoted_to_world_pose"] is False


def test_invalid_world_matrix_contract_fails_closed() -> None:
    value = _world_handoff(ready=True)
    value["format"] = "SHIFT.NotTheWorldMatrixContract/1"
    report = build_camera_follow_source_frontier(value)
    assert report["vehicle_world_matrix_handoff"]["format_valid"] is False
    assert report["vehicle_world_matrix_handoff"]["ready_for_camera_source_join"] is False
    assert "camera-follow:vehicle-world-matrix-handoff-invalid-format" in report["blocking_reasons"]


def test_report_is_json_serializable() -> None:
    encoded = json.dumps(build_camera_follow_source_frontier(_world_handoff(ready=False)), sort_keys=True)
    assert "SHIFT.CameraFollowSourceFrontier/1" in encoded
    assert "CTrackingCamData byte +0x78" in encoded
    assert "FUN_008216a0" in encoded
