import specialized_provider_solver_ir_runtime as runtime


def test_assignment_operator_map_deduplicates_same_statement():
    report = {
        "assignments": [
            {"pivot_index": 0, "source_line": 10, "operator": "product"},
            {"pivot_index": 0, "source_line": 10, "operator": "product"},
        ]
    }
    assert runtime._assignment_operator_map(report) == {
        (0, 10): "product"
    }


def test_assignment_operator_map_rejects_conflict():
    report = {
        "assignments": [
            {"pivot_index": 0, "source_line": 10, "operator": "product"},
            {"pivot_index": 0, "source_line": 10, "operator": "subtraction"},
        ]
    }
    try:
        runtime._assignment_operator_map(report)
    except ValueError as exc:
        assert "conflicting operator signatures" in str(exc)
    else:
        raise AssertionError("conflicting signatures were accepted")


def test_validate_solver_ir_requires_sequential_pivot_blocks():
    result = runtime.validate_solver_ir(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "blocks": [
                {
                    "pivot_index": 1,
                    "diagonal_address": "0x1000",
                    "assignments": [],
                },
                {
                    "pivot_index": 0,
                    "diagonal_address": "0x1010",
                    "assignments": [],
                },
            ],
            "errors": [],
        }
    )
    assert result["ready"] is False
    assert "pivot-block-order-mismatch" in result["errors"]


def test_summarize_solver_ir_counts_read_domains():
    report = {
        "provider_id": 1,
        "scalar_count": 2,
        "blocks": [
            {
                "pivot_index": 0,
                "assignments": [
                    {
                        "operator": "subtract-product",
                        "workspace_reads": [{"domain": "workspace"}],
                        "output_reads": [],
                        "global_reads": [{"domain": "global"}],
                    }
                ],
            },
            {
                "pivot_index": 1,
                "assignments": [
                    {
                        "operator": "scale-or-product-by-pivot",
                        "workspace_reads": [],
                        "output_reads": [{"domain": "output_vector"}],
                        "global_reads": [],
                    }
                ],
            },
        ],
        "ready": True,
    }
    summary = runtime.summarize_solver_ir(report)
    assert summary["assignments"] == 2
    assert summary["workspace_reads"] == 1
    assert summary["output_reads"] == 1
    assert summary["global_reads"] == 1
    assert summary["operator_counts"] == {
        "scale-or-product-by-pivot": 1,
        "subtract-product": 1,
    }
