import specialized_provider_output_schedule_runtime as runtime


def test_destination_address_direct_and_loop_forms():
    assert runtime._destination_address(
        "DAT_00002000 = x;",
        None,
    ) == 0x2000
    assert runtime._destination_address(
        "*(double *)(&DAT_00002000 + local_10 * 8) = x;",
        3,
    ) == 0x2018
    assert runtime._destination_address(
        "(&DAT_00002000)[local_10] = x;",
        4,
    ) == 0x2020


def test_validate_output_schedule_rejects_wrong_terminal_pivot():
    result = runtime.validate_output_schedule(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "assignments": [
                {
                    "pivot_index": 0,
                    "stage": "terminal-output",
                    "destination": {"index": 0},
                    "rhs_output": [],
                },
                {
                    "pivot_index": 1,
                    "stage": "terminal-output",
                    "destination": {"index": 1},
                    "rhs_output": [],
                },
            ],
            "output_dependency_edges": [],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "assignment-0-terminal-output-wrong-pivot" in result["errors"]


def test_validate_output_schedule_checks_rhs_indices():
    result = runtime.validate_output_schedule(
        {
            "provider_id": 0,
            "scalar_count": 2,
            "assignments": [
                {
                    "pivot_index": 0,
                    "stage": "forward-output",
                    "destination": {"index": 0},
                    "rhs_output": [
                        {"index": 2},
                    ],
                },
                {
                    "pivot_index": 1,
                    "stage": "terminal-output",
                    "destination": {"index": 1},
                    "rhs_output": [],
                },
            ],
            "output_dependency_edges": [],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "assignment-0-rhs-output-index-out-of-range" in result["errors"]


def test_summarize_output_schedule_counts_stages():
    result = runtime.summarize_output_schedule(
        {
            "provider_id": 1,
            "scalar_count": 3,
            "assignments": [
                {"stage": "forward-output", "destination": {"index": 0}},
                {"stage": "forward-output", "destination": {"index": 1}},
                {"stage": "terminal-output", "destination": {"index": 2}},
            ],
            "output_dependency_edges": [
                {"pivot_index": 2, "destination_index": 2, "source_index": 1},
            ],
            "ready": True,
        }
    )

    assert result["output_assignment_count"] == 3
    assert result["output_dependency_edge_count"] == 1
    assert result["stage_counts"] == {
        "forward-output": 2,
        "terminal-output": 1,
    }
