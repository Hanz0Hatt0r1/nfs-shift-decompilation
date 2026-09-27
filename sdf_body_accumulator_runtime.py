"""Source-backed per-body solver accumulator storage for SHIFT SDF physics."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFBodyAccumulatorRuntime/1"

BODY_STORAGE = {
    "primary": {"base": "+0x150", "count": "+0xa4", "element_size": 8},
    "secondary": {"base": "+0x154", "count": "+0xa8", "element_size": 8},
    "row_pointers": {"base": "+0x158", "count": "+0xac", "element_size": 4},
    "row_indices": {"base": "+0x15c", "count_source": "+0xac", "element_size": 4},
}

HINGE_SAMPLE = {
    "base": "+0x164",
    "stride": 0xA0,
    "transform_flag": "+0x98",
    "negative_body_pointer": "+0x90",
    "negative_sample_pointer": "+0x84",
    "sample_transform": "+0x78",
}


def describe_sdf_body_accumulator_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "storage-contract",
        "ready": True,
        "function": "FUN_007bb8d0",
        "storage": BODY_STORAGE,
        "hinge_refresh": {
            "sample_array": HINGE_SAMPLE["base"],
            "sample_stride": HINGE_SAMPLE["stride"],
            "condition": "sample +0x98 != 0",
            "transform_call": "FUN_007aefb0",
            "destination": "negative body +0xd4",
            "source": "hinge sample +0x78",
            "sample": "hinge sample +0x84",
        },
        "reset": {
            "primary": "zero +0xa4 double entries beginning at +0x150",
            "secondary": "zero +0xa8 double entries beginning at +0x154",
        },
        "pointer_table": {
            "source_index_vector": "+0x15c",
            "destination_pointer_table": "+0x158",
            "formula": "row_pointers[i] = +0x154 + row_indices[i] * 8",
            "count": "+0xac",
        },
        "evidence": {
            "function": "FUN_007bb8d0",
            "hinge_transform_helper": "FUN_007aefb0",
        },
        "limitations": [
            "Primary/secondary accumulator semantics are preserved as raw storage regions.",
            "The pointer table is described structurally; row index generation is outside this function.",
        ],
    }


def build_sdf_body_accumulator_reset(
    *,
    primary_count: int,
    secondary_count: int,
    row_indices: Sequence[int],
) -> dict[str, Any]:
    p = int(primary_count)
    s = int(secondary_count)
    indices = [int(value) for value in row_indices]
    if p < 0 or s < 0:
        raise ValueError("accumulator counts must be non-negative")
    return {
        "format": "SHIFT.SDFBodyAccumulatorReset/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "primary_count": p,
        "secondary_count": s,
        "primary_after_reset": [0.0] * p,
        "secondary_after_reset": [0.0] * s,
        "row_indices": indices,
        "row_pointers": [
            f"+0x154+{index}*8"
            for index in indices
        ],
        "evidence": {
            "function": "FUN_007bb8d0",
            "primary_base": "+0x150",
            "secondary_base": "+0x154",
            "pointer_table_base": "+0x158",
            "row_index_base": "+0x15c",
        },
    }


def validate_sdf_body_accumulator_reset(report: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    p = int(report.get("primary_count", 0))
    s = int(report.get("secondary_count", 0))
    if len(report.get("primary_after_reset") or []) != p:
        errors.append("primary-count-mismatch")
    if len(report.get("secondary_after_reset") or []) != s:
        errors.append("secondary-count-mismatch")
    if len(report.get("row_pointers") or []) != len(report.get("row_indices") or []):
        errors.append("pointer-table-count-mismatch")
    return {
        "format": "SHIFT.SDFBodyAccumulatorValidation/1",
        "version": 1,
        "ready": not errors,
        "status": "validated" if not errors else "blocked",
        "errors": errors,
        "evidence": {"function": "FUN_007bb8d0"},
    }
