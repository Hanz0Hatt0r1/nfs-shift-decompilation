from camera_matrix_vector_runtime import (
    build_camera_affine_basis,
    build_camera_basis_matrix,
    move_camera_counter_toward_zero,
    transform_matrix_rows_by_vector,
    update_camera_signed_counter,
)


def test_matrix_vector_transform_matches_reflection_shape():
    identity = [
        1,0,0,0,
        0,1,0,0,
        0,0,1,0,
        0,0,0,1,
    ]
    result = transform_matrix_rows_by_vector(identity, [1,0,0,0])
    assert result[0:4] == [-1.0, 0.0, 0.0, 0.0]
    assert result[4:8] == [0.0, 1.0, 0.0, 0.0]
    assert result[12:16] == [0.0, 0.0, 0.0, 1.0]


def test_basis_generator_writes_only_source_sparse_positions():
    result = build_camera_basis_matrix([1,2,3], [4,5,6])
    assert len(result) == 16
    assert result[3] == 0.0
    assert result[7] == 0.0
    assert result[11] == 0.0


def test_affine_basis_sets_last_row_to_zero_zero_zero_one():
    result = build_camera_affine_basis([1,2,3], [4,5,6])
    assert result[12:16] == [0.0, 0.0, 0.0, 1.0]


def test_signed_counter_has_hard_bounds_without_force():
    assert update_camera_signed_counter(-10, increase=False)["after"] == -10
    assert update_camera_signed_counter(10, increase=True)["after"] == 10
    assert update_camera_signed_counter(-10, increase=False, force=True)["after"] == -11
    assert update_camera_signed_counter(10, increase=True, force=True)["after"] == 11


def test_signed_counter_toward_zero_returns_source_sign_byte():
    positive = move_camera_counter_toward_zero(2)
    negative = move_camera_counter_toward_zero(-2)
    zero = move_camera_counter_toward_zero(0)
    assert (positive["after"], positive["output"]) == (1, 1)
    assert (negative["after"], negative["output"]) == (-1, 0)
    assert zero["changed"] is False
