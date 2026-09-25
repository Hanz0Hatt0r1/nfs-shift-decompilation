"""Evidence-backed CameraManager event handlers from SHIFT.exe.

FUN_0080b910 / FUN_0080bf30 / FUN_0080c230 / FUN_0080c2e0 are the concrete
handlers named by FUN_0080c710 for event types 0..3.

The module preserves call order, mode gates, and field writes. Unknown helper
semantics remain explicit rather than being guessed.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.CameraEventHandlersRuntime/1"


def describe_event_type_0(
    *,
    argument_a: Any,
    argument_b: int,
    slot_index: int,
) -> dict[str, Any]:
    """Trace FUN_0080b910."""
    return {
        "format": FORMAT,
        "version": 1,
        "event_type": 0,
        "handler": "FUN_0080b910",
        "actions": [
            {
                "action": "write outer +0x800",
                "value": argument_a,
            },
            {
                "action": "FUN_0080de00",
                "slot_index": int(slot_index),
                "arguments": {
                    "group": argument_a,
                    "sub_index": int(argument_b),
                },
            },
        ],
        "evidence": {
            "outer_field": "+0x800",
            "slot_address": "outer +0x290 + slot_index*0x2aa0",
            "target": "FUN_0080de00",
        },
    }


def describe_event_type_1(
    *,
    argument_a: Any,
    argument_b: Any,
    active_mode: int,
    active_camera_id: int,
) -> dict[str, Any]:
    """Trace FUN_0080bf30."""
    mode = int(active_mode)
    if mode not in (2, 3):
        return {
            "format": FORMAT,
            "version": 1,
            "event_type": 1,
            "handler": "FUN_0080bf30",
            "path": "fallback-static",
            "actions": [
                {
                    "action": "FUN_0080b910",
                    "arguments": {
                        "first": argument_a,
                        "second": -2,
                        "slot_index": 0,
                    },
                }
            ],
            "evidence": {
                "mode_field": "+0x26a8",
                "fallback": "FUN_0080b910(this,param_1,-2,0)",
            },
        }

    return {
        "format": FORMAT,
        "version": 1,
        "event_type": 1,
        "handler": "FUN_0080bf30",
        "path": "mode-2-or-3",
        "actions": [
            {
                "action": "FUN_0080be50",
                "arguments": {
                    "first": argument_a,
                    "second": argument_b,
                    "camera_id": int(active_camera_id),
                    "slot_index": 0,
                },
            }
        ],
        "evidence": {
            "mode_field": "+0x26a8",
            "accepted_modes": [2, 3],
            "active_camera_id": "+0x26a0",
            "target": "FUN_0080be50",
        },
    }


def describe_event_type_2(
    *,
    argument_a: int,
    argument_b: int,
    active_mode: int,
    outer_service_available: bool = True,
) -> dict[str, Any]:
    """Trace FUN_0080c230."""
    mode = int(active_mode)
    actions: list[dict[str, Any]] = []

    if mode in (2, 3):
        if int(argument_a) != -1:
            actions.append({
                "action": "FUN_0080b910",
                "arguments": {
                    "group": int(argument_a),
                    "sub_index": -2,
                    "slot_index": 0,
                },
            })
            status = "forwarded-to-static-view"
        else:
            status = "mode-2/3-no-op"
        return {
            "format": FORMAT,
            "version": 1,
            "event_type": 2,
            "handler": "FUN_0080c230",
            "path": "mode-2-or-3",
            "status": status,
            "actions": actions,
            "evidence": {
                "mode_field": "+0x26a8",
                "target": "FUN_0080b910",
                "condition": "argument_a != -1",
            },
        }

    actions.append({
        "action": "FUN_0080be50",
        "status": "attempted" if outer_service_available and int(argument_a) != -1 else "skipped",
        "arguments": {
            "first": int(argument_a),
            "second": int(argument_b),
            "camera_source": "FUN_00811a20(FUN_0080bfb0().+0x568)",
            "slot_index": 0,
        },
    })

    actions.append({
        "action": "write global camera-service +0xb4",
        "value": 0,
    })
    actions.append({
        "action": "tracking-buffer +0x2ec = FUN_0040f0d0(outer +0x3c)",
        "condition": "tracking buffer pointer is non-null",
    })

    return {
        "format": FORMAT,
        "version": 1,
        "event_type": 2,
        "handler": "FUN_0080c230",
        "path": "non-mode-2/3",
        "status": "applied" if outer_service_available and int(argument_a) != -1 else "partial",
        "actions": actions,
        "evidence": {
            "manager_lookup": "FUN_0080bfb0",
            "service_source": "+0x568",
            "service_type_helper": "FUN_00811a20",
            "group_dispatch": "FUN_0080be50",
            "service_flag_reset": "+0xb4 = 0",
            "tracking_timestamp_field": "active tracking buffer +0x2ec",
            "timestamp_helper": "FUN_0040f0d0(outer +0x3c)",
        },
        "limitations": [
            "FUN_00811a20 result is retained as an opaque service/type argument",
            "FUN_0080be50 semantics remain opaque",
        ],
    }


def describe_event_type_3(
    *,
    argument_a: int,
    argument_b: int,
    active_mode: int,
    incoming_mode_flag: bool | None,
) -> dict[str, Any]:
    """Trace FUN_0080c2e0 while preserving its unresolved extraout_DL value."""
    current_mode_is_23 = int(active_mode) in (2, 3)
    current_flag = current_mode_is_23

    if incoming_mode_flag is None:
        return {
            "format": FORMAT,
            "version": 1,
            "event_type": 3,
            "handler": "FUN_0080c2e0",
            "path": "opaque-flag-compare",
            "actions": [],
            "condition": {
                "left": current_flag,
                "right": "extraout_DL (unresolved)",
            },
            "fallbacks": {
                "equal": "FUN_0080bf30",
                "different": "FUN_0080c230",
            },
            "evidence": {
                "mode_test": "active mode == 2 or 3",
                "comparison": "cVar1 == extraout_DL",
            },
            "limitations": [
                "the decompiler's extraout_DL is not assigned a guessed source value",
            ],
        }

    equal = current_flag == bool(incoming_mode_flag)
    return {
        "format": FORMAT,
        "version": 1,
        "event_type": 3,
        "handler": "FUN_0080c2e0",
        "path": "branch-resolved",
        "comparison_equal": equal,
        "comparison": {
            "current_mode_2_or_3": current_flag,
            "incoming_mode_flag": bool(incoming_mode_flag),
        },
        "next_handler": "FUN_0080bf30" if equal else "FUN_0080c230",
        "arguments": {
            "first": int(argument_a),
            "second": int(argument_b),
        },
        "evidence": {
            "comparison": "cVar1 == extraout_DL",
            "equal_target": "FUN_0080bf30",
            "different_target": "FUN_0080c230",
        },
        "limitations": [
            "the origin of extraout_DL is unresolved in the decompiler output",
        ],
    }
