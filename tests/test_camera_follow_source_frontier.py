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


def test_default_frontier_never_invents_camera_follow_source() -> None:
    report = build_camera_follow_source_frontier()

    assert report["format"] == FORMAT
    assert report["ready"] is False
    assert report["native_camera_follow_ready"] is False
    assert report["process2_action"] == REQUEST_PROCESS1
    assert report["candidate"] == {
        "mode": 2,
        "activation_function": "FUN_0080e0d0",
        "source": "active_buffer+0x1ca0",
        "source_stride": 0x460,
        "preapply_vfunc_offset": 0x90,
        "controller_apply_function": "FUN_0080d300",
        "common_apply_vfunc_offset": 0x64,
        "source_manager_back_reference_offset": 0x44,
        "candidate_only": True,
    }
    assert report["vehicle_world_matrix_handoff"]["evaluated"] is False
    assert (
        "camera-follow:retail-vehicle-world-matrix-handoff-not-supplied"
        in report["blocking_reasons"]
    )
    assert report["native_admission"][
        "may_serialize_opaque_word0_as_native_pointer"
    ] is False
    assert report["boundary"]["camera_source_pointer_invented"] is False
    assert report["boundary"]["camera_source_vtable_invented"] is False
    assert report["boundary"]["camera_math_inferred"] is False


def test_current_phase705_contract_keeps_bind_and_world_matrix_blocked() -> None:
    report = build_camera_follow_source_frontier(_world_handoff(ready=False))
    state = report["vehicle_world_matrix_handoff"]

    assert state["evaluated"] is True
    assert state["format_valid"] is True
    assert state["current_retail_identity_ready"] is True
    assert state["current_retail_BODY0_bind_ready"] is False
    assert state["current_retail_world_matrix_ready"] is False
    assert state["persistent_vulkan_transport_available"] is True
    assert state["ready_for_camera_source_join"] is False
    assert "camera-follow:retail-BODY0-bind-not-ready" in report[
        "blocking_reasons"
    ]
    assert "camera-follow:retail-vehicle-world-matrix-not-ready" in report[
        "blocking_reasons"
    ]


def test_future_positive_world_matrix_does_not_bypass_camera_static_proof() -> None:
    report = build_camera_follow_source_frontier(_world_handoff(ready=True))
    state = report["vehicle_world_matrix_handoff"]

    assert state["ready_for_camera_source_join"] is True
    assert report["proof_state"]["retail_vehicle_world_matrix_ready"] is True
    assert report["ready"] is False
    assert report["process2_action"] == REQUEST_PROCESS1
    assert report["native_admission"][
        "may_bind_vehicle_transform_to_camera_source"
    ] is False
    assert report["native_admission"][
        "may_schedule_camera_after_vehicle_update"
    ] is False
    assert report["proof_state"][
        "mode2_runtime_argument_vehicle_identity_ready"
    ] is False
    assert report["proof_state"]["mode2_source_vtable_identity_ready"] is False
    assert report["proof_state"]["mode2_vehicle_pose_dependency_ready"] is False
    assert report["proof_state"]["camera_follow_update_order_ready"] is False


def test_frontier_freezes_all_known_camera_source_lanes() -> None:
    report = build_camera_follow_source_frontier()
    lanes = {row["mode"]: row for row in report["source_lanes"]}

    assert sorted(lanes) == [1, 2, 3, 4]
    assert lanes[1]["source"] == "active_buffer+0x20"
    assert lanes[2]["source"] == "active_buffer+0x1ca0"
    assert lanes[2]["source_stride"] == 0x460
    assert lanes[2]["preapply_virtual_call"] == {
        "offset": 0x90,
        "argument": "runtime_argument",
    }
    assert lanes[2]["common_apply_virtual_call"] == {
        "offset": 0x64,
        "manager_back_reference_offset": 0x44,
    }
    assert lanes[2]["playable_follow_candidate"] is True
    assert lanes[2]["candidate_only"] is True
    assert lanes[3]["source"] == "active_buffer+0x17a0"
    assert lanes[3]["source_stride"] == 0x280
    assert lanes[4]["activation"] == "FUN_0080d520"
    assert lanes[4]["playable_follow_candidate"] is False


def test_frontier_turns_vague_camera_blocker_into_exact_process1_worklist() -> None:
    report = build_camera_follow_source_frontier()
    rows = {row["id"]: row for row in report["process1_requested_proof"]}

    assert set(rows) == {
        "mode2_runtime_argument_identity",
        "mode2_source_vtable_identity",
        "mode2_vehicle_pose_dependency",
        "camera_follow_update_order",
    }
    assert rows["mode2_runtime_argument_identity"]["target"] == "FUN_0080e0d0"
    assert rows["mode2_source_vtable_identity"]["target"] == (
        "active_buffer+0x1ca0 source object"
    )
    assert "+0x90" in rows["mode2_source_vtable_identity"]["request"]
    assert "+0x64" in rows["mode2_source_vtable_identity"]["request"]
    assert rows["camera_follow_update_order"]["required_for_native_follow"] is True
    assert report["boundary"][
        "mode2_tracking_label_promoted_to_player_vehicle_follow_proof"
    ] is False
    assert report["boundary"][
        "retail_update_cadence_inferred_from_native_fixed_step"
    ] is False


def test_invalid_world_matrix_contract_fails_closed() -> None:
    value = _world_handoff(ready=True)
    value["format"] = "SHIFT.NotTheWorldMatrixContract/1"
    report = build_camera_follow_source_frontier(value)

    assert report["vehicle_world_matrix_handoff"]["format_valid"] is False
    assert report["vehicle_world_matrix_handoff"][
        "ready_for_camera_source_join"
    ] is False
    assert "camera-follow:vehicle-world-matrix-handoff-invalid-format" in report[
        "blocking_reasons"
    ]


def test_report_is_json_serializable() -> None:
    report = build_camera_follow_source_frontier(_world_handoff(ready=False))
    encoded = json.dumps(report, sort_keys=True)
    assert "SHIFT.CameraFollowSourceFrontier/1" in encoded
