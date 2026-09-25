from camera_view_matrix_build_runtime import (
    compute_depth_coefficients,
    compute_rate_ratio,
    describe_camera_view_matrix_build,
)


def test_depth_coefficients_match_explicit_near_far_formula():
    result = compute_depth_coefficients(near_z=1.0, far_z=750.0)
    assert result["span"] == 749.0
    assert result["far_over_span"] == 750.0 / 749.0
    assert result["minus_near_times_far_over_span"] == -750.0 / 749.0


def test_depth_coefficients_reject_equal_near_far():
    try:
        compute_depth_coefficients(near_z=1.0, far_z=1.0)
    except ValueError:
        return
    raise AssertionError("expected equal NearZ/FarZ rejection")


def test_rate_ratio_is_zero_when_input_scalar_is_zero():
    result = compute_rate_ratio(
        input_scalar=0,
        helper_00900b10=3,
        helper_00900c40=2,
    )
    assert result["ratio"] == 0.0
    assert result["status"] == "zero-input"


def test_rate_ratio_uses_two_global_helpers_when_scalar_is_nonzero():
    result = compute_rate_ratio(
        input_scalar=4,
        helper_00900b10=3,
        helper_00900c40=2,
    )
    assert result["half_scalar"] == 2.0
    assert result["ratio"] == 1.5


def test_matrix_build_keeps_helper_order_and_intermediate_shapes():
    result = describe_camera_view_matrix_build(
        orientation_quaternion=[1, 0, 0, 0],
        position=[1, 2, 3],
        near_z=1,
        far_z=750,
        input_scalar=2,
        helper_00900b10=4,
        helper_00900c40=2,
        converted_matrix=list(range(12)),
        transformed_matrix=list(range(12)),
        final_matrix=list(range(16)),
    )
    assert result["helper_boundaries"]["FUN_00445ec0"]["output_shape"] == 12
    assert result["source_order"][:3] == [
        "FUN_008207c0",
        "FUN_00445ec0",
        "FUN_00630a50",
    ]
    assert result["source_order"][-2:] == [
        "FUN_00401610",
        "FUN_00401d10",
    ]


def test_matrix_build_scales_rate_ratio_by_camera_data_268c():
    result = describe_camera_view_matrix_build(
        orientation_quaternion=[1, 0, 0, 0],
        position=[0, 0, 0],
        near_z=1,
        far_z=3,
        input_scalar=2,
        helper_00900b10=4,
        helper_00900c40=2,
        camera_data_268c=4,
    )
    assert result["rate_ratio"]["ratio"] == 2.0
    assert result["rate_ratio"]["scaled_ratio"] == 0.5
    assert result["projection_state_constants"]["+0x5c"] == 0.0
