import pytest

import sdf_post_solve_runtime as runtime


def _body():
    return {"angular": [10.0, 20.0, 30.0], "linear": [1.0, 2.0, 3.0]}


def test_joint_solution_uses_three_scalars_and_positive_negative_helpers():
    result = runtime.apply_joint_solution(
        _body(),
        _body(),
        positive_point=(1, 0, 0),
        negative_point=(0, 1, 0),
        solved=(2, 3, 4),
    )
    assert result["constraint"] == "JOINT"
    assert result["positive"]["linear"] == [3.0, 5.0, 7.0]
    assert result["negative"]["linear"] == [-1.0, -1.0, -1.0]
    assert result["positive"]["angular"] == [10.0, 24.0, 27.0]
    assert result["negative"]["angular"] == [6.0, 20.0, 28.0]


def test_hinge_solution_updates_only_angular_state_with_two_solved_scalars():
    result = runtime.apply_hinge_solution(
        _body(),
        _body(),
        sample_angular=(1, 2, 3),
        sample_linear=(4, 5, 6),
        solved=(2, 3),
    )
    assert result["angular_delta"] == [14.0, 19.0, 24.0]
    assert result["positive"]["angular"] == [24.0, 39.0, 54.0]
    assert result["negative"]["angular"] == [-4.0, 1.0, 6.0]
    assert result["positive"]["linear"] == [1.0, 2.0, 3.0]
    assert result["negative"]["linear"] == [1.0, 2.0, 3.0]


def test_bar_solution_scales_direction_and_uses_body_helpers():
    result = runtime.apply_bar_solution(
        _body(),
        _body(),
        positive_point=(1, 0, 0),
        negative_point=(0, 1, 0),
        direction=(1, 2, 3),
        solved=2,
    )
    assert result["contribution"] == [2.0, 4.0, 6.0]
    assert result["positive"]["linear"] == [3.0, 6.0, 9.0]
    assert result["negative"]["linear"] == [-1.0, -2.0, -3.0]


def test_post_solve_contract_matches_retail_widths_and_order():
    report = runtime.describe_post_solve_application_contract()
    assert report["function"] == "FUN_007b4110"
    assert report["solver_vector"] == "PhysicsSystem +0x40"
    assert report["constraints"]["JOINT"]["width"] == 3
    assert report["constraints"]["HINGE"]["width"] == 2
    assert report["constraints"]["BAR"]["width"] == 1
    assert report["order"] == ["JOINT", "HINGE", "BAR"]


def test_joint_and_bar_reject_wrong_scalar_width():
    with pytest.raises(ValueError, match="JOINT"):
        runtime.apply_joint_solution(
            _body(), _body(),
            positive_point=(0,0,0),
            negative_point=(0,0,0),
            solved=(1, 2),
        )
