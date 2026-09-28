import pytest

from matrix_vector_transform_runtime import (
    M00_OFFSET,
    M01_OFFSET,
    M02_OFFSET,
    M10_OFFSET,
    M11_OFFSET,
    M12_OFFSET,
    M20_OFFSET,
    M21_OFFSET,
    M22_OFFSET,
    Matrix3x3,
    Vec3,
    build_contract,
    transform_vector,
)


def test_fun_007af0a0_matches_recovered_component_order():
    m = Matrix3x3(
        1, 2, 3,
        4, 5, 6,
        7, 8, 9,
    )
    out = transform_vector(m, (10, 20, 30))
    assert out.as_tuple() == pytest.approx((300, 360, 420))


def test_identity_matrix_preserves_vector():
    m = Matrix3x3(
        1, 0, 0,
        0, 1, 0,
        0, 0, 1,
    )
    out = transform_vector(m, (1.5, -2.0, 3.25))
    assert out.as_tuple() == pytest.approx((1.5, -2.0, 3.25))


def test_contract_freezes_float_matrix_offsets():
    c = build_contract()
    assert c["matrix_float_offsets"]["row0"] == ["0x00", "0x04", "0x08"]
    assert c["matrix_float_offsets"]["row1"] == ["0x0c", "0x10", "0x14"]
    assert c["matrix_float_offsets"]["row2"] == ["0x18", "0x1c", "0x20"]
    assert c["input_conversion"] == "each double input component is cast to float32"
    assert M00_OFFSET == 0x00
    assert M01_OFFSET == 0x04
    assert M02_OFFSET == 0x08
    assert M10_OFFSET == 0x0C
    assert M11_OFFSET == 0x10
    assert M12_OFFSET == 0x14
    assert M20_OFFSET == 0x18
    assert M21_OFFSET == 0x1C
    assert M22_OFFSET == 0x20


def test_invalid_vector_size_rejected():
    with pytest.raises(ValueError):
        transform_vector(Matrix3x3(1,2,3,4,5,6,7,8,9), (1.0, 2.0))


def test_fun_007aefb0_is_exposed_by_retail_function_name():
    matrix = Matrix3x3(
        1, 2, 3,
        4, 5, 6,
        7, 8, 9,
    )
    from matrix_vector_transform_runtime import transform_fun_007aefb0
    assert transform_fun_007aefb0(matrix, (10, 20, 30)).as_tuple() == pytest.approx((140, 320, 500))


def test_build_contract_freezes_both_retail_helpers():
    contract = build_contract()
    assert contract["helpers"]["FUN_007af0a0"]["canonical_api"] == "transform_fun_007af0a0"
    assert contract["helpers"]["FUN_007aefb0"]["canonical_api"] == "transform_fun_007aefb0"
    assert contract["helpers"]["FUN_007aefb0"]["source_line"] == 810220
