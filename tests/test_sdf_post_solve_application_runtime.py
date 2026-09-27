import pytest

import sdf_post_solve_application_runtime as runtime


def test_joint_solution_uses_three_solved_scalars_and_positive_negative_helpers():
    result = runtime.apply_joint_solution(
        positive_state={"angular": [0, 0, 0], "linear": [10, 20, 30]},
        negative_state={"angular": [1, 2, 3], "linear": [4, 5, 6]},
        solver_vector=[9, 10, 20, 30, 40],
        scalar_base=1,
        positive_lever_arm=(1, 2, 3),
        negative_lever_arm=(4, 5, 6),
    )
    assert result["solution"] == [10.0, 20.0, 30.0]
    assert result["positive"]["linear"] == [20.0, 40.0, 60.0]
    assert result["positive"]["angular"] == [0.0, 0.0, 0.0]
    assert result["negative"]["linear"] == [-6.0, -15.0, -24.0]
    assert result["positive"]["delta"]["source_function"] == "FUN_007baa70"
    assert result["negative"]["delta"]["source_function"] == "FUN_007baaf0"


def test_hinge_angular_delta_matches_direct_two_scalar_update():
    result = runtime.hinge_angular_delta(
        [2.0, 3.0],
        angular_row=(1.0, 2.0, 3.0),
        linear_row=(4.0, 5.0, 6.0),
        sign=1,
    )
    assert result["angular_delta"] == pytest.approx([14.0, 19.0, 24.0])

    negative = runtime.hinge_angular_delta(
        [2.0, 3.0],
        angular_row=(1.0, 2.0, 3.0),
        linear_row=(4.0, 5.0, 6.0),
        sign=-1,
    )
    assert negative["angular_delta"] == pytest.approx([-14.0, -19.0, -24.0])


def test_hinge_solution_updates_only_angular_channels():
    result = runtime.apply_hinge_solution(
        positive_angular=(1.0, 2.0, 3.0),
        negative_angular=(4.0, 5.0, 6.0),
        solver_vector=[0.0, 0.0, 2.0, 3.0],
        scalar_base=2,
        positive_angular_row=(1.0, 2.0, 3.0),
        positive_linear_row=(4.0, 5.0, 6.0),
        negative_angular_row=(2.0, 1.0, 0.0),
        negative_linear_row=(0.0, 3.0, 4.0),
    )
    assert result["positive_angular"] == pytest.approx([15.0, 21.0, 27.0])
    assert result["negative_angular"] == pytest.approx([0.0, -6.0, -6.0])
    assert result["positive_delta"] == pytest.approx([14.0, 19.0, 24.0])
    assert result["negative_delta"] == pytest.approx([-4.0, -11.0, -12.0])


def test_bar_solution_scales_direction_by_one_solved_scalar():
    result = runtime.apply_bar_solution(
        positive_state={"angular": [0, 0, 0], "linear": [0, 0, 0]},
        negative_state={"angular": [0, 0, 0], "linear": [0, 0, 0]},
        solver_vector=[0.0, 0.0, 3.0],
        scalar_base=2,
        positive_lever_arm=(1.0, 0.0, 0.0),
        negative_lever_arm=(2.0, 0.0, 0.0),
        bar_direction=(2.0, 3.0, 4.0),
    )
    assert result["solution_scalar"] == 3.0
    assert result["vector_solution"] == pytest.approx([6.0, 9.0, 12.0])
    assert result["positive"]["linear"] == pytest.approx([6.0, 9.0, 12.0])
    assert result["negative"]["linear"] == pytest.approx([-6.0, -9.0, -12.0])
    assert result["positive"]["angular"] == pytest.approx([0.0, -12.0, 9.0])
    assert result["negative"]["angular"] == pytest.approx([0.0, 24.0, -18.0])


def test_post_solve_contract_matches_retail():
    report = runtime.describe_post_solve_application_contract()
    assert report["function"] == "FUN_007b4110"
    assert report["source_line"] == 814168
    assert report["constraints"]["JOINT"]["width"] == 3
    assert report["constraints"]["HINGE"]["width"] == 2
    assert report["constraints"]["BAR"]["width"] == 1
    assert report["constraints"]["HINGE"]["positive_update"].startswith(
        "direct angular + solved[0]*angular_row"
    )


def test_post_solve_rejects_short_solver_vector():
    with pytest.raises(ValueError, match="outside solver vector"):
        runtime.apply_bar_solution(
            positive_state={"angular": [0, 0, 0], "linear": [0, 0, 0]},
            negative_state={"angular": [0, 0, 0], "linear": [0, 0, 0]},
            solver_vector=[1.0],
            scalar_base=1,
            positive_lever_arm=(0, 0, 0),
            negative_lever_arm=(0, 0, 0),
            bar_direction=(1, 0, 0),
        )
