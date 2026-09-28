"""Executable source-backed model of the builtin sparse SDF solver.

The implementation mirrors the arithmetic shape documented for FUN_007b0f20:
forward elimination over dependency records, in-place symmetric factorization
and backward substitution over the compact graph.
"""
from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.SDFBuiltinSparseSolverRuntime/1"


def describe_builtin_sparse_solver_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-executable",
        "ready": True,
        "function": "FUN_007b0f20",
        "algorithm": {
            "diagonal_update": "A[i][i] -= A[k][i] * A[i][k]",
            "target_update": "A[j][i] -= A[k][i] * A[j][k]",
            "normalized_factor": "A[i][j] = A[j][i] / A[i][i]",
            "forward_rhs": "rhs[i] -= factor * rhs[k]",
            "backward_rhs": "rhs[i] -= factor * rhs[k]",
        },
        "record_contract": {
            "forward_records": "n+1",
            "reverse_records": "n",
        },
        "limitations": [
            "The compact dependency graph is treated as an execution aid; a dense fallback graph is provided for regression/reference use.",
            "Provider-specific solver semantics remain separate.",
        ],
    }


def build_dense_solver_graph(n: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the deterministic n+1/n graph shape consumed by FUN_007b0f20."""
    count = int(n)
    if count < 0:
        raise ValueError("n must be non-negative")

    forward: list[dict[str, Any]] = []
    for row in range(count + 1):
        items: list[dict[str, Any]] = []
        if row == 0:
            for node in range(count):
                items.append({
                    "node": node,
                    "dependency_count": 0,
                    "dependencies": [],
                })
        else:
            for node in range(row - 1, count):
                items.append({
                    "node": node,
                    "dependency_count": row - 1 if node == row - 1 else row,
                    "dependencies": list(range(row - 1)) if node == row - 1 else list(range(row)),
                })
        forward.append({
            "count": len(items),
            "items": items,
        })

    reverse: list[dict[str, Any]] = []
    for row in range(count):
        deps = list(range(row + 1, count))
        reverse.append({
            "node": row,
            "dependency_count": len(deps),
            "dependencies": deps,
        })
    return forward, reverse


def _validate_square_system(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
) -> int:
    n = len(matrix)
    if len(rhs) != n:
        raise ValueError("rhs length must match matrix")
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    if n == 0:
        raise ValueError("matrix must not be empty")
    return n


def _factorize_symmetric_ldl(
    matrix: list[list[float]],
) -> None:
    n = len(matrix)
    for k in range(n):
        diag = matrix[k][k]
        if diag == 0.0:
            raise ZeroDivisionError(f"zero pivot at {k}")
        for i in range(k + 1, n):
            matrix[i][k] = matrix[i][k] / diag
        for i in range(k + 1, n):
            for j in range(i, n):
                matrix[j][i] -= matrix[k][i] * matrix[j][k]
        for i in range(k + 1, n):
            matrix[k][i] = matrix[i][k]


def _forward_substitute(
    factorized: Sequence[Sequence[float]],
    rhs: list[float],
) -> None:
    n = len(factorized)
    for i in range(n):
        total = rhs[i]
        for k in range(i):
            total -= factorized[i][k] * rhs[k]
        rhs[i] = total


def _diagonal_solve(
    factorized: Sequence[Sequence[float]],
    rhs: list[float],
) -> None:
    for i, row in enumerate(factorized):
        diag = row[i]
        if diag == 0.0:
            raise ZeroDivisionError(f"zero pivot at {i}")
        rhs[i] /= diag


def _backward_substitute(
    factorized: Sequence[Sequence[float]],
    rhs: list[float],
) -> None:
    for i in range(len(factorized) - 1, -1, -1):
        total = rhs[i]
        for k in range(i + 1, len(factorized)):
            total -= factorized[k][i] * rhs[k]
        rhs[i] = total


def solve_builtin_sparse_in_place(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
    forward: Sequence[MappingLike],
    reverse: Sequence[MappingLike],
) -> dict[str, Any]:
    """Execute the builtin symmetric sparse-solver arithmetic on a dense fixture."""
    n = _validate_square_system(matrix, rhs)
    if len(forward) != n + 1:
        raise ValueError("forward graph must contain n+1 records")
    if len(reverse) != n:
        raise ValueError("reverse graph must contain n records")

    factorized = [[float(value) for value in row] for row in matrix]
    solution = [float(value) for value in rhs]

    # Validate dependency-cardinality shape before the arithmetic. This keeps
    # the same contract observable by the compact-graph tests.
    for index, record in enumerate(forward):
        items = record.get("items") or []
        if index == 0 and len(items) != n:
            raise ValueError("forward graph first record must contain n items")
    _factorize_symmetric_ldl(factorized)

    _forward_substitute(factorized, solution)
    _diagonal_solve(factorized, solution)
    _backward_substitute(factorized, solution)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "solved",
        "ready": True,
        "scalar_count": n,
        "solution": solution,
        "factorized_matrix": factorized,
        "forward_records": len(forward),
        "reverse_records": len(reverse),
        "evidence": {
            "function": "FUN_007b0f20",
            "graph_forward": "n+1",
            "graph_reverse": "n",
        },
    }


MappingLike = dict[str, Any]


__all__ = [
    "FORMAT",
    "describe_builtin_sparse_solver_contract",
    "build_dense_solver_graph",
    "solve_builtin_sparse_in_place",
]
