"""Validate live provider scalar-reset effects.

Phase 494 observes the provider reset functions directly and validates the two
source-derived sentinel effects that every selector case owns:
the selector's diagonal workspace cell becomes exactly 1.0 and the matching
provider output-vector cell becomes exactly 0.0.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from specialized_provider_runtime import get_provider
from specialized_provider_storage_runtime import get_storage_layout
from specialized_provider_row_storage_runtime import get_row_pointers

FORMAT = "SHIFT.SpecializedProviderScalarResetEffectRuntime/1"

def _fmt_addr(address: int) -> str:
    return f"0x{address:08x}"



def _expected_addresses(provider_id: int, selector: int) -> dict[str, int]:
    layout = get_storage_layout(provider_id)
    pointers = get_row_pointers(provider_id)
    if not 0 <= int(selector) < layout.scalar_count:
        raise ValueError("selector outside provider scalar domain")

    return {
        "diagonal": pointers[int(selector)] + int(selector) * 8,
        "output": layout.output_vector_base + int(selector) * 8,
    }


def build_reset_effect_event(
    *,
    provider_id: int,
    selector: int,
    frame_index: int | None,
    reset_event_count: int,
    provider_pointer: int,
    provider_vtable: int,
    diagonal_before: float,
    diagonal_after: float,
    output_before: float,
    output_after: float,
) -> dict[str, Any]:
    addresses = _expected_addresses(provider_id, selector)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "captured",
        "ready": True,
        "provider_id": int(provider_id),
        "provider_pointer": int(provider_pointer),
        "provider_vtable": int(provider_vtable),
        "selector": int(selector),
        "frame_index": frame_index,
        "reset_event_count": int(reset_event_count),
        "addresses": {
            "diagonal": _fmt_addr(addresses["diagonal"]),
            "output": _fmt_addr(addresses["output"]),
        },
        "values": {
            "diagonal_before": float(diagonal_before),
            "diagonal_after": float(diagonal_after),
            "output_before": float(output_before),
            "output_after": float(output_after),
        },
        "expected": {
            "diagonal_after": 1.0,
            "output_after": 0.0,
        },
    }


def validate_reset_effect_event(
    event: Mapping[str, Any],
) -> dict[str, Any]:
    provider_id = int(event.get("provider_id", -1))
    selector = int(event.get("selector", -1))
    reset_event_count = int(event.get("reset_event_count", -1))
    values = event.get("values") or {}

    errors: list[str] = []

    if provider_id not in (0, 1):
        errors.append("unsupported-provider-id")
    else:
        scalar_count = get_storage_layout(provider_id).scalar_count
        expected_vtable = get_provider(provider_id).vtable_address
        if int(event.get("provider_vtable", -1)) != expected_vtable:
            errors.append("provider-vtable-mismatch")
        if not 0 <= selector < scalar_count:
            errors.append(
                f"selector-out-of-domain:selector={selector}:count={scalar_count}"
            )

        try:
            addresses = _expected_addresses(
                provider_id,
                selector,
            )
        except ValueError:
            addresses = None
        if addresses is not None:
            observed = event.get("addresses") or {}
            if observed.get("diagonal") != _fmt_addr(addresses["diagonal"]):
                errors.append("diagonal-address-mismatch")
            if observed.get("output") != _fmt_addr(addresses["output"]):
                errors.append("output-address-mismatch")

    if reset_event_count <= 0:
        errors.append("non-positive-reset-event-count")

    required_values = (
        "diagonal_before",
        "diagonal_after",
        "output_before",
        "output_after",
    )
    for name in required_values:
        if name not in values:
            errors.append(f"missing-value:{name}")

    if values.get("diagonal_after") != 1.0:
        errors.append("diagonal-after-not-one")
    if values.get("output_after") != 0.0:
        errors.append("output-after-not-zero")

    return {
        "format": "SHIFT.SpecializedProviderScalarResetEffectValidation/1",
        "version": 1,
        "ready": not errors,
        "provider_id": provider_id,
        "selector": selector,
        "reset_event_count": reset_event_count,
        "errors": errors,
    }


def summarize_reset_effect_events(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    valid = 0
    invalid = 0
    providers = Counter()
    frames = Counter()

    for event in events:
        result = validate_reset_effect_event(event)
        if result["ready"]:
            valid += 1
        else:
            invalid += 1

        providers[str(event.get("provider_id"))] += 1
        if event.get("frame_index") is not None:
            frames[str(event["frame_index"])] += 1

    return {
        "format": "SHIFT.SpecializedProviderScalarResetEffectSummary/1",
        "version": 1,
        "event_count": len(events),
        "valid_count": valid,
        "invalid_count": invalid,
        "provider_counts": dict(sorted(providers.items())),
        "frame_counts": dict(sorted(frames.items(), key=lambda item: int(item[0]))),
        "ready": invalid == 0,
    }


def validate_reset_effect_batch(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []

    for index, event in enumerate(events):
        result = validate_reset_effect_event(event)
        if not result["ready"]:
            errors.extend(
                f"event-{index}:{error}"
                for error in result["errors"]
            )

    counts = [
        int(event.get("reset_event_count", -1))
        for event in events
    ]
    if counts != sorted(counts):
        errors.append("reset-event-count-order-mismatch")
    if len(counts) != len(set(counts)):
        errors.append("duplicate-reset-event-count")

    return {
        "format": "SHIFT.SpecializedProviderScalarResetEffectBatchValidation/1",
        "version": 1,
        "ready": not errors,
        "event_count": len(events),
        "errors": errors,
    }


def build_reset_effect_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "sentinels": {
            "diagonal": "row_pointer[selector] + 8*selector",
            "diagonal_value_after": 1.0,
            "output": "output_vector_base + 8*selector",
            "output_value_after": 0.0,
        },
        "capture": {
            "entry": "provider reset vtable +0x1c",
            "return": "provider reset function return",
            "sequence_id": "FUN_007b2210 monotonic reset_event_count",
        },
        "scope": {
            "full_case_zero_footprint": "not captured here",
            "matrix_semantics": "not inferred",
        },
        "status": "source-backed-provider-reset-effect",
    }


__all__ = [
    "FORMAT",
    "build_reset_effect_event",
    "validate_reset_effect_event",
    "summarize_reset_effect_events",
    "validate_reset_effect_batch",
    "build_reset_effect_contract",
]
