import math

import specialized_provider_capture_differential_runtime as runtime


def test_normalize_post_solve_accepts_rhs():
    result = runtime.normalize_post_solve(
        {"rhs": [1.0, 2.0, 3.0]},
        scalar_count=3,
    )
    assert result == [1.0, 2.0, 3.0]


def test_normalize_post_solve_accepts_solution_alias():
    result = runtime.normalize_post_solve(
        {"solution": [1.0, 2.0]},
        scalar_count=2,
    )
    assert result == [1.0, 2.0]


def test_dense_capture_differential_predicts_solution():
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

    result = runtime.run_capture_differential(
        {
            "scalar_count": 3,
            "matrix": matrix,
            "rhs": rhs,
        },
        expected_post_solve={"rhs": expected},
        abs_tol=1e-12,
        rel_tol=1e-12,
    )

    assert result["status"] == "matched"
    assert result["ready"] is True
    assert result["mode"] == "dense-reference"


def test_capture_differential_is_predicted_only_without_post_solve():
    result = runtime.run_capture_differential(
        {
            "scalar_count": 2,
            "matrix": ((2.0, 1.0), (1.0, 2.0)),
            "rhs": (3.0, 3.0),
        }
    )

    assert result["status"] == "predicted-only"
    assert result["ready"] is True
    assert result["comparison"] is None


def test_capture_differential_reports_numeric_divergence():
    result = runtime.run_capture_differential(
        {
            "scalar_count": 2,
            "matrix": ((2.0, 1.0), (1.0, 2.0)),
            "rhs": (3.0, 3.0),
        },
        expected_post_solve={"solution": [0.0, 0.0]},
        abs_tol=1e-12,
        rel_tol=1e-12,
    )

    assert result["status"] == "numeric-divergence"
    assert result["ready"] is False
    assert result["comparison"]["mismatch_count"] == 2


def test_capture_differential_blocks_bad_factor_pattern():
    result = runtime.run_capture_differential(
        {
            "scalar_count": 3,
            "matrix": (
                (2.0, 1.0, 0.0),
                (1.0, 3.0, 1.0),
                (0.0, 1.0, 2.0),
            ),
            "rhs": (3.0, 4.0, 3.0),
        },
        factor_edges={(0, 1)},
    )

    assert result["status"] == "blocked"
    assert result["ready"] is False
    assert result["errors"][0]["kind"] == "executor"


def test_summarize_capture_differential():
    summary = runtime.summarize_capture_differential(
        {
            "scalar_count": 40,
            "mode": "source-pattern-guided",
            "status": "numeric-divergence",
            "comparison": {
                "mismatch_count": 3,
                "max_abs_error": 0.25,
                "max_rel_error": 0.5,
            },
            "ready": False,
        }
    )

    assert summary["scalar_count"] == 40
    assert summary["numeric_divergence"] is True
    assert summary["mismatch_count"] == 3
    assert math.isclose(summary["max_abs_error"], 0.25)
