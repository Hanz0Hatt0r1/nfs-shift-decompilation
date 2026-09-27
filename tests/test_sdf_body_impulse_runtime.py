import pytest

import sdf_body_impulse_runtime as runtime


def test_positive_body_accumulator_delta_matches_retail_cross_product():
    result = runtime.body_accumulator_delta(
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
        sign=1,
    )
    assert result["source_function"] == "FUN_007baa70"
    assert result["linear_delta"] == [4.0, 5.0, 6.0]
    assert result["angular_delta"] == [-3.0, 6.0, -3.0]
    assert result["storage_offsets"]["angular"] == ["+0x48", "+0x50", "+0x58"]


def test_negative_body_accumulator_delta_matches_retail_subtraction():
    result = runtime.body_accumulator_delta(
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
        sign=-1,
    )
    assert result["source_function"] == "FUN_007baaf0"
    assert result["linear_delta"] == [-4.0, -5.0, -6.0]
    assert result["angular_delta"] == [3.0, -6.0, 3.0]


def test_apply_body_accumulator_delta_is_source_symmetric():
    positive = runtime.apply_body_accumulator_delta(
        {"angular": [10, 20, 30], "linear": [1, 2, 3]},
        (1, 0, 0),
        (0, 2, 0),
        sign=1,
    )
    negative = runtime.apply_body_accumulator_delta(
        {"angular": [10, 20, 30], "linear": [1, 2, 3]},
        (1, 0, 0),
        (0, 2, 0),
        sign=-1,
    )
    assert positive["angular"] == [10.0, 20.0, 32.0]
    assert positive["linear"] == [1.0, 4.0, 3.0]
    assert negative["angular"] == [10.0, 20.0, 28.0]
    assert negative["linear"] == [1.0, 0.0, 3.0]


def test_body_accumulator_delta_rejects_non_unit_sign():
    with pytest.raises(ValueError, match="sign"):
        runtime.body_accumulator_delta((0, 0, 0), (1, 1, 1), sign=0)
