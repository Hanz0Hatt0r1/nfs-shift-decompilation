"""Experimental numeric executor for the specialized-provider solver family.

Phase 457 provides a clean-room numerical reference implementing the algebraic
shape supported by the recovered evidence: symmetric pivoting, reciprocal
diagonal, lower-factor normalization, Schur-style updates, and forward/diagonal/
backward solve.

The executor is explicitly *hypothesis-level*. It is not declared retail-identical
until runtime capture or numeric differential evidence proves the packed
workspace mapping and exact update schedule.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Sequence

FORMAT = "SHIFT.SpecializedProviderExperimentalNumericExecutor/1"


@dataclass(frozen=True)
class Factorization:
    l: tuple[tuple[float, ...], ...]
    d: tuple[float, ...]


def _validate_square(matrix: Sequence[Sequence[float]]) -> int:
    n = len(matrix)
    if n == 0:
        raise ValueError("matrix must be non-empty")
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    return n


def _validate_symmetric(matrix: Sequence[Sequence[float]], tol: float) -> None:
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(float(matrix[i][j]) - float(matrix[j][i])) > tol:
                raise ValueError(
                    f"matrix is not symmetric at ({i},{j})"
                )


def _edge_set(
    n: int,
    factor_edges: Iterable[tuple[int, int]] | None,
) -> set[tuple[int, int]]:
    if factor_edges is None:
        return {
            (row, column)
            for row in range(n)
            for column in range(row + 1, n)
        }

    edges: set[tuple[int, int]] = set()
    for row, column in factor_edges:
        row = int(row)
        column = int(column)
        if not (0 <= row < column < n):
            raise ValueError(
                f"factor edge outside strict upper domain: ({row},{column})"
            )
        edges.add((row, column))
    return edges


def factorize_ldlt(
    matrix: Sequence[Sequence[float]],
    *,
    factor_edges: Iterable[tuple[int, int]] | None = None,
    symmetry_tolerance: float = 1e-10,
    pivot_tolerance: float = 1e-14,
) -> Factorization:
    """Compute a unit-lower LDL^T factorization.

    With factor_edges=None this is dense LDL^T. With a supplied edge set, a
    structural zero is enforced when an edge is absent. This sparse mode is a
    reconstruction hypothesis matching the recovered lower-factor topology.
    """
    n = _validate_square(matrix)
    _validate_symmetric(matrix, symmetry_tolerance)
    edges = _edge_set(n, factor_edges)

    a = [
        [float(value) for value in row]
        for row in matrix
    ]
    l = [
        [0.0] * n
        for _ in range(n)
    ]
    d = [0.0] * n

    for i in range(n):
        l[i][i] = 1.0

        pivot = a[i][i]
        if not isfinite(pivot) or abs(pivot) <= pivot_tolerance:
            raise ZeroDivisionError(
                f"singular or near-singular pivot at {i}: {pivot!r}"
            )
        d[i] = pivot

        for j in range(i + 1, n):
            if (i, j) not in edges:
                l[j][i] = 0.0
                continue
            l[j][i] = a[j][i] / d[i]

        for j in range(i + 1, n):
            if (i, j) not in edges:
                continue
            lij = l[j][i]
            for k in range(i + 1, n):
                if (i, k) not in edges or (j, k) not in edges:
                    continue
                a[j][k] -= lij * a[i][k]
                a[k][j] = a[j][k]

    return Factorization(
        l=tuple(tuple(row) for row in l),
        d=tuple(d),
    )


def solve_ldlt(
    matrix: Sequence[Sequence[float]],
    rhs: Sequence[float],
    *,
    factor_edges: Iterable[tuple[int, int]] | None = None,
    symmetry_tolerance: float = 1e-10,
    pivot_tolerance: float = 1e-14,
) -> list[float]:
    n = _validate_square(matrix)
    if len(rhs) != n:
        raise ValueError("rhs length must equal matrix dimension")

    factorization = factorize_ldlt(
        matrix,
        factor_edges=factor_edges,
        symmetry_tolerance=symmetry_tolerance,
        pivot_tolerance=pivot_tolerance,
    )
    l = factorization.l
    d = factorization.d

    # Forward solve: L y = b
    y = [float(value) for value in rhs]
    for i in range(n):
        for j in range(i + 1, n):
            y[j] -= l[j][i] * y[i]

    # Diagonal solve: D z = y
    z = [0.0] * n
    for i in range(n):
        z[i] = y[i] / d[i]

    # Backward solve: L^T x = z
    x = list(z)
    for i in range(n - 1, -1, -1):
        for j in range(i + 1, n):
            x[i] -= l[j][i] * x[j]

    return x


def reconstruct(
    matrix: Sequence[Sequence[float]],
    *,
    factor_edges: Iterable[tuple[int, int]] | None = None,
) -> tuple[list[list[float]], list[float]]:
    """Return reconstructed L*D*L^T and diagonal for differential testing."""
    factorization = factorize_ldlt(
        matrix,
        factor_edges=factor_edges,
    )
    l = factorization.l
    d = factorization.d
    n = len(d)

    reconstructed = [
        [0.0] * n
        for _ in range(n)
    ]
    for i in range(n):
        for j in range(n):
            total = 0.0
            for k in range(n):
                total += l[i][k] * d[k] * l[j][k]
            reconstructed[i][j] = total

    return reconstructed, list(d)


def residual(
    matrix: Sequence[Sequence[float]],
    x: Sequence[float],
    rhs: Sequence[float],
) -> list[float]:
    n = _validate_square(matrix)
    if len(x) != n or len(rhs) != n:
        raise ValueError("vector dimensions must match matrix dimension")

    return [
        sum(float(matrix[i][j]) * float(x[j]) for j in range(n))
        - float(rhs[i])
        for i in range(n)
    ]


def max_abs(values: Sequence[float]) -> float:
    return max((abs(float(value)) for value in values), default=0.0)


def validate_solution(
    matrix: Sequence[Sequence[float]],
    x: Sequence[float],
    rhs: Sequence[float],
    *,
    tolerance: float = 1e-9,
) -> dict[str, float | bool]:
    errors = residual(matrix, x, rhs)
    maximum = max_abs(errors)
    return {
        "ready": maximum <= float(tolerance),
        "max_abs_residual": maximum,
        "tolerance": float(tolerance),
    }


def build_executor_contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "version": 1,
        "algebra": {
            "factorization": "unit-lower LDL^T hypothesis",
            "pivot": "reciprocal diagonal",
            "factor": "future-column normalization",
            "update": "Schur-style symmetric trailing update",
            "solve": "forward / diagonal / descending backward",
        },
        "storage": {
            "factor_edges": "optional source-derived structural mask",
            "packed_workspace_mapping": "not assumed by numeric core",
        },
        "status": "experimental-numeric-reference",
        "limitations": [
            "This implementation is an algebraic reference, not a retail binary clone.",
            "Sparse structural mode is valid only when the supplied factor edge set matches the matrix's true factorization sparsity.",
            "No provider class, physical units, or BMW runtime provider identity is inferred.",
        ],
    }


__all__ = [
    "FORMAT",
    "Factorization",
    "build_executor_contract",
    "factorize_ldlt",
    "solve_ldlt",
    "reconstruct",
    "residual",
    "max_abs",
    "validate_solution",
]
