"""Exact static row-pointer tables exposed by the specialized SHIFT providers.

The initialization functions FUN_007d2f70 and FUN_007cd980 populate one pointer
per solver row. The address differences define the provider's static row
segments. This module records those addresses and derives segment sizes without
claiming that a segment's capacity is identical to a matrix non-zero count.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from specialized_provider_storage_runtime import (
    PROVIDER0_STORAGE,
    PROVIDER1_STORAGE,
    ProviderStorageLayout,
)

FORMAT = "SHIFT.SpecializedProviderRowStorageRuntime/1"

PROVIDER0_ROW_POINTERS = (
    0x00C21738, 0x00C21800, 0x00C218C8, 0x00C21978, 0x00C21A50,
    0x00C21B28, 0x00C21C18, 0x00C21CE0, 0x00C21D90, 0x00C21E68,
    0x00C21F08, 0x00C21FD0, 0x00C22098, 0x00C22148, 0x00C22220,
    0x00C222F8, 0x00C223E8, 0x00C224B0, 0x00C22560, 0x00C22638,
    0x00C22778, 0x00C228B8, 0x00C229F8, 0x00C22B38, 0x00C22C78,
    0x00C22DA0, 0x00C22EC8, 0x00C22FF0, 0x00C23118, 0x00C23240,
    0x00C23330, 0x00C23420, 0x00C23510, 0x00C23600, 0x00C236F0,
    0x00C237C8, 0x00C238A0, 0x00C23978, 0x00C23A50, 0x00C23B28,
)

PROVIDER1_ROW_POINTERS = (
    0x00C1FE38, 0x00C1FEE8, 0x00C1FF98, 0x00C20048, 0x00C200F8,
    0x00C201A8, 0x00C20258, 0x00C20308, 0x00C203B8, 0x00C20468,
    0x00C204C8, 0x00C20560, 0x00C205F8, 0x00C20690, 0x00C20728,
    0x00C20810, 0x00C20920, 0x00C20A30, 0x00C20AB0, 0x00C20B30,
    0x00C20BB0, 0x00C20CC0, 0x00C20D40, 0x00C20DC0, 0x00C20E80,
    0x00C20F40, 0x00C21000, 0x00C210C0, 0x00C21180, 0x00C21218,
    0x00C212B0, 0x00C21348, 0x00C213E0, 0x00C21478,
)


@dataclass(frozen=True)
class RowSegment:
    row: int
    start: int
    end: int
    bytes: int
    doubles: int


def get_row_pointers(provider_id: int) -> tuple[int, ...]:
    if provider_id == 0:
        return PROVIDER0_ROW_POINTERS
    if provider_id == 1:
        return PROVIDER1_ROW_POINTERS
    raise ValueError(f"unsupported provider id: {provider_id}")


def get_storage_layout(provider_id: int) -> ProviderStorageLayout:
    if provider_id == 0:
        return PROVIDER0_STORAGE
    if provider_id == 1:
        return PROVIDER1_STORAGE
    raise ValueError(f"unsupported provider id: {provider_id}")


def build_row_segments(provider_id: int) -> tuple[RowSegment, ...]:
    pointers = get_row_pointers(provider_id)
    layout = get_storage_layout(provider_id)
    segments = []
    for row, start in enumerate(pointers):
        end = pointers[row + 1] if row + 1 < len(pointers) else layout.output_vector_base
        size = end - start
        if size < 0:
            raise ValueError(f"row {row} has descending pointer address")
        if size % 8:
            raise ValueError(f"row {row} segment is not double-aligned")
        segments.append(RowSegment(
            row=row,
            start=start,
            end=end,
            bytes=size,
            doubles=size // 8,
        ))
    return tuple(segments)


def validate_row_pointer_table(provider_id: int) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    pointers = get_row_pointers(provider_id)
    errors: list[str] = []

    if len(pointers) != layout.scalar_count:
        errors.append("pointer-count-does-not-equal-scalar-count")
    if pointers and pointers[0] != layout.factor_workspace_base:
        errors.append("first-pointer-does-not-equal-factor-workspace-base")
    if pointers != tuple(sorted(pointers)):
        errors.append("row-pointers-not-monotonic")

    segments = build_row_segments(provider_id)
    total_doubles = sum(segment.doubles for segment in segments)
    if total_doubles != layout.factor_workspace_doubles:
        errors.append("row-segment-sum-does-not-equal-workspace-size")

    for previous, current in zip(pointers, pointers[1:]):
        if current - previous <= 0:
            errors.append("non-positive-row-segment")
            break

    if segments and segments[-1].end != layout.output_vector_base:
        errors.append("last-row-segment-does-not-end-at-output-vector")

    return {
        "format": "SHIFT.SpecializedProviderRowStorageValidation/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": errors,
        "row_count": len(pointers),
        "workspace_doubles": total_doubles,
        "segments": [
            {
                "row": s.row,
                "start": hex(s.start),
                "end": hex(s.end),
                "bytes": s.bytes,
                "doubles": s.doubles,
            }
            for s in segments
        ],
    }


def build_row_storage_contract() -> dict[str, Any]:
    providers = []
    for provider_id in (0, 1):
        layout = get_storage_layout(provider_id)
        segments = build_row_segments(provider_id)
        validation = validate_row_pointer_table(provider_id)
        providers.append({
            "provider_id": provider_id,
            "row_pointer_table": {
                "base": hex(layout.row_pointer_base),
                "entry_count": layout.scalar_count,
                "entry_size_bytes": 4,
            },
            "pointer_addresses": [hex(p) for p in get_row_pointers(provider_id)],
            "row_segments": [
                {
                    "row": s.row,
                    "start": hex(s.start),
                    "end": hex(s.end),
                    "doubles": s.doubles,
                }
                for s in segments
            ],
            "workspace_double_count": layout.factor_workspace_doubles,
            "validation": validation,
        })
    return {
        "format": FORMAT,
        "version": 1,
        "source_functions": {
            "provider0_init": "FUN_007d2f70",
            "provider1_init": "FUN_007cd980",
        },
        "providers": providers,
        "status": "source-backed-static-row-topology",
        "limitations": [
            "A row-segment double count is storage capacity/extent, not a direct non-zero count.",
            "Internal sparse index encoding inside each segment remains to be decoded from the provider solve implementation.",
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_row_storage_contract(), indent=2, sort_keys=True))
