"""Build the endpoint-aware dynamic contribution schedule.

Phase 492 refines Phase 491 by preserving the per-BODY endpoint population
semantics. A runtime constraint contributes a self block once for each BODY
endpoint, then contributes pair blocks for every pair of groups sharing that
BODY. The cell union remains lower-triangle storage, while operation
multiplicity is preserved for later numeric accumulation.
"""
from __future__ import annotations

from typing import Any, Mapping

from body_scalar_group_population_runtime import build_scalar_group_witness
from body_matrix_structure_runtime import matrix_cells_for_body_groups

FORMAT = "SHIFT.SDFEndpointContributionScheduleRuntime/1"

KERNELS = {
    "JOINT": "FUN_007bbb80",
    "HINGE": "FUN_007bb250",
    "BAR": "FUN_007bb6c0",
}


def _self_cells(group: Mapping[str, Any]) -> set[tuple[int, int]]:
    base = int(group["scalar_base"])
    width = int(group["width"])
    return {
        (base + row, base + column)
        for row in range(width)
        for column in range(row + 1)
    }


def _pair_cells(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> set[tuple[int, int]]:
    left_base = int(left["scalar_base"])
    right_base = int(right["scalar_base"])
    left_width = int(left["width"])
    right_width = int(right["width"])

    if left_base == right_base:
        raise ValueError("two distinct endpoint groups share scalar base")

    if left_base < right_base:
        row_base = right_base
        row_width = right_width
        column_base = left_base
        column_width = left_width
    else:
        row_base = left_base
        row_width = left_width
        column_base = right_base
        column_width = right_width

    return {
        (row_base + row_offset, column_base + column_offset)
        for row_offset in range(row_width)
        for column_offset in range(column_width)
    }


def _pair_kernel(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    left_section = str(left["section"]).upper()
    right_section = str(right["section"]).upper()
    if "JOINT" in {left_section, right_section}:
        return KERNELS["JOINT"]
    if "HINGE" in {left_section, right_section}:
        return KERNELS["HINGE"]
    return KERNELS["BAR"]


def build_endpoint_contribution_schedule(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    witness = build_scalar_group_witness(solver_domain)
    errors = list(witness.get("errors") or [])
    operations: list[dict[str, Any]] = []

    groups_by_body = witness.get("groups_by_body") or {}
    cell_provenance: dict[str, list[dict[str, Any]]] = {}

    for body, groups in sorted(groups_by_body.items()):
        materialized = list(groups)

        for group_index, group in enumerate(materialized):
            section = str(group["section"]).upper()
            cells = _self_cells(group)
            operation = {
                "kind": "self",
                "body": str(body),
                "group_index": group_index,
                "runtime_record_index": int(
                    group["runtime_record_index"]
                ),
                "ordered_position": int(group["ordered_position"]),
                "endpoint_field": group["endpoint_field"],
                "section": section,
                "kernel": KERNELS[section],
                "scalar_base": int(group["scalar_base"]),
                "width": int(group["width"]),
                "row_base": int(group["scalar_base"]),
                "column_base": int(group["scalar_base"]),
                "cells": [
                    [row, column]
                    for row, column in sorted(cells)
                ],
            }
            operations.append(operation)

            for row, column in cells:
                cell_provenance.setdefault(
                    f"{row},{column}",
                    [],
                ).append(
                    {
                        "kind": "self",
                        "body": str(body),
                        "group_index": group_index,
                        "runtime_record_index": int(
                            group["runtime_record_index"]
                        ),
                        "endpoint_field": group["endpoint_field"],
                        "section": section,
                        "kernel": KERNELS[section],
                    }
                )

        for left_index in range(len(materialized)):
            for right_index in range(left_index + 1, len(materialized)):
                left = materialized[left_index]
                right = materialized[right_index]
                try:
                    cells = _pair_cells(left, right)
                except ValueError as exc:
                    errors.append(
                        f"body-{body}-pair-{left_index}-{right_index}:{exc}"
                    )
                    continue

                if int(left["scalar_base"]) < int(right["scalar_base"]):
                    row_base = int(right["scalar_base"])
                    row_width = int(right["width"])
                    column_base = int(left["scalar_base"])
                    column_width = int(left["width"])
                else:
                    row_base = int(left["scalar_base"])
                    row_width = int(left["width"])
                    column_base = int(right["scalar_base"])
                    column_width = int(right["width"])

                kernel = _pair_kernel(left, right)
                operation = {
                    "kind": "pair",
                    "body": str(body),
                    "left_group_index": left_index,
                    "right_group_index": right_index,
                    "left_runtime_record_index": int(
                        left["runtime_record_index"]
                    ),
                    "right_runtime_record_index": int(
                        right["runtime_record_index"]
                    ),
                    "left_ordered_position": int(
                        left["ordered_position"]
                    ),
                    "right_ordered_position": int(
                        right["ordered_position"]
                    ),
                    "left_endpoint_field": left["endpoint_field"],
                    "right_endpoint_field": right["endpoint_field"],
                    "left_section": str(left["section"]).upper(),
                    "right_section": str(right["section"]).upper(),
                    "kernel": kernel,
                    "row_base": row_base,
                    "column_base": column_base,
                    "row_width": row_width,
                    "column_width": column_width,
                    "cells": [
                        [row, column]
                        for row, column in sorted(cells)
                    ],
                }
                operations.append(operation)

                for row, column in cells:
                    cell_provenance.setdefault(
                        f"{row},{column}",
                        [],
                    ).append(
                        {
                            "kind": "pair",
                            "body": str(body),
                            "left_group_index": left_index,
                            "right_group_index": right_index,
                            "left_runtime_record_index": int(
                                left["runtime_record_index"]
                            ),
                            "right_runtime_record_index": int(
                                right["runtime_record_index"]
                            ),
                            "left_endpoint_field": left[
                                "endpoint_field"
                            ],
                            "right_endpoint_field": right[
                                "endpoint_field"
                            ],
                            "left_section": str(
                                left["section"]
                            ).upper(),
                            "right_section": str(
                                right["section"]
                            ).upper(),
                            "kernel": kernel,
                        }
                    )

    total_cells = {
        (int(row), int(column))
        for key in cell_provenance
        for row, column in [key.split(",", 1)]
        for row, column in [(int(row), int(column))]
    }
    self_operation_count = sum(
        operation["kind"] == "self"
        for operation in operations
    )
    pair_operation_count = sum(
        operation["kind"] == "pair"
        for operation in operations
    )

    canonical_provenance = {
        key: list(entries)
        for key, entries in sorted(cell_provenance.items())
    }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors and witness.get("ready") is True,
        "scalar_count": int(witness.get("scalar_count", 0)),
        "runtime_constraint_records": int(
            witness.get("runtime_constraint_records", 0)
        ),
        "body_count": int(witness.get("body_count", 0)),
        "endpoint_group_count": int(
            witness.get("endpoint_insertion_count", 0)
        ),
        "self_operation_count": self_operation_count,
        "pair_operation_count": pair_operation_count,
        "operation_count": len(operations),
        "write_cell_count": len(total_cells),
        "strict_upper_write_cell_count": sum(
            row < column
            for row, column in total_cells
        ),
        "operations": operations,
        "cell_provenance": canonical_provenance,
        "errors": errors,
        "source_contract": {
            "self": "one operation per BODY endpoint group",
            "pair": "one operation per unordered pair of groups sharing the same BODY",
            "storage": "larger scalar base is lower-triangle row-domain",
        },
    }


def compare_with_phase491(
    endpoint_schedule: Mapping[str, Any],
    phase491: Mapping[str, Any],
) -> dict[str, Any]:
    current = {
        key
        for key in endpoint_schedule.get("cell_provenance") or {}
    }
    previous = {
        key
        for key in phase491.get("cell_provenance") or {}
    }
    missing = sorted(previous - current)
    extra = sorted(current - previous)

    return {
        "format": "SHIFT.SDFEndpointContributionScheduleComparison/1",
        "version": 1,
        "ready": not missing and not extra,
        "status": "matched" if not missing and not extra else "structural-divergence",
        "previous_cell_count": len(previous),
        "current_cell_count": len(current),
        "missing_from_endpoint_schedule": missing,
        "extra_in_endpoint_schedule": extra,
    }


def summarize_endpoint_schedule(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "scalar_count": report.get("scalar_count"),
        "body_count": report.get("body_count"),
        "runtime_constraint_records": report.get(
            "runtime_constraint_records"
        ),
        "endpoint_group_count": report.get("endpoint_group_count"),
        "self_operation_count": report.get("self_operation_count"),
        "pair_operation_count": report.get("pair_operation_count"),
        "operation_count": report.get("operation_count"),
        "write_cell_count": report.get("write_cell_count"),
        "strict_upper_write_cell_count": report.get(
            "strict_upper_write_cell_count"
        ),
        "ready": bool(report.get("ready")),
    }


def validate_endpoint_schedule(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    operations = report.get("operations") or []

    if len(operations) != int(report.get("operation_count", 0)):
        errors.append("operation-count-mismatch")

    expected_self = int(report.get("endpoint_group_count", 0))
    if int(report.get("self_operation_count", 0)) != expected_self:
        errors.append("self-operation-count-mismatch")

    for operation in operations:
        for row, column in operation.get("cells") or []:
            row = int(row)
            column = int(column)
            if not (
                0 <= row < scalar_count
                and 0 <= column < scalar_count
                and row >= column
            ):
                errors.append(
                    f"operation-cell-out-of-lower-domain:{row},{column}"
                )
        if operation.get("kernel") not in KERNELS.values():
            errors.append(
                f"operation-unknown-kernel:{operation.get('kernel')}"
            )

    if int(report.get("write_cell_count", 0)) != len(
        report.get("cell_provenance") or {}
    ):
        errors.append("write-cell-provenance-count-mismatch")

    return {
        "format": "SHIFT.SDFEndpointContributionScheduleValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
    }


def build_endpoint_schedule_contract(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    report = build_endpoint_contribution_schedule(solver_domain)
    report["summary"] = summarize_endpoint_schedule(report)
    report["validation"] = validate_endpoint_schedule(report)
    return report


__all__ = [
    "FORMAT",
    "KERNELS",
    "build_endpoint_contribution_schedule",
    "compare_with_phase491",
    "summarize_endpoint_schedule",
    "validate_endpoint_schedule",
    "build_endpoint_schedule_contract",
]
