"""Structural reconstruction of FUN_007ba2b0.

Phase 485 captures the source-backed way one BODY contributes to the pre-
acceptance logical matrix: scalar indices are partitioned into width-3, width-2
and width-1 groups, and FUN_007ba2b0 writes exact 1.0 values across the
cartesian product of every pair of groups, symmetrically.

It intentionally does not decode the scalar-index producers themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

FORMAT = "SHIFT.BODYMatrixStructureRuntime/1"

GROUPS = {
    3: {
        "count_offset": 0x98,
        "storage_offset": 0x160,
        "record_stride": 0x40,
        "scalar_index_offset": 0x30,
        "allocated_record_bytes": 0x40,
    },
    2: {
        "count_offset": 0x9C,
        "storage_offset": 0x164,
        "record_stride": 0xA0,
        "scalar_index_offset": 0x94,
        "allocated_record_bytes": 0xA0,
    },
    1: {
        "count_offset": 0xA0,
        "storage_offset": 0x168,
        "record_stride": 0x60,
        "scalar_index_offset": 0x30,
        "allocated_record_bytes": 0x60,
    },
}


@dataclass(frozen=True)
class BodyGroup:
    width: int
    scalar_indices: tuple[int, ...]


def group_descriptor(width: int) -> dict[str, int]:
    try:
        return dict(GROUPS[int(width)])
    except KeyError as exc:
        raise ValueError(f"unsupported body group width: {width}") from exc


def build_body_group(
    width: int,
    scalar_indices: Sequence[int],
) -> BodyGroup:
    width = int(width)
    indices = tuple(int(value) for value in scalar_indices)
    if width not in GROUPS:
        raise ValueError(f"unsupported body group width: {width}")
    if len(indices) != width:
        raise ValueError(
            f"group width {width} requires {width} scalar indices"
        )
    return BodyGroup(width=width, scalar_indices=indices)


def matrix_cells_for_body_groups(
    groups: Iterable[BodyGroup],
) -> set[tuple[int, int]]:
    """Return ordered matrix cells written by FUN_007ba2b0 for these groups."""
    materialized = tuple(groups)
    cells: set[tuple[int, int]] = set()

    for source_group in materialized:
        for target_group in materialized:
            for source_index in source_group.scalar_indices:
                for target_index in target_group.scalar_indices:
                    cells.add((source_index, target_index))
    return cells


def strict_upper_structure(
    groups: Iterable[BodyGroup],
) -> set[tuple[int, int]]:
    return {
        (row, column)
        for row, column in matrix_cells_for_body_groups(groups)
        if row < column
    }


def build_source_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": "FUN_007ba2b0",
        "signature": "void __thiscall FUN_007ba2b0(void *this,int param_1)",
        "arguments": {
            "this": "BODY runtime object",
            "param_1": "logical matrix row-pointer table",
        },
        "body_group_fields": {
            "group_width_3": "+0x98 / +0x160",
            "group_width_2": "+0x9c / +0x164",
            "group_width_1": "+0xa0 / +0x168",
        },
        "group_records": {
            "width_3": {
                "count_offset": "0x98",
                "storage_offset": "0x160",
                "record_stride": "0x40",
                "scalar_index_offset": "0x30",
                "record_bytes": "0x40",
            },
            "width_2": {
                "count_offset": "0x9c",
                "storage_offset": "0x164",
                "record_stride": "0xa0",
                "scalar_index_offset": "0x94",
                "record_bytes": "0xa0",
            },
            "width_1": {
                "count_offset": "0xa0",
                "storage_offset": "0x168",
                "record_stride": "0x60",
                "scalar_index_offset": "0x30",
                "record_bytes": "0x60",
            },
        },
        "operation": {
            "initial_matrix_state": "zeroed by FUN_007b2010",
            "source_group_widths": [3, 2, 1],
            "target_group_widths": [3, 2, 1],
            "cell_value": "exact binary64 1.0",
            "symmetry": "both [row][column] and [column][row] are written",
            "coverage": "cartesian product of scalar indices in every source/target group pair",
        },
        "lifecycle": {
            "caller": "FUN_007b2010",
            "call_frequency": "once per BODY",
            "stage": "before provider +0x14 acceptance",
        },
        "interpretation": {
            "matrix_role": "structural support seed",
            "provider_acceptance_relation": "acceptance later checks non-zero/zero support of this pre-selection matrix",
        },
        "limitations": [
            "Scalar-index producer functions are not decoded in this phase.",
            "The group widths are structural source facts; no semantic variable names are assigned.",
            "The resulting 1.0 cells are a structural seed, not claimed to be final physical coefficients.",
        ],
        "status": "source-backed-body-matrix-structure",
    }


def validate_body_structure() -> dict[str, Any]:
    errors: list[str] = []

    expected = {
        3: (0x98, 0x160, 0x40, 0x30),
        2: (0x9C, 0x164, 0xA0, 0x94),
        1: (0xA0, 0x168, 0x60, 0x30),
    }
    for width, values in expected.items():
        descriptor = group_descriptor(width)
        if (
            descriptor["count_offset"],
            descriptor["storage_offset"],
            descriptor["record_stride"],
            descriptor["scalar_index_offset"],
        ) != values:
            errors.append(f"group-{width}-descriptor-mismatch")

    sample = (
        build_body_group(3, (1, 2, 3)),
        build_body_group(2, (4, 5)),
        build_body_group(1, (6,)),
    )
    cells = matrix_cells_for_body_groups(sample)
    upper = strict_upper_structure(sample)

    if (1, 4) not in cells or (4, 1) not in cells:
        errors.append("cross-group-symmetry-missing")
    if (1, 1) not in cells or (6, 6) not in cells:
        errors.append("within-group-diagonal-missing")
    if (1, 4) not in upper:
        errors.append("strict-upper-cross-group-cell-missing")

    return {
        "format": "SHIFT.BODYMatrixStructureValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "GROUPS",
    "BodyGroup",
    "group_descriptor",
    "build_body_group",
    "matrix_cells_for_body_groups",
    "strict_upper_structure",
    "build_source_contract",
    "validate_body_structure",
]
