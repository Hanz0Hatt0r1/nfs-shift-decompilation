import pytest

from camera_switch_gate_runtime import CameraSwitchState, evaluate_switch_gate


def test_matching_clean_state_is_fast_path():
    state = CameraSwitchState(mode=2, active_buffer_sub_index=-1, active_buffer_sub_flag=0, camera_id=7, dirty=False)
    result = evaluate_switch_gate(
        state,
        requested_mode=2,
        requested_sub_index=99,
        requested_sub_flag=0,
        requested_camera_id=7,
    )
    assert result["status"] == "already-current"
    assert result["transition_required"] is False


def test_mode_one_requires_sub_index_match():
    state = CameraSwitchState(mode=1, active_buffer_sub_index=4, active_buffer_sub_flag=0, camera_id=-1, dirty=False)
    result = evaluate_switch_gate(
        state,
        requested_mode=1,
        requested_sub_index=5,
        requested_sub_flag=0,
        requested_camera_id=-1,
    )
    assert result["transition_required"] is True


def test_non_mode_one_ignores_sub_index_for_gate():
    state = CameraSwitchState(mode=2, active_buffer_sub_index=4, active_buffer_sub_flag=0, camera_id=7, dirty=False)
    result = evaluate_switch_gate(
        state,
        requested_mode=2,
        requested_sub_index=5,
        requested_sub_flag=0,
        requested_camera_id=7,
    )
    assert result["transition_required"] is False


def test_dirty_state_forces_transition():
    state = CameraSwitchState(mode=3, active_buffer_sub_index=-1, active_buffer_sub_flag=0, camera_id=7, dirty=True)
    result = evaluate_switch_gate(
        state,
        requested_mode=3,
        requested_sub_index=0,
        requested_sub_flag=0,
        requested_camera_id=7,
    )
    assert result["transition_required"] is True
    assert result["state_after"]["dirty"] is False


def test_different_flag_or_camera_id_forces_transition():
    state = CameraSwitchState(mode=2, active_buffer_sub_index=-1, active_buffer_sub_flag=0, camera_id=7, dirty=False)
    for flag, camera_id in [(1, 7), (0, 8)]:
        result = evaluate_switch_gate(
            state,
            requested_mode=2,
            requested_sub_index=-1,
            requested_sub_flag=flag,
            requested_camera_id=camera_id,
        )
        assert result["transition_required"] is True
