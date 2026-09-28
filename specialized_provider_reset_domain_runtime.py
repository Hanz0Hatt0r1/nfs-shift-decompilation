"""Unified reset storage domain for specialized provider state.

Phase 480 centralizes reset-domain construction so later analyses cannot
accidentally omit bulk-clear intervals or confuse unit-diagonal seeds with zero
initialization.
"""
from __future__ import annotations

from typing import Any, Mapping

from specialized_provider_reset_profile_runtime import extract_reset_profile
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderResetDomainRuntime/1"


def _slots_from_bulk_clears(
    rows: list[Mapping[str, Any]],
    *,
    start: int,
    end: int,
) -> set[int]:
    slots: set[int] = set()
    for row in rows:
        for clear in row.get("bulk_clears") or []:
            clear_start = int(str(clear["base"]), 16)
            clear_end = clear_start + int(clear["bytes"])
            clipped_start = max(start, clear_start)
            clipped_end = min(end, clear_end)
            if clipped_start < clipped_end:
                slots.update(range(clipped_start, clipped_end, 8))
    return slots


def build_reset_domain(
    reset_report: Mapping[str, Any],
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    start = layout.factor_workspace_base
    end = layout.output_vector_base + layout.output_vector_bytes
    rows = list(reset_report.get("rows") or [])

    direct_zero = {
        int(str(address), 16)
        for row in rows
        for address in row.get("zero_assignments") or []
        if start <= int(str(address), 16) < end
    }
    bulk_zero = _slots_from_bulk_clears(
        rows,
        start=start,
        end=end,
    )
    zero_addresses = direct_zero | bulk_zero
    unit_addresses = {
        int(str(row["diagonal_address"]), 16)
        for row in rows
        if row.get("diagonal_address") is not None
        and start
        <= int(str(row["diagonal_address"]), 16)
        < end
    }
    touched_addresses = zero_addresses | unit_addresses

    workspace_start = layout.factor_workspace_base
    workspace_end = layout.output_vector_base
    output_start = layout.output_vector_base
    output_end = output_start + layout.output_vector_bytes

    def count_in(start_address: int, end_address: int, values: set[int]) -> int:
        return sum(
            start_address <= address < end_address
            for address in values
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "reset_function": reset_report.get("reset_function"),
        "direct_zero_slot_count": len(direct_zero),
        "bulk_zero_slot_count": len(bulk_zero),
        "reset_zero_slot_count": len(zero_addresses),
        "unit_diagonal_slot_count": len(unit_addresses),
        "reset_touched_slot_count": len(touched_addresses),
        "workspace_zero_slot_count": count_in(
            workspace_start,
            workspace_end,
            zero_addresses,
        ),
        "workspace_unit_slot_count": count_in(
            workspace_start,
            workspace_end,
            unit_addresses,
        ),
        "output_zero_slot_count": count_in(
            output_start,
            output_end,
            zero_addresses,
        ),
        "output_unit_slot_count": count_in(
            output_start,
            output_end,
            unit_addresses,
        ),
        "zero_addresses": [hex(address) for address in sorted(zero_addresses)],
        "unit_diagonal_addresses": [
            hex(address)
            for address in sorted(unit_addresses)
        ],
        "touched_addresses": [
            hex(address)
            for address in sorted(touched_addresses)
        ],
        "ready": bool(reset_report.get("ready")),
        "errors": list(reset_report.get("errors") or []),
    }


def extract_reset_domain(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    report = extract_reset_profile(
        source,
        provider_id=provider_id,
    )
    return build_reset_domain(
        report,
        provider_id=provider_id,
    )


def validate_reset_domain(report: Mapping[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    provider_id = int(report.get("provider_id", -1))
    layout = get_storage_layout(provider_id)
    scalar_count = int(report.get("scalar_count", 0))

    zero = {
        int(str(address), 16)
        for address in report.get("zero_addresses") or []
    }
    unit = {
        int(str(address), 16)
        for address in report.get("unit_diagonal_addresses") or []
    }
    touched = {
        int(str(address), 16)
        for address in report.get("touched_addresses") or []
    }

    if not unit <= touched:
        errors.append("unit-domain-not-subset-touched")
    if not zero <= touched:
        errors.append("zero-domain-not-subset-touched")

    expected_start = layout.factor_workspace_base
    expected_end = layout.output_vector_base + layout.output_vector_bytes
    if any(
        not (expected_start <= address < expected_end)
        for address in touched
    ):
        errors.append("reset-touched-address-outside-provider-storage")

    if len(unit) != scalar_count:
        errors.append(
            f"unit-diagonal-count:expected={scalar_count}:actual={len(unit)}"
        )

    if int(report.get("reset_touched_slot_count", 0)) != len(touched):
        errors.append("reset-touched-count-mismatch")

    if int(report.get("reset_zero_slot_count", 0)) != len(zero):
        errors.append("reset-zero-count-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderResetDomainValidation/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": errors,
    }


def summarize_reset_domain(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "direct_zero_slot_count": report.get("direct_zero_slot_count"),
        "bulk_zero_slot_count": report.get("bulk_zero_slot_count"),
        "reset_zero_slot_count": report.get("reset_zero_slot_count"),
        "unit_diagonal_slot_count": report.get("unit_diagonal_slot_count"),
        "reset_touched_slot_count": report.get("reset_touched_slot_count"),
        "workspace_zero_slot_count": report.get("workspace_zero_slot_count"),
        "output_zero_slot_count": report.get("output_zero_slot_count"),
        "ready": bool(report.get("ready")),
    }


def build_reset_domain_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_reset_domain(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_reset_domain(report)
        report["validation"] = validate_reset_domain(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "semantics": {
            "reset_zero": "direct zero assignments plus slots covered by reset bulk clears",
            "unit_diagonal": "one exact 1.0 seed per selector case",
            "touched": "union of reset-zero and unit-diagonal slots",
        },
        "limitations": [
            "The reset domain is storage-level evidence and does not imply matrix coordinates.",
            "Cleanup equality is intentionally not folded into domain validity; provider 1 has a documented cleanup-only subset.",
        ],
        "status": "source-backed-unified-reset-domain",
    }


__all__ = [
    "FORMAT",
    "build_reset_domain",
    "extract_reset_domain",
    "validate_reset_domain",
    "summarize_reset_domain",
    "build_reset_domain_contract",
]
