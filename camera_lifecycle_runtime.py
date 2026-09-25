"""Evidence-backed CameraManager lifecycle and slot-reset contracts.

Recovered from FUN_0080bc80, FUN_0080bce0, FUN_0080bd50, FUN_0080bd80,
FUN_0080c180, and FUN_0080ea10.

This module focuses only on proven lifecycle fields and call ordering. The
large per-camera state initializers/resetters are represented as explicit
field groups instead of inventing meanings for their opaque helper calls.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraLifecycleRuntime/1"
SLOT_COUNT = 3
SLOT_STRIDE = 0x2AA0


def resolve_lifecycle_timestamp(
    base_timestamp: int,
    *,
    high_resolution_enabled: bool,
    high_resolution_delta: int = 0,
) -> dict[str, Any]:
    """Model the timestamp assignment shared by bc80/bce0/bd50."""
    base = int(base_timestamp)
    if high_resolution_enabled:
        value = base + int(high_resolution_delta)
        return {
            "timestamp": value,
            "source": "FUN_0040f0d0(+0x3c) + +0x44",
            "expression": "+0x44 + FUN_0040f0d0(+0x3c)",
        }
    return {
        "timestamp": base,
        "source": "+0x44",
        "expression": "+0x44",
    }


def describe_manager_initialize(
    *,
    base_timestamp: int,
    high_resolution_enabled: bool,
    high_resolution_delta: int = 0,
) -> dict[str, Any]:
    """Trace FUN_0080bc80."""
    timing = resolve_lifecycle_timestamp(
        base_timestamp,
        high_resolution_enabled=high_resolution_enabled,
        high_resolution_delta=high_resolution_delta,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "initialize",
        "slot_initialization": {
            "count": SLOT_COUNT,
            "stride": SLOT_STRIDE,
            "target": "FUN_0080ea10",
        },
        "time_cursor_after": timing["timestamp"],
        "actions": [
            {
                "action": "FUN_0080ea10",
                "slot_index": index,
                "slot_offset": index * SLOT_STRIDE,
            }
            for index in range(SLOT_COUNT)
        ]
        + [
            {
                "action": "write +0x828",
                "value": timing["timestamp"],
            }
        ],
        "evidence": {
            "function": "FUN_0080bc80",
            "initialized_cursor": "+0x828",
            "base_timestamp": "+0x44",
            "high_resolution_flag": "+0x4c bit 2",
        },
        "limitations": [
            "FUN_0080ea10 is summarized by its proven field/reset boundaries",
        ],
    }


def describe_manager_reset(
    *,
    base_timestamp: int,
    high_resolution_enabled: bool,
    high_resolution_delta: int = 0,
) -> dict[str, Any]:
    """Trace FUN_0080bce0."""
    timing = resolve_lifecycle_timestamp(
        base_timestamp,
        high_resolution_enabled=high_resolution_enabled,
        high_resolution_delta=high_resolution_delta,
    )
    actions = [
        {
            "action": "FUN_0080dc60",
            "slot_index": index,
            "slot_offset": index * SLOT_STRIDE,
        }
        for index in range(SLOT_COUNT)
    ]
    actions.append({
        "action": "FUN_00818940",
        "arguments": {"source": "manager +0x568"},
    })
    actions.append({
        "action": "write +0x828",
        "value": timing["timestamp"],
    })
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reset",
        "slot_reset": {
            "count": SLOT_COUNT,
            "stride": SLOT_STRIDE,
            "target": "FUN_0080dc60",
        },
        "global_reset": "FUN_00818940(manager +0x568)",
        "time_cursor_after": timing["timestamp"],
        "actions": actions,
        "evidence": {
            "function": "FUN_0080bce0",
            "time_cursor": "+0x828",
            "global_camera_state": "+0x568",
        },
        "limitations": [
            "FUN_0080dc60 helper calls and global +0x568 semantics are not synthesized",
        ],
    }


def describe_time_origin_refresh(
    *,
    base_timestamp: int,
    high_resolution_enabled: bool,
    high_resolution_delta: int = 0,
) -> dict[str, Any]:
    """Trace FUN_0080bd50."""
    timing = resolve_lifecycle_timestamp(
        base_timestamp,
        high_resolution_enabled=high_resolution_enabled,
        high_resolution_delta=high_resolution_delta,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "time-origin-refresh",
        "actions": [{"action": "write +0x828", "value": timing["timestamp"]}],
        "time_cursor_after": timing["timestamp"],
        "evidence": {
            "function": "FUN_0080bd50",
            "time_cursor": "+0x828",
        },
    }


def describe_post_load_sync(
    *,
    slot_container_present: bool,
    slot_enabled: Sequence[bool],
) -> dict[str, Any]:
    """Trace FUN_0080bd80's active-slot synchronization pass."""
    if len(slot_enabled) != SLOT_COUNT:
        raise ValueError(f"FUN_0080bd80 expects {SLOT_COUNT} slot states")

    actions: list[dict[str, Any]] = []
    if slot_container_present:
        for index, enabled in enumerate(slot_enabled):
            if enabled:
                actions.append({
                    "action": "FUN_0080e420",
                    "slot_index": index,
                    "slot_offset": index * SLOT_STRIDE,
                    "sync_object": f"slot[{index}] +0x2580",
                })
        actions.append({
            "action": "write +0x82c",
            "value": 1,
        })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "post-load-sync",
        "slot_container_present": bool(slot_container_present),
        "actions": actions,
        "sync_mark_after": 1 if slot_container_present else None,
        "evidence": {
            "function": "FUN_0080bd80",
            "slot_container": "+0x290",
            "slot_enabled": "+0x2690",
            "sync_target": "+0x2580",
            "sync_helper": "FUN_0080e420",
            "sync_marker": "+0x82c",
        },
        "limitations": [
            "the marker is exposed as a lifecycle flag; its wider ownership semantics are unresolved",
        ],
    }


def describe_post_load_lifecycle(
    *,
    feature_enabled: bool,
    sync_marker: bool,
    slot_container_present: bool,
    slot_enabled: Sequence[bool],
) -> dict[str, Any]:
    """Trace FUN_0080c180's guarded post-load callback."""
    if not feature_enabled:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "post-load-lifecycle",
            "status": "feature-disabled",
            "actions": [],
            "sync_marker_after": sync_marker,
            "evidence": {"function": "FUN_0080c180", "guard": "+0x28"},
        }

    actions: list[dict[str, Any]] = []
    marker_after = True
    if not sync_marker:
        sync = describe_post_load_sync(
            slot_container_present=slot_container_present,
            slot_enabled=slot_enabled,
        )
        actions.append(sync)
    actions.append({
        "action": "write +0x82c",
        "value": 0,
    })
    marker_after = False
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "post-load-lifecycle",
        "status": "processed",
        "actions": actions,
        "sync_marker_after": marker_after,
        "evidence": {
            "function": "FUN_0080c180",
            "feature_guard": "+0x28 != 0",
            "sync_marker": "+0x82c",
            "sync_path": "FUN_0080bd80 when marker == 0",
        },
    }


def describe_slot_initializer(
    *,
    slot_base: int | str,
) -> dict[str, Any]:
    """Summarize the proven FUN_0080ea10 initialization footprint."""
    base = slot_base
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-initialize",
        "target": base,
        "writes": {
            "+0x64": base,
            "+0xc24": base,
            "+0x17e4": base,
            "+0x1a64": base,
            "+0x1ce4": base,
            "+0x2144": base,
            "+0x2560": 0,
            "+0x2568": 0,
            "+0x256c": 0,
            "+0x2570": 0,
            "+0x2574": -1,
            "+0x2578": -1,
            "+0x257c": 0,
            "+0x2690": 0,
            "+0x2694": 0,
            "+0x2698": 0,
            "+0x269c": 0,
            "+0x269d": 0,
            "+0x26a0": -1,
            "+0x26a4": -1,
            "+0x26a8": 0,
            "+0x26ac": 0,
            "+0x29d8": 0,
            "+0x29dc": 0,
            "+0x2a74": 0,
            "+0x2a75": 0,
            "+0x2a76": 0,
            "+0x2a80": 0,
        },
        "opaque_helpers": [
            "FUN_00403cc0",
            "FUN_0081c8f0",
            "FUN_0081caa0",
            "slot camera vtable +0x90",
            "FUN_0080d880",
            "FUN_0080e800",
        ],
        "evidence": {
            "function": "FUN_0080ea10",
            "slot_stride": "0x2aa0",
        },
        "limitations": [
            "the expanded +0x29d8..+0x2a76 initializer block is preserved as raw field writes",
            "vtable/helper effects are not inferred",
        ],
    }
