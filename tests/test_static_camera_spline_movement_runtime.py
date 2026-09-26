from static_camera_spline_movement_runtime import (
    SplineCursor,
    move_cursor_backward_segment,
    move_cursor_forward_segment,
    normalize_wrapped_y,
    sample_static_camera_position,
    scan_backward_until_positive,
    scan_forward_until_positive,
)


def test_position_sampler_keeps_blend_factor_and_vec3():
    result = sample_static_camera_position(
        cursor=SplineCursor(1, 2, 0.25),
        blend_factor=0.5,
        sampled_position=[1, 2, 3],
    )
    assert result["position"] == [1.0, 2.0, 3.0]
    assert result["action"]["function"] == "FUN_008135b0"


def test_forward_segment_transition_sets_parameter_zero():
    updated, result = move_cursor_forward_segment(
        SplineCursor(1, 2, 0.75),
        next_node=2,
    )
    assert result["status"] == "advanced"
    assert updated == SplineCursor(2, 2, 0.0)


def test_backward_segment_transition_sets_parameter_one():
    updated, result = move_cursor_backward_segment(
        SplineCursor(2, 2, 0.25),
        previous_node=1,
    )
    assert result["status"] == "advanced"
    assert updated == SplineCursor(1, 2, 1.0)


def test_backward_scan_uses_exact_five_percent_steps():
    cursor = SplineCursor(1, 0, 0.20)
    seen = []

    def score_at(current):
        seen.append(current.parameter)
        return 1.0 if current.parameter <= 0.10 else -1.0

    updated, result = scan_backward_until_positive(
        cursor,
        blend_factor=0.3,
        initial_score=-1.0,
        score_at=score_at,
    )
    assert seen == [0.15, 0.10]
    assert updated.parameter == 0.10
    assert result["status"] == "found-positive"


def test_forward_scan_uses_exact_five_percent_steps():
    cursor = SplineCursor(1, 0, 0.80)
    seen = []

    def score_at(current):
        seen.append(current.parameter)
        return 1.0 if current.parameter >= 0.90 else -1.0

    updated, result = scan_forward_until_positive(
        cursor,
        initial_score=-1.0,
        score_at=score_at,
    )
    assert seen == [0.85, 0.90]
    assert updated.parameter == 0.90
    assert result["status"] == "found-positive"


def test_backward_scan_can_transition_to_previous_segment():
    cursor = SplineCursor(2, 0, 0.0)

    updated, result = scan_backward_until_positive(
        cursor,
        blend_factor=0.2,
        initial_score=-1.0,
        score_at=lambda _: -1.0,
        previous_node=1,
        max_steps=1,
    )
    assert result["status"] == "segment-transitioned"
    assert updated == SplineCursor(1, 0, 1.0)


def test_forward_scan_can_transition_to_next_segment():
    cursor = SplineCursor(1, 0, 1.0)

    updated, result = scan_forward_until_positive(
        cursor,
        initial_score=-1.0,
        score_at=lambda _: -1.0,
        next_node=2,
        max_steps=1,
    )
    assert result["status"] == "segment-transitioned"
    assert updated == SplineCursor(2, 0, 0.0)


def test_y_wrap_uses_absolute_count_times_eight():
    assert normalize_wrapped_y(10, -2) == -6.0
    assert normalize_wrapped_y(10, 1) == 2.0
