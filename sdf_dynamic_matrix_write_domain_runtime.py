"""Enumerate the dynamic matrix write domain of JOINT/HINGE/BAR kernels.

Phase 491 is intentionally coefficient-free. It derives the lower-triangle cells
that the recovered coupling kernels can write from the ordered solver-domain
constraint blocks and the endpoint-sharing graph.

Kernel ownership follows the already reconstructed source split:
JOINT-centric writes -> FUN_007bbb80, HINGE-centric -> FUN_007bb250,
BAR/BAR -> FUN_007bb6c0.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from rigid_body_sdf_runtime import build_sdf_constraint_connectivity_matrix

FORMAT = "SHIFT.SDFDynamicMatrixWriteDomainRuntime/1"

KERNELS = {
    "JOINT": "FUN_007bbb80",
    "HINGE": "FUN_007bb250",
    "BAR": "FUN_007bb6c0",
}


def _section(record: Mapping[str, Any]) -> str:
    value = str(record.get("section", "")).upper()
    if value not in KERNELS:
        raise ValueError(f"unsupported solver section: {value}")
    return value


def _width(record: Mapping[str, Any]) -> int:
    return int(record.get("solver_width", 0))


def _base(record: Mapping[str, Any]) -> int:
    return int(record.get("scalar_base", -1))


def _lower_self_cells(base: int, width: int) -> set[tuple[int, int]]:
    return {
        (base + row_offset, base + column_offset)
        for row_offset in range(width)
        for column_offset in range(row_offset + 1)
    }


def _pair_lower_cells(
    left_base: int,
    left_width: int,
    right_base: int,
    right_width: int,
) -> set[tuple[int, int]]:
    if left_base == right_base:
        raise ValueError("distinct runtime blocks must not share scalar base")

    if left_base < right_base:
        row_base, row_width = right_base, right_width
        column_base, column_width = left_base, left_width
    else:
        row_base, row_width = left_base, left_width
        column_base, column_width = right_base, right_width

    return {
        (row_base + row_offset, column_base + column_offset)
        for row_offset in range(row_width)
        for column_offset in range(column_width)
    }


def _pair_kernel(left_section: str, right_section: str) -> str:
    if "JOINT" in {left_section, right_section}:
        return KERNELS["JOINT"]
    if "HINGE" in {left_section, right_section}:
        return KERNELS["HINGE"]
    return KERNELS["BAR"]


def build_dynamic_write_domain(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    records = list(solver_domain.get("records") or [])
    scalar_count = int(solver_domain.get("solver_scalar_count", 0))
    errors: list[str] = []

    try:
        connectivity = build_sdf_constraint_connectivity_matrix(
            {
                "records": [
                    {
                        "source_record_index": record.get(
                            "source_record_index",
                            record.get("runtime_record_index", index),
                        ),
                        "source_section": record.get(
                            "source_section",
                            record.get("section"),
                        ),
                        "section": record.get("section"),
                        "posbody": record.get("posbody"),
                        "negbody": record.get("negbody"),
                        "vectors": {},
                    }
                    for index, record in enumerate(records)
                ],
                "body_count": solver_domain.get("body_count"),
            }
        )
    except (TypeError, ValueError) as exc:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "scalar_count": scalar_count,
            "records": [],
            "connectivity": None,
            "errors": [f"connectivity-build:{exc}"],
        }

    shared_pairs = list(connectivity.get("shared_body_pairs") or [])
    writes: list[dict[str, Any]] = []
    cell_provenance: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)

    self_cells: set[tuple[int, int]] = set()
    pair_cells: set[tuple[int, int]] = set()

    for runtime_record_index, record in enumerate(records):
        section = _section(record)
        width = _width(record)
        base = _base(record)

        if width <= 0:
            errors.append(
                f"record-{runtime_record_index}-nonpositive-width"
            )
            continue

        expected_range = list(range(base, base + width))
        actual_range = [
            int(value)
            for value in record.get("scalar_indices") or []
        ]
        if actual_range != expected_range:
            errors.append(
                f"record-{runtime_record_index}-scalar-range-mismatch"
            )
            continue

        if base < 0 or base + width > scalar_count:
            errors.append(
                f"record-{runtime_record_index}-scalar-range-out-of-domain"
            )
            continue

        cells = _lower_self_cells(base, width)
        self_cells.update(cells)
        witness = {
            "kind": "self",
            "kernel": KERNELS[section],
            "runtime_record_index": int(
                record.get("runtime_record_index", runtime_record_index)
            ),
            "ordered_position": runtime_record_index,
            "section": section,
            "row_base": base,
            "column_base": base,
            "width": width,
            "same_record": True,
        }
        writes.append(
            {
                **witness,
                "cell_count": len(cells),
                "cells": [
                    [row, column]
                    for row, column in sorted(cells)
                ],
            }
        )
        for cell in cells:
            cell_provenance[cell].append(witness)

    for pair in shared_pairs:
        left = int(pair.get("left", -1))
        right = int(pair.get("right", -1))
        shared_body = str(pair.get("shared_body", ""))

        if not (0 <= left < len(records) and 0 <= right < len(records)):
            errors.append(
                f"connectivity-pair-out-of-domain:{left}:{right}"
            )
            continue

        left_record = records[left]
        right_record = records[right]
        left_section = _section(left_record)
        right_section = _section(right_record)
        left_base = _base(left_record)
        right_base = _base(right_record)
        left_width = _width(left_record)
        right_width = _width(right_record)

        try:
            cells = _pair_lower_cells(
                left_base,
                left_width,
                right_base,
                right_width,
            )
        except ValueError as exc:
            errors.append(
                f"pair-{left}-{right}:{exc}"
            )
            continue

        pair_cells.update(cells)
        kernel = _pair_kernel(
            left_section,
            right_section,
        )
        if left_base < right_base:
            row_base, column_base = right_base, left_base
            row_width, column_width = right_width, left_width
        else:
            row_base, column_base = left_base, right_base
            row_width, column_width = left_width, right_width

        witness = {
            "kind": "pair",
            "kernel": kernel,
            "left_runtime_record_index": int(
                left_record.get("runtime_record_index", left)
            ),
            "right_runtime_record_index": int(
                right_record.get("runtime_record_index", right)
            ),
            "left_ordered_position": left,
            "right_ordered_position": right,
            "left_section": left_section,
            "right_section": right_section,
            "shared_body": shared_body,
            "same_side_rule": "source side flags decide add/subtract",
            "row_base": row_base,
            "column_base": column_base,
            "row_width": row_width,
            "column_width": column_width,
        }
        writes.append(
            {
                **witness,
                "cell_count": len(cells),
                "cells": [
                    [row, column]
                    for row, column in sorted(cells)
                ],
            }
        )
        for cell in cells:
            cell_provenance[cell].append(witness)

    canonical: dict[str, list[dict[str, Any]]] = {}
    for (row, column), entries in sorted(cell_provenance.items()):
        unique = {
            tuple(sorted(entry.items()))
            for entry in entries
        }
        canonical[f"{row},{column}"] = [
            dict(items)
            for items in sorted(unique)
        ]

    all_cells = self_cells | pair_cells
    strict_upper = {
        (row, column)
        for row, column in all_cells
        if row < column
    }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors and connectivity.get("ready") is True,
        "scalar_count": scalar_count,
        "runtime_constraint_records": len(records),
        "shared_constraint_pairs": len(shared_pairs),
        "self_cell_count": len(self_cells),
        "pair_cell_count": len(pair_cells),
        "union_cell_count": len(all_cells),
        "strict_upper_cell_count": len(strict_upper),
        "writes": writes,
        "cell_provenance": canonical,
        "connectivity": connectivity,
        "kernel_write_counts": {
            kernel: sum(
                entry.get("kernel") == kernel
                for entry in writes
            )
            for kernel in KERNELS.values()
        },
        "errors": list(dict.fromkeys(errors)),
    }


def provenance_for_dynamic_cell(
    report: Mapping[str, Any],
    row: int,
    column: int,
) -> list[dict[str, Any]]:
    return [
        dict(entry)
        for entry in (
            report.get("cell_provenance") or {}
        ).get(f"{int(row)},{int(column)}", [])
    ]


def summarize_dynamic_write_domain(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "scalar_count": report.get("scalar_count"),
        "runtime_constraint_records": report.get(
            "runtime_constraint_records"
        ),
        "shared_constraint_pairs": report.get(
            "shared_constraint_pairs"
        ),
        "self_cell_count": report.get("self_cell_count"),
        "pair_cell_count": report.get("pair_cell_count"),
        "union_cell_count": report.get("union_cell_count"),
        "strict_upper_cell_count": report.get(
            "strict_upper_cell_count"
        ),
        "kernel_write_counts": dict(
            report.get("kernel_write_counts") or {}
        ),
        "ready": bool(report.get("ready")),
    }


def validate_dynamic_write_domain(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    for key, entries in (
        report.get("cell_provenance") or {}
    ).items():
        try:
            row_text, column_text = str(key).split(",", 1)
            row = int(row_text)
            column = int(column_text)
        except (TypeError, ValueError):
            errors.append(f"invalid-dynamic-cell-key:{key}")
            continue

        if not (
            0 <= row < scalar_count
            and 0 <= column < scalar_count
            and row >= column
        ):
            errors.append(f"dynamic-cell-out-of-lower-domain:{key}")

        for entry in entries:
            if entry.get("kernel") not in KERNELS.values():
                errors.append(
                    f"unknown-dynamic-kernel:{key}:{entry.get('kernel')}"
                )

    if int(report.get("union_cell_count", 0)) != len(
        report.get("cell_provenance") or {}
    ):
        errors.append("dynamic-cell-count-provenance-mismatch")

    return {
        "format": "SHIFT.SDFDynamicMatrixWriteDomainValidation/1",
        "version": 1,
        "ready": not errors,
        "scalar_count": scalar_count,
        "errors": list(dict.fromkeys(errors)),
    }


def build_dynamic_write_domain_contract(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    report = build_dynamic_write_domain(solver_domain)
    report["summary"] = summarize_dynamic_write_domain(report)
    report["validation"] = validate_dynamic_write_domain(report)
    return report


__all__ = [
    "FORMAT",
    "KERNELS",
    "build_dynamic_write_domain",
    "provenance_for_dynamic_cell",
    "summarize_dynamic_write_domain",
    "validate_dynamic_write_domain",
    "build_dynamic_write_domain_contract",
]
