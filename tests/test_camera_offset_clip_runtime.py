from camera_offset_clip_runtime import (
    clip_camera_offset,
    compute_tracking_offset_scalar,
    describe_camera_offset_blend,
)


def test_tracking_offset_scalar_ends_with_resolved_value_times_two():
    result = compute_tracking_offset_scalar(
        camera_fov=1.0,
        tracking_magnitude=-3.0,
        helper_9030d0=2.0,
        helper_902770=0.75,
    )
    assert result["half_fov"] == 0.5
    assert result["scaled_magnitude"] == 6.0
    assert result["offset_scalar"] == 1.5


def test_positive_tracking_magnitude_selects_clipped_lower_bound():
    result = clip_camera_offset(
        initial_lower=-1,
        initial_upper=1,
        clipped_lower=-0.25,
        clipped_upper=0.8,
        positive_tracking_magnitude=True,
    )
    assert result["selected_offset"] == -0.25


def test_non_positive_tracking_magnitude_keeps_upper_bound():
    result = clip_camera_offset(
        initial_lower=-1,
        initial_upper=1,
        clipped_lower=-0.25,
        clipped_upper=0.8,
        positive_tracking_magnitude=False,
    )
    assert result["selected_offset"] == 0.8


def test_camera_offset_timer_reset_uses_eb20_result_and_ratio_inverse():
    result = describe_camera_offset_blend(
        transformed_point=[1, 2, 4],
        direction=[1, 0, 0],
        helper_004011f0_result=[1, 0, 0, 0],
        depth_w=2,
        blend_source=0.5,
        tracking_error_magnitude=2,
        tracking_frequency=2,
        tracking_correction_speed=0.5,
        tracking_ratio=4,
        current_300=0.6,
        current_304=0.4,
        current_308=0.1,
        delta=0.2,
        helper_eb20_reset=0.75,
        helper_9_02e40=0.25,
    )
    assert result["timer"]["reset"] is True
    assert result["timer"]["updated_304"] == 0.75
    assert result["timer"]["after"] == 0.25


def test_camera_offset_final_direction_term_uses_blended_scalar_minus_half():
    result = describe_camera_offset_blend(
        transformed_point=[0, 0, 2],
        direction=[1, 2, 3],
        helper_004011f0_result=[1, 0, 0, 0],
        depth_w=2,
        blend_source=1,
        tracking_error_magnitude=4,
        tracking_frequency=0,
        tracking_correction_speed=0,
        tracking_ratio=1,
        current_300=0.75,
        current_304=0.75,
        current_308=1,
        delta=0,
        helper_9_02e40=0,
    )
    assert result["blended_scalar"] == 0.75
    assert result["direction_offset"] == 1.0
    assert result["final_point"] == [1.0, 2.0, 3.0]
