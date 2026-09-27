import pytest

from matrix_vector_transform_runtime import Matrix3x3
import sdf_hinge_bar_matrix_coupling_runtime as runtime


def test_hinge_bar_pair_block_matches_source_for_identity_frame():
    result = runtime.evaluate_hinge_bar_pair(
        Matrix3x3(1,0,0,0,1,0,0,0,1),
        hinge_angular=(2,3,4),
        hinge_linear=(5,6,7),
        bar_point=(1,0,2),
        bar_direction=(3,4,5),
        hinge_base=6,
        bar_base=2,
        same_side=True,
    )
    assert result["raw_coefficients"] == {"d5": 3.0, "d6": -6.0}
    assert result["block"] == [[3.0], [-6.0]]
    assert result["storage_orientation"] == "hinge_rows_by_bar_column"


def test_hinge_bar_pair_block_reverses_orientation_and_sign():
    result = runtime.evaluate_hinge_bar_pair(
        Matrix3x3(1,0,0,0,1,0,0,0,1),
        hinge_angular=(2,3,4),
        hinge_linear=(5,6,7),
        bar_point=(1,0,2),
        bar_direction=(3,4,5),
        hinge_base=2,
        bar_base=6,
        same_side=False,
    )
    assert result["block"] == [[-3.0, 6.0]]
    assert result["storage_orientation"] == "bar_row_by_hinge_columns"


def test_hinge_bar_block_application_updates_only_target_cells():
    result = runtime.apply_hinge_bar_block(
        [[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
        row_base=1,
        column_base=0,
        block=((2.0,), (-3.0,)),
    )
    assert result == [
        [0.0,0.0,0.0],
        [2.0,0.0,0.0],
        [-3.0,0.0,0.0],
        [0.0,0.0,0.0],
    ]


def test_hinge_bar_matrix_contract_matches_retail():
    result = runtime.describe_hinge_bar_matrix_coupling_contract()
    assert result["function"] == "FUN_007bb250"
    assert result["source_line"] == 819302
    assert result["block"]["shape"] == "2x1"
    assert result["block"]["same_side"] == "add"
    assert result["block"]["different_side"] == "subtract"


def test_hinge_bar_pair_rejects_invalid_body_frame_dimensions():
    with pytest.raises(ValueError, match="3x3"):
        runtime.evaluate_hinge_bar_pair(
            Matrix3x3(1,0,0,0,1,0,0,0,1),
            hinge_angular=(1,2),
            hinge_linear=(1,2,3),
            bar_point=(1,2,3),
            bar_direction=(1,2,3),
            hinge_base=2,
            bar_base=1,
            same_side=True,
        )
