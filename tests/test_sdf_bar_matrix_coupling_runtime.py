import pytest

from matrix_vector_transform_runtime import Matrix3x3
import sdf_bar_matrix_coupling_runtime as runtime


def test_bar_cross_frame_uses_point_direction_cross_product_then_body_transform():
    result = runtime.evaluate_bar_cross_frame(
        Matrix3x3(
            1, 0, 0,
            0, 2, 0,
            0, 0, 3,
        ),
        (1, 2, 3),
        (4, 5, 6),
    )
    assert result["cross"] == [-3.0, 6.0, -3.0]
    assert result["transformed"] == [-3.0, 12.0, -9.0]


def test_bar_self_coefficient_matches_source_equation():
    result = runtime.evaluate_bar_self_coefficient(
        Matrix3x3(1,0,0,0,2,0,0,0,3),
        point=(1,2,3),
        direction=(4,5,6),
        inverse_scalar=2.0,
    )
    assert result["scalar_coefficient"] == pytest.approx(262.0)
    assert result["storage"]["self_destination"] == (
        "this +0x158 row-pointer table [base][base]"
    )


def test_bar_pair_coefficient_matches_source_equation_and_sign():
    positive = runtime.evaluate_bar_pair_coefficient(
        Matrix3x3(1,0,0,0,1,0,0,0,1),
        outer_point=(1,2,3),
        outer_direction=(4,5,6),
        inner_point=(7,8,9),
        inner_direction=(10,11,12),
        inverse_scalar=2.0,
        outer_base=5,
        inner_base=3,
        same_side=True,
    )
    negative = runtime.evaluate_bar_pair_coefficient(
        Matrix3x3(1,0,0,0,1,0,0,0,1),
        outer_point=(1,2,3),
        outer_direction=(4,5,6),
        inner_point=(7,8,9),
        inner_direction=(10,11,12),
        inverse_scalar=2.0,
        outer_base=5,
        inner_base=3,
        same_side=False,
    )
    assert positive["raw_coefficient"] == pytest.approx(388.0)
    assert positive["coefficient"] == pytest.approx(388.0)
    assert negative["coefficient"] == pytest.approx(-388.0)
    assert positive["storage"]["matrix_cell"] == {"row": 5, "column": 3}


def test_bar_pair_addressing_uses_max_base_for_row():
    result = runtime.evaluate_bar_pair_coefficient(
        Matrix3x3(1,0,0,0,1,0,0,0,1),
        outer_point=(1,0,0),
        outer_direction=(0,1,0),
        inner_point=(0,0,1),
        inner_direction=(1,0,0),
        inverse_scalar=1.0,
        outer_base=2,
        inner_base=7,
        same_side=True,
    )
    assert result["storage"]["matrix_cell"] == {"row": 7, "column": 2}


def test_bar_scalar_application_updates_only_target_cell():
    result = runtime.apply_bar_scalar(
        [[0,0,0],[0,0,0],[0,0,0]],
        row=2,
        column=1,
        value=3.5,
    )
    assert result == [
        [0.0,0.0,0.0],
        [0.0,0.0,0.0],
        [0.0,3.5,0.0],
    ]


def test_bar_matrix_coupling_contract_matches_retail():
    result = runtime.describe_bar_matrix_coupling_contract()
    assert result["function"] == "FUN_007bb6c0"
    assert result["source_line"] == 819471
    assert result["sample_stride"] == 0x60
    assert result["scalar_base_offset"] == "+0x30"
    assert result["side_flag_offset"] == "+0x34"
