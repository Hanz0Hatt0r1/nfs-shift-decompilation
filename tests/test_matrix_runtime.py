import pytest

from matrix_runtime import matrix_to_4x4, normalize_matrix_contract, parse_matrix


def test_orientation_is_reordered_to_internal_wxyz():
    result = parse_matrix(
        offset=[1, 2, 3],
        orientation_input=[0.1, 0.2, 0.3, 0.4],
        scale=2,
    )
    assert result["quaternion_internal_wxyz"] == [0.4, 0.1, 0.2, 0.3]
    assert result["offset"] == [1.0, 2.0, 3.0]
    assert result["scale"] == 2.0


def test_missing_scale_defaults_to_one():
    assert parse_matrix(orientation_input=[0, 0, 0, 1])["scale"] == 1.0


def test_matrix_to_4x4_preserves_translation():
    result = parse_matrix(offset=[1, 2, 3], orientation_input=[0, 0, 0, 1])
    matrix = matrix_to_4x4(result)
    assert matrix[3:4] == [1.0]
    assert matrix[7:8] == [2.0]
    assert matrix[11:12] == [3.0]
    assert matrix[15] == 1.0


def test_invalid_vector_length_is_rejected():
    with pytest.raises(ValueError):
        parse_matrix(offset=[1, 2], orientation_input=[0, 0, 0, 1])


def test_normalize_keeps_unknown_fields_out_of_contract():
    result = normalize_matrix_contract({
        "offset": [0, 0, 0],
        "quaternion_internal_wxyz": [1, 0, 0, 0],
        "scale": 1,
        "unknown": "not interpreted",
    })
    assert result["validated"] is True
    assert "unknown" not in result
