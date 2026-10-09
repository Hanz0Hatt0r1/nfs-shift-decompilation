import pytest

import sdf_builtin_sparse_solver_runtime as runtime


def test_builtin_solver_contract_matches_fun_007b0f20():
    report = runtime.describe_builtin_sparse_solver_contract()
    assert report["ready"] is True
    assert report["function"] == "FUN_007b0f20"
    assert report["algorithm"]["diagonal_update"] == (
        "A[i][i] -= A[k][i] * A[i][k]"
    )
    assert report["algorithm"]["target_update"] == (
        "A[j][i] -= A[k][i] * A[j][k]"
    )
    assert report["algorithm"]["normalized_factor"] == (
        "A[i][j] = A[j][i] / A[i][i]"
    )
    assert report["record_contract"]["forward_records"] == "n+1"
    assert report["record_contract"]["reverse_records"] == "n"


def test_dense_graph_builder_matches_retail_record_shape():
    forward, reverse = runtime.build_dense_solver_graph(3)
    assert len(forward) == 4
    assert len(reverse) == 3
    assert [item["node"] for item in forward[0]["items"]] == [0, 1, 2]
    assert forward[1]["items"][0]["dependencies"] == [0]
    assert forward[2]["items"][0]["dependencies"] == [0, 1]
    assert len(forward[3]["items"]) == 3
    assert reverse[0]["dependencies"] == [1, 2]
    assert reverse[2]["dependencies"] == []


def test_builtin_solver_reproduces_known_three_by_three_solution():
    matrix = [
        [4.0, 1.0, 1.0],
        [1.0, 3.0, 0.0],
        [1.0, 0.0, 2.0],
    ]
    rhs = [9.0, 7.0, 7.0]
    forward, reverse = runtime.build_dense_solver_graph(3)
    result = runtime.solve_builtin_sparse_in_place(
        matrix,
        rhs,
        forward,
        reverse,
    )
    assert result["ready"] is True
    assert result["solution"] == pytest.approx([1.0, 2.0, 3.0])
    assert result["scalar_count"] == 3
    assert result["factorized_matrix"][0][1] == pytest.approx(0.25)
    assert result["factorized_matrix"][1][2] == pytest.approx(-0.0909090909)


def test_builtin_solver_matches_numpy_for_deterministic_spd_case():
    numpy = pytest.importorskip("numpy")
    matrix = numpy.array([
        [6.0, 1.0, 2.0, 0.0],
        [1.0, 5.0, 0.5, 1.0],
        [2.0, 0.5, 7.0, 1.5],
        [0.0, 1.0, 1.5, 4.0],
    ])
    rhs = numpy.array([3.0, -2.0, 7.0, 1.0])
    forward, reverse = runtime.build_dense_solver_graph(4)
    result = runtime.solve_builtin_sparse_in_place(
        matrix.tolist(),
        rhs.tolist(),
        forward,
        reverse,
    )
    expected = numpy.linalg.solve(matrix, rhs)
    assert result["solution"] == pytest.approx(expected.tolist(), rel=1e-12, abs=1e-12)


def test_builtin_solver_rejects_bad_graph_cardinality():
    with pytest.raises(ValueError, match=r"n\+1"):
        runtime.solve_builtin_sparse_in_place(
            [[1.0]],
            [1.0],
            [],
            [{"node": 0, "dependencies": []}],
        )


def test_builtin_solver_rejects_zero_pivot():
    forward, reverse = runtime.build_dense_solver_graph(1)
    with pytest.raises(ZeroDivisionError, match="zero pivot"):
        runtime.solve_builtin_sparse_in_place(
            [[0.0]],
            [1.0],
            forward,
            reverse,
        )
