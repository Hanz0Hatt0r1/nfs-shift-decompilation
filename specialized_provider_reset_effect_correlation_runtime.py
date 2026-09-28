"""Correlate scalar-reset dispatch events with measured provider reset effects.

Phase 501 joins Phase 485/487 selector events with Phase 494 provider reset
sentinel captures using the monotonic reset_event_count. A correlation is valid
only when provider identity, frame and selector agree.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from specialized_provider_scalar_reset_capture_runtime import (
    normalize_scalar_reset_event,
    validate_scalar_reset_events,
)
from specialized_provider_scalar_reset_effect_runtime import (
    validate_reset_effect_batch,
    validate_reset_effect_event,
)

FORMAT = "SHIFT.SpecializedProviderResetEffectCorrelationRuntime/1"


def correlate_reset_effect_event(
    reset_event: Mapping[str, Any],
    effect_event: Mapping[str, Any],
) -> dict[str, Any]:
    reset = normalize_scalar_reset_event(reset_event)
    effect_validation = validate_reset_effect_event(effect_event)

    errors = list(effect_validation["errors"])

    reset_count = int(reset.get("call_index", -1))
    effect_count = int(effect_event.get("reset_event_count", -1))
    if reset_count != effect_count:
        errors.append(
            f"reset-event-count-mismatch:{reset_count}:{effect_count}"
        )

    if reset.get("provider_id") != effect_event.get("provider_id"):
        errors.append("provider-id-mismatch")

    reset_frame = reset.get("frame_index")
    effect_frame = effect_event.get("frame_index")
    if reset_frame != effect_frame:
        errors.append("frame-index-mismatch")

    if int(reset["selector"]) != int(effect_event.get("selector", -1)):
        errors.append("selector-mismatch")

    if reset.get("provider_vtable") is not None:
        if int(reset["provider_vtable"]) != int(
            effect_event.get("provider_vtable", -1)
        ):
            errors.append("provider-vtable-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderResetEffectCorrelation/1",
        "version": 1,
        "ready": not errors,
        "status": "correlated" if not errors else "blocked",
        "reset_event": {
            "call_index": reset_count,
            "frame_index": reset_frame,
            "provider_id": reset.get("provider_id"),
            "selector": int(reset["selector"]),
            "caller_return_address": reset.get(
                "caller_return_address"
            ),
        },
        "effect_event": {
            "reset_event_count": effect_count,
            "frame_index": effect_frame,
            "provider_id": effect_event.get("provider_id"),
            "selector": int(effect_event.get("selector", -1)),
            "addresses": dict(effect_event.get("addresses") or {}),
            "values": dict(effect_event.get("values") or {}),
        },
        "errors": errors,
    }


def correlate_reset_effect_stream(
    reset_events: Sequence[Mapping[str, Any]],
    effect_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    reset_validation = validate_scalar_reset_events(reset_events)
    effect_validation = validate_reset_effect_batch(effect_events)

    errors.extend(
        f"reset:{error}"
        for error in reset_validation.get("errors") or []
    )
    errors.extend(
        f"effect:{error}"
        for error in effect_validation.get("errors") or []
    )

    reset_by_count = {
        int(event["call_index"]): event
        for event in reset_events
    }
    effect_by_count = {
        int(event.get("reset_event_count", -1)): event
        for event in effect_events
    }

    correlations: list[dict[str, Any]] = []
    for count in sorted(
        set(reset_by_count) | set(effect_by_count)
    ):
        reset_event = reset_by_count.get(count)
        effect_event = effect_by_count.get(count)

        if reset_event is None:
            errors.append(f"missing-reset-event:{count}")
            continue
        if effect_event is None:
            errors.append(f"missing-reset-effect:{count}")
            continue

        correlation = correlate_reset_effect_event(
            reset_event,
            effect_event,
        )
        correlations.append(correlation)
        errors.extend(
            f"event-{count}:{error}"
            for error in correlation.get("errors") or []
        )

    return {
        "format": FORMAT,
        "version": 1,
        "ready": not errors,
        "status": "correlated" if not errors else "blocked",
        "reset_event_count": len(reset_events),
        "effect_event_count": len(effect_events),
        "correlated_count": len(correlations),
        "correlations": correlations,
        "reset_validation": reset_validation,
        "effect_validation": effect_validation,
        "errors": list(dict.fromkeys(errors)),
    }


def summarize_reset_effect_correlation(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    providers: dict[str, int] = {}
    frames: dict[str, int] = {}

    for correlation in report.get("correlations") or []:
        if correlation.get("status") != "correlated":
            continue

        provider = str(
            correlation["reset_event"].get("provider_id")
        )
        frame = correlation["reset_event"].get("frame_index")
        providers[provider] = providers.get(provider, 0) + 1
        if frame is not None:
            frame_key = str(frame)
            frames[frame_key] = frames.get(frame_key, 0) + 1

    return {
        "format": "SHIFT.SpecializedProviderResetEffectCorrelationSummary/1",
        "version": 1,
        "reset_event_count": int(report.get("reset_event_count", 0)),
        "effect_event_count": int(report.get("effect_event_count", 0)),
        "correlated_count": int(report.get("correlated_count", 0)),
        "provider_correlated_counts": dict(sorted(providers.items())),
        "frame_correlated_counts": dict(
            sorted(frames.items(), key=lambda item: int(item[0]))
        ),
        "unmatched_count": (
            int(report.get("reset_event_count", 0))
            + int(report.get("effect_event_count", 0))
            - 2 * int(report.get("correlated_count", 0))
        ),
        "ready": bool(report.get("ready")),
    }


def build_reset_effect_correlation_contract(
    reset_events: Sequence[Mapping[str, Any]],
    effect_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    report = correlate_reset_effect_stream(
        reset_events,
        effect_events,
    )
    report["summary"] = summarize_reset_effect_correlation(report)
    return report


__all__ = [
    "FORMAT",
    "correlate_reset_effect_event",
    "correlate_reset_effect_stream",
    "summarize_reset_effect_correlation",
    "build_reset_effect_correlation_contract",
]
