import pytest

import specialized_provider_runtime as runtime


def test_provider0_vtable_identity_and_dimension():
    p = runtime.get_provider(0)
    assert p.vtable_address == 0x00B0FC5C
    assert p.scalar_count == 40
    assert p.acceptance_function == 0x007C6E50
    assert p.solve_function == 0x007C7200
    assert p.vtable_04_accessor == 0x007D2EB0
    assert p.vtable_08_accessor == 0x007D2EC0
    assert p.vtable_0c_accessor == 0x007D2ED0
    assert p.vtable_2c_accessor == 0x007D2F00
    assert p.accessor_results[0x0C] == "0x00c21698"
    assert p.constant_24 == 0x4A6
    assert p.constant_28 == 0x28


def test_provider1_vtable_identity_and_dimension():
    p = runtime.get_provider(1)
    assert p.vtable_address == 0x00B0FC8C
    assert p.scalar_count == 34
    assert p.acceptance_function == 0x007CDB40
    assert p.solve_function == 0x007CDFC0
    assert p.vtable_04_accessor == 0x007D2F10
    assert p.vtable_08_accessor == 0x007D2F20
    assert p.vtable_0c_accessor == 0x007D2F30
    assert p.vtable_2c_accessor == 0x007D2F60
    assert p.accessor_results[0x0C] == "0x00c1fdb0"
    assert p.constant_24 == 0x2EA
    assert p.constant_28 == 0x22


def test_provider0_rle_covers_exact_40x40_upper_triangle():
    bits = runtime.provider_signature(0)
    assert len(bits) == 40 * 39 // 2 == 780
    assert sum(bits) == 450
    assert len(bits) - sum(bits) == 330


def test_provider1_rle_covers_exact_34x34_upper_triangle():
    bits = runtime.provider_signature(1)
    assert len(bits) == 34 * 33 // 2 == 561
    assert sum(bits) == 315
    assert len(bits) - sum(bits) == 246


def test_rle_starts_zero_and_interleaves_transition_cells():
    bits = runtime.decode_transition_rle((1, 0, 1), 3)
    assert bits == [False, True, False]


def test_provider_match_ignores_diagonal_and_lower_triangle():
    bits = runtime.provider_signature(0)
    matrix = [[0.0] * 40 for _ in range(40)]
    cursor = 0
    for row in range(40):
        for column in range(row + 1, 40):
            matrix[row][column] = 1.0 if bits[cursor] else 0.0
            matrix[column][row] = 999.0
            cursor += 1
    for i in range(40):
        matrix[i][i] = float("nan")
    result = runtime.match_provider_sparsity(0, matrix)
    assert result["matched"] is True
    assert result["mismatch_count"] == 0


def test_one_upper_triangle_flip_is_rejected():
    bits = runtime.provider_signature(0)
    matrix = [[0.0] * 40 for _ in range(40)]
    cursor = 0
    for row in range(40):
        for column in range(row + 1, 40):
            matrix[row][column] = 1.0 if bits[cursor] else 0.0
            cursor += 1
    row, column = next((r, c) for r in range(40) for c in range(r + 1, 40) if matrix[r][c] == 0.0)
    matrix[row][column] = 1.0
    result = runtime.match_provider_sparsity(0, matrix)
    assert result["matched"] is False
    assert result["mismatch_count"] == 1


def test_dimension_mismatch_is_explicit():
    result = runtime.match_provider_sparsity(1, [[0.0] * 40 for _ in range(40)])
    assert result["ready"] is False
    assert result["reason"] == "dimension-mismatch"


def test_unknown_provider_rejected():
    with pytest.raises(ValueError):
        runtime.get_provider(2)
