"""Executable source-backed model of the builtin SDF sparse solver."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFBuiltinSparseSolverRuntime/1"

# Phase 423: restored executable reference for FUN_007b0f20.


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
            "The compact graph is represented as an execution contract; the dense helper below is a deterministic numerical reference.",
            "Provider-specific solver semantics remain opaque.",
        ],
    }


def build_dense_solver_graph(n: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the deterministic n+1/n record shape consumed by FUN_007b0f20."""
    count = int(n)
    if count < 0:
        raise ValueError("n must be non-negative")

    forward: list[dict[str, Any]] = []
    for row in range(count + 1):
        if row == 0:
            items = [
                {
                    "node": node,
                    "dependency_count": 0,
                    "dependencies": [],
                }
                for node in range(count)
            ]
        elif row == count:
            items = [
                {
                    "node": node,
                    "dependency_count": 0,
                    "dependencies": [],
                }
                for node in range(count)
            ]
        else:
            items = [
                {
                    "node": node,
                    "dependency_count": row,
                    "dependencies": list(range(row)),
                }
                for node in range(row - 1, count)
            ]
        forward.append({"count": len(items), "items": items})

    reverse: list[dict[str, Any]] = []
    for row in range(count):
        dependencies = list(range(row + 1, count))
        reverse.append({
            "node": row,
            "dependency_count": len(dependencies),
            "dependencies": dependencies,
        })
    return forward, reverse

def _validate_square_system(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
) -> int:
    n = len(matrix)
    if n == 0:
        raise ValueError("matrix must not be empty")
    if len(rhs) != n:
        raise ValueError("rhs length must match matrix")
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    return n


def _factorize_symmetric_ldl(
    matrix: list[list[float]],
) -> None:
    """Factor a symmetric matrix as L*D*L^T in-place.

    Lower-triangle entries store L factors. Upper-triangle entries are mirrored
    from the corresponding lower factor so that the source-visible normalized
    factor relation A[i][j] = A[j][i] / A[i][i] remains observable.
    """
    n = len(matrix)
    for i in range(n):
        for k in range(i):
            correction = 0.0
            for j in range(k):
                correction += matrix[i][j] * matrix[k][j] * matrix[j][j]
            matrix[i][k] = (matrix[i][k] - correction) / matrix[k][k]

        diagonal = matrix[i][i]
        for k in range(i):
            diagonal -= matrix[i][k] * matrix[i][k] * matrix[k][k]
        if diagonal == 0.0:
            raise ZeroDivisionError(f"zero pivot at {i}")
        matrix[i][i] = diagonal



def _mirror_upper_factors(matrix: list[list[float]]) -> None:
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j] = matrix[j][i]


def _forward_substitute(
    factorized: Sequence[Sequence[float]],
    rhs: list[float],
) -> None:
    for i in range(len(factorized)):
        for k in range(i):
            rhs[i] -= factorized[i][k] * rhs[k]


def _diagonal_solve(
    factorized: Sequence[Sequence[float]],
    rhs: list[float],
) -> None:
    for i, row in enumerate(factorized):
        diagonal = row[i]
        if diagonal == 0.0:
            raise ZeroDivisionError(f"zero pivot at {i}")
        rhs[i] /= diagonal


def _backward_substitute(
    factorized: Sequence[Sequence[float]],
    rhs: list[float],
) -> None:
    for i in range(len(factorized) - 1, -1, -1):
        for k in range(i + 1, len(factorized)):
            rhs[i] -= factorized[k][i] * rhs[k]


def solve_builtin_sparse_in_place(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
    forward: Sequence[Mapping[str, Any]],
    reverse: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Solve one deterministic symmetric system using the builtin arithmetic."""
    n = _validate_square_system(matrix, rhs)
    if len(forward) != n + 1:
        raise ValueError("forward graph must contain n+1 records")
    if len(reverse) != n:
        raise ValueError("reverse graph must contain n records")

    factorized = [[float(value) for value in row] for row in matrix]
    solution = [float(value) for value in rhs]

    for index, record in enumerate(forward):
        items = record.get("items") or []
        expected = n if index == 0 else n - index + 1
        if index < n and len(items) != expected:
            raise ValueError(f"forward record {index} item count mismatch")

    _factorize_symmetric_ldl(factorized)
    _mirror_upper_factors(factorized)
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
            "forward_records": "n+1",
            "reverse_records": "n",
        },
    }


__all__ = [
    "FORMAT",
    "describe_builtin_sparse_solver_contract",
    "build_dense_solver_graph",
    "solve_builtin_sparse_in_place",
]
