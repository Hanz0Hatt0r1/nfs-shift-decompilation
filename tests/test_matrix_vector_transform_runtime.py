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
    build_contract,
    transform_fun_007aefb0,
    transform_fun_007af010,
    transform_fun_007af0a0,
    transform_vector,
)


def test_fun_007af0a0_matches_retail_machine_component_order():
    m = Matrix3x3(
        1, 2, 3,
        4, 5, 6,
        7, 8, 9,
    )
    out = transform_vector(m, (10, 20, 30))
    assert out.as_tuple() == pytest.approx((300, 360, 420))


def test_identity_matrix_preserves_full_double_vector_precision():
    m = Matrix3x3(
        1, 0, 0,
        0, 1, 0,
        0, 0, 1,
    )
    perturbation = 1.0 + 2.0 ** -30
    assert float(perturbation) != 1.0
    out = transform_fun_007aefb0(m, (perturbation, -2.0, 3.25))
    assert out.x == perturbation
    assert out.y == -2.0
    assert out.z == 3.25


def test_transpose_identity_preserves_full_double_vector_precision():
    m = Matrix3x3(
        1, 0, 0,
        0, 1, 0,
        0, 0, 1,
    )
    perturbation = -1.0 - 2.0 ** -31
    out = transform_fun_007af0a0(m, (perturbation, 2.0, -3.0))
    assert out.x == perturbation
    assert out.y == 2.0
    assert out.z == -3.0


def test_fun_007af010_scales_first_column_with_double_scalar():
    m = Matrix3x3(
        1, 2, 3,
        4, 5, 6,
        7, 8, 9,
    )
    scalar = 1.0 + 2.0 ** -30
    out = transform_fun_007af010(m, scalar)
    assert out.as_tuple() == (scalar, 4.0 * scalar, 7.0 * scalar)


def test_contract_freezes_machine_operand_widths_hashes_and_offsets():
    c = build_contract()
    assert c["format"] == "SHIFT.MatrixVectorTransformRuntime/3"
    assert c["matrix_float_offsets"]["row0"] == ["0x00", "0x04", "0x08"]
    assert c["matrix_float_offsets"]["row1"] == ["0x0c", "0x10", "0x14"]
    assert c["matrix_float_offsets"]["row2"] == ["0x18", "0x1c", "0x20"]
    assert c["input_conversion"].startswith("QWORD vector/scalar operands")
    assert c["numeric_boundary"]["input_components_are_cast_to_float"] is False
    assert c["numeric_boundary"]["machine_vector_operand_width_bits"] == 64
    assert c["numeric_boundary"]["matrix_component_width_bits"] == 32
    assert c["numeric_boundary"]["output_component_width_bits"] == 64
    assert c["helpers"]["FUN_007aefb0"]["sha256"] == (
        "76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29"
    )
    assert c["helpers"]["FUN_007af010"]["sha256"] == (
        "f3256201dee28b97260576ee14c522e236a44d1808516ed8e42efd2e2e2e8324"
    )
    assert c["helpers"]["FUN_007af0a0"]["sha256"] == (
        "8cd039935dbbe493db7742f7af1859d9abcc7d9c40f212c3f2fa331e992c52cc"
    )
    assert M00_OFFSET == 0x00
    assert M01_OFFSET == 0x04
    assert M02_OFFSET == 0x08
    assert M10_OFFSET == 0x0C
    assert M11_OFFSET == 0x10
    assert M12_OFFSET == 0x14
    assert M20_OFFSET == 0x18
    assert M21_OFFSET == 0x1C
    assert M22_OFFSET == 0x20


def test_invalid_vector_size_and_nonfinite_scalar_rejected():
    with pytest.raises(ValueError):
        transform_vector(Matrix3x3(1,2,3,4,5,6,7,8,9), (1.0, 2.0))
    with pytest.raises(ValueError):
        transform_fun_007af010(Matrix3x3(1,2,3,4,5,6,7,8,9), float("inf"))


def test_fun_007aefb0_is_exposed_by_retail_function_name():
    matrix = Matrix3x3(
        1, 2, 3,
        4, 5, 6,
        7, 8, 9,
    )
    assert transform_fun_007aefb0(matrix, (10, 20, 30)).as_tuple() == pytest.approx((140, 320, 500))


def test_build_contract_freezes_transform_trio():
    contract = build_contract()
    assert contract["helpers"]["FUN_007af0a0"]["canonical_api"] == "transform_fun_007af0a0"
    assert contract["helpers"]["FUN_007aefb0"]["canonical_api"] == "transform_fun_007aefb0"
    assert contract["helpers"]["FUN_007af010"]["canonical_api"] == "transform_fun_007af010"
    assert contract["helpers"]["FUN_007aefb0"]["source_line"] == 810220
    assert contract["helpers"]["FUN_007af010"]["source_line"] == 810237
    assert contract["helpers"]["FUN_007af0a0"]["source_line"] == 810279
