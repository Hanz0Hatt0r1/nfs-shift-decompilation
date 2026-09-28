"""Exact machine-callsite attribution for FUN_007b2210 reset events.

Phase 486 maps the caller return address saved by the Phase 485 GDB probe to
the three source-level constraint groups and their selector ordinal within the
3/2/1 call widths.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.SpecializedProviderScalarResetCallsiteRuntime/1"

CALLS = (
    {
        "return_address": 0x007B4029,
        "call_address": 0x007B4024,
        "group": "JOINT/HINGE",
        "group_width": 3,
        "ordinal": 0,
        "source_line": 814124,
        "selector_delta": 0,
    },
    {
        "return_address": 0x007B4034,
        "call_address": 0x007B402F,
        "group": "JOINT/HINGE",
        "group_width": 3,
        "ordinal": 1,
        "source_line": 814124,
        "selector_delta": 1,
    },
    {
        "return_address": 0x007B403F,
        "call_address": 0x007B403A,
        "group": "JOINT/HINGE",
        "group_width": 3,
        "ordinal": 2,
        "source_line": 814124,
        "selector_delta": 2,
    },
    {
        "return_address": 0x007B407E,
        "call_address": 0x007B4079,
        "group": "SECONDARY",
        "group_width": 2,
        "ordinal": 0,
        "source_line": 814138,
        "selector_delta": 0,
    },
    {
        "return_address": 0x007B4089,
        "call_address": 0x007B4084,
        "group": "SECONDARY",
        "group_width": 2,
        "ordinal": 1,
        "source_line": 814138,
        "selector_delta": 1,
    },
    {
        "return_address": 0x007B40CB,
        "call_address": 0x007B40C6,
        "group": "BAR",
        "group_width": 1,
        "ordinal": 0,
        "source_line": 814150,
        "selector_delta": 0,
    },
)

BY_RETURN_ADDRESS = {
    int(entry["return_address"]): entry
    for entry in CALLS
}


def get_callsite_by_return_address(
    return_address: int,
) -> dict[str, Any] | None:
    entry = BY_RETURN_ADDRESS.get(int(return_address))
    return None if entry is None else dict(entry)


def attribute_reset_event(
    event: Mapping[str, Any],
) -> dict[str, Any]:
    return_address = event.get("caller_return_address")
    if return_address is None:
        return {
            "ready": False,
            "status": "unattributed",
            "reason": "caller-return-address-missing",
            "event": dict(event),
        }

    callsite = get_callsite_by_return_address(int(return_address))
    if callsite is None:
        return {
            "ready": False,
            "status": "unattributed",
            "reason": "unknown-caller-return-address",
            "return_address": hex(int(return_address)),
            "event": dict(event),
        }

    selector = int(event.get("selector", -1))
    delta = int(callsite["selector_delta"])
    expected_group_width = int(callsite["group_width"])
    local_ordinal = int(callsite["ordinal"])

    errors: list[str] = []
    if selector < 0:
        errors.append("negative-selector")
    if local_ordinal < 0 or local_ordinal >= expected_group_width:
        errors.append("ordinal-out-of-group")
    if local_ordinal != delta:
        errors.append("selector-delta-metadata-mismatch")

    return {
        "ready": not errors,
        "status": "attributed" if not errors else "blocked",
        "return_address": hex(int(return_address)),
        "call_address": hex(int(callsite["call_address"])),
        "group": callsite["group"],
        "group_width": expected_group_width,
        "ordinal": local_ordinal,
        "source_line": int(callsite["source_line"]),
        "selector": selector,
        "selector_delta": delta,
        "errors": errors,
    }


def attribute_reset_events(
    events: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        attribute_reset_event(event)
        for event in events
    ]


def summarize_reset_callsite_attribution(
    attributed: list[Mapping[str, Any]],
) -> dict[str, Any]:
    group_counts = {group: 0 for group in ("JOINT/HINGE", "SECONDARY", "BAR")}
    unattributed = 0
    for item in attributed:
        if item.get("status") != "attributed":
            unattributed += 1
            continue
        group = str(item["group"])
        group_counts[group] = group_counts.get(group, 0) + 1

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCallsiteSummary/1",
        "version": 1,
        "event_count": len(attributed),
        "attributed_count": len(attributed) - unattributed,
        "unattributed_count": unattributed,
        "group_counts": group_counts,
        "known_return_addresses": [
            hex(int(address))
            for address in sorted(BY_RETURN_ADDRESS)
        ],
    }


def validate_reset_callsite_table() -> dict[str, Any]:
    errors: list[str] = []

    if len(CALLS) != 6:
        errors.append("unexpected-callsite-count")

    expected = [
        ("JOINT/HINGE", 0, 0x007B4029),
        ("JOINT/HINGE", 1, 0x007B4034),
        ("JOINT/HINGE", 2, 0x007B403F),
        ("SECONDARY", 0, 0x007B407E),
        ("SECONDARY", 1, 0x007B4089),
        ("BAR", 0, 0x007B40CB),
    ]
    actual = [
        (
            str(entry["group"]),
            int(entry["ordinal"]),
            int(entry["return_address"]),
        )
        for entry in CALLS
    ]
    if actual != expected:
        errors.append("callsite-table-mismatch")

    if len(BY_RETURN_ADDRESS) != len(CALLS):
        errors.append("duplicate-return-address")

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCallsiteValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
    }


def build_callsite_attribution_contract() -> dict[str, Any]:
    validation = validate_reset_callsite_table()
    return {
        "format": FORMAT,
        "version": 1,
        "dispatcher": "FUN_007b2210",
        "calls": [dict(entry) for entry in CALLS],
        "validation": validation,
        "basis": {
            "return_address": "stack [ESP] at FUN_007b2210 entry",
            "call_address": "5 bytes before corresponding return address for these direct CALL rel32 sites",
            "group_source_lines": {
                "JOINT/HINGE": 814124,
                "SECONDARY": 814138,
                "BAR": 814150,
            },
        },
        "limitations": [
            "Attribution depends on the exact retail image addresses and assumes the unmodified PE callsite layout.",
            "Selector value is preserved independently; callsite attribution does not reinterpret its semantic meaning.",
            "No physical constraint or matrix meaning is inferred.",
        ],
        "status": "source-backed-runtime-reset-callsite-attribution",
    }


__all__ = [
    "FORMAT",
    "CALLS",
    "BY_RETURN_ADDRESS",
    "get_callsite_by_return_address",
    "attribute_reset_event",
    "attribute_reset_events",
    "summarize_reset_callsite_attribution",
    "validate_reset_callsite_table",
    "build_callsite_attribution_contract",
]
