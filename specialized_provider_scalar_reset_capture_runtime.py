"""Normalize and validate live FUN_007b2210 scalar-reset events.

Phase 485 records the scalar selector together with the raw provider pointer and
its first vtable word. Provider identity is derived only from an exact vtable
match, while the raw pointer is always preserved for later provenance work.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SpecializedProviderScalarResetCaptureRuntime/2"


def normalize_scalar_reset_event(
    event: Mapping[str, Any],
) -> dict[str, Any]:
    scalar_count = int(event.get("scalar_count", -1))
    selector = int(event.get("selector", -1))
    provider_id_raw = event.get("provider_id")
    provider_id = (
        None if provider_id_raw is None else int(provider_id_raw)
    )
    provider_pointer = int(event.get("provider_pointer", 0))
    provider_vtable_raw = event.get("provider_vtable")
    provider_vtable = (
        None
        if provider_vtable_raw is None
        else int(provider_vtable_raw)
    )
    physics_system = int(event.get("physics_system", 0))
    call_index = int(event.get("call_index", -1))

    if provider_pointer == 0:
        backend = "builtin"
    elif provider_id in (0, 1):
        backend = "provider"
    else:
        backend = "unknown"

    return {
        "format": FORMAT,
        "version": 2,
        "status": "normalized",
        "ready": True,
        "frame_index": event.get("frame_index"),
        "call_index": call_index,
        "physics_system": physics_system,
        "provider_pointer": provider_pointer,
        "provider_vtable": provider_vtable,
        "provider_id": provider_id,
        "backend": backend,
        "scalar_count": scalar_count,
        "selector": selector,
        "source_function": "FUN_007b2210",
        "source_address": hex(
            int(event.get("source_address", 0x007B2210))
        ),
        "caller_return_address": (
            None
            if event.get("caller_return_address") is None
            else int(event["caller_return_address"])
        ),
        "provider_reset_vtable_offset": (
            "0x1c" if backend == "provider" else None
        ),
        "registers": dict(event.get("registers") or {}),
    }


def validate_scalar_reset_event(
    event: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = normalize_scalar_reset_event(event)
    errors: list[str] = []

    n = int(normalized["scalar_count"])
    selector = int(normalized["selector"])
    provider_pointer = int(normalized["provider_pointer"])
    provider_id = normalized["provider_id"]
    provider_vtable = normalized["provider_vtable"]

    if n <= 0:
        errors.append("non-positive-scalar-count")
    elif not 0 <= selector < n:
        errors.append(
            f"selector-out-of-domain:selector={selector}:count={n}"
        )

    if provider_pointer == 0:
        if normalized["backend"] != "builtin":
            errors.append("builtin-backend-classification-mismatch")
    else:
        if provider_vtable is None:
            errors.append("provider-vtable-missing")
        if normalized["backend"] == "unknown":
            errors.append("unknown-provider-vtable")
        elif provider_id not in (0, 1):
            errors.append("provider-id-missing")
    
    if int(normalized["call_index"]) < 0:
        errors.append("negative-call-index")

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCaptureValidation/2",
        "version": 2,
        "ready": not errors,
        "errors": errors,
        "frame_index": normalized["frame_index"],
        "call_index": normalized["call_index"],
        "provider_id": provider_id,
        "provider_pointer": provider_pointer,
        "provider_vtable": provider_vtable,
        "backend": normalized["backend"],
        "selector": selector,
        "scalar_count": n,
        "caller_return_address": normalized["caller_return_address"],
    }


def normalize_scalar_reset_events(
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [normalize_scalar_reset_event(event) for event in events]


def summarize_scalar_reset_events(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = normalize_scalar_reset_events(events)
    backends = Counter(
        str(event["backend"])
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

    provider_vtables = sorted({
        int(event["provider_vtable"])
        for event in normalized
        if event.get("provider_vtable") is not None
    })

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCaptureSummary/2",
        "version": 2,
        "event_count": len(normalized),
        "provider_event_count": int(backends.get("provider", 0)),
        "builtin_event_count": int(backends.get("builtin", 0)),
        "unknown_event_count": int(backends.get("unknown", 0)),
        "frame_count": len(frames),
        "frames": frames,
        "events_per_frame": {
            str(frame): count
            for frame, count in sorted(per_frame.items())
        },
        "provider_vtables": [
            hex(value)
            for value in provider_vtables
        ],
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
        "format": "SHIFT.SpecializedProviderScalarResetCaptureBatchValidation/2",
        "version": 2,
        "ready": not errors,
        "event_count": len(events),
        "errors": errors,
    }


def build_scalar_reset_capture_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 2,
        "event": {
            "required": [
                "call_index",
                "scalar_count",
                "selector",
                "provider_pointer",
                "physics_system",
            ],
            "optional": [
                "frame_index",
                "provider_vtable",
                "provider_id",
                "caller_return_address",
                "registers",
            ],
            "source": "FUN_007b2210",
        },
        "backend": {
            "provider": "provider pointer nonzero and first vtable word matches recovered provider vtable",
            "builtin": "provider pointer zero; selector resets logical row/column/RHS locally",
            "unknown": "provider pointer nonzero but vtable is not one of the recovered provider vtables",
        },
        "validation": [
            "selector in [0, scalar_count)",
            "provider pointer zero implies builtin backend",
            "nonzero provider pointer requires a recognized provider vtable",
            "nonnegative ordered call_index",
        ],
        "scope": {
            "group_attribution": "not decoded; caller return address is retained for later correlation",
            "matrix_semantics": "not inferred",
            "runtime_timing": "represented by ordered event/frame fields",
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
