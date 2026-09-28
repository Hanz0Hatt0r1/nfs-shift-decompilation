"""Normalize and validate live FUN_007b2210 scalar-reset events.

Phase 485 defines the capture contract used by the GDB probe. It deliberately
records selector provenance at runtime without claiming which constraint group
produced an event; group attribution can be added later from call-stack/source
context.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SpecializedProviderScalarResetCaptureRuntime/1"


def normalize_scalar_reset_event(
    event: Mapping[str, Any],
) -> dict[str, Any]:
    scalar_count = int(event.get("scalar_count", -1))
    selector = int(event.get("selector", -1))
    provider = int(event.get("provider", 0))
    physics_system = int(event.get("physics_system", 0))
    call_index = int(event.get("call_index", -1))

    return {
        "format": FORMAT,
        "version": 1,
        "status": "normalized",
        "ready": True,
        "frame_index": event.get("frame_index"),
        "call_index": call_index,
        "physics_system": physics_system,
        "provider": provider,
        "backend": "provider" if provider != 0 else "builtin",
        "scalar_count": scalar_count,
        "selector": selector,
        "source_function": "FUN_007b2210",
        "source_address": hex(int(event.get("source_address", 0x007B2210))),
        "provider_reset_vtable_offset": "0x1c" if provider != 0 else None,
        "registers": dict(event.get("registers") or {}),
    }


def validate_scalar_reset_event(
    event: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = normalize_scalar_reset_event(event)
    errors: list[str] = []

    n = int(normalized["scalar_count"])
    selector = int(normalized["selector"])
    provider = int(normalized["provider"])

    if n <= 0:
        errors.append("non-positive-scalar-count")
    elif not 0 <= selector < n:
        errors.append(
            f"selector-out-of-domain:selector={selector}:count={n}"
        )

    if provider not in (0, 1):
        errors.append(f"unsupported-provider-pointer:{provider}")

    if int(normalized["call_index"]) < 0:
        errors.append("negative-call-index")

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCaptureValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
        "frame_index": normalized["frame_index"],
        "call_index": normalized["call_index"],
        "provider": provider,
        "selector": selector,
        "scalar_count": n,
    }


def normalize_scalar_reset_events(
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [normalize_scalar_reset_event(event) for event in events]


def summarize_scalar_reset_events(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = normalize_scalar_reset_events(events)
    providers = Counter(
        "provider" if int(event["provider"]) != 0 else "builtin"
        for event in normalized
    )
    frames = sorted({
        int(event["frame_index"])
        for event in normalized
        if event.get("frame_index") is not None
    })

    per_frame = Counter(
        int(event["frame_index"])
        for event in normalized
        if event.get("frame_index") is not None
    )

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCaptureSummary/1",
        "version": 1,
        "event_count": len(normalized),
        "provider_event_count": int(providers.get("provider", 0)),
        "builtin_event_count": int(providers.get("builtin", 0)),
        "frame_count": len(frames),
        "frames": frames,
        "events_per_frame": {
            str(frame): count
            for frame, count in sorted(per_frame.items())
        },
        "selector_min": min(
            (int(event["selector"]) for event in normalized),
            default=None,
        ),
        "selector_max": max(
            (int(event["selector"]) for event in normalized),
            default=None,
        ),
    }


def validate_scalar_reset_events(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    for index, event in enumerate(events):
        result = validate_scalar_reset_event(event)
        if not result["ready"]:
            errors.extend(
                f"event-{index}:{error}"
                for error in result["errors"]
            )

    call_indices = [
        int(normalize_scalar_reset_event(event)["call_index"])
        for event in events
    ]
    if call_indices != sorted(call_indices):
        errors.append("call-index-order-mismatch")
    if len(call_indices) != len(set(call_indices)):
        errors.append("duplicate-call-index")

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCaptureBatchValidation/1",
        "version": 1,
        "ready": not errors,
        "event_count": len(events),
        "errors": errors,
    }


def build_scalar_reset_capture_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "event": {
            "required": [
                "call_index",
                "scalar_count",
                "selector",
                "provider",
                "physics_system",
            ],
            "optional": [
                "frame_index",
                "registers",
            ],
            "source": "FUN_007b2210",
        },
        "backend": {
            "provider": "provider pointer nonzero; selector delegates to vtable +0x1c",
            "builtin": "provider pointer zero; selector resets logical row/column/RHS locally",
        },
        "validation": [
            "selector in [0, scalar_count)",
            "provider pointer is 0 or 1",
            "nonnegative ordered call_index",
        ],
        "scope": {
            "group_attribution": "not encoded",
            "matrix_semantics": "not inferred",
            "runtime_timing": "represented only by ordered event/frame fields",
        },
        "status": "source-backed-specialized-provider-scalar-reset-capture",
    }


__all__ = [
    "FORMAT",
    "normalize_scalar_reset_event",
    "validate_scalar_reset_event",
    "normalize_scalar_reset_events",
    "summarize_scalar_reset_events",
    "validate_scalar_reset_events",
    "build_scalar_reset_capture_contract",
]
