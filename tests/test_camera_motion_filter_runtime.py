from camera_motion_filter_runtime import (
    CameraMotionFilterState,
    update_motion_filter,
)


def test_disabled_profile_scale_leaves_state_and_output_unchanged():
    state = CameraMotionFilterState(
        response_x=1, response_y=2, response_z=3,
        target_x=4, target_y=5, target_z=6,
    )
    new_state, output, result = update_motion_filter(
        state,
        delta=0.1,
        reference_vector=[0, 0, 0],
        profile_scale=0,
        output_vector=[7, 8, 9],
    )
    assert result["status"] == "profile-scale-disabled"
    assert new_state == state
    assert output == [7.0, 8.0, 9.0]


def test_motion_filter_updates_target_and_response_states():
    state = CameraMotionFilterState(
        response_x=0,
        response_y=0,
        response_z=0,
        target_x=1,
        target_y=2,
        target_z=3,
    )
    new_state, output, result = update_motion_filter(
        state,
        delta=0.1,
        reference_vector=[0, 0, 0],
        profile_scale=1,
        output_vector=[0, 0, 0],
    )
    assert new_state.target_x == 0.0
    assert new_state.target_y == 0.0
    assert new_state.target_z == 0.0
    assert result["errors"] == [1.0, 2.0, 3.0]
    assert output == [
        new_state.response_x,
        new_state.response_y,
        new_state.response_z,
    ]


def test_motion_filter_output_is_scaled_by_profile_scale():
    state = CameraMotionFilterState(
        response_x=0,
        response_y=0,
        response_z=0,
        target_x=1,
        target_y=0,
        target_z=0,
    )
    _, output, _ = update_motion_filter(
        state,
        delta=1.0,
        reference_vector=[0, 0, 0],
        profile_scale=2,
        output_vector=[1, 2, 3],
    )
    assert output[0] == 2.0
    assert output[1] == 2.0
    assert output[2] == 3.0


def test_motion_filter_requires_three_component_vectors():
    state = CameraMotionFilterState()
    try:
        update_motion_filter(
            state,
            delta=0.1,
            reference_vector=[1, 2],
            profile_scale=1,
            output_vector=[0, 0, 0],
        )
    except ValueError:
        return
    raise AssertionError("expected three-component reference vector")
