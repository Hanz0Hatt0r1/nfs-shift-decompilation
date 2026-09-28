"""Reconstruct active scalar selector groups from runtime reset events.

Phase 492 consumes exact Phase 486 callsite attribution and reconstructs the
selector base for each active constraint record:
    selector, selector+1, ... selector+(width-1)

This is a runtime indexing reconstruction only. It does not assign physical
meaning to the resulting scalar ids.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from specialized_provider_scalar_reset_callsite_runtime import (
    get_callsite_by_return_address,
)
from specialized_provider_scalar_reset_capture_runtime import (
    normalize_scalar_reset_event,
    validate_scalar_reset_events,
)
from specialized_provider_scalar_reset_sequence_runtime import (
    GROUP_ORDER,
)

FORMAT = "SHIFT.SpecializedProviderActiveScalarGroupRuntime/1"


def _callsite(event: Mapping[str, Any]) -> dict[str, Any]:
    inline = event.get("callsite")
    if isinstance(inline, Mapping) and inline.get("status") == "attributed":
        return dict(inline)

    return get_callsite_by_return_address(
        int(event["caller_return_address"])
    ) or {}


def reconstruct_frame_groups(
    events: Sequence[Mapping[str, Any]],
    *,
    frame_index: int,
) -> dict[str, Any]:
    frame_events = [
        event
        for event in events
        if event.get("frame_index") is not None
        and int(event["frame_index"]) == int(frame_index)
    ]

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors: list[str] = []
    active_records: list[dict[str, Any]] = []

    current_group: str | None = None
    current_width = 0
    current_selectors: list[int] = []

    def flush_record() -> None:
        nonlocal current_selectors
        if current_group is None or not current_selectors:
            current_selectors = []
            return

        group = current_group
        width = current_width
        if len(current_selectors) != width:
            errors.append(
                f"{group}-record-width-mismatch:"
                f"expected={width}:actual={len(current_selectors)}"
            )
        base_selector = current_selectors[0]
        expected = [
            base_selector + offset
            for offset in range(len(current_selectors))
        ]
        if current_selectors != expected:
            errors.append(
                f"{group}-selector-contiguity:"
                f"observed={current_selectors}:expected={expected}"
            )

        active_records.append(
            {
                "group": group,
                "width": width,
                "base_selector": base_selector,
                "selectors": list(current_selectors),
            }
        )
        groups[group].append(active_records[-1])
        current_selectors = []

    for raw_event in frame_events:
        callsite = _callsite(raw_event)
        if not callsite:
            errors.append("missing-callsite-attribution")
            continue

        group = str(callsite.get("group"))
        ordinal = int(callsite.get("ordinal", -1))
        width = int(callsite.get("group_width", -1))
        selector = int(
            normalize_scalar_reset_event(raw_event)["selector"]
        )

        if group not in GROUP_ORDER:
            errors.append(f"unknown-group:{group}")
            continue

        if group != current_group:
            flush_record()
            current_group = group
            current_width = width

        if ordinal == 0 and current_selectors:
            flush_record()

        current_selectors.append(selector)

        if ordinal != len(current_selectors) - 1:
            errors.append(
                f"{group}-ordinal-mismatch:"
                f"expected={len(current_selectors)-1}:observed={ordinal}"
            )

        if len(current_selectors) == width:
            flush_record()

    flush_record()

    return {
        "frame_index": int(frame_index),
        "event_count": len(frame_events),
        "active_record_count": len(active_records),
        "groups": {
            group: list(groups.get(group, []))
            for group in GROUP_ORDER
            if groups.get(group)
        },
        "active_records": active_records,
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
    }


def reconstruct_active_scalar_groups(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    batch = validate_scalar_reset_events(events)
    errors = list(batch.get("errors") or [])

    frames = sorted({
        int(event["frame_index"])
        for event in events
        if event.get("frame_index") is not None
    })

    reports = [
        reconstruct_frame_groups(
            events,
            frame_index=frame,
        )
        for frame in frames
    ]

    errors.extend(
        f"frame-{report['frame_index']}:{error}"
        for report in reports
        for error in report["errors"]
    )

    return {
        "format": FORMAT,
        "version": 1,
        "event_count": len(events),
        "frame_count": len(reports),
        "frames": reports,
        "event_validation": batch,
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
    }


def summarize_active_scalar_groups(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    group_counts = {
        group: 0
        for group in GROUP_ORDER
    }
    active_record_counts = {
        group: 0
        for group in GROUP_ORDER
    }

    for frame in report.get("frames") or []:
        for group, records in (frame.get("groups") or {}).items():
            group_counts[group] = group_counts.get(group, 0) + sum(
                len(record.get("selectors") or [])
                for record in records
            )
            active_record_counts[group] = (
                active_record_counts.get(group, 0)
                + len(records)
            )

    return {
        "format": "SHIFT.SpecializedProviderActiveScalarGroupSummary/1",
        "version": 1,
        "event_count": int(report.get("event_count", 0)),
        "frame_count": int(report.get("frame_count", 0)),
        "scalar_events_by_group": group_counts,
        "active_records_by_group": active_record_counts,
        "ready": bool(report.get("ready")),
    }


def build_active_scalar_group_contract(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    report = reconstruct_active_scalar_groups(events)
    report["summary"] = summarize_active_scalar_groups(report)
    return report


__all__ = [
    "FORMAT",
    "GROUP_ORDER",
    "reconstruct_frame_groups",
    "reconstruct_active_scalar_groups",
    "summarize_active_scalar_groups",
    "build_active_scalar_group_contract",
]
