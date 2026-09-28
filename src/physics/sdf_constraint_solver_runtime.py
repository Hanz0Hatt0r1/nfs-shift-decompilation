"""Source-backed execution contract for the SHIFT SDF sparse constraint solver.

The retail solver consumes the compact graph emitted by FUN_007b1360 and the
constraint matrix assembled before it. This module records the exact traversal,
record layout and provider bypass without inventing the meaning of individual
matrix coefficients.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence
from sdf_builtin_sparse_solver_runtime import solve_builtin_sparse_in_place

FORMAT = "SHIFT.SDFConstraintSolverRuntime/1"

FORWARD_ITEM_LAYOUT = {
    "node": "+0x00 byte",
    "dependency_count": "+0x01 byte",
    "dependency_pointer": "+0x04 u32",
}
OUTER_RECORD_LAYOUT = {
    "count": "+0x00 u32",
    "item_pointer": "+0x04 u32",
}


def describe_sdf_sparse_solver_contract(
    *,
    constraint_count: int | None = None,
) -> dict[str, Any]:
    """Describe FUN_007b0f20 without assigning hidden coefficient semantics."""
    count = None if constraint_count is None else int(constraint_count)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "execution-contract",
        "ready": True,
        "constraint_count": count,
        "solver_scalar_count": count,
        "function": "FUN_007b0f20",
        "inputs": {
            "graph_this": {
                "forward_table": "+0x00",
                "reverse_table": "+0x04",
                "edge_record_pool": "+0x08",
                "dependency_index_bytes": "+0x0c",
            },
            "matrix_rows": "param_1: row-pointer array, one double[n] row per solver variable",
            "rhs_vector": "param_2: writable double[n] solve vector",
            "count": "param_3: solver variable count",
        },
        "forward_pass": {
            "range": "i = 0 .. n-1",
            "outer_record": "forward_table[i]",
            "first_edge": "outer_record.item_pointer",
            "first_edge_role": "eliminate lower dependencies from row i before diagonal reciprocal",
            "diagonal_scale": "1.0 / row_i[i]",
            "remaining_edges": "apply each remaining edge item to its target node before forward RHS normalization",
            "terminal_record": "forward_table[n]",
            "terminal_role": "subtract terminal lower dependencies from RHS[i], then multiply by diagonal_scale",
        },
        "backward_pass": {
            "range": "i = n-2 .. 0",
            "record_source": "reverse_table[i]",
            "role": "subtract already-solved upper dependencies from RHS[i]",
            "terminal_reverse_node": "n-1 record is allocated but not traversed by the back-substitution loop",
        },
        "edge_record": {
            "size": 8,
            "layout": FORWARD_ITEM_LAYOUT,
            "dependency_indices": "byte-sized node indices in +0x04 pointer target",
        },
        "graph_outer_record": {
            "size": 8,
            "layout": OUTER_RECORD_LAYOUT,
            "forward_count": "n+1",
            "reverse_count": "n",
        },
        "provider_bypass": {
            "owner": "physics system +0x48",
            "provider_present": "invoke provider vtable +0x18 instead of FUN_007b0f20",
            "provider_absent": "invoke FUN_007b0f20",
        },
        "evidence": {
            "solver": "FUN_007b0f20",
            "graph_builder": "FUN_007b1360",
            "graph_reset": "FUN_007b10d0",
            "provider_selector": "FUN_007d2e70",
            "provider_finalize": "vtable +0x2c",
        },
        "limitations": [
            "The numeric coefficient meaning of the matrix rows is unresolved.",
            "This contract records traversal and storage semantics, not a substitute numerical solver.",
            "The provider-specific +0x18 implementation is intentionally opaque.",
        ],
    }


def validate_sdf_solver_contract(report: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a Phase 386 graph report against the solver input contract."""
    graph_count = report.get("constraint_count")
    forward = report.get("forward_records") or []
    reverse = report.get("reverse_records") or []
    errors: list[str] = []
    if graph_count is None:
        errors.append("missing:constraint_count")
    else:
        n = int(graph_count)
        if len(forward) != n + 1:
            errors.append(f"forward-record-count:{len(forward)}:{n + 1}")
        if len(reverse) != n:
            errors.append(f"reverse-record-count:{len(reverse)}:{n}")
    for index, record in enumerate(forward):
        items = record.get("items") or []
        if int(record.get("count", len(items))) != len(items):
            errors.append(f"forward:{index}:count-mismatch")
        for item_index, item in enumerate(items):
            deps = item.get("dependencies") or []
            if int(item.get("dependency_count", len(deps))) != len(deps):
                errors.append(f"forward:{index}:{item_index}:dependency-count-mismatch")
            if any(int(dep) < 0 for dep in deps):
                errors.append(f"forward:{index}:{item_index}:negative-dependency")
    for index, record in enumerate(reverse):
        deps = record.get("dependencies") or []
        if int(record.get("dependency_count", len(deps))) != len(deps):
            errors.append(f"reverse:{index}:dependency-count-mismatch")
        if any(int(dep) < 0 for dep in deps):
            errors.append(f"reverse:{index}:negative-dependency")
    return {
        "format": "SHIFT.SDFConstraintSolverValidation/1",
        "version": 1,
        "ready": not errors,
        "status": "validated" if not errors else "blocked",
        "constraint_count": graph_count,
        "solver_scalar_count": graph_count,
        "errors": list(dict.fromkeys(errors)),
        "evidence": {
            "solver": "FUN_007b0f20",
            "graph_builder": "FUN_007b1360",
        },
    }



def solve_sdf_builtin(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
    forward_records: Sequence[Mapping[str, Any]],
    reverse_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Public compatibility wrapper for the exact FUN_007b0f20 numeric kernel."""
    return solve_builtin_sparse_in_place(
        matrix,
        rhs,
        forward_records,
        reverse_records,
    )
