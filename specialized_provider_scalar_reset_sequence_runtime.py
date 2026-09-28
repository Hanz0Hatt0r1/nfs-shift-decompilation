"""Validate runtime FUN_007b2210 event ordering against exact source callsite shape.

Phase 488 uses the Phase 486 callsite table to check each frame's observed event
stream. Within each source group, an active constraint record must contribute
ordinals 0..width-1, and the three source groups must appear in JOINT/HINGE →
SECONDARY → BAR order.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from specialized_provider_scalar_reset_callsite_runtime import (
    get_callsite_by_return_address,
)
from specialized_provider_scalar_reset_capture_runtime import (
    normalize_scalar_reset_event,
    validate_scalar_reset_event,
)

FORMAT = "SHIFT.SpecializedProviderScalarResetEventSequenceRuntime/1"

GROUP_ORDER = {
    "JOINT/HINGE": 0,
    "SECONDARY": 1,
    "BAR": 2,
}


def _attribution(event: Mapping[str, Any]) -> dict[str, Any]:
    callsite = event.get("callsite")
    if isinstance(callsite, Mapping) and callsite.get("status") == "attributed":
        return dict(callsite)

    return get_callsite_by_return_address(
        int(event["caller_return_address"])
    ) or {}


def validate_group_event_sequence(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    attributed: list[dict[str, Any]] = []

    for index, raw in enumerate(events):
        schema = validate_scalar_reset_event(raw)
        if not schema["ready"]:
            errors.extend(
                f"event-{index}:{error}"
                for error in schema["errors"]
            )

        try:
            event = normalize_scalar_reset_event(raw)
        except (TypeError, ValueError) as exc:
            errors.append(f"event-{index}:normalize:{exc}")
            continue

        callsite = _attribution(raw)
        if not callsite:
            errors.append(f"event-{index}:missing-callsite-attribution")
            continue
        if callsite.get("status") == "unattributed":
            errors.append(
                f"event-{index}:{callsite.get('reason','unattributed')}"
            )
            continue

        group = str(callsite.get("group"))
        ordinal = int(callsite.get("ordinal", -1))
        width = int(callsite.get("group_width", -1))
        selector = int(event["selector"])

        if group not in GROUP_ORDER:
            errors.append(f"event-{index}:unknown-group:{group}")
            continue
        if not 0 <= ordinal < width:
            errors.append(f"event-{index}:ordinal-out-of-range")

        attributed.append(
            {
                "index": index,
                "frame_index": event.get("frame_index"),
                "group": group,
                "group_rank": GROUP_ORDER[group],
                "ordinal": ordinal,
                "width": width,
                "selector": selector,
                "callsite_return_address": int(
                    callsite["return_address"], 16
                )
                if isinstance(callsite.get("return_address"), str)
                else int(event["caller_return_address"]),
            }
        )

    grouped: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    for item in attributed:
        grouped[item["frame_index"]].append(item)

    frame_reports: list[dict[str, Any]] = []
    for frame, frame_events in sorted(
        grouped.items(),
        key=lambda item: (-1 if item[0] is None else int(item[0])),
    ):
        frame_errors: list[str] = []
        last_group_rank = -1
        current_group: str | None = None
        expected_ordinal = 0
        current_width = 0

        for item in frame_events:
            group = item["group"]
            rank = item["group_rank"]
            ordinal = item["ordinal"]
            width = item["width"]

            if rank < last_group_rank:
                frame_errors.append("group-order-regression")

            if group != current_group:
                current_group = group
                current_width = width
                expected_ordinal = 0

            if ordinal != expected_ordinal:
                frame_errors.append(
                    f"group-{group}-ordinal-sequence:"
                    f"expected={expected_ordinal}:observed={ordinal}"
                )

            if expected_ordinal < current_width - 1:
                expected_ordinal += 1
            else:
                expected_ordinal = 0

            last_group_rank = rank

        frame_reports.append(
            {
                "frame_index": frame,
                "event_count": len(frame_events),
                "ready": not frame_errors,
                "errors": frame_errors,
                "groups": [
                    {
                        "group": group,
                        "event_count": sum(
                            item["group"] == group
                            for item in frame_events
                        ),
                        "ordinals": [
                            item["ordinal"]
                            for item in frame_events
                            if item["group"] == group
                        ],
                    }
                    for group in GROUP_ORDER
                    if any(
                        item["group"] == group
                        for item in frame_events
                    )
                ],
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "ready": not errors and all(
            report["ready"] for report in frame_reports
        ),
        "event_count": len(events),
        "attributed_count": len(attributed),
        "frame_count": len(frame_reports),
        "frames": frame_reports,
        "errors": errors,
    }


def summarize_group_event_sequence(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    frame_reports = list(report.get("frames") or [])
    group_counts = {
        group: sum(
            int(frame.get("event_count", 0))
            for frame in frame_reports
            if any(
                item.get("group") == group
                for item in frame.get("groups") or []
            )
        )
        for group in GROUP_ORDER
    }

    return {
        "format": "SHIFT.SpecializedProviderScalarResetEventSequenceSummary/1",
        "version": 1,
        "event_count": int(report.get("event_count", 0)),
        "attributed_count": int(report.get("attributed_count", 0)),
        "frame_count": len(frame_reports),
        "group_frame_presence": {
            group: sum(
                any(
                    item.get("group") == group
                    for item in frame.get("groups") or []
                )
                for frame in frame_reports
            )
            for group in GROUP_ORDER
        },
        "frame_errors": sum(
            len(frame.get("errors") or [])
            for frame in frame_reports
        ),
        "ready": bool(report.get("ready")),
    }


def build_event_sequence_contract(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    report = validate_group_event_sequence(events)
    report["summary"] = summarize_group_event_sequence(report)
    return report


__all__ = [
    "FORMAT",
    "GROUP_ORDER",
    "validate_group_event_sequence",
    "summarize_group_event_sequence",
    "build_event_sequence_contract",
]
