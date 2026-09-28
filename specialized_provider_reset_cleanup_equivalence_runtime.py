"""Cross-check specialized-provider reset state against cleanup zero coverage.

Phase 468 combines the Phase 466 reset profile with the Phase 467 cleanup
profile. It proves whether the direct reset-zero address set reproduces the
storage slots cleared by cleanup and whether the reset's unit-diagonal writes
land on that same zero baseline.

The comparison remains storage-level; no matrix semantics are assigned.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_reset_profile_runtime import (
    extract_reset_profile,
)
from specialized_provider_zero_baseline_runtime import (
    extract_zero_baseline_profile,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderResetCleanupEquivalenceRuntime/1"


def _profile_zero_addresses(
    reset_report: dict[str, Any],
    *,
    start: int,
    end: int,
) -> set[int]:
    """Return all reset-zero storage slots, including bulk-clear ranges."""
    addresses = {
        int(str(address), 16)
        for row in reset_report.get("rows") or []
        for address in row.get("zero_assignments") or []
        if start <= int(str(address), 16) < end
    }

    for row in reset_report.get("rows") or []:
        for clear in row.get("bulk_clears") or []:
            clear_start = int(str(clear["base"]), 16)
            clear_end = clear_start + int(clear["bytes"])
            clipped_start = max(start, clear_start)
            clipped_end = min(end, clear_end)
            if clipped_start < clipped_end:
                addresses.update(
                    range(
                        clipped_start,
                        clipped_end,
                        8,
                    )
                )

    return addresses


def _coverage_slots(region: dict[str, Any]) -> set[int]:
    slots: set[int] = set()
    for interval in region.get("merged_intervals") or []:
        start = int(str(interval["start"]), 16)
        end = int(str(interval["end"]), 16)
        slots.update(
            range(
                start,
                end,
                8,
            )
        )
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
    reset = extract_reset_profile(
        source,
        provider_id=provider_id,
    )

    cleanup_slots = (
        _coverage_slots(cleanup["workspace"])
        | _coverage_slots(cleanup["output_vector"])
    )
    reset_zero = _profile_zero_addresses(
        reset,
        start=layout.factor_workspace_base,
        end=layout.output_vector_base + layout.output_vector_bytes,
    )
    reset_one = _profile_unit_addresses(reset)

    reset_zero_minus_cleanup = reset_zero - cleanup_slots
    cleanup_minus_reset_zero = cleanup_slots - reset_zero
    diagonal_outside_cleanup = reset_one - cleanup_slots
    diagonal_not_zero_before_seed = reset_one - reset_zero
    output_start = layout.output_vector_base
    output_end = output_start + layout.output_vector_bytes

    reset_output_zero = {
        address
        for address in reset_zero
        if output_start <= address < output_end
    }
    cleanup_output = {
        address
        for address in cleanup_slots
        if output_start <= address < output_end
    }

    errors = list(cleanup.get("errors") or [])
    errors.extend(reset.get("errors") or [])

    if reset_zero_minus_cleanup:
        errors.append(
            f"reset-zero-not-in-cleanup:{len(reset_zero_minus_cleanup)}"
        )
    if cleanup_minus_reset_zero:
        errors.append(
            f"cleanup-slot-missing-reset-zero:{len(cleanup_minus_reset_zero)}"
        )
    if diagonal_outside_cleanup:
        errors.append(
            f"diagonal-outside-cleanup:{len(diagonal_outside_cleanup)}"
        )
    if diagonal_not_zero_before_seed:
        errors.append(
            f"diagonal-not-reset-zero:{len(diagonal_not_zero_before_seed)}"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "reset_function": reset["reset_function"],
        "cleanup_function": cleanup["cleanup_function"],
        "cleanup_storage_slot_count": len(cleanup_slots),
        "reset_zero_slot_count": len(reset_zero),
        "reset_unit_diagonal_count": len(reset_one),
        "reset_zero_cleanup_exact_match": (
            reset_zero == cleanup_slots
        ),
        "unit_diagonal_inside_cleanup": reset_one <= cleanup_slots,
        "unit_diagonal_in_reset_zero_domain": unit_diagonal_in_reset_zero_domain,
        "output_cleanup_slot_count": len(cleanup_output),
        "output_reset_zero_slot_count": len(reset_output_zero),
        "output_zero_exact_match": (
            cleanup_output == reset_output_zero
        ),
        "reset_zero_not_in_cleanup": [
            hex(address)
            for address in sorted(reset_zero_minus_cleanup)
        ],
        "cleanup_missing_reset_zero": [
            hex(address)
            for address in sorted(cleanup_minus_reset_zero)
        ],
        "diagonal_outside_cleanup": [
            hex(address)
            for address in sorted(diagonal_outside_cleanup)
        ],
        "diagonal_not_reset_zero": [
            hex(address)
            for address in sorted(diagonal_not_zero_before_seed)
        ],
        "ready": not errors,
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
        "reset_zero_cleanup_exact_match": report.get(
            "reset_zero_cleanup_exact_match"
        ),
        "unit_diagonal_inside_cleanup": report.get(
            "unit_diagonal_inside_cleanup"
        ),
        "unit_diagonal_in_reset_zero_domain": report.get(
            "unit_diagonal_in_reset_zero_domain"
        ),
        "output_zero_exact_match": report.get(
            "output_zero_exact_match"
        ),
        "ready": bool(report.get("ready")),
    }


def validate_reset_cleanup(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])

    if not bool(report.get("reset_zero_cleanup_exact_match")):
        errors.append("reset-zero-cleanup-not-exact")
    if not bool(report.get("unit_diagonal_inside_cleanup")):
        errors.append("unit-diagonal-outside-cleanup")
    if not bool(report.get("output_zero_exact_match")):
        errors.append("output-zero-set-not-equivalent")

    scalar_count = int(report.get("scalar_count", 0))
    if int(report.get("reset_unit_diagonal_count", 0)) != scalar_count:
        errors.append(
            f"unit-diagonal-count:expected={scalar_count}:"
            f"actual={report.get('reset_unit_diagonal_count', 0)}"
        )

    return {
        "format": "SHIFT.SpecializedProviderResetCleanupEquivalenceValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
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
            "sequence": "cleanup zero coverage -> reset zero writes -> unit-diagonal seeds",
            "exact_match": "requires reset zero address set == cleanup-covered storage slots",
            "diagonal_seed": "each pivot's 1.0 address must already belong to the reset-zero set",
        },
        "limitations": [
            "This proves storage initialization order, not matrix semantics.",
            "The cleanup/reset equality is address-level and depends on the recovered provider layouts.",
            "No assertion is made that the zeroed storage set is a complete logical matrix.",
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
