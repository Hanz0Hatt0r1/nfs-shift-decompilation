import math

import specialized_provider_experimental_numeric_runtime as runtime


def _matmul_transpose(l, d):
    n = len(d)
    return [
        [
            sum(l[i][k] * d[k] * l[j][k] for k in range(n))
            for j in range(n)
        ]
        for i in range(n)
    ]


def test_dense_ldlt_reconstructs_known_matrix():
    l = (
        (1.0, 0.0, 0.0),
        (0.5, 1.0, 0.0),
        (-0.25, 0.75, 1.0),
    )
    d = (4.0, 3.0, 2.0)
    matrix = _matmul_transpose(l, d)

    reconstructed, diagonal = runtime.reconstruct(matrix)

    assert diagonal == list(d)
    for left, right in zip(reconstructed, matrix):
        assert all(
            math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
            for a, b in zip(left, right)
        )


def test_sparse_guided_ldlt_reconstructs_matching_structural_matrix():
    factor_edges = {
        (0, 1),
        (0, 2),
        (1, 2),
        (1, 3),
        (2, 3),
    }
    l = (
        (1.0, 0.0, 0.0, 0.0),
        (0.25, 1.0, 0.0, 0.0),
        (-0.50, 0.40, 1.0, 0.0),
        (0.0, -0.30, 0.60, 1.0),
    )
    d = (5.0, 4.0, 3.0, 2.0)
    matrix = _matmul_transpose(l, d)

    reconstructed, diagonal = runtime.reconstruct(
        matrix,
        factor_edges=factor_edges,
    )

    assert diagonal == list(d)
    for left, right in zip(reconstructed, matrix):
        assert all(
            math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
            for a, b in zip(left, right)
        )


def test_solve_ldlt_returns_known_solution():
    matrix = (
        (4.0, 1.0, 0.0),
        (1.0, 3.0, 1.0),
        (0.0, 1.0, 2.0),
    )
    expected = [1.0, -2.0, 3.0]
    rhs = [
        sum(matrix[i][j] * expected[j] for j in range(3))
        for i in range(3)
    ]

    result = runtime.solve_ldlt(matrix, rhs)
    check = runtime.validate_solution(
        matrix,
        result,
        rhs,
        tolerance=1e-12,
    )

    assert check["ready"] is True
    assert all(
        math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
        for a, b in zip(result, expected)
    )


def test_validate_rejects_nonsymmetric_matrix():
    try:
        runtime.factorize_ldlt(
            (
                (2.0, 1.0),
                (0.0, 2.0),
            )
        )
    except ValueError as exc:
        assert "not symmetric" in str(exc)
    else:
        raise AssertionError("nonsymmetric matrix was accepted")


def test_validate_solution_reports_residual():
    result = runtime.validate_solution(
        ((2.0,),),
        [1.0],
        [2.0],
        tolerance=1e-12,
    )

    assert result["ready"] is True
    assert result["max_abs_residual"] == 0.0


def test_executor_contract_is_explicitly_experimental():
    contract = runtime.build_executor_contract()

    assert contract["status"] == "experimental-numeric-reference"
    assert contract["algebra"]["factorization"] == "unit-lower LDL^T hypothesis"
    assert contract["storage"]["factor_edges"] == (
        "optional source-derived structural mask"
    )


def test_factor_support_uses_upper_coordinates():
    factorization = runtime.Factorization(
        l=(
            (1.0, 0.0, 0.0),
            (0.5, 1.0, 0.0),
            (0.0, -0.25, 1.0),
        ),
        d=(2.0, 3.0, 4.0),
    )

    assert runtime.factor_support(factorization) == {
        (0, 1),
        (1, 2),
    }


def test_compare_factor_pattern_accepts_matching_dense_factor_support():
    l = (
        (1.0, 0.0, 0.0),
        (0.5, 1.0, 0.0),
        (0.0, -0.25, 1.0),
    )
    d = (2.0, 3.0, 4.0)
    matrix = _matmul_transpose(l, d)

    result = runtime.compare_factor_pattern(
        matrix,
        {(0, 1), (1, 2)},
    )

    assert result["ready"] is True
    assert result["missing_edges"] == []
    assert result["extra_edges"] == []


def test_compare_factor_pattern_rejects_extra_factor_edge():
    matrix = (
        (2.0, 1.0, 0.0),
        (1.0, 3.0, 1.0),
        (0.0, 1.0, 2.0),
    )

    result = runtime.compare_factor_pattern(
        matrix,
        {(0, 1)},
    )

    assert result["ready"] is False
    assert (1, 2) in result["extra_edges"]


def test_solve_guided_rejects_inadmissible_pattern():
    matrix = (
        (2.0, 1.0, 0.0),
        (1.0, 3.0, 1.0),
        (0.0, 1.0, 2.0),
    )

    try:
        runtime.solve_guided(
            matrix,
            [1.0, 2.0, 3.0],
            factor_edges={(0, 1)},
        )
    except ValueError as exc:
        assert "not admissible" in str(exc)
    else:
        raise AssertionError("inadmissible factor pattern was accepted")
