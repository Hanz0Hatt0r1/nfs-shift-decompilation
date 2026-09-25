import pytest

from camera_state_snapshot_runtime import (
    CameraBufferState,
    CameraManagerState,
    begin_camera_buffer_swap,
    complete_camera_buffer_update,
    snapshot_camera_state,
)
from camera_switch_gate_runtime import CameraSwitchState, evaluate_switch_gate


def test_camera_snapshot_keeps_six_runtime_values_distinct():
    state = CameraManagerState(
        active_buffer_index=1,
        camera_source="opaque-camera-source",
        mode=3,
        sub_index=12,
        camera_id=8,
        active_group=4,
        group_restore_value=6,
        sub_flag=1,
    )
    result = snapshot_camera_state(state)
    snap = result["snapshot"]
    assert snap["camera_source"] == "opaque-camera-source"
    assert snap["mode"] == 3
    assert snap["buffer_sub_index"] == 12
    assert snap["camera_id"] == 8
    assert snap["active_group"] == 4
    assert snap["group_restore_value"] == 6
    assert snap["buffer_index"] == 1
    assert snap["buffer_sub_flag"] == 1


def test_buffer_swap_toggles_between_the_two_runtime_buffers():
    result = begin_camera_buffer_swap(CameraBufferState(index=0))
    assert result["status"] == "swapped"
    assert result["new_index"] == 1
    assert result["copy_edges"]["camera_data"]["src_base"] == "buffer[0]+0xbe0"
    assert result["copy_edges"]["camera_data"]["dst_base"] == "buffer[1]+0x20"


def test_second_buffer_swap_reverses_copy_direction():
    result = begin_camera_buffer_swap(CameraBufferState(index=1))
    assert result["new_index"] == 0
    assert result["copy_edges"]["tracking_camera_state"]["src_base"] == "buffer[1]+0x2100"
    assert result["copy_edges"]["tracking_camera_state"]["dst_base"] == "buffer[0]+0x1ca0"


def test_swap_is_guarded_when_update_is_already_in_progress():
    result = begin_camera_buffer_swap(CameraBufferState(index=0), update_in_progress=True)
    assert result["status"] == "busy"
    assert result["changed"] is False
    assert result["new_index"] == 0


def test_update_completion_clears_the_guard():
    result = complete_camera_buffer_update(CameraBufferState(index=1))
    assert result["status"] == "ready"
    assert result["update_in_progress"] is False


def test_switch_gate_uses_active_buffer_fields_for_mode_one():
    state = CameraSwitchState(
        mode=1,
        active_buffer_sub_index=4,
        active_buffer_sub_flag=1,
        camera_id=9,
        dirty=False,
    )
    same = evaluate_switch_gate(
        state,
        requested_mode=1,
        requested_sub_index=4,
        requested_sub_flag=1,
        requested_camera_id=9,
    )
    different = evaluate_switch_gate(
        state,
        requested_mode=1,
        requested_sub_index=5,
        requested_sub_flag=1,
        requested_camera_id=9,
    )
    assert same["transition_required"] is False
    assert different["transition_required"] is True


def test_non_mode_one_does_not_compare_requested_sub_index_but_does_compare_flag():
    state = CameraSwitchState(
        mode=2,
        active_buffer_sub_index=4,
        active_buffer_sub_flag=1,
        camera_id=9,
        dirty=False,
    )
    same = evaluate_switch_gate(
        state,
        requested_mode=2,
        requested_sub_index=999,
        requested_sub_flag=1,
        requested_camera_id=9,
    )
    different_flag = evaluate_switch_gate(
        state,
        requested_mode=2,
        requested_sub_index=999,
        requested_sub_flag=0,
        requested_camera_id=9,
    )
    assert same["transition_required"] is False
    assert different_flag["transition_required"] is True
