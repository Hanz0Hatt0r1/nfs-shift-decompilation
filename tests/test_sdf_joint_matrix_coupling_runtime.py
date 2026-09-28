import pytest

import sdf_joint_matrix_coupling_runtime as runtime


IDENTITY = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


def test_joint_tensor_terms_match_source_intermediates():
    result = runtime.derive_joint_tensor_terms(IDENTITY, (1.0, 2.0, 3.0))
    assert result == {
        "d6": 0.0,
        "d10": 3.0,
        "d1": -2.0,
        "d2": -3.0,
        "d3": 0.0,
        "d12": 1.0,
        "d15": 2.0,
        "d19": -1.0,
        "d18": 0.0,
    }


def test_joint_self_block_matches_source_lower_triangle():
    result = runtime.evaluate_joint_self_block(
        IDENTITY,
        joint_position=(1.0, 2.0, 3.0),
        inverse_scalar=2.0,
    )
    assert result["lower_triangle"] == {
        "00": 15.0,
        "10": -2.0,
        "11": 12.0,
        "20": -3.0,
        "21": -6.0,
        "22": 7.0,
    }


def test_joint_joint_pair_block_matches_source():
    result = runtime.evaluate_joint_joint_pair_block(
        IDENTITY,
        outer_position=(1.0, 2.0, 3.0),
        inner_position=(4.0, 5.0, 6.0),
        inverse_scalar=2.0,
        outer_base=5,
        inner_base=2,
        same_side=True,
    )
    assert result["raw_block"] == [
        [30.0, -8.0, -12.0],
        [-5.0, 24.0, -15.0],
        [-6.0, -12.0, 16.0],
    ]
    assert result["storage_orientation"] == "outer_rows_by_inner_columns"


def test_joint_joint_pair_block_reverses_layout_and_sign():
    result = runtime.evaluate_joint_joint_pair_block(
        IDENTITY,
        outer_position=(1.0, 2.0, 3.0),
        inner_position=(4.0, 5.0, 6.0),
        inverse_scalar=2.0,
        outer_base=2,
        inner_base=5,
        same_side=False,
    )
    assert result["block"] == [
        [-30.0, 5.0, 6.0],
        [8.0, -24.0, 12.0],
        [12.0, 15.0, -16.0],
    ]
    assert result["storage_orientation"] == "inner_rows_by_outer_columns"


def test_joint_hinge_pair_block_matches_source():
    result = runtime.evaluate_joint_hinge_pair_block(
        IDENTITY,
        joint_position=(1.0, 2.0, 3.0),
        hinge_angular=(4.0, 5.0, 6.0),
        hinge_linear=(7.0, 8.0, 9.0),
        inverse_scalar=2.0,
        joint_base=5,
        hinge_base=2,
        same_side=True,
    )
    assert result["block"] == [
        [3.0, 6.0],
        [-6.0, -12.0],
        [3.0, 6.0],
    ]
    assert result["storage_orientation"] == "joint_rows_by_hinge_columns"


def test_joint_hinge_pair_block_reverses_layout_and_sign():
    result = runtime.evaluate_joint_hinge_pair_block(
        IDENTITY,
        joint_position=(1.0, 2.0, 3.0),
        hinge_angular=(4.0, 5.0, 6.0),
        hinge_linear=(7.0, 8.0, 9.0),
        inverse_scalar=2.0,
        joint_base=2,
        hinge_base=5,
        same_side=False,
    )
    assert result["block"] == [
        [-3.0, 6.0, -3.0],
        [-6.0, 12.0, -6.0],
    ]
    assert result["storage_orientation"] == "hinge_rows_by_joint_columns"


def test_joint_bar_pair_block_matches_source():
    result = runtime.evaluate_joint_bar_pair_block(
        IDENTITY,
        joint_position=(1.0, 2.0, 3.0),
        bar_point=(4.0, 5.0, 6.0),
        bar_direction=(7.0, 8.0, 9.0),
        inverse_scalar=2.0,
        joint_base=5,
        bar_base=2,
        same_side=True,
    )
    assert result["raw_block"] == [38.0, 22.0, 6.0]
    assert result["block"] == [[38.0], [22.0], [6.0]]
    assert result["storage_orientation"] == "joint_rows_by_bar_column"


def test_joint_bar_pair_block_reverses_layout_and_sign():
    result = runtime.evaluate_joint_bar_pair_block(
        IDENTITY,
        joint_position=(1.0, 2.0, 3.0),
        bar_point=(4.0, 5.0, 6.0),
        bar_direction=(7.0, 8.0, 9.0),
        inverse_scalar=2.0,
        joint_base=2,
        bar_base=5,
        same_side=False,
    )
    assert result["block"] == [[-38.0, -22.0, -6.0]]
    assert result["storage_orientation"] == "bar_row_by_joint_columns"


def test_lower_triangle_block_application_updates_expected_cells():
    result = runtime.apply_lower_triangle_block(
        [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        row_base=1,
        column_base=0,
        block=((1, 2), (3, 4)),
    )
    assert result == [
        [0.0, 0.0, 0.0],
        [1.0, 2.0, 0.0],
        [3.0, 4.0, 0.0],
    ]


def test_joint_matrix_coupling_contract_matches_retail_function():
    result = runtime.describe_joint_matrix_coupling_contract()
    assert result["function"] == "FUN_007bbb80"
    assert result["source_line"] == 819720
    assert result["mixed"]["hinge"]["block_shape"] == "3x2"
    assert result["mixed"]["bar"]["block_shape"] == "3x1"
    assert result["sign_rule"] == "equal side flags add; differing flags subtract"


def test_joint_self_block_with_off_diagonal_tensor_matches_source():
    tensor = (
        (2.0, 1.0, 3.0),
        (1.0, 4.0, 2.0),
        (3.0, 2.0, 5.0),
    )
    result = runtime.evaluate_joint_self_block(
        tensor,
        joint_position=(1.0, 2.0, 3.0),
        inverse_scalar=2.0,
    )
    assert result["intermediates"]["d15"] == 1.0
    assert result["lower_triangle"] == {
        "00": 34.0,
        "10": -1.0,
        "11": 10.0,
        "20": -14.0,
        "21": 1.0,
        "22": 6.0,
    }



def test_joint_tensor_d15_uses_m01_not_m02():
    result = runtime.derive_joint_tensor_terms(
        (
            (2.0, 3.0, 4.0),
            (3.0, 5.0, 6.0),
            (4.0, 6.0, 7.0),
        ),
        (1.0, 2.0, 3.0),
    )
    assert result["d15"] == 1.0


def test_joint_self_block_exposes_non_degenerate_d15_effect():
    result = runtime.evaluate_joint_self_block(
        (
            (2.0, 3.0, 4.0),
            (3.0, 5.0, 6.0),
            (4.0, 6.0, 7.0),
        ),
        joint_position=(1.0, 2.0, 3.0),
        inverse_scalar=1.0,
    )
    assert result["intermediates"]["d15"] == 1.0
