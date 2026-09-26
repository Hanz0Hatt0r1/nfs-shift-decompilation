"""Exact RenderCameraViewManager singleton lifecycle from SHIFT.exe.

Recovered from FUN_00811280, FUN_008112a0, FUN_008112b0, FUN_008112e0 and
FUN_00811310. This remains in the camera-management layer; no renderer
implementation is touched.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.RenderCameraViewManagerRuntime/1"
SINGLETON_SYMBOL = "DAT_00c25760"
INIT_GUARD_SYMBOL = "_DAT_00c259e0"


def describe_render_camera_view_manager_constructor() -> dict[str, Any]:
    """Reproduce FUN_00811280."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "constructor",
        "actions": [
            {"action": "FUN_00647a10", "target": "this"},
            {
                "action": "write vtable",
                "value": "PTR_FUN_00b15aa8",
            },
            {
                "action": "FUN_00647820",
                "argument": "RenderCameraViewManager",
            },
        ],
        "evidence": {
            "function": "FUN_00811280",
            "label": "RenderCameraViewManager",
            "vtable": "PTR_FUN_00b15aa8",
        },
    }


def describe_render_camera_view_manager_reset() -> dict[str, Any]:
    """Reproduce FUN_008112a0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reset",
        "actions": [
            {"action": "write vtable", "value": "PTR_FUN_00b15aa8"},
            {"action": "FUN_00647b20"},
        ],
        "evidence": {"function": "FUN_008112a0"},
    }


def describe_render_camera_view_manager_delete(
    *,
    delete_flag: int,
) -> dict[str, Any]:
    """Reproduce FUN_008112b0's conditional deallocation."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "delete",
        "delete_flag": int(delete_flag),
        "actions": [
            {"action": "FUN_008112a0"},
            {
                "action": "FUN_00886930",
                "condition": "(delete_flag & 1) != 0",
            }
        ],
        "evidence": {"function": "FUN_008112b0"},
    }


def get_render_camera_view_manager_singleton(
    *,
    guard_before: int,
    constructor_succeeds: bool = True,
) -> dict[str, Any]:
    """Reproduce FUN_008112e0's lazy singleton guard."""
    guard = int(guard_before)
    if guard & 1:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "singleton",
            "status": "existing",
            "symbol": SINGLETON_SYMBOL,
            "guard_after": guard,
            "actions": [],
            "evidence": {"function": "FUN_008112e0"},
        }

    actions = [
        {"action": f"{INIT_GUARD_SYMBOL} |= 1"},
        {
            "action": "FUN_00811280",
            "target": SINGLETON_SYMBOL,
            "success": bool(constructor_succeeds),
        },
        {
            "action": "_atexit",
            "target": "LAB_00aa3b00",
        },
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "singleton",
        "status": "initialized" if constructor_succeeds else "constructor-failed",
        "symbol": SINGLETON_SYMBOL,
        "guard_after": guard | 1,
        "actions": actions,
        "evidence": {
            "function": "FUN_008112e0",
            "guard": INIT_GUARD_SYMBOL,
            "singleton": SINGLETON_SYMBOL,
        },
    }


def describe_camera_manager_refresh_bridge() -> dict[str, Any]:
    """Reproduce FUN_00811310's one-call boundary."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-manager-refresh-bridge",
        "actions": [
            {"action": "FUN_0080bfb0", "result": "camera manager"},
            {
                "action": "FUN_0080c180",
                "argument": "camera manager",
            },
        ],
        "return_value": 0,
        "evidence": {
            "function": "FUN_00811310",
            "manager_lookup": "FUN_0080bfb0",
            "refresh": "FUN_0080c180",
        },
    }
