"""Compare provider cleanup coverage with the canonical reset domain.

Phase 481 consumes the Phase 480 reset-domain contract rather than rebuilding
reset zero/seed sets locally. The canonical relationship is:

    cleanup-covered storage = reset-zero slots union unit-diagonal seeds

with the two reset sets expected to be disjoint for the shipped providers.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_reset_domain_runtime import (
    extract_reset_domain,
)
from specialized_provider_zero_baseline_runtime import (
    extract_zero_baseline_profile,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderResetCleanupEquivalenceRuntime/1"


def _coverage_slots(region: dict[str, Any]) -> set[int]:
    slots: set[int] = set()
    for interval in region.get("merged_intervals") or []:
        start = int(str(interval["start"]), 16)
        end = int(str(interval["end"]), 16)
        slots.update(range(start, end, 8))
    slots.update(
        int(str(address), 16)
        for address in region.get("direct_zero_addresses") or []
    )
    return slots


def compare_reset_cleanup(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    cleanup = extract_zero_baseline_profile(
        source,
        provider_id=provider_id,
    )
    reset_domain = extract_reset_domain(
        source,
        provider_id=provider_id,
    )

    cleanup_slots = (
        _coverage_slots(cleanup["workspace"])
        | _coverage_slots(cleanup["output_vector"])
    )
    reset_zero = {
        int(str(address), 16)
        for address in reset_domain.get("zero_addresses") or []
    }
    reset_one = {
        int(str(address), 16)
        for address in reset_domain.get(
            "unit_diagonal_addresses"
        ) or []
    }
    reset_touched = {
        int(str(address), 16)
        for address in reset_domain.get("touched_addresses") or []
    }

    reset_zero_minus_cleanup = reset_zero - cleanup_slots
    cleanup_minus_reset_zero = cleanup_slots - reset_zero
    diagonal_outside_cleanup = reset_one - cleanup_slots
    diagonal_overlap_reset_zero = reset_one & reset_zero

    cleanup_reconstructed_from_reset = (
        reset_touched == cleanup_slots
    )
    cleanup_reset_partition_disjoint = not diagonal_overlap_reset_zero

    output_start = layout.output_vector_base
    output_end = output_start + layout.output_vector_bytes
    cleanup_output = {
        address
        for address in cleanup_slots
        if output_start <= address < output_end
    }
    reset_output_zero = {
        address
        for address in reset_zero
        if output_start <= address < output_end
    }
    reset_output_touched = {
        address
        for address in reset_touched
        if output_start <= address < output_end
    }

    errors = list(cleanup.get("errors") or [])
    errors.extend(reset_domain.get("errors") or [])

    if reset_zero_minus_cleanup:
        errors.append(
            f"reset-zero-not-in-cleanup:{len(reset_zero_minus_cleanup)}"
        )
    missing_seed_slots = cleanup_minus_reset_zero - reset_one
    if missing_seed_slots:
        errors.append(
            f"cleanup-slot-missing-reset-seed:{len(missing_seed_slots)}"
        )
    if diagonal_outside_cleanup:
        errors.append(
            f"diagonal-outside-cleanup:{len(diagonal_outside_cleanup)}"
        )
    if diagonal_overlap_reset_zero:
        errors.append(
            f"diagonal-overlaps-reset-zero:{len(diagonal_overlap_reset_zero)}"
        )
    if not cleanup_reconstructed_from_reset:
        errors.append("cleanup-not-reconstructed-from-reset")

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "reset_function": reset_domain.get("reset_function"),
        "cleanup_function": cleanup.get("cleanup_function"),
        "cleanup_storage_slot_count": len(cleanup_slots),
        "reset_zero_slot_count": len(reset_zero),
        "reset_unit_diagonal_count": len(reset_one),
        "reset_touched_slot_count": len(reset_touched),
        "reset_zero_cleanup_exact_match": (
            reset_zero == cleanup_slots
        ),
        "reset_zero_subset_cleanup": reset_zero <= cleanup_slots,
        "unit_diagonal_inside_cleanup": reset_one <= cleanup_slots,
        "unit_diagonal_overlaps_reset_zero": bool(
            diagonal_overlap_reset_zero
        ),
        "cleanup_reconstructed_from_reset": cleanup_reconstructed_from_reset,
        "cleanup_reset_partition_disjoint": cleanup_reset_partition_disjoint,
        "output_cleanup_slot_count": len(cleanup_output),
        "output_reset_zero_slot_count": len(reset_output_zero),
        "output_reset_touched_slot_count": len(reset_output_touched),
        "output_zero_exact_match": (
            cleanup_output == reset_output_touched
        ),
        "reset_zero_not_in_cleanup": [
            hex(address)
            for address in sorted(reset_zero_minus_cleanup)
        ],
        "cleanup_missing_reset_zero": [
            hex(address)
            for address in sorted(cleanup_minus_reset_zero)
        ],
        "cleanup_missing_reset_seed": [
            hex(address)
            for address in sorted(missing_seed_slots)
        ],
        "diagonal_outside_cleanup": [
            hex(address)
            for address in sorted(diagonal_outside_cleanup)
        ],
        "unit_diagonal_in_reset_zero_domain": False,
        "ready": not errors and reset_domain.get("ready") is True,
        "errors": errors,
    }


def summarize_reset_cleanup(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "cleanup_storage_slot_count": report.get(
            "cleanup_storage_slot_count"
        ),
        "reset_zero_slot_count": report.get("reset_zero_slot_count"),
        "reset_unit_diagonal_count": report.get(
            "reset_unit_diagonal_count"
        ),
        "reset_touched_slot_count": report.get(
            "reset_touched_slot_count"
        ),
        "reset_zero_cleanup_exact_match": report.get(
            "reset_zero_cleanup_exact_match"
        ),
        "reset_zero_subset_cleanup": report.get(
            "reset_zero_subset_cleanup"
        ),
        "unit_diagonal_inside_cleanup": report.get(
            "unit_diagonal_inside_cleanup"
        ),
        "unit_diagonal_overlaps_reset_zero": report.get(
            "unit_diagonal_overlaps_reset_zero"
        ),
        "cleanup_reconstructed_from_reset": report.get(
            "cleanup_reconstructed_from_reset"
        ),
        "cleanup_reset_partition_disjoint": report.get(
            "cleanup_reset_partition_disjoint"
        ),
        "output_zero_exact_match": report.get(
            "output_zero_exact_match"
        ),
        "ready": bool(report.get("ready")),
    }


def validate_reset_cleanup(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    if not bool(report.get("reset_zero_subset_cleanup")):
        errors.append("reset-zero-not-subset-of-cleanup")
    if not bool(report.get("unit_diagonal_inside_cleanup")):
        errors.append("unit-diagonal-outside-cleanup")
    if bool(report.get("unit_diagonal_overlaps_reset_zero")):
        errors.append("unit-diagonal-overlaps-reset-zero")
    if not bool(report.get("cleanup_reconstructed_from_reset")):
        errors.append("cleanup-not-reconstructed-from-reset")
    if not bool(report.get("cleanup_reset_partition_disjoint")):
        errors.append("cleanup-reset-partition-not-disjoint")
    if not bool(report.get("output_zero_exact_match")):
        errors.append("output-zero-set-not-equivalent")
    if int(report.get("reset_unit_diagonal_count", 0)) != scalar_count:
        errors.append(
            f"unit-diagonal-count:expected={scalar_count}:"
            f"actual={report.get('reset_unit_diagonal_count', 0)}"
        )

    return {
        "format": (
            "SHIFT.SpecializedProviderResetCleanupEquivalenceValidation/1"
        ),
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
    }


def build_reset_cleanup_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = compare_reset_cleanup(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_reset_cleanup(report)
        report["validation"] = validate_reset_cleanup(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "interpretation": {
            "partition": (
                "cleanup-covered storage = reset-zero slots union "
                "unit-diagonal seed slots"
            ),
            "zero_subset": (
                "reset-zero slots must be a subset of cleanup coverage"
            ),
            "diagonal_seed": (
                "unit-diagonal seed addresses must lie in cleanup coverage "
                "and be disjoint from reset-zero slots"
            ),
        },
        "limitations": [
            "This proves storage initialization topology, not matrix semantics.",
            "Cleanup and reset are compared as storage domains; no per-frame reset frequency is inferred.",
            "The canonical reset domain is supplied by Phase 480.",
        ],
        "status": "source-backed-reset-cleanup-equivalence",
    }


__all__ = [
    "FORMAT",
    "compare_reset_cleanup",
    "summarize_reset_cleanup",
    "validate_reset_cleanup",
    "build_reset_cleanup_contract",
]
