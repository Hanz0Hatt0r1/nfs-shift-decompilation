"""Deterministic solver-scalar domain mapping for real BMW M3 SDF topology."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from rigid_body_sdf_runtime import (
    build_sdf_constraint_connectivity_matrix,
    optimize_sdf_constraint_order,
    compile_sdf_runtime_topology,
)

FORMAT = "SHIFT.BMWM3SolverDomainRuntime/1"


def build_solver_domain(
    sdf_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Lower an SDF report to the ordered 40-scalar-style solver domain."""
    topology = compile_sdf_runtime_topology(sdf_report)
    if topology.get("ready") is not True:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "constraint_record_count": topology.get("constraint_count", 0),
            "solver_scalar_count": 0,
            "records": [],
            "unresolved": list(topology.get("unresolved") or []),
        }

    ordering = optimize_sdf_constraint_order(sdf_report)
    if ordering.get("ready") is not True:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "constraint_record_count": topology.get("constraint_count", 0),
            "solver_scalar_count": 0,
            "records": [],
            "unresolved": list(ordering.get("unresolved") or []),
        }

    constraints = list(topology.get("constraints") or [])
    order = [int(value) for value in ordering.get("order") or []]
    widths_by_record = [int(value) for value in ordering.get("block_widths") or []]
    offsets_by_position = [
        int(value) for value in ordering.get("block_offsets") or []
    ]
    if len(order) != len(constraints):
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "constraint_record_count": len(constraints),
            "solver_scalar_count": 0,
            "records": [],
            "unresolved": ["ordering-record-count-mismatch"],
        }

    records: list[dict[str, Any]] = []
    for position, record_index in enumerate(order):
        constraint = constraints[record_index]
        width = widths_by_record[record_index]
        scalar_base = offsets_by_position[position]
        records.append({
            "ordered_position": position,
            "runtime_record_index": record_index,
            "source_record_index": int(constraint["source_record_index"]),
            "source_section": str(constraint["source_section"]),
            "section": str(constraint["section"]),
            "name": constraint.get("name"),
            "posbody": constraint.get("posbody"),
            "negbody": constraint.get("negbody"),
            "solver_width": width,
            "scalar_base": scalar_base,
            "scalar_end": scalar_base + width,
            "scalar_indices": list(range(scalar_base, scalar_base + width)),
            "source_line": constraint.get("source_line"),
            "side_flag_offset": (
                "+0x34" if constraint["section"] in {"JOINT", "BAR"} else "+0x98"
            ),
            "scalar_base_offset": (
                "+0x30" if constraint["section"] in {"JOINT", "BAR"} else "+0x94"
            ),
        })

    scalar_count = int(ordering.get("solver_scalar_count", 0))
    errors: list[str] = []
    cursor = 0
    for row in records:
        if row["scalar_base"] != cursor:
            errors.append(
                f"scalar-gap-before:{row['ordered_position']}:{row['scalar_base']}:{cursor}"
            )
        cursor = int(row["scalar_end"])
    if cursor != scalar_count:
        errors.append(f"scalar-total-mismatch:{cursor}:{scalar_count}")

    width_counts: dict[str, int] = {"JOINT": 0, "HINGE": 0, "BAR": 0}
    for row in records:
        width_counts[row["section"]] = width_counts.get(row["section"], 0) + 1

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "constraint_record_count": len(records),
        "solver_scalar_count": scalar_count,
        "constraint_width_counts": width_counts,
        "order": order,
        "records": records,
        "ordering": {
            "initial_cost": ordering.get("initial_cost"),
            "final_cost": ordering.get("final_cost"),
            "improvement_count": ordering.get("improvement_count"),
            "pass_count": ordering.get("pass_count"),
        },
        "connectivity": {
            "shared_body_pair_count": (
                ordering.get("connectivity", {}).get("shared_body_pair_count", 0)
            ),
        },
        "errors": errors,
        "evidence": {
            "topology": "FUN_007b3150",
            "ordering": "FUN_007b1b60",
            "scalar_expansion": "FUN_007ba2b0",
            "solver_widths": {"JOINT": 3, "HINGE": 2, "BAR": 1},
        },
    }


def validate_expected_bmw_shape(
    solver_domain: Mapping[str, Any],
    *,
    body_count: int,
    joint_hinge_count: int,
    bar_count: int,
) -> dict[str, Any]:
    """Validate the real BMW M3 intake shape without requiring raw game bytes."""
    expected_constraints = joint_hinge_count * 2 + bar_count
    expected_scalars = joint_hinge_count * 3 + joint_hinge_count * 2 + bar_count
    width_counts = dict(solver_domain.get("constraint_width_counts") or {})
    errors: list[str] = []
    if int(solver_domain.get("constraint_record_count", -1)) != expected_constraints:
        errors.append("constraint-record-count")
    if int(solver_domain.get("solver_scalar_count", -1)) != expected_scalars:
        errors.append("solver-scalar-count")
    if int(width_counts.get("JOINT", -1)) != joint_hinge_count:
        errors.append("joint-count")
    if int(width_counts.get("HINGE", -1)) != joint_hinge_count:
        errors.append("hinge-count")
    if int(width_counts.get("BAR", -1)) != bar_count:
        errors.append("bar-count")
    if len(solver_domain.get("records") or []) != expected_constraints:
        errors.append("record-list-count")
    return {
        "format": "SHIFT.BMWM3SolverDomainShapeValidation/1",
        "version": 1,
        "ready": not errors,
        "body_count": int(body_count),
        "expected_constraint_record_count": expected_constraints,
        "expected_solver_scalar_count": expected_scalars,
        "actual_constraint_record_count": int(
            solver_domain.get("constraint_record_count", -1)
        ),
        "actual_solver_scalar_count": int(
            solver_domain.get("solver_scalar_count", -1)
        ),
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "build_solver_domain",
    "validate_expected_bmw_shape",
]
