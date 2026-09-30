import struct

import pytest

from vulkan_world_transform_packet import (
    CONVENTION_D3D_ROW_TO_GLSL_COLUMN,
    FORMAT,
    HEADER,
    MAGIC,
    MATRIX,
    VERSION,
    build_vulkan_world_transform_packet,
    transform_point_d3d_row_vector,
)


def _world(tx=10.0, ty=20.0, tz=30.0):
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        tx, ty, tz, 1.0,
    ]


def test_world_transform_packet_preserves_d3d_row_major_bytes(tmp_path):
    output = tmp_path / "world_transform.svwt"
    report = build_vulkan_world_transform_packet(
        {"world_matrix": _world()},
        output,
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["translation_xyz"] == [10.0, 20.0, 30.0]
    assert report["binary"]["magic"] == "SVWT"
    assert report["binary"]["convention"] == (
        CONVENTION_D3D_ROW_TO_GLSL_COLUMN
    )
    assert report["boundary"]["serializes_world_transform"] is True
    assert report["boundary"]["executes_world_transform"] is False

    raw = output.read_bytes()
    magic, version, convention, matrix_bytes = HEADER.unpack_from(raw, 0)
    assert magic == MAGIC
    assert version == VERSION
    assert convention == CONVENTION_D3D_ROW_TO_GLSL_COLUMN
    assert matrix_bytes == MATRIX.size
    assert list(MATRIX.unpack_from(raw, HEADER.size)) == pytest.approx(
        _world()
    )


def test_d3d_row_vector_translation_matches_expected_point():
    result = transform_point_d3d_row_vector(
        _world(),
        [1.0, 2.0, 3.0],
    )
    assert result == pytest.approx([11.0, 22.0, 33.0, 1.0])


def test_same_row_major_bytes_are_glsl_transpose_semantics():
    matrix = _world(5.0, -2.0, 8.0)
    # Interpreting row-major D3D bytes as GLSL's default column-major mat4
    # yields transpose(M). Multiplying that by a column vector must therefore
    # equal the D3D row-vector p*M result.
    glsl_columns = [
        matrix[index:index + 4]
        for index in range(0, 16, 4)
    ]
    point = [2.0, 3.0, 4.0, 1.0]
    glsl_result = [
        sum(glsl_columns[column][row] * point[column] for column in range(4))
        for row in range(4)
    ]
    d3d_result = transform_point_d3d_row_vector(
        matrix,
        point[:3],
    )
    assert glsl_result == pytest.approx(d3d_result)


def test_nested_world_matrix_is_accepted(tmp_path):
    nested = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [4.0, 5.0, 6.0, 1.0],
    ]
    report = build_vulkan_world_transform_packet(
        {"world_matrix": nested},
        tmp_path / "nested.svwt",
    )
    assert report["matrix"][12:15] == [4.0, 5.0, 6.0]


@pytest.mark.parametrize(
    "matrix",
    [
        [1.0] * 15,
        _world()[:-1] + [0.0],
        _world()[:3] + [1.0] + _world()[4:],
    ],
)
def test_invalid_world_matrix_is_rejected(tmp_path, matrix):
    with pytest.raises(ValueError):
        build_vulkan_world_transform_packet(
            {"world_matrix": matrix},
            tmp_path / "bad.svwt",
        )
