import pytest

import sdf_constraint_seed_write_runtime as runtime


def test_seed_write_enumeration_accepts_only_one_zero_or_one():
    result = runtime.enumerate_seed_writes(
        [
            [1, 0, 1],
            [0, 0, 0],
            [1, 0, 1],
        ]
    )
    assert len(result) == 4
    assert result[0] == {"row": 0, "column": 0, "value": 1.0}
    assert result[-1] == {"row": 2, "column": 2, "value": 1.0}


def test_seed_matrix_reports_symmetry_and_diagonal():
    result = runtime.materialize_seed_matrix(
        [
            [1, 1, 0],
            [1, 1, 1],
            [0, 1, 1],
        ]
    )
    assert result["write_count"] == 7
    assert result["diagonal_one"] is True
    assert result["symmetric"] is True
    assert result["row_nonzero_counts"] == [2, 3, 2]
    assert result["matrix_bit_hash_sha256"] == (
        "e42efb4f8a4f56d8f1d79dc0ed19d30fca4da1e2a7c9b0bc6e035aa21f5b7a13"
    )


def test_seed_matrix_rejects_non_binary_coefficients():
    with pytest.raises(ValueError, match="only 0.0 and 1.0"):
        runtime.materialize_seed_matrix(
            [
                [1.0, 0.5],
                [0.5, 1.0],
            ]
        )


def test_seed_write_application_is_additive():
    result = runtime.apply_seed_writes(
        [[2, 3], [4, 5]],
        [
            {"row": 0, "column": 0, "value": 1.0},
            {"row": 1, "column": 0, "value": 1.0},
        ],
    )
    assert result == [[3.0, 3.0], [5.0, 5.0]]


def test_seed_write_contract_is_source_backed():
    result = runtime.describe_seed_write_contract()
    assert result["function"] == "FUN_007ba2b0"
    assert result["source_line"] == 818608
    assert result["value"] == 1.0
    assert result["storage"]["matrix_pool"] == "+0x154"
