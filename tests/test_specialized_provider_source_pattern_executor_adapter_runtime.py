import math

import specialized_provider_source_pattern_executor_adapter_runtime as runtime


def test_source_pattern_edge_contract_deduplicates_edges():
    pattern = {
        "ready": True,
        "edges": [
            {"pivot_index": 0, "column": 1},
            {"pivot_index": 0, "column": 1},
            {"pivot_index": 1, "column": 2},
        ],
    }

    result = runtime.check_source_pattern_admissibility(
        (
            (2.0, 1.0, 0.0),
            (1.0, 3.0, 1.0),
            (0.0, 1.0, 2.0),
        ),
        pattern,
    )

    assert result["ready"] is False
    assert (1, 2) in result["extra_edges"]


def test_solve_with_source_pattern_requires_ready_contract():
    try:
        runtime.solve_with_source_pattern(
            ((2.0, 1.0), (1.0, 2.0)),
            [1.0, 1.0],
            {"ready": False, "edges": []},
        )
    except ValueError as exc:
        assert "source factor pattern is not ready" in str(exc)
    else:
        raise AssertionError("unready source pattern was accepted")


def test_source_pattern_admissibility_accepts_exact_support():
    l = (
        (1.0, 0.0, 0.0),
        (0.5, 1.0, 0.0),
        (0.0, -0.25, 1.0),
    )
    d = (2.0, 3.0, 4.0)
    matrix = [
        [
            sum(l[i][k] * d[k] * l[j][k] for k in range(3))
            for j in range(3)
        ]
        for i in range(3)
    ]

    pattern = {
        "ready": True,
        "edges": [
            {"pivot_index": 0, "column": 1},
            {"pivot_index": 1, "column": 2},
        ],
    }

    result = runtime.check_source_pattern_admissibility(
        matrix,
        pattern,
    )

    assert result["ready"] is True
    assert result["missing_edges"] == []
    assert result["extra_edges"] == []


def test_admissibility_result_preserves_numeric_factorization():
    pattern = {
        "ready": True,
        "edges": [
            {"pivot_index": 0, "column": 1},
        ],
    }

    result = runtime.check_source_pattern_admissibility(
        ((2.0, 1.0), (1.0, 3.0)),
        pattern,
    )

    factorization = result["factorization"]
    assert math.isclose(factorization.d[0], 2.0)
    assert math.isclose(factorization.d[1], 2.5)
