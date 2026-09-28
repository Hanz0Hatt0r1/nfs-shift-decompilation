"""Validate reset-event ordering metadata against provider solve captures.

Phase 489 uses the monotonic scalar-reset event counter written by the GDB probe
to establish that provider solve snapshots occur after the observed per-frame
FUN_007b2210 reset sequence. It does not infer any mathematical solver state.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from specialized_provider_capture_runtime import normalize_provider_capture
from specialized_provider_scalar_reset_capture_runtime import (
    normalize_scalar_reset_event,
    validate_scalar_reset_events,
)

FORMAT = "SHIFT.SpecializedProviderResetSolveOrderRuntime/1"


def _metadata(capture: Mapping[str, Any]) -> Mapping[str, Any]:
    value = capture.get("metadata")
    return value if isinstance(value, Mapping) else {}


def compare_provider_solve_order(
    provider_capture: Mapping[str, Any],
    reset_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    capture = normalize_provider_capture(provider_capture)
    events = [
        normalize_scalar_reset_event(event)
        for event in reset_events
    ]
    batch_validation = validate_scalar_reset_events(reset_events)

    frame_index = capture.get("frame_index")
    metadata = _metadata(capture)
    errors = list(batch_validation.get("errors") or [])

    if frame_index is None:
        errors.append("provider-frame-index-missing")
        frame = None
    else:
        frame = int(frame_index)

    total_count_raw = metadata.get("scalar_reset_event_count")
    frame_count_raw = metadata.get(
        "scalar_reset_events_since_frame_entry"
    )

    if total_count_raw is None:
        errors.append("scalar-reset-event-count-missing")
        total_count = None
    else:
        total_count = int(total_count_raw)

    if frame_count_raw is None:
        errors.append("scalar-reset-frame-count-missing")
        frame_count = None
    else:
        frame_count = int(frame_count_raw)

    prior_events = []
    same_frame_events = []
    if frame is not None:
        prior_events = [
            event
            for event in events
            if event.get("frame_index") is not None
            and int(event["frame_index"]) <= frame
        ]
        same_frame_events = [
            event
            for event in events
            if event.get("frame_index") is not None
            and int(event["frame_index"]) == frame
        ]

    max_prior_call_index = max(
        (
            int(event["call_index"])
            for event in prior_events
        ),
        default=0,
    )

    if total_count is not None and total_count != max_prior_call_index:
        errors.append(
            "provider-solve-reset-counter-mismatch:"
            f"metadata={total_count}:events={max_prior_call_index}"
        )

    if frame_count is not None and frame_count != len(same_frame_events):
        errors.append(
            "provider-solve-frame-reset-count-mismatch:"
            f"metadata={frame_count}:events={len(same_frame_events)}"
        )

    same_provider = [
        event
        for event in same_frame_events
        if (
            event.get("provider_id") is None
            or int(event["provider_id"]) == capture["provider_id"]
        )
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": not errors,
        "provider_id": capture["provider_id"],
        "frame_index": frame,
        "scalar_count": capture["scalar_count"],
        "reset_event_count_at_solve": total_count,
        "reset_events_same_frame": len(same_frame_events),
        "reset_events_same_provider_frame": len(same_provider),
        "max_prior_reset_call_index": max_prior_call_index,
        "provider_stage": capture["stage"],
        "errors": errors,
    }


def compare_provider_pre_post_order(
    pre_capture: Mapping[str, Any],
    post_capture: Mapping[str, Any],
    reset_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pre = compare_provider_solve_order(
        pre_capture,
        reset_events,
    )
    post = compare_provider_solve_order(
        post_capture,
        reset_events,
    )
    errors = list(pre["errors"]) + list(post["errors"])

    if pre["provider_id"] != post["provider_id"]:
        errors.append("provider-id-mismatch")
    if pre["frame_index"] != post["frame_index"]:
        errors.append("frame-index-mismatch")
    if (
        pre["reset_event_count_at_solve"] is not None
        and post["reset_event_count_at_solve"] is not None
        and pre["reset_event_count_at_solve"]
        != post["reset_event_count_at_solve"]
    ):
        errors.append("reset-counter-changed-after-solve")

    return {
        "format": "SHIFT.SpecializedProviderResetSolveOrderComparison/1",
        "version": 1,
        "ready": not errors,
        "provider_id": pre["provider_id"],
        "frame_index": pre["frame_index"],
        "pre": pre,
        "post": post,
        "errors": list(dict.fromkeys(errors)),
    }


def summarize_provider_solve_order(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "provider_id": report.get("provider_id"),
        "frame_index": report.get("frame_index"),
        "reset_event_count_at_solve": report.get(
            "reset_event_count_at_solve"
        ),
        "reset_events_same_frame": report.get(
            "reset_events_same_frame"
        ),
        "reset_events_same_provider_frame": report.get(
            "reset_events_same_provider_frame"
        ),
        "provider_stage": report.get("provider_stage"),
        "ready": bool(report.get("ready")),
    }


def build_reset_solve_order_contract(
    provider_capture: Mapping[str, Any],
    reset_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    report = compare_provider_solve_order(
        provider_capture,
        reset_events,
    )
    report["summary"] = summarize_provider_solve_order(report)
    return report


__all__ = [
    "FORMAT",
    "compare_provider_solve_order",
    "compare_provider_pre_post_order",
    "summarize_provider_solve_order",
    "build_reset_solve_order_contract",
]
