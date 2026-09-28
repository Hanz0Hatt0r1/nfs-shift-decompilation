"""Exact numeric builtin solver kernel recovered from FUN_007b0f20."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFBuiltinSparseSolverRuntime/1"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SOURCE_LINE = 811506


def _copy_matrix(matrix: Sequence[Sequence[float | int]]) -> list[list[float]]:
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    return [[float(value) for value in row] for row in matrix]


def _copy_vector(vector: Sequence[float | int], n: int) -> list[float]:
    if len(vector) != n:
        raise ValueError("rhs length must match matrix dimension")
    return [float(value) for value in vector]


def solve_builtin_sparse_in_place(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
    forward_records: Sequence[Mapping[str, Any]],
    reverse_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Mirror FUN_007b0f20 sparse factorization plus forward/back substitution.

    forward_records contains n+1 outer records. For each pivot i:
      - item 0 contains lower-dependency indices used to update the diagonal;
      - remaining items describe later rows whose column-i value is eliminated;
      - forward_records[n].items[i] contains the forward-substitution dependencies.

    reverse_records[i] supplies the upper dependencies for back substitution.
    """
    a = _copy_matrix(matrix)
    n = len(a)
    b = _copy_vector(rhs, n)

    if len(forward_records) != n + 1:
        raise ValueError("forward_records must contain n+1 records")
    if len(reverse_records) != n:
        raise ValueError("reverse_records must contain n records")

    operations: list[dict[str, Any]] = []

    terminal_items = list(forward_records[n].get("items") or [])
    if len(terminal_items) != n:
        raise ValueError("terminal forward record must contain one item per scalar row")

    for i in range(n):
        pivot_items = list(forward_records[i].get("items") or [])
        if not pivot_items:
            raise ValueError(f"forward record {i} has no pivot item")
        pivot_deps = [int(value) for value in (pivot_items[0].get("dependencies") or [])]

        for k in pivot_deps:
            if k < 0 or k >= i:
                raise ValueError(f"invalid pivot dependency {k} at row {i}")
            a[i][i] -= a[k][i] * a[i][k]

        diagonal = a[i][i]
        if diagonal == 0.0:
            raise ZeroDivisionError(f"zero pivot at row {i}")
        inv_diagonal = 1.0 / diagonal

        for item in pivot_items[1:]:
            j = int(item.get("node", -1))
            if j <= i or j >= n:
                raise ValueError(f"invalid forward target {j} for pivot {i}")
            for k in [int(value) for value in (item.get("dependencies") or [])]:
                if k < 0 or k >= i:
                    raise ValueError(f"invalid row dependency {k} for target {j}")
                a[j][i] -= a[k][i] * a[j][k]
            a[i][j] = a[j][i] * inv_diagonal

        terminal = terminal_items[i]
        for k in [int(value) for value in (terminal.get("dependencies") or [])]:
            if k < 0 or k >= i:
                raise ValueError(f"invalid RHS dependency {k} at row {i}")
            b[i] -= a[i][k] * b[k]
        b[i] *= inv_diagonal

        operations.append({
            "pivot": i,
            "diagonal": diagonal,
            "inverse_diagonal": inv_diagonal,
            "forward_targets": [int(item.get("node", -1)) for item in pivot_items[1:]],
        })

    for i in range(n - 2, -1, -1):
        reverse = reverse_records[i]
        for k in [int(value) for value in (reverse.get("dependencies") or [])]:
            if k <= i or k >= n:
                raise ValueError(f"invalid reverse dependency {k} at row {i}")
            b[i] -= a[i][k] * b[k]

    return {
        "format": "SHIFT.SDFBuiltinSparseSolverResult/1",
        "version": 1,
        "status": "solved",
        "ready": True,
        "scalar_count": n,
        "solution": b,
        "factorized_matrix": a,
        "operations": operations,
        "evidence": {
            "function": "FUN_007b0f20",
            "source_file": SOURCE_FILE,
            "source_sha256": SOURCE_SHA256,
            "source_line": SOURCE_LINE,
            "factorization": "sparse LDL^T-style in-place storage",
            "forward_range": "0..n-1",
            "backward_range": "n-2..0",
            "terminal_forward_record": "forward_records[n]",
            "terminal_reverse_record": "reverse_records[n-1] allocated but not traversed",
        },
    }


def build_dense_solver_graph(n: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build a deterministic full-dependency graph useful for numeric regression."""
    size = int(n)
    if size < 1:
        raise ValueError("n must be positive")

    forward: list[dict[str, Any]] = []
    for i in range(size):
        items = [{
            "node": i,
            "dependency_count": i,
            "dependencies": list(range(i)),
        }]
        for j in range(i + 1, size):
            items.append({
                "node": j,
                "dependency_count": i,
                "dependencies": list(range(i)),
            })
        forward.append({"count": len(items), "items": items})

    forward.append({
        "count": size,
        "items": [
            {
                "node": i,
                "dependency_count": i,
                "dependencies": list(range(i)),
            }
            for i in range(size)
        ],
    })

    reverse = [
        {
            "node": i,
            "dependency_count": size - i - 1,
            "dependencies": list(range(i + 1, size)),
        }
        for i in range(size)
    ]
    return forward, reverse


def describe_builtin_sparse_solver_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-executable",
        "ready": True,
        "function": "FUN_007b0f20",
        "algorithm": {
            "family": "sparse symmetric factorization with forward/back substitution",
            "diagonal_update": "A[i][i] -= A[k][i] * A[i][k]",
            "target_update": "A[j][i] -= A[k][i] * A[j][k]",
            "normalized_factor": "A[i][j] = A[j][i] / A[i][i]",
            "forward_rhs": "b[i] = (b[i] - sum(A[i][k] * b[k])) / A[i][i]",
            "backward_rhs": "b[i] -= sum(A[i][j] * b[j])",
        },
        "record_contract": {
            "forward_records": "n+1",
            "reverse_records": "n",
            "pivot_item": "forward[i].items[0]",
            "terminal_forward": "forward[n].items[i]",
            "backward_record": "reverse[i]",
        },
        "limitations": [
            "This reproduces builtin numeric execution only. Provider vtable +0x18 remains separate.",
            "Matrix coefficient physical meaning is intentionally not assigned.",
        ],
    }


__all__ = [
    "FORMAT",
    "solve_builtin_sparse_in_place",
    "build_dense_solver_graph",
    "describe_builtin_sparse_solver_contract",
]
