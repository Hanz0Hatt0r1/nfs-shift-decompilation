import pytest

import sdf_body_tensor_runtime as runtime


def test_body_tensor_identity_basis_preserves_diagonal():
    result = runtime.build_symmetric_body_tensor(
        (2.0, 3.0, 5.0),
        ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    )
    assert result["ready"] is True
    assert result["matrix"] == [
        [2.0, 0.0, 0.0],
        [0.0, 3.0, 0.0],
        [0.0, 0.0, 5.0],
    ]


def test_body_tensor_matches_source_symmetric_expansion():
    result = runtime.build_symmetric_body_tensor(
        (2.0, 3.0, 5.0),
        ((1, 2, 3), (4, 5, 6), (7, 8, 9)),
    )
    assert result["matrix"] == [
        [59.0, 128.0, 197.0],
        [128.0, 287.0, 446.0],
        [197.0, 446.0, 695.0],
    ]
    assert result["runtime_offsets"] == [
        ["+0xb0", "+0xb4", "+0xb8"],
        ["+0xbc", "+0xc0", "+0xc4"],
        ["+0xc8", "+0xcc", "+0xd0"],
    ]


def test_body_tensor_contract_preserves_inverse_diagonal_relation():
    report = runtime.describe_sdf_body_tensor_contract()
    assert report["source_diagonal_offsets"] == ["+0x138", "+0x140", "+0x148"]
    assert report["related_initialization"]["inverse_source"] == [
        "+0x128", "+0x12c", "+0x130"
    ]


def test_body_tensor_rejects_wrong_dimensions():
    with pytest.raises(ValueError, match="3x3"):
        runtime.build_symmetric_body_tensor(
            (1, 2, 3),
            ((1, 0), (0, 1)),
        )
