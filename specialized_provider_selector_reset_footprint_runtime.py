"""Map provider scalar selectors to the exact reset storage footprint.

Phase 493 combines the canonical reset-domain parsing with the runtime active
scalar-group reconstruction. Each selector is mapped to its case-local zero
stores, bulk-clear slots and unit-diagonal seed.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from specialized_provider_reset_profile_runtime import (
    extract_reset_profile,
)
from specialized_provider_reset_domain_runtime import (
    extract_reset_domain,
)
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_active_scalar_group_runtime import (
    reconstruct_active_scalar_groups,
)

FORMAT = "SHIFT.SpecializedProviderSelectorResetFootprintRuntime/1"


def _case_footprint(row: Mapping[str, Any]) -> dict[str, Any]:
    zero_direct = {
        int(str(address), 16)
        for address in row.get("zero_assignments") or []
    }
    zero_bulk: set[int] = set()
    for clear in row.get("bulk_clears") or []:
        start = int(str(clear["base"]), 16)
        end = start + int(clear["bytes"])
        zero_bulk.update(range(start, end, 8))

    unit = (
        None
        if row.get("diagonal_address") is None
        else int(str(row["diagonal_address"]), 16)
    )
    zero = zero_direct | zero_bulk
    touched = zero | ({unit} if unit is not None else set())

    return {
        "selector": int(row["pivot_index"]),
        "direct_zero_addresses": [
            hex(address) for address in sorted(zero_direct)
        ],
        "bulk_zero_addresses": [
            hex(address) for address in sorted(zero_bulk)
        ],
        "zero_addresses": [
            hex(address) for address in sorted(zero)
        ],
        "unit_diagonal_address": (
            None if unit is None else hex(unit)
        ),
        "touched_addresses": [
            hex(address) for address in sorted(touched)
        ],
        "direct_zero_count": len(zero_direct),
        "bulk_zero_count": len(zero_bulk),
        "zero_count": len(zero),
        "touched_count": len(touched),
    }


def extract_selector_reset_footprint(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    profile = extract_reset_profile(
        source,
        provider_id=provider_id,
    )
    domain = extract_reset_domain(
        source,
        provider_id=provider_id,
    )

    errors = list(profile.get("errors") or [])
    errors.extend(domain.get("errors") or [])

    footprints = {
        int(row["pivot_index"]): _case_footprint(row)
        for row in profile.get("rows") or []
    }

    expected = list(range(layout.scalar_count))
    actual = sorted(footprints)
    if actual != expected:
        errors.append(
            f"selector-domain-mismatch:expected={expected[0]}..{expected[-1]}"
            f":actual={actual}"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "reset_function": profile.get("reset_function"),
        "reset_domain_zero_count": domain.get("reset_zero_slot_count"),
        "reset_domain_unit_count": domain.get(
            "unit_diagonal_slot_count"
        ),
        "selectors": [
            footprints[index]
            for index in expected
            if index in footprints
        ],
        "ready": not errors,
        "errors": errors,
    }


def expand_runtime_reset_footprint(
    source: str,
    runtime_events: Sequence[Mapping[str, Any]],
    *,
    provider_id: int,
) -> dict[str, Any]:
    static = extract_selector_reset_footprint(
        source,
        provider_id=provider_id,
    )
    provider_events: list[Mapping[str, Any]] = []
    for event in runtime_events:
        provider_event = event.get("provider_id")
        if provider_event is None:
            continue
        if int(provider_event) == int(provider_id):
            provider_events.append(event)

    active = reconstruct_active_scalar_groups(
        provider_events,
    )
    static_by_selector = {
        int(item["selector"]): item
        for item in static.get("selectors") or []
    }

    frame_reports: list[dict[str, Any]] = []
    errors = list(static.get("errors") or [])
    errors.extend(active.get("errors") or [])

    for frame in active.get("frames") or []:
        selectors = [
            int(item["base_selector"]) + offset
            for item in frame.get("active_records") or []
            for offset in range(int(item["width"]))
        ]
        footprints: list[dict[str, Any]] = []
        unknown_selectors: list[int] = []

        for selector in selectors:
            footprint = static_by_selector.get(selector)
            if footprint is None:
                unknown_selectors.append(selector)
                continue
            footprints.append({
                "selector": selector,
                "touched_addresses": list(
                    footprint["touched_addresses"]
                ),
                "touched_count": footprint["touched_count"],
            })

        if unknown_selectors:
            errors.append(
                f"frame-{frame['frame_index']}-unknown-selector:"
                + ",".join(
                    str(value)
                    for value in sorted(set(unknown_selectors))
                )
            )

        frame_reports.append({
            "frame_index": frame["frame_index"],
            "runtime_event_count": frame["event_count"],
            "runtime_selector_count": len(selectors),
            "selectors": selectors,
            "reset_footprints": footprints,
            "unknown_selector_count": len(unknown_selectors),
            "ready": not unknown_selectors and frame["ready"],
            "errors": list(frame.get("errors") or []),
        })

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": static["scalar_count"],
        "static_selector_footprint": static,
        "runtime_active_groups": active,
        "runtime_event_input_count": len(runtime_events),
        "runtime_event_provider_filtered_count": len(provider_events),
        "frames": frame_reports,
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
    }


def summarize_selector_reset_footprint(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    selectors = report.get("static_selector_footprint", {}).get(
        "selectors"
    ) or []

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "selector_count": len(selectors),
        "total_selector_touched_addresses": sum(
            int(item.get("touched_count", 0))
            for item in selectors
        ),
        "frame_count": len(report.get("frames") or []),
        "runtime_selector_count": sum(
            int(frame.get("runtime_selector_count", 0))
            for frame in report.get("frames") or []
        ),
        "unknown_runtime_selector_count": sum(
            int(frame.get("unknown_selector_count", 0))
            for frame in report.get("frames") or []
        ),
        "ready": bool(report.get("ready")),
    }


def build_selector_reset_footprint_contract(
    source: str,
    runtime_events: Sequence[Mapping[str, Any]],
    *,
    provider_id: int,
) -> dict[str, Any]:
    report = expand_runtime_reset_footprint(
        source,
        runtime_events,
        provider_id=provider_id,
    )
    report["summary"] = summarize_selector_reset_footprint(report)
    return report


__all__ = [
    "FORMAT",
    "extract_selector_reset_footprint",
    "expand_runtime_reset_footprint",
    "summarize_selector_reset_footprint",
    "build_selector_reset_footprint_contract",
]
