from matrix_vector_transform_runtime import Matrix3x3

import sdf_body_state_projection_runtime as runtime


def test_body_state_projection_contract_distinguishes_pre_and_post_solve():
    report = runtime.describe_sdf_body_state_projection_contract()
    assert report["format"] == "SHIFT.SDFBodyStateProjectionRuntime/2"
    assert report["pre_solve_entry"]["function"] == "FUN_007bc680"
    assert report["post_solve_entry"]["function"] == "FUN_007b4110"
    assert report["post_solve_projection"]["solver_vector"] == "PhysicsSystem +0x40"


def test_body_state_projection_preserves_retail_pre_solve_call_order():
    report = runtime.describe_sdf_body_state_projection_contract()
    assert report["pre_solve_call_order"] == [
        "FUN_007aefb0",
        "FUN_007bac60",
        "FUN_007bae40",
        "FUN_007bb090",
        "FUN_007bbb80",
        "FUN_007bb250",
        "FUN_007bb6c0",
    ]


def test_post_solve_joint_hinge_bar_widths_and_destinations():
    report = runtime.describe_sdf_body_state_projection_contract()
    assert report["post_solve_projection"]["joint"]["width"] == 3
    assert report["post_solve_projection"]["joint"]["positive_apply"] == "FUN_007baa70"
    assert report["post_solve_projection"]["joint"]["negative_apply"] == "FUN_007baaf0"
    assert report["post_solve_projection"]["hinge"]["width"] == 2
    assert report["post_solve_projection"]["bar"]["width"] == 1
    assert report["post_solve_projection"]["bar"]["vector_source"] == "+0x40/+0x48/+0x50"


def test_solver_reset_contract_matches_fun_007b2210():
    report = runtime.describe_sdf_body_state_projection_contract()
    assert report["solver_reset"]["function"] == "FUN_007b2210"
    assert report["solver_reset"]["source_line"] == 812551
    assert report["solver_reset"]["builtin"] == (
        "zero selected matrix row and column, set diagonal to 1.0, zero RHS"
    )


def test_post_solve_order_records_builtin_solver_then_application():
    result = runtime.describe_sdf_post_solve_order()
    assert result["ready"] is True
    assert result["order"][-2:] == [
        "provider vtable +0x18 or FUN_007b0f20",
        "FUN_007b4110 solved-vector application",
    ]


def test_fun_007bc680_preprojection_seed_matches_retail_residual_and_transform():
    result = runtime.evaluate_fun_007bc680_preprojection(
        body_correction=(1.0, 2.0, 3.0),
        body_axis=(4.0, 5.0, 6.0),
        angular_state=(10.0, 20.0, 30.0),
        body_frame=Matrix3x3(
            1.0, 2.0, 3.0,
            4.0, 5.0, 6.0,
            7.0, 8.0, 9.0,
        ),
        linear_state=(2.0, 4.0, 6.0),
        inverse_scalar=0.5,
    )
    assert result["format"] == "SHIFT.SDFBodyPreProjectionRuntime/1"
    assert result["source_function"] == "FUN_007bc680"
    assert result["transform_function"] == "FUN_007aefb0"
    assert result["residual"] == [7.0, 26.0, 27.0]
    assert result["transformed_residual"] == [140.0, 320.0, 500.0]
    assert result["scaled_linear"] == [1.0, 2.0, 3.0]
    assert result["full_constraint_projection_executed"] is False


def test_fun_007bc680_preprojection_rejects_non_finite_seed():
    import pytest

    with pytest.raises(ValueError, match="inverse_scalar must be finite"):
        runtime.evaluate_fun_007bc680_preprojection(
            body_correction=(0.0, 0.0, 0.0),
            body_axis=(0.0, 0.0, 0.0),
            angular_state=(0.0, 0.0, 0.0),
            body_frame=Matrix3x3(
                1.0, 0.0, 0.0,
                0.0, 1.0, 0.0,
                0.0, 0.0, 1.0,
            ),
            linear_state=(0.0, 0.0, 0.0),
            inverse_scalar=float("nan"),
        )
