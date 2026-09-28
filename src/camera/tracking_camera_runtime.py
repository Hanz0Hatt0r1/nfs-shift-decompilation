"""Evidence-backed TrackingCamera data/constructor ABI.

Recovered from FUN_0081f830, FUN_0081f8c0, FUN_0081f990, FUN_0081eab0,
FUN_0081ea80, FUN_0081f1a0 and FUN_0081f240.

The module exposes raw constructor/default writes, copy fields, reflected
property registration, and the secondary seven-slot input registry.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.TrackingCameraRuntime/1"
INPUT_SLOT_BASE = 0x440
INPUT_SLOT_COUNT = 7


def tracking_data_defaults() -> dict[str, Any]:
    """Reproduce FUN_0081f830's raw data initializer."""
    writes = {
        0x00: 0x3F800000,
        0x04: 0,
        0x08: 0,
        0x0C: 0,
        0x10: 0,
        0x14: 0,
        0x18: 0,
        0x1C: 0,
        0x20: 0,
        0x24: 0,
        0x28: 0,
        0x2C: 0,
        0x30: 0,
        0x34: 0,
        0x38: 0,
        0x3C: 0,
        0x40: 0,
        0x44: 0,
        0x48: 0x3F800000,
        0x50: 0xFFFFFFFF,
        0x54: 0xFFFFFFFF,
        0x58: 0,
        0x5C: 0,
        0x60: 0x3F800000,
        0x68: 0,
        0x6C: 0,
        0x70: 0,
        0x74: 0,
        0x78: 0,
        0x7C: 0,
        0x80: 0x3F000000,
        0x84: 0x3F000000,
        0x88: 0,
    }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-data-defaults",
        "writes": {f"+0x{k:02x}": v for k, v in writes.items()},
        "byte_writes": {
            "+0x64": 0,
        },
        "evidence": {"function": "FUN_0081f830"},
    }


def describe_tracking_camera_constructor() -> dict[str, Any]:
    """Reproduce FUN_0081f8c0's derived constructor writes."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-camera-constructor",
        "actions": [
            {"action": "FUN_00813180", "purpose": "base static camera defaults"},
            {"action": "write vtable", "value": "PTR_FUN_00b165e8"},
        ],
        "writes": {
            "+0xf0": 0,
            "+0xf4": 0,
            "+0xf8": 0xFFFFFFFF,
            "+0xfc": 0xFFFFFFFF,
            "+0x100": 0,
            "+0x101": 0,
            "+0x104": 0,
            "+0x108": 0,
            "+0x10c": 0,
            "+0x110": 0,
            "+0x114": 0,
            "+0x118": 0,
            "+0x11c": 0,
            "+0x120": 0,
            "+0x124": 0,
            "+0x128": 0,
            "+0x12c": 0,
            "+0x130": 0,
            "+0x134": 0,
            "+0x138": 0,
            "+0x13c": 0,
            "+0x140": 0,
            "+0x144": 0,
            "+0x148": 0,
        },
        "evidence": {
            "function": "FUN_0081f8c0",
            "base_constructor": "FUN_00813180",
            "tracking_vtable": "PTR_FUN_00b165e8",
        },
    }


def copy_tracking_camera_state(source: Mapping[int, Any]) -> dict[str, Any]:
    """Reproduce FUN_0081f990's tracking-copy range."""
    offsets = [
        0xF0, 0xF4, 0xF8, 0xFC, 0x100, 0x101,
        0x104, 0x108, 0x128, 0x12C, 0x130, 0x134,
        0x138, 0x13C, 0x140, 0x144, 0x148,
    ]
    missing = [x for x in offsets if x not in source]
    if missing:
        raise ValueError(f"missing tracking source offsets: {missing}")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-copy",
        "copies": {f"+0x{x:02x}": source[x] for x in offsets},
        "reset_fields": ["+0x10c", "+0x110", "+0x114", "+0x118", "+0x11c", "+0x120", "+0x124"],
        "evidence": {"function": "FUN_0081f990"},
    }


def tracking_property_registration() -> dict[str, Any]:
    """Reproduce FUN_0081ebc0's reflected TrackingCamera properties."""
    names = [
        ("MovementRate", 10, 0xF0),
        ("TrackingRate", 10, 0xF4),
        ("SplineID", 0x0D, 0xF8),
        ("TargetSplineID", 0x0D, 0xFC),
        ("bAutoZoom", 0x20, 0x100),
        ("bStaticDirection", 0x20, 0x101),
        ("SplineChaseDir", 10, 0x104),
        ("TargetSplineChaseDir", 10, 0x108),
        ("TrackingLag", 10, 0x128),
        ("TrackingLagSmoothening", 10, 0x12C),
        ("TrackingErrorFrequency", 10, 0x130),
        ("TrackingErrorCorrectionSpeed", 10, 0x134),
        ("TrackingErrorMagnitude", 10, 0x138),
        ("SplinesRatio", 10, 0x13C),
        ("bSyncSplines", 0x20, 0x140),
        ("OnSplineEndReached", 0x0D, 0x144),
        ("OnTargetSplineEndReached", 0x0D, 0x148),
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-property-registration",
        "registration_object": "DAT_00b8e0e8",
        "properties": [
            {"name": n, "type_id": t, "offset": o, "flags": 3}
            for n, t, o in names
        ],
        "evidence": {
            "function": "FUN_0081ebc0",
            "registration_helper": "FUN_0063a280",
        },
    }


def clear_tracking_input_slots(slots: Sequence[Any]) -> list[Any]:
    if len(slots) != INPUT_SLOT_COUNT:
        raise ValueError("tracking input storage contains exactly seven slots")
    return [None] * INPUT_SLOT_COUNT


def register_tracking_input(
    slots: Sequence[Any],
    *,
    action_index: int,
    action_object: Any,
    frame_stack_accepts: bool,
) -> tuple[list[Any], dict[str, Any]]:
    index = int(action_index)
    next_slots = list(slots)
    if len(next_slots) != INPUT_SLOT_COUNT:
        raise ValueError("tracking input storage contains exactly seven slots")
    if action_object in (None, 0) or not 1 <= index <= 6:
        return next_slots, {
            "format": FORMAT, "version": 1, "status": "rejected",
        }
    if next_slots[index] not in (None, 0):
        return next_slots, {
            "format": FORMAT, "version": 1, "status": "occupied",
            "slot": index,
        }
    if not frame_stack_accepts:
        return next_slots, {
            "format": FORMAT, "version": 1, "status": "frame-stack-rejected",
        }
    next_slots[index] = action_object
    return next_slots, {
        "format": FORMAT,
        "version": 1,
        "status": "registered",
        "storage_offset": INPUT_SLOT_BASE + index * 4,
        "evidence": {
            "function": "FUN_0081eab0",
            "frame_stack": "+0x320",
            "valid_range": "1..6",
        },
    }


def describe_tracking_free_look_factory() -> dict[str, Any]:
    """Trace FUN_0081f240's two registered free-look actions."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-free-look-factory",
        "actions": [
            {
                "action": "FUN_00671230",
                "name": "Free Look Left/Right",
                "binding": "type3/0/4/2",
                "registered_index": 3,
            },
            {
                "action": "FUN_00671230",
                "name": "Free Look Up/Down",
                "binding": "type3/0/4/3",
                "registered_index": 4,
            },
        ],
        "evidence": {
            "function": "FUN_0081f240",
            "registration": "FUN_0081eab0",
        },
    }
