import pytest

from matrix_vector_transform_runtime import Matrix3x3
import sdf_hinge_matrix_coupling_runtime as runtime


def test_hinge_row_transform_uses_body_frame_for_angular_and_linear_rows():
    result = runtime.transform_hinge_rows(
        Matrix3x3(
            1, 0, 0,
            0, 2, 0,
            0, 0, 3,
        ),
        (1, 2, 3),
        (4, 5, 6),
    )
    assert result["angular"] == [1.0, 4.0, 9.0]
    assert result["linear"] == [4.0, 10.0, 18.0]


def test_hinge_self_lower_block_matches_source_dot_products():
    result = runtime.evaluate_hinge_self_lower_block(
        Matrix3x3(
            1, 0, 0,
            0, 2, 0,
            0, 0, 3,
        ),
        (1, 2, 3),
        (4, 5, 6),
    )
    assert result["self_block"] == {
        "row_base_col_base": 36.0,
        "row_base_plus_1_col_base": 88.0,
        "row_base_plus_1_col_base_plus_1": 192.0,
    }


def test_hinge_pair_block_inner_before_outer_matches_source_orientation():
    result = runtime.evaluate_hinge_pair_block(
        Matrix3x3(1,0,0,0,1,0,0,0,1),
        outer_angular=(1, 2, 3),
        outer_linear=(4, 5, 6),
        inner_angular=(7, 8, 9),
        inner_linear=(10, 11, 12),
        outer_base=4,
        inner_base=2,
        same_side=True,
    )
    assert result["raw_coefficients"] == {
        "d5": 50.0,
        "d6": 68.0,
        "d8": 122.0,
        "d7": 167.0,
    }
    assert result["block"] == [
        [50.0, 68.0],
        [122.0, 167.0],
    ]
    assert result["storage_orientation"] == "outer_rows_by_inner_columns"


def test_hinge_pair_block_inner_after_outer_transposes_off_diagonal_layout():
    result = runtime.evaluate_hinge_pair_block(
        Matrix3x3(1,0,0,0,1,0,0,0,1),
        outer_angular=(1, 2, 3),
        outer_linear=(4, 5, 6),
        inner_angular=(7, 8, 9),
        inner_linear=(10, 11, 12),
        outer_base=2,
        inner_base=4,
        same_side=False,
    )
    assert result["block"] == [
        [-50.0, -122.0],
        [-68.0, -167.0],
    ]
    assert result["storage_orientation"] == "inner_rows_by_outer_columns"


def test_hinge_pair_block_application_updates_only_target_cells():
    matrix = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    result = runtime.apply_hinge_pair_block(
        matrix,
        row_base=1,
        col_base=2,
        block=((1, 2), (3, 4)),
    )
    assert result == [
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 2.0],
        [0.0, 0.0, 3.0, 4.0],
        [0.0, 0.0, 0.0, 0.0],
    ]


def test_hinge_matrix_coupling_contract_matches_retail():
    result = runtime.describe_hinge_matrix_coupling_contract()
    assert result["function"] == "FUN_007bb250"
    assert result["source_line"] == 819302
    assert result["self_block"]["upper_off_diagonal"] == "not written by this helper"
    assert result["pair_block"]["same_side"] == "add"
    assert result["pair_block"]["different_side"] == "subtract"
