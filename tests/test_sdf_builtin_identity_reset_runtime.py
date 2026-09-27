import pytest

import sdf_builtin_identity_reset_runtime as runtime


def _matrix_pool(n: int) -> list[float]:
    return [float(row * n + col + 1) for row in range(n) for col in range(n)]


def test_identity_reset_matches_retail_row_column_order():
    result = runtime.apply_identity_reset_to_row_storage(
        _matrix_pool(4),
        scalar_count=4,
        row_indices=[0, 4, 8, 12],
        node=2,
        rhs=[10, 20, 30, 40],
    )
    assert result["matrix_pool"] == [
        1.0, 2.0, 0.0, 4.0,
        5.0, 6.0, 0.0, 8.0,
        0.0, 0.0, 1.0, 0.0,
        13.0, 14.0, 0.0, 16.0,
    ]
    assert result["rhs"] == [10.0, 20.0, 0.0, 40.0]


def test_identity_reset_sets_diagonal_after_both_zero_passes():
    result = runtime.apply_identity_reset_to_row_storage(
        _matrix_pool(3),
        scalar_count=3,
        row_indices=[0, 3, 6],
        node=1,
        rhs=[1, 2, 3],
    )
    assert result["matrix_pool"][4] == 1.0
    assert result["matrix_pool"][1] == 0.0
    assert result["matrix_pool"][3] == 0.0
    assert result["rhs"][1] == 0.0


def test_identity_reset_supports_multiple_selected_nodes():
    result = runtime.apply_identity_resets_to_row_storage(
        _matrix_pool(4),
        scalar_count=4,
        row_indices=[0, 4, 8, 12],
        nodes=[1, 3, 1],
        rhs=[1, 2, 3, 4],
    )
    assert result["nodes"] == [1, 3]
    assert result["rhs"] == [1.0, 0.0, 3.0, 0.0]
    assert result["matrix_pool"] == [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 9.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def test_identity_reset_rejects_invalid_storage_shape():
    with pytest.raises(ValueError, match="shorter"):
        runtime.apply_identity_reset_to_row_storage(
            [0.0, 1.0],
            scalar_count=2,
            row_indices=[0, 2],
            node=1,
            rhs=[0.0, 0.0],
        )


def test_identity_reset_contract_exposes_provider_boundary():
    report = runtime.describe_identity_reset_contract()
    assert report["function"] == "FUN_007b2210"
    assert report["source_line"] == 812551
    assert report["provider_path"]["provider_pointer"] == "physics-system +0x48"
    assert report["provider_path"]["virtual_slot"] == "+0x1c"


def test_identity_reset_preserves_unselected_rhs_and_matrix_cells():
    result = runtime.apply_identity_reset_to_row_storage(
        [float(i) for i in range(1, 17)],
        scalar_count=4,
        row_indices=[0, 4, 8, 12],
        node=1,
        rhs=[10, 20, 30, 40],
    )
    assert result["rhs"] == [10.0, 0.0, 30.0, 40.0]
    assert result["matrix_pool"][0] == 1.0
    assert result["matrix_pool"][2] == 3.0
    assert result["matrix_pool"][8] == 9.0
    assert result["matrix_pool"][10] == 11.0
