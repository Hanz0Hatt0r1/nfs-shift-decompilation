"""Source-backed export of SDF body accumulators into solver buffers."""
from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.SDFBodySolverExportRuntime/1"

SOURCE_OFFSETS = {
    "primary": "+0x150",
    "primary_count": "+0xa4",
    "secondary": "+0x154",
    "secondary_count": "+0xa8",
}


def describe_sdf_body_solver_export_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007ba570",
        "sources": SOURCE_OFFSETS,
        "destination_arguments": {
            "primary_destination": "param_1",
            "secondary_destination": "param_2",
        },
        "operations": [
            {
                "source": "+0x150",
                "count": "+0xa4",
                "stride": 8,
                "operation": "destination[i] += source[i]",
            },
            {
                "source": "+0x154",
                "count": "+0xa8",
                "stride": 8,
                "operation": "destination[i] += source[i]",
            },
        ],
        "order": [
            "copy primary accumulator",
            "copy secondary accumulator",
        ],
        "limitations": [
            "Destination buffers are caller-owned and their higher-level role is intentionally unnamed.",
            "No physical units are inferred from the double channels.",
        ],
    }


def export_body_accumulators(
    primary: Sequence[float | int],
    secondary: Sequence[float | int],
    primary_destination: Sequence[float | int],
    secondary_destination: Sequence[float | int],
) -> dict[str, Any]:
    """Apply the exact additive buffer transfer performed by FUN_007ba570."""
    if len(primary_destination) < len(primary):
        raise ValueError("primary destination is shorter than primary accumulator")
    if len(secondary_destination) < len(secondary):
        raise ValueError("secondary destination is shorter than secondary accumulator")

    primary_out = [float(value) for value in primary_destination]
    secondary_out = [float(value) for value in secondary_destination]
    for index, value in enumerate(primary):
        primary_out[index] += float(value)
    for index, value in enumerate(secondary):
        secondary_out[index] += float(value)

    return {
        "format": "SHIFT.SDFBodySolverExportResult/1",
        "version": 1,
        "status": "applied",
        "ready": True,
        "primary": primary_out,
        "secondary": secondary_out,
        "source_counts": {
            "primary": len(primary),
            "secondary": len(secondary),
        },
        "evidence": {
            "function": "FUN_007ba570",
            "primary_source": "+0x150",
            "secondary_source": "+0x154",
            "primary_count": "+0xa4",
            "secondary_count": "+0xa8",
        },
    }
