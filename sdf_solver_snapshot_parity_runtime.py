"""Compare reconstructed SDF solver storage with an external runtime snapshot."""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFSolverSnapshotParityRuntime/1"


def _as_float_list(values: Sequence[float | int], *, name: str) -> list[float]:
    return [float(value) for value in values]


def compare_solver_snapshot(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    *,
    abs_tolerance: float = 0.0,
    max_diffs: int = 100,
) -> dict[str, Any]:
    """Compare structural and numeric solver state without inferring its origin."""
    tol = float(abs_tolerance)
    if tol < 0.0:
        raise ValueError("abs_tolerance must be non-negative")

    diffs: list[dict[str, Any]] = []
    structural_errors: list[str] = []

    expected_n = int(expected.get("scalar_count", -1))
    actual_n = int(actual.get("scalar_count", -1))
    if expected_n != actual_n:
        structural_errors.append(f"scalar-count:{expected_n}:{actual_n}")

    expected_indices = [int(value) for value in expected.get("row_indices", [])]
    actual_indices = [int(value) for value in actual.get("row_indices", [])]
    if expected_indices != actual_indices:
        structural_errors.append("row-indices-mismatch")

    expected_matrix = _as_float_list(expected.get("matrix_pool", []), name="expected.matrix_pool")
    actual_matrix = _as_float_list(actual.get("matrix_pool", []), name="actual.matrix_pool")
    if len(expected_matrix) != len(actual_matrix):
        structural_errors.append(f"matrix-length:{len(expected_matrix)}:{len(actual_matrix)}")

    for index, (left, right) in enumerate(zip(expected_matrix, actual_matrix)):
        if math.isfinite(left) and math.isfinite(right):
            error = abs(left - right)
        elif left == right:
            error = 0.0
        else:
            error = math.inf
        if error > tol:
            row = index // expected_n if expected_n > 0 else -1
            column = index % expected_n if expected_n > 0 else -1
            diffs.append({
                "flat_index": index,
                "row": row,
                "column": column,
                "expected": left,
                "actual": right,
                "abs_error": error,
            })
            if len(diffs) >= int(max_diffs):
                break

    expected_rhs = _as_float_list(expected.get("rhs", []), name="expected.rhs")
    actual_rhs = _as_float_list(actual.get("rhs", []), name="actual.rhs")
    if len(expected_rhs) != len(actual_rhs):
        structural_errors.append(f"rhs-length:{len(expected_rhs)}:{len(actual_rhs)}")
    rhs_diffs: list[dict[str, Any]] = []
    for index, (left, right) in enumerate(zip(expected_rhs, actual_rhs)):
        if math.isfinite(left) and math.isfinite(right):
            error = abs(left - right)
        elif left == right:
            error = 0.0
        else:
            error = math.inf
        if error > tol:
            rhs_diffs.append({
                "index": index,
                "expected": left,
                "actual": right,
                "abs_error": error,
            })
            if len(rhs_diffs) >= int(max_diffs):
                break

    return {
        "format": FORMAT,
        "version": 1,
        "status": "match" if not structural_errors and not diffs and not rhs_diffs else "mismatch",
        "ready": True,
        "structural_match": not structural_errors,
        "numeric_match": not diffs and not rhs_diffs,
        "abs_tolerance": tol,
        "scalar_count": {
            "expected": expected_n,
            "actual": actual_n,
        },
        "matrix": {
            "expected_length": len(expected_matrix),
            "actual_length": len(actual_matrix),
            "diff_count": len(diffs),
            "diffs": diffs,
        },
        "rhs": {
            "expected_length": len(expected_rhs),
            "actual_length": len(actual_rhs),
            "diff_count": len(rhs_diffs),
            "diffs": rhs_diffs,
        },
        "structural_errors": structural_errors,
    }


def assert_solver_snapshot_match(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    *,
    abs_tolerance: float = 0.0,
) -> dict[str, Any]:
    """Return a compact assertion-ready report."""
    result = compare_solver_snapshot(
        expected,
        actual,
        abs_tolerance=abs_tolerance,
        max_diffs=20,
    )
    if result["status"] != "match":
        raise AssertionError({
            "status": result["status"],
            "structural_errors": result["structural_errors"],
            "matrix_diff_count": result["matrix"]["diff_count"],
            "rhs_diff_count": result["rhs"]["diff_count"],
            "first_matrix_diff": result["matrix"]["diffs"][:1],
            "first_rhs_diff": result["rhs"]["diffs"][:1],
        })
    return result


def build_snapshot_from_retail_storage(
    *,
    scalar_count: int,
    row_indices: Sequence[int],
    matrix_pool: Sequence[float | int],
    rhs: Sequence[float | int],
) -> dict[str, Any]:
    """Normalize an externally captured retail-style storage snapshot."""
    n = int(scalar_count)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")
    expected_matrix_len = n * n
    if len(row_indices) != n:
        raise ValueError("row_indices length must equal scalar_count")
    if len(matrix_pool) != expected_matrix_len:
        raise ValueError("matrix_pool length must equal scalar_count^2")
    if len(rhs) != n:
        raise ValueError("rhs length must equal scalar_count")
    return {
        "format": "SHIFT.SDFSolverSnapshot/1",
        "version": 1,
        "scalar_count": n,
        "row_indices": [int(value) for value in row_indices],
        "matrix_pool": _as_float_list(matrix_pool, name="matrix_pool"),
        "rhs": _as_float_list(rhs, name="rhs"),
    }


__all__ = [
    "FORMAT",
    "compare_solver_snapshot",
    "assert_solver_snapshot_match",
    "build_snapshot_from_retail_storage",
]
