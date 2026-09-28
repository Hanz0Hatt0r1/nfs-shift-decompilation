import specialized_provider_factor_pattern_runtime as runtime


FIXTURE = """
void FUN_example(void)
{
  double dVar1;
  dVar1 = 1.0 / _DAT_00001000;
  for (local_10 = 1; local_10 < 4; local_10 = local_10 + 1) {
    *(double *)(&DAT_00001000 + local_10 * 8) = 0.0;
  }
  DAT_00001020 = 1.0;
  dVar1 = 1.0 / _DAT_00001008;
  for (local_10 = 2; local_10 < 4; local_10 = local_10 + 1) {
    *(double *)(&DAT_00001008 + local_10 * 8) = 0.0;
  }
}
void FUN_next(void)
{
}
"""


def test_extract_row_targets_from_fixture():
    body, _ = runtime.extract_function_body(
        FIXTURE,
        "FUN_example",
        next_function_marker="void FUN_next(void)",
    )
    lines = body.splitlines()
    targets = runtime._extract_row_targets(
        lines,
        row_base=0x1000,
        row_segment_end=4,
        pivot_index=0,
    )
    assert targets == {1, 2, 3}


def test_future_column_filter_removes_past_and_diagonal():
    targets = runtime._extract_row_targets(
        [
            "DAT_00001000 = 1.0;",
            "DAT_00001008 = 2.0;",
            "DAT_00001010 = 3.0;",
        ],
        row_base=0x1000,
        row_segment_end=4,
        pivot_index=1,
    )
    assert targets == {2}


def test_validate_empty_report_fails_shape():
    result = runtime.validate_factor_pattern({
        "scalar_count": 2,
        "rows": [],
        "ready": True,
        "errors": [],
    })
    assert result["ready"] is False
    assert "row-count:expected=2:actual=0" in result["errors"]


def test_summary_counts_factor_edges():
    report = {
        "provider_id": 0,
        "scalar_count": 3,
        "rows": [
            {"pivot_index": 0, "factor_columns": [1, 2], "factor_column_count": 2},
            {"pivot_index": 1, "factor_columns": [2], "factor_column_count": 1},
            {"pivot_index": 2, "factor_columns": [], "factor_column_count": 0},
        ],
        "ready": True,
    }
    summary = runtime.summarize_factor_pattern(report)
    assert summary["total_factor_edges"] == 3
    assert summary["max_factor_column_count"] == 2
    assert summary["rows_with_no_future_factors"] == [2]
