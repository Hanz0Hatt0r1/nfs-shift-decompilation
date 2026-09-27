import pytest

from matrix_vector_transform_runtime import Matrix3x3
import sdf_body_frame_runtime as runtime


def test_transpose_transform_matches_fun_007aefb0():
    matrix = Matrix3x3(
        1, 2, 3,
        4, 5, 6,
        7, 8, 9,
    )
    result = runtime.transform_vector_transpose(matrix, (1, 2, 3))
    assert result == (14.0, 32.0, 50.0)


def test_body_frame_prepare_matches_m_transpose_diag_c_m():
    matrix = Matrix3x3(
        1, 0, 0,
        0, 2, 0,
        0, 0, 3,
    )
    result = runtime.prepare_body_frame_vector(
        matrix,
        (1, 2, 3),
        (4, 5, 6),
    )
    assert result["local_vector"] == [1.0, 4.0, 9.0]
    assert result["scaled_local_vector"] == [4.0, 20.0, 54.0]
    assert result["output_vector"] == [4.0, 40.0, 162.0]
    assert result["runtime_output_offsets"] == ["+0x30", "+0x38", "+0x40"]


def test_body_frame_contract_preserves_source_chain():
    report = runtime.describe_sdf_body_frame_contract()
    assert report["function"] == "FUN_007ba7e0"
    assert report["forward_transform"]["function"] == "FUN_007af0a0"
    assert report["transpose_transform"]["function"] == "FUN_007aefb0"
    assert report["composite"] == "M^T * diag(C) * M * body_vector"


def test_body_frame_prepare_rejects_wrong_scale_width():
    with pytest.raises(ValueError, match="three"):
        runtime.prepare_body_frame_vector(
            Matrix3x3(1,0,0,0,1,0,0,0,1),
            (1,2,3),
            (1,2),
        )
