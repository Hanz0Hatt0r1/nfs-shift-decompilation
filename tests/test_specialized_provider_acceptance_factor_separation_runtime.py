import specialized_provider_acceptance_factor_separation_runtime as runtime


def test_acceptance_edges_uses_strict_upper_coordinates():
    edges = runtime.acceptance_edges(0)

    assert all(row < column < 40 for row, column in edges)
    assert len(edges) == 450


def test_factor_edges_from_report_is_unique():
    report = {
        "rows": [
            {"pivot_index": 0, "factor_columns": [1, 2, 2]},
            {"pivot_index": 1, "factor_columns": [2]},
        ]
    }

    assert runtime.factor_edges_from_report(report) == {
        (0, 1),
        (0, 2),
        (1, 2),
    }


def test_validate_comparison_rejects_non_upper_factor_edge():
    result = runtime.validate_comparison(
        {
            "provider_id": 0,
            "scalar_count": 3,
            "acceptance_edge_count": 1,
            "factor_edge_count": 1,
            "overlap_count": 0,
            "factor_edges": [
                {"row": 2, "column": 1},
            ],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "invalid-factor-edge:2,1" in result["errors"]


def test_summarize_comparison_reports_set_metrics():
    result = runtime.summarize_comparison(
        {
            "provider_id": 1,
            "scalar_count": 4,
            "acceptance_edge_count": 5,
            "factor_edge_count": 3,
            "overlap_count": 2,
            "factor_only_count": 1,
            "acceptance_only_count": 3,
            "ready": True,
        }
    )

    assert result["union"] == 6
    assert result["jaccard"] == 2 / 6
