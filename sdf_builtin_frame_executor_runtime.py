"""End-to-end builtin SDF frame execution from assembled matrix to solved scalars."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from sdf_constraint_matrix_assembly_runtime import apply_builtin_row_identity_constraints
from sdf_builtin_sparse_solver_runtime import solve_builtin_sparse_in_place

FORMAT = "SHIFT.SDFBuiltinFrameExecutorRuntime/1"


def execute_builtin_solver_frame(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
    forward_records: Sequence[Mapping[str, Any]],
    reverse_records: Sequence[Mapping[str, Any]],
    selected_identity_nodes: Sequence[int] = (),
) -> dict[str, Any]:
    """Apply FUN_007b2210 then FUN_007b0f20 to one assembled logical matrix."""
    reset = apply_builtin_row_identity_constraints(
        matrix,
        rhs,
        selected_identity_nodes,
    )
    solved = solve_builtin_sparse_in_place(
        reset["matrix"],
        reset["rhs"],
        forward_records,
        reverse_records,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "solved",
        "ready": True,
        "scalar_count": solved["scalar_count"],
        "selected_identity_nodes": list(reset["nodes"]),
        "pre_reset_matrix": [[float(value) for value in row] for row in matrix],
        "pre_reset_rhs": [float(value) for value in rhs],
        "post_reset_matrix": reset["matrix"],
        "post_reset_rhs": reset["rhs"],
        "solution": solved["solution"],
        "factorized_matrix": solved["factorized_matrix"],
        "solver_operations": solved["operations"],
        "lifecycle": [
            "FUN_007b2210 identity row/column reset",
            "FUN_007b0f20 builtin sparse solve",
        ],
        "evidence": {
            "matrix_reset": "FUN_007b2210",
            "solver": "FUN_007b0f20",
        },
    }


def describe_builtin_frame_executor_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-executable",
        "ready": True,
        "stages": [
            {
                "function": "FUN_007b2210",
                "role": "apply selected identity row/column constraints before solve",
            },
            {
                "function": "FUN_007b0f20",
                "role": "factorize and solve the resulting sparse system",
            },
        ],
        "inputs": {
            "matrix": "assembled logical solver matrix",
            "rhs": "assembled solver RHS vector",
            "forward_records": "FUN_007b1360 forward dependency graph",
            "reverse_records": "FUN_007b1360 reverse dependency graph",
            "selected_identity_nodes": "runtime +0x70 bit-0 selections",
        },
        "limitations": [
            "Provider vtable +0x18 is not part of the builtin executor.",
            "This executor does not synthesize retail matrix/RHS values.",
        ],
    }


__all__ = [
    "FORMAT",
    "execute_builtin_solver_frame",
    "describe_builtin_frame_executor_contract",
]
