from tracking_camera_orientation_output_runtime import (
    describe_tracking_orientation,
    normalize3,
)


def test_normalize3_is_zero_safe():
    assert normalize3([0, 0, 0]) == ((0.0, 0.0, 0.0), 0.0)


def test_target_spline_branch_builds_direction_basis_and_uses_eb50():
    result = describe_tracking_orientation(
        target_mode=1,
        target_spline_id=3,
        static_direction=False,
        camera_position=[0, 0, 0],
        target_position=[1, 0, 0],
        stored_quaternion=[1, 0, 0, 0],
        service_available=False,
        spline_output_basis=[1,0,0, 0,1,0, 0,0,1],
        spline_helper_args=[1,0,0,0,1,0,0,0,1,0],
    )
    assert result["branch"] == "target-spline-direction"
    assert result["direction"]["unit"] == (1.0, 0.0, 0.0)
    assert any(a["action"] == "FUN_0063eb50" for a in result["actions"])


def test_target_mode_falls_back_to_service_and_emits_401130():
    result = describe_tracking_orientation(
        target_mode=1,
        target_spline_id=4,
        static_direction=True,
        camera_position=[0,0,0],
        target_position=[0,0,1],
        stored_quaternion=[1,0,0,0],
        service_available=True,
        service_orientation=[1,0,0,0],
    )
    assert result["branch"] == "target-service-fallback"
    assert result["output"] == [1,0,0,0]
    assert result["actions"][-1]["action"] == "FUN_00401130"


def test_non_target_static_direction_copies_quaternion_verbatim():
    result = describe_tracking_orientation(
        target_mode=0,
        target_spline_id=-1,
        static_direction=True,
        camera_position=[0,0,0],
        target_position=[0,0,1],
        stored_quaternion=[0.2,0.3,0.4,0.5],
        service_available=False,
    )
    assert result["branch"] == "static-direction"
    assert result["output"] == [0.2,0.3,0.4,0.5]


def test_non_target_dynamic_branch_zeroes_pitch_helper_for_vertical_axis_case():
    result = describe_tracking_orientation(
        target_mode=0,
        target_spline_id=-1,
        static_direction=False,
        camera_position=[0,0,0],
        target_position=[0,2,0],
        stored_quaternion=[1,0,0,0],
        service_available=False,
        angle_902620=1.0,
        angle_90285a=2.0,
    )
    assert result["branch"] == "derived-quaternion"
    assert result["angles"]["FUN_0090285a"] == 0.0
