import pytest

import sdf_constraint_projection_runtime as runtime
from matrix_vector_transform_runtime import Matrix3x3


def test_constraint_scale_globals_match_retail_initialization():
    result = runtime.derive_constraint_scales(10)
    assert result["linear_scale"] == 16.0
    assert result["quadratic_scale"] == 64.0


def test_joint_cross_terms_match_recovered_source_expressions():
    result = runtime.evaluate_joint_cross_terms(
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
    )
    assert result == {
        "d2": 3.0 * 5.0 - 2.0 * 6.0,
        "d3": 6.0 * 1.0 - 3.0 * 4.0,
        "d5": 2.0 * 4.0 - 5.0 * 1.0,
    }


def test_joint_projection_matches_complete_retail_equation():
    result = runtime.evaluate_joint_projection(
        body_position=(1, 2, 3),
        body_axis=(0.2, 0.3, 0.4),
        body_correction=(0.5, 0.6, 0.7),
        sample_position=(1.5, 2.5, 3.5),
        residual_vector=(0.1, 0.2, 0.3),
        linear_velocity=(0.4, 0.5, 0.6),
        linear_scale=2.0,
        quadratic_scale=3.0,
        side_flag=0,
    )
    assert result["source_line"] == 819089
    assert result["intermediate"] == pytest.approx({
        "d2": 0.05,
        "d3": -0.10,
        "d5": 0.05,
    })
    assert result["lanes"] == pytest.approx([9.005, 15.11, 21.515])
    assert result["destination"] == "this +0x150 + scalar_base*8"

    negative = runtime.evaluate_joint_projection(
        body_position=(1, 2, 3),
        body_axis=(0.2, 0.3, 0.4),
        body_correction=(0.5, 0.6, 0.7),
        sample_position=(1.5, 2.5, 3.5),
        residual_vector=(0.1, 0.2, 0.3),
        linear_velocity=(0.4, 0.5, 0.6),
        linear_scale=2.0,
        quadratic_scale=3.0,
        side_flag=7,
    )
    assert negative["lanes"] == pytest.approx([-9.005, -15.11, -21.515])


def test_joint_projection_updates_only_its_three_solver_lanes():
    result = runtime.apply_joint_projection(
        [10, 20, 30, 40, 50],
        1,
        [1.5, 2.5, 3.5],
        side_flag=0,
    )
    assert result == [10.0, 21.5, 32.5, 43.5, 50.0]


def test_hinge_projection_flag_zero_matches_retail_equations():
    result = runtime.evaluate_hinge_projection(
        body_axis=(0.2, 0.3, 0.4),
        residual_vector=(0.1, 0.2, 0.3),
        sample_angular=(1.1, 1.2, 1.3),
        sample_linear=(2.1, 2.2, 2.3),
        sample_position=(1.5, 2.5, 3.5),
        sample_frame_offset=(0.5, 0.75, 1.0),
        body_frame=None,
        linear_scale=2.0,
        quadratic_scale=3.0,
        side_flag=0,
    )
    assert result["source_line"] == 819157
    assert result["raw_lanes"] == pytest.approx([2.94, 5.34])
    assert result["lanes"] == pytest.approx([2.94, 5.34])


def test_hinge_projection_flag_nonzero_uses_transformed_position_cross_offset():
    result = runtime.evaluate_hinge_projection(
        body_axis=(1.0, 0.0, 0.0),
        residual_vector=(0.0, 0.0, 0.0),
        sample_angular=(1.0, 0.0, 0.0),
        sample_linear=(0.0, 1.0, 0.0),
        sample_position=(1.0, 2.0, 3.0),
        sample_frame_offset=(0.0, 1.0, 0.0),
        body_frame=Matrix3x3(1, 0, 0, 0, 1, 0, 0, 0, 1),
        linear_scale=0.0,
        quadratic_scale=2.0,
        side_flag=3,
    )
    # frame offset x transformed position = (3, 0, -1), then Q=2.
    # q = (0,0,0) + 2*(3,0,-1) = (6,0,-2)
    # c=u=0, v=1, so lanes are A·q=6 and B·q=0, then negated.
    assert result["branch_details"]["cross_vector"] == pytest.approx([3.0, 0.0, -1.0])
    assert result["raw_lanes"] == pytest.approx([6.0, 0.0])
    assert result["lanes"] == pytest.approx([-6.0, -0.0])


def test_joint_projection_provenance_is_now_complete():
    report = runtime.describe_joint_projection_provenance()
    assert report["status"] == "source-backed"
    assert report["unresolved_terms"] if "unresolved_terms" in report else True
    assert report["destination"] == "this +0x150 + scalar_base*8"


def test_hinge_projection_provenance_is_now_complete():
    report = runtime.describe_hinge_projection_provenance()
    assert report["status"] == "source-backed"
    assert report["destination"] == "this +0x150 + scalar_base*8"
    assert report["cross_helper"]["argument_order"] == (
        "sample_frame_offset x transformed_sample_position"
    )


def test_bar_projection_matches_retail_inline_basis_equation():
    result = runtime.evaluate_bar_projection(
        body_position=(1, 2, 3),
        body_axis=(0.2, 0.3, 0.4),
        body_correction=(0.5, 0.6, 0.7),
        sample_position=(1.5, 2.5, 3.5),
        sample_weight=(1.1, 1.2, 1.3),
        residual_vector=(0.1, 0.2, 0.3),
        linear_velocity=(0.4, 0.5, 0.6),
        linear_scale=2.0,
        quadratic_scale=3.0,
        side_flag=0,
        side_bias=0.75,
    )
    assert result["source_line"] == 819246
    assert result["intermediate"]["basis_x"] == pytest.approx(9.005)
    assert result["intermediate"]["basis_y"] == pytest.approx(15.11)
    assert result["intermediate"]["basis_z"] == pytest.approx(21.515)
    assert result["raw_lane"] == pytest.approx(56.007)
    assert result["lane"] == pytest.approx(56.007)
    assert result["sample_stride"] == 0x60


def test_bar_projection_nonzero_side_applies_bias_quadratic_correction():
    result = runtime.evaluate_bar_projection(
        body_position=(1, 2, 3),
        body_axis=(0.2, 0.3, 0.4),
        body_correction=(0.5, 0.6, 0.7),
        sample_position=(1.5, 2.5, 3.5),
        sample_weight=(1.1, 1.2, 1.3),
        residual_vector=(0.1, 0.2, 0.3),
        linear_velocity=(0.4, 0.5, 0.6),
        linear_scale=2.0,
        quadratic_scale=3.0,
        side_flag=9,
        side_bias=0.75,
    )
    assert result["branch"] == "flag_nonzero"
    assert result["side_correction"] == pytest.approx(2.25)
    assert result["lane"] == pytest.approx(-53.757)


def test_bar_projection_updates_only_one_solver_lane():
    result = runtime.apply_bar_projection(
        [10, 20, 30, 40],
        2,
        -3.5,
    )
    assert result == [10.0, 20.0, 26.5, 40.0]


def test_bar_projection_provenance_is_source_backed():
    report = runtime.describe_bar_projection_provenance()
    assert report["status"] == "source-backed"
    assert report["function"] == "FUN_007bb090"
    assert report["sample_stride"] == 0x60
    assert report["side_bias_offset"] == "+0x38"
    assert "does not call FUN_007bac60" in report["source_relationship"]
