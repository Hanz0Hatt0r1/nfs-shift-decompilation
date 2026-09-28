import specialized_provider_update_graph_runtime as runtime


def _segments():
    return (
        type("Segment", (), {"row": 0, "start": 0x1000, "end": 0x1030})(),
        type("Segment", (), {"row": 1, "start": 0x1030, "end": 0x1050})(),
    )


def test_extract_workspace_writes_expands_pointer_loop_and_array_loop():
    lines = [
        "for (local_10 = 1; local_10 < 4; local_10 = local_10 + 1) {",
        "  *(double *)(&DAT_00001000 + local_10 * 8) = 0.0;",
        "}",
        "for (local_10 = 5; local_10 < 7; local_10 = local_10 + 1) {",
        "  (&DAT_00001000)[local_10] = 0.0;",
        "}",
        "DAT_00001038 = 1.0;",
    ]
    writes = runtime._extract_workspace_writes(
        lines,
        first_source_line=100,
        segments=_segments(),
    )

    cells = {(write.cell.row, write.cell.column) for write in writes}
    assert cells == {
        (0, 1), (0, 2), (0, 3), (0, 5), (1, 0), (1, 1)
    }
    assert {write.access for write in writes} == {
        "loop-pointer-lhs", "loop-array-lhs", "direct-lhs"
    }


def test_flat_array_write_can_cross_row_segment_boundary():
    lines = [
        "for (local_10 = 5; local_10 < 7; local_10 = local_10 + 1) {",
        "  (&DAT_00001000)[local_10] = 0.0;",
        "}",
    ]
    writes = runtime._extract_workspace_writes(
        lines,
        first_source_line=1,
        segments=_segments(),
    )

    assert [(w.cell.row, w.cell.column) for w in writes] == [
        (0, 5), (1, 0)
    ]


def test_group_target_rows_excludes_current_pivot_row():
    writes = (
        runtime.WorkspaceWrite(10, runtime.WorkspaceCell(2, 2), "direct-lhs"),
        runtime.WorkspaceWrite(11, runtime.WorkspaceCell(3, 1), "direct-lhs"),
        runtime.WorkspaceWrite(12, runtime.WorkspaceCell(3, 2), "direct-lhs"),
        runtime.WorkspaceWrite(13, runtime.WorkspaceCell(1, 1), "direct-lhs"),
    )
    targets = runtime._group_target_rows(1, writes)

    assert targets == (
        {"row": 2, "columns": [2], "column_count": 1},
        {"row": 3, "columns": [1, 2], "column_count": 2},
    )


def test_validation_allows_prior_rows_only_in_terminal_pivot():
    base = {
        "format": runtime.FORMAT,
        "version": 1,
        "provider_id": 0,
        "scalar_count": 2,
        "rows": [
            {
                "pivot_index": 0,
                "factor_columns": [1],
                "target_rows": [{"row": 1, "columns": [0], "column_count": 1}],
                "prior_workspace_rows": [],
            },
            {
                "pivot_index": 1,
                "factor_columns": [],
                "target_rows": [],
                "prior_workspace_rows": [0],
            },
        ],
        "errors": [],
    }

    result = runtime.validate_update_graph(base)
    assert result["ready"] is True
    assert result["errors"] == []


def test_validation_rejects_prior_row_before_terminal_pivot():
    result = runtime.validate_update_graph(
        {
            "scalar_count": 2,
            "rows": [
                {
                    "pivot_index": 0,
                    "factor_columns": [],
                    "target_rows": [],
                    "prior_workspace_rows": [0],
                },
                {
                    "pivot_index": 1,
                    "factor_columns": [],
                    "target_rows": [],
                    "prior_workspace_rows": [],
                },
            ],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "pivot-0-unexpected-prior-workspace-row-write" in result["errors"]


def test_summary_aggregates_target_edges_and_workspace_sites():
    report = {
        "provider_id": 1,
        "scalar_count": 2,
        "rows": [
            {
                "pivot_index": 0,
                "workspace_write_site_count": 7,
                "workspace_unique_cell_count": 5,
                "target_rows": [
                    {"row": 1, "columns": [0, 1], "column_count": 2}
                ],
                "prior_workspace_rows": [],
            },
            {
                "pivot_index": 1,
                "workspace_write_site_count": 4,
                "workspace_unique_cell_count": 4,
                "target_rows": [],
                "prior_workspace_rows": [0],
            },
        ],
        "ready": True,
    }

    summary = runtime.summarize_update_graph(report)
    assert summary["target_row_edges"] == 1
    assert summary["future_target_unique_cell_writes"] == 2
    assert summary["prior_workspace_row_edges"] == 1
    assert summary["workspace_write_sites"] == 11
    assert summary["workspace_unique_cells"] == 9
