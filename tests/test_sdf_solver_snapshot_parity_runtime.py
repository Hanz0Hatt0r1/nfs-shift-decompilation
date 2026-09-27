import pytest

import sdf_solver_snapshot_parity_runtime as runtime


def _snapshot():
    return {
        "scalar_count": 3,
        "row_indices": [0, 3, 6],
        "matrix_pool": [
            1.0, 2.0, 3.0,
            4.0, 5.0, 6.0,
            7.0, 8.0, 9.0,
        ],
        "rhs": [10.0, 20.0, 30.0],
    }


def test_solver_snapshot_exact_match():
    result = runtime.compare_solver_snapshot(_snapshot(), _snapshot())
    assert result["status"] == "match"
    assert result["structural_match"] is True
    assert result["numeric_match"] is True
    assert result["matrix"]["diff_count"] == 0
    assert result["rhs"]["diff_count"] == 0


def test_solver_snapshot_matches_with_absolute_tolerance():
    actual = _snapshot()
    actual["matrix_pool"][4] += 1e-7
    actual["rhs"][1] -= 2e-7
    result = runtime.compare_solver_snapshot(
        _snapshot(),
        actual,
        abs_tolerance=1e-6,
    )
    assert result["status"] == "match"
    assert result["numeric_match"] is True


def test_solver_snapshot_reports_matrix_and_rhs_differences():
    actual = _snapshot()
    actual["matrix_pool"][4] += 0.25
    actual["rhs"][1] -= 1.5
    result = runtime.compare_solver_snapshot(
        _snapshot(),
        actual,
        abs_tolerance=1e-6,
        max_diffs=10,
    )
    assert result["status"] == "mismatch"
    assert result["matrix"]["diff_count"] == 1
    assert result["matrix"]["diffs"][0]["row"] == 1
    assert result["matrix"]["diffs"][0]["column"] == 1
    assert result["rhs"]["diff_count"] == 1
    assert result["rhs"]["diffs"][0]["index"] == 1


def test_solver_snapshot_reports_structural_difference():
    actual = _snapshot()
    actual["row_indices"] = [0, 4, 8]
    actual["scalar_count"] = 4
    result = runtime.compare_solver_snapshot(_snapshot(), actual)
    assert result["status"] == "mismatch"
    assert "scalar-count:3:4" in result["structural_errors"]
    assert "row-indices-mismatch" in result["structural_errors"]
    assert "matrix-length:9:9" not in result["structural_errors"]


def test_solver_snapshot_limits_matrix_diff_list():
    actual = _snapshot()
    actual["matrix_pool"] = [value + 1.0 for value in actual["matrix_pool"]]
    result = runtime.compare_solver_snapshot(
        _snapshot(),
        actual,
        max_diffs=2,
    )
    assert result["matrix"]["diff_count"] == 2
    assert len(result["matrix"]["diffs"]) == 2


def test_solver_snapshot_builder_normalizes_external_storage():
    result = runtime.build_snapshot_from_retail_storage(
        scalar_count=2,
        row_indices=[0, 2],
        matrix_pool=[1, 2, 3, 4],
        rhs=[5, 6],
    )
    assert result == {
        "format": "SHIFT.SDFSolverSnapshot/1",
        "version": 1,
        "scalar_count": 2,
        "row_indices": [0, 2],
        "matrix_pool": [1.0, 2.0, 3.0, 4.0],
        "rhs": [5.0, 6.0],
    }


def test_solver_snapshot_builder_rejects_invalid_lengths():
    with pytest.raises(ValueError, match="matrix_pool length"):
        runtime.build_snapshot_from_retail_storage(
            scalar_count=2,
            row_indices=[0, 2],
            matrix_pool=[1, 2, 3],
            rhs=[4, 5],
        )


def test_solver_snapshot_assertion_fails_with_compact_message():
    actual = _snapshot()
    actual["matrix_pool"][0] = 99.0
    with pytest.raises(AssertionError):
        runtime.assert_solver_snapshot_match(_snapshot(), actual)
