"""Source-backed per-frame SDF constraint solver lifecycle.

This contract covers FUN_007b3f40 and FUN_007b4110 after the solver graph and
scalar-domain reconstruction. It records storage/call order and body projection
without assigning undocumented physical units.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFConstraintSolverFrameRuntime/1"


def describe_sdf_solver_frame_contract(
    *,
    solver_scalar_count: int | None = None,
    body_count: int | None = None,
) -> dict[str, Any]:
    n = None if solver_scalar_count is None else int(solver_scalar_count)
    bodies = None if body_count is None else int(body_count)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "execution-contract",
        "ready": True,
        "solver_scalar_count": n,
        "body_count": bodies,
        "entry": "FUN_007b3f40",
        "provider_branch": {
            "provider_absent": {
                "matrix_clear": "zero scalar_count x scalar_count doubles at row pointers +0x3c",
                "rhs_clear": "zero scalar_count doubles at +0x40",
            },
            "provider_present": {
                "reset_hook": "provider vtable +0x20",
                "matrix_clear": "provider-owned",
                "rhs_clear": "provider-owned",
            },
        },
        "common_pre_solve": [
            {
                "function": "FUN_007b3ed0",
                "purpose": "refresh all JOINT/HINGE/BAR sampled constraint transforms via their postload helpers",
            },
            {
                "function": "FUN_007b4110",
                "purpose": "project current solved scalar vector entries through sampled constraints into body accumulator triplets",
            },
        ],
        "body_projection": {
            "JOINT": {
                "width": 3,
                "sample_scalar_base": "+0x30",
                "positive_body_call": "FUN_007baa70(sample +0x18, solved[base:base+3])",
                "negative_body_call": "FUN_007baaf0(sample +0x18, solved[base:base+3])",
            },
            "HINGE": {
                "width": 2,
                "sample_scalar_base": "+0x94",
                "positive_body_projection": "signed linear combination of sample +0x48/+0x50/+0x58/+0x60/+0x68/+0x70 and solved[base:base+2]",
                "negative_body_projection": "same coefficients with opposite accumulator sign",
            },
            "BAR": {
                "width": 1,
                "sample_scalar_base": "+0x30",
                "impulse_vector": "sample +0x40/+0x48/+0x50 multiplied by solved[base]",
                "positive_body_call": "FUN_007baa70(sample +0x18, impulse_vector)",
                "negative_body_call": "FUN_007baaf0(sample +0x18, impulse_vector)",
            },
        },
        "scalar_consumers": {
            "JOINT": "three consecutive doubles beginning at sampled +0x30",
            "HINGE": "two consecutive doubles beginning at sampled +0x94",
            "BAR": "one double beginning at sampled +0x30",
        },
        "builtin_diagonal_reset": {
            "function": "FUN_007b2210",
            "behavior": [
                "zero selected row",
                "zero selected column",
                "write 1.0 to selected diagonal entry",
                "zero corresponding rhs entry",
            ],
            "selection_source": "constraint runtime +0x70 low bit and sampled scalar base index",
        },
        "solve_dispatch": {
            "provider_present": "provider vtable +0x18",
            "provider_absent": "FUN_007b0f20",
            "rhs_storage": "physics-system +0x4c",
            "matrix_storage": "physics-system +0x3c",
            "scalar_count": "physics-system +0x34",
        },
        "evidence": {
            "frame_entry": "FUN_007b3f40",
            "constraint_refresh": "FUN_007b3ed0",
            "body_projection": "FUN_007b4110",
            "diagonal_reset": "FUN_007b2210",
            "builtin_solver": "FUN_007b0f20",
        },
        "limitations": [
            "The accumulator triplets are kept as storage coordinates; physical force/torque units are not assigned here.",
            "Provider hooks +0x20 and +0x18 remain opaque implementations.",
            "The contract does not claim numerical equivalence for the provider backend.",
        ],
    }


def derive_builtin_diagonal_reset_nodes(
    scalar_connectivity: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover the scalar rows/columns targeted by FUN_007b2210."""
    order = [int(value) for value in scalar_connectivity.get("order") or []]
    widths = [int(value) for value in scalar_connectivity.get("block_widths") or []]
    bases = {
        int(key): int(value)
        for key, value in (scalar_connectivity.get("solver_base_index_by_record") or {}).items()
    }
    selected: list[dict[str, Any]] = []
    scalar_nodes: list[int] = []
    for record in order:
        base = bases.get(record)
        if base is None or base & 1 == 0:
            continue
        width = widths[record]
        nodes = list(range(base, base + width))
        selected.append({
            "record_index": record,
            "base_index": base,
            "width": width,
            "nodes": nodes,
        })
        scalar_nodes.extend(nodes)
    return {
        "format": "SHIFT.SDFBuiltinDiagonalReset/1",
        "version": 1,
        "status": "derived",
        "ready": True,
        "selected_record_count": len(selected),
        "selected_records": selected,
        "scalar_nodes": scalar_nodes,
        "unique_scalar_nodes": list(dict.fromkeys(scalar_nodes)),
        "evidence": {
            "function": "FUN_007b2210",
            "selection": "runtime constraint +0x70 low bit is set",
            "base_index_source": "sample +0x30 (JOINT/BAR) or +0x94 (HINGE)",
            "widths": {"JOINT": 3, "HINGE": 2, "BAR": 1},
        },
    }


def apply_builtin_diagonal_reset(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
    nodes: Sequence[int],
) -> dict[str, Any]:
    """Apply the exact row/column/RHS reset performed by FUN_007b2210."""
    n = len(matrix)
    if len(rhs) != n:
        raise ValueError("rhs length must match matrix size")
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")

    out_matrix = [
        [float(value) for value in row]
        for row in matrix
    ]
    out_rhs = [float(value) for value in rhs]
    selected = sorted(set(int(node) for node in nodes))
    for node in selected:
        if node < 0 or node >= n:
            raise ValueError(f"reset node out of range: {node}")
        for column in range(n):
            out_matrix[node][column] = 0.0
        for row in range(n):
            out_matrix[row][node] = 0.0
        out_matrix[node][node] = 1.0
        out_rhs[node] = 0.0
    return {
        "format": "SHIFT.SDFBuiltinDiagonalResetResult/1",
        "version": 1,
        "status": "applied",
        "ready": True,
        "nodes": selected,
        "matrix": out_matrix,
        "rhs": out_rhs,
        "evidence": {
            "function": "FUN_007b2210",
            "operations": [
                "zero selected row",
                "zero selected column",
                "set selected diagonal to 1.0",
                "zero selected RHS entry",
            ],
        },
    }




def validate_sdf_solver_frame_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    summary = profile.get("summary") or {}
    for key in ("sdf_solver_scalar_count", "sdf_constraint_solver_graph_ready"):
        if key not in summary:
            errors.append(f"missing-summary:{key}")
    if summary.get("sdf_constraint_solver_graph_ready") is not True:
        errors.append("solver-graph-not-ready")
    if summary.get("sdf_sparse_solver_contract_ready") is not True:
        errors.append("sparse-solver-contract-not-ready")
    return {
        "format": "SHIFT.SDFConstraintSolverFrameValidation/1",
        "version": 1,
        "ready": not errors,
        "status": "validated" if not errors else "blocked",
        "errors": list(dict.fromkeys(errors)),
        "evidence": {"frame_entry": "FUN_007b3f40", "body_projection": "FUN_007b4110"},
    }
