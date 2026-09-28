"""Cross-check source-derived factor addresses against real provider mutations.

Phase 465 maps each source factor edge through the exact provider row pointer
table and compares those absolute addresses with the Phase 464 pre/post write
footprint. The comparison is descriptive: factor addresses are expected to be a
subset of the broader provider write footprint, but numeric no-op writes are not
treated as failures.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from specialized_provider_capture_diff_runtime import compare_provider_captures
from specialized_provider_row_storage_runtime import get_row_pointers
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_source_pattern_executor_adapter_runtime import (
    extract_source_factor_edges,
)

FORMAT = "SHIFT.SpecializedProviderSourceCaptureWriteCrosscheckRuntime/1"


def factor_edge_addresses(
    provider_id: int,
    edges: Sequence[tuple[int, int]],
) -> list[dict[str, Any]]:
    pointers = get_row_pointers(provider_id)
    layout = get_storage_layout(provider_id)
    result: list[dict[str, Any]] = []

    for pivot, column in edges:
        pivot = int(pivot)
        column = int(column)
        if not (0 <= pivot < column < layout.scalar_count):
            raise ValueError(
                f"factor edge outside scalar domain: ({pivot},{column})"
            )
        address = pointers[pivot] + column * 8
        if not (
            layout.factor_workspace_base
            <= address
            < layout.output_vector_base
        ):
            raise ValueError(
                f"factor address outside provider workspace: {f"0x{address:08x}"}"
            )
        result.append(
            {
                "pivot_index": pivot,
                "column": column,
                "address": hex(address),
            }
        )

    return result


def crosscheck_source_factor_writes(
    source_pattern: Mapping[str, Any],
    capture_before: Mapping[str, Any],
    capture_after: Mapping[str, Any],
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    provider_id = int(source_pattern["provider_id"])
    edges = {
        (
            int(item["pivot_index"]),
            int(item["column"]),
        )
        for item in source_pattern.get("edges") or []
    }

    capture_diff = compare_provider_captures(
        capture_before,
        capture_after,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    changed_workspace = {
        int(entry["address"], 16)
        for entry in capture_diff.get("workspace_changes") or []
    }
    factor_addresses = factor_edge_addresses(
        provider_id,
        sorted(edges),
    )
    expected_factor_addresses = {
        int(item["address"], 16)
        for item in factor_addresses
    }

    overlap = expected_factor_addresses & changed_workspace
    factor_only = expected_factor_addresses - changed_workspace
    capture_only = changed_workspace - expected_factor_addresses

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "source_factor_edge_count": len(edges),
        "source_factor_address_count": len(expected_factor_addresses),
        "capture_changed_workspace_address_count": len(changed_workspace),
        "overlap_count": len(overlap),
        "factor_address_not_observed_changed_count": len(factor_only),
        "capture_workspace_change_not_factor_count": len(capture_only),
        "overlap_addresses": [
            hex(address)
            for address in sorted(overlap)
        ],
        "factor_addresses_not_observed_changed": [
            hex(address)
            for address in sorted(factor_only)
        ],
        "capture_changes_outside_factor": [
            hex(address)
            for address in sorted(capture_only)
        ],
        "capture_diff_ready": bool(capture_diff.get("ready")),
        "source_pattern_ready": source_pattern.get("ready") is True,
        "ready": bool(capture_diff.get("ready"))
        and source_pattern.get("ready") is True,
        "errors": list(capture_diff.get("errors") or []),
    }


def build_source_capture_crosscheck(
    source: str,
    capture_before: Mapping[str, Any],
    capture_after: Mapping[str, Any],
    *,
    provider_id: int,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    source_pattern = extract_source_factor_edges(
        source,
        provider_id=provider_id,
    )
    return crosscheck_source_factor_writes(
        source_pattern,
        capture_before,
        capture_after,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )


def summarize_crosscheck(report: Mapping[str, Any]) -> dict[str, Any]:
    source_count = int(report.get("source_factor_edge_count", 0))
    overlap = int(report.get("overlap_count", 0))
    return {
        "provider_id": report.get("provider_id"),
        "source_factor_edge_count": source_count,
        "capture_changed_workspace_address_count": int(
            report.get("capture_changed_workspace_address_count", 0)
        ),
        "overlap_count": overlap,
        "source_factor_overlap_ratio": (
            overlap / source_count
            if source_count
            else 1.0
        ),
        "factor_address_not_observed_changed_count": int(
            report.get("factor_address_not_observed_changed_count", 0)
        ),
        "capture_workspace_change_not_factor_count": int(
            report.get("capture_workspace_change_not_factor_count", 0)
        ),
        "ready": bool(report.get("ready")),
    }


def validate_crosscheck(report: Mapping[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])

    factor_count = int(report.get("source_factor_address_count", 0))
    overlap = int(report.get("overlap_count", 0))
    factor_not_changed = int(
        report.get("factor_address_not_observed_changed_count", 0)
    )
    if overlap + factor_not_changed != factor_count:
        errors.append("factor-address-partition-mismatch")

    capture_count = int(
        report.get("capture_changed_workspace_address_count", 0)
    )
    capture_outside = int(
        report.get("capture_workspace_change_not_factor_count", 0)
    )
    if overlap + capture_outside != capture_count:
        errors.append("capture-address-partition-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderSourceCaptureWriteCrosscheckValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
    }


__all__ = [
    "FORMAT",
    "factor_edge_addresses",
    "crosscheck_source_factor_writes",
    "build_source_capture_crosscheck",
    "summarize_crosscheck",
    "validate_crosscheck",
]
