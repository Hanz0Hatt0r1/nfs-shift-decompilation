"""Provenance for each structural cell of the pre-acceptance BODY matrix.

Phase 489 explains why a structural matrix cell is non-zero by retaining the
BODY and scalar-group witnesses that generated it. A cell can have multiple
producers when several constraints share the same BODY.

This is a storage/structure provenance layer. It does not assign physical
meaning to the cell.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from body_scalar_group_population_runtime import build_scalar_group_witness

FORMAT = "SHIFT.BodyMatrixCellProvenanceRuntime/1"


def _cell_key(row: int, column: int) -> str:
    return f"{int(row)},{int(column)}"


def build_cell_provenance(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    witness = build_scalar_group_witness(solver_domain)
    scalar_count = int(witness.get("scalar_count", 0))
    provenance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors = list(witness.get("errors") or [])

    for body, groups in (
        witness.get("groups_by_body") or {}
    ).items():
        materialized = list(groups)
        for source_index, source_group in enumerate(materialized):
            for target_index, target_group in enumerate(materialized):
                for row in source_group.get("scalar_indices") or []:
                    for column in target_group.get("scalar_indices") or []:
                        row = int(row)
                        column = int(column)
                        if not (
                            0 <= row < scalar_count
                            and 0 <= column < scalar_count
                        ):
                            errors.append(
                                f"cell-out-of-domain:{row}:{column}"
                            )
                            continue

                        key = _cell_key(row, column)
                        provenance[key].append(
                            {
                                "body": str(body),
                                "source_group_index": source_index,
                                "target_group_index": target_index,
                                "source_ordered_position": int(
                                    source_group["ordered_position"]
                                ),
                                "target_ordered_position": int(
                                    target_group["ordered_position"]
                                ),
                                "source_runtime_record_index": int(
                                    source_group["runtime_record_index"]
                                ),
                                "target_runtime_record_index": int(
                                    target_group["runtime_record_index"]
                                ),
                                "source_endpoint_field": (
                                    source_group["endpoint_field"]
                                ),
                                "target_endpoint_field": (
                                    target_group["endpoint_field"]
                                ),
                                "source_section": source_group["section"],
                                "target_section": target_group["section"],
                                "source_scalar_index": row,
                                "target_scalar_index": column,
                                "value": 1.0,
                            }
                        )

    # Deduplicate equivalent witnesses while preserving deterministic order.
    canonical: dict[str, list[dict[str, Any]]] = {}
    for key, entries in sorted(provenance.items()):
        unique = {
            tuple(sorted(entry.items()))
            for entry in entries
        }
        canonical[key] = [
            dict(items)
            for items in sorted(unique)
        ]

    nonzero_cells = set(canonical)
    diagonal_cells = {
        _cell_key(index, index)
        for index in range(scalar_count)
        if _cell_key(index, index) in nonzero_cells
    }
    symmetric = all(
        _cell_key(row, column) in nonzero_cells
        and _cell_key(column, row) in nonzero_cells
        for row in range(scalar_count)
        for column in range(row + 1, scalar_count)
        if _cell_key(row, column) in nonzero_cells
        or _cell_key(column, row) in nonzero_cells
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "scalar_count": scalar_count,
        "body_count": int(witness.get("body_count", 0)),
        "provenance": canonical,
        "nonzero_cell_count": len(nonzero_cells),
        "diagonal_cell_count": len(diagonal_cells),
        "max_producers_per_cell": max(
            (len(entries) for entries in canonical.values()),
            default=0,
        ),
        "symmetric_support": symmetric,
        "witness": {
            "endpoint_insertions": int(
                witness.get("endpoint_insertion_count", 0)
            ),
            "runtime_constraint_records": int(
                witness.get("runtime_constraint_records", 0)
            ),
        },
        "errors": list(dict.fromkeys(errors)),
    }


def provenance_for_cell(
    report: Mapping[str, Any],
    row: int,
    column: int,
) -> list[dict[str, Any]]:
    key = _cell_key(row, column)
    return [
        dict(entry)
        for entry in (
            report.get("provenance") or {}
        ).get(key, [])
    ]


def summarize_cell_provenance(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    provenance = report.get("provenance") or {}
    producer_counts = [len(entries) for entries in provenance.values()]
    return {
        "scalar_count": report.get("scalar_count"),
        "body_count": report.get("body_count"),
        "nonzero_cell_count": report.get(
            "nonzero_cell_count"
        ),
        "diagonal_cell_count": report.get(
            "diagonal_cell_count"
        ),
        "max_producers_per_cell": report.get(
            "max_producers_per_cell"
        ),
        "cells_with_multiple_producers": sum(
            count > 1
            for count in producer_counts
        ),
        "symmetric_support": bool(
            report.get("symmetric_support")
        ),
        "ready": bool(report.get("ready")),
    }


def validate_cell_provenance(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    provenance = report.get("provenance") or {}

    for key, entries in provenance.items():
        try:
            row_text, column_text = str(key).split(",", 1)
            row = int(row_text)
            column = int(column_text)
        except (TypeError, ValueError):
            errors.append(f"invalid-cell-key:{key}")
            continue

        if not (
            0 <= row < scalar_count
            and 0 <= column < scalar_count
        ):
            errors.append(f"cell-key-out-of-domain:{key}")

        for entry in entries:
            if float(entry.get("value", 0.0)) != 1.0:
                errors.append(f"non-unit-provenance-value:{key}")
            if int(entry.get("source_scalar_index", -1)) != row:
                errors.append(
                    f"source-index-mismatch:{key}"
                )
            if int(entry.get("target_scalar_index", -1)) != column:
                errors.append(
                    f"target-index-mismatch:{key}"
                )

    if int(report.get("nonzero_cell_count", 0)) != len(provenance):
        errors.append("nonzero-cell-count-mismatch")

    return {
        "format": "SHIFT.BodyMatrixCellProvenanceValidation/1",
        "version": 1,
        "ready": not errors,
        "scalar_count": scalar_count,
        "errors": list(dict.fromkeys(errors)),
    }


def build_cell_provenance_contract(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    report = build_cell_provenance(solver_domain)
    report["summary"] = summarize_cell_provenance(report)
    report["validation"] = validate_cell_provenance(report)
    return report


__all__ = [
    "FORMAT",
    "build_cell_provenance",
    "provenance_for_cell",
    "summarize_cell_provenance",
    "validate_cell_provenance",
    "build_cell_provenance_contract",
]
