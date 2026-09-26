"""Evidence-backed CameraManager constructor/layout runtime from FUN_0080f740.

This module records the two double-buffered view/camera object groups and the
raw manager transition state initialized by the executable. It intentionally
keeps helper-created objects opaque.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.CameraManagerConstructorRuntime/1"

DOUBLE_BUFFER_LAYOUT = {
    "active_buffer_index": 0x2560,
    "service_pointer": 0x2564,
    "active_camera_source": 0x2568,
    "previous_camera_source": 0x256C,
    "previous_buffer_index": 0x2570,
    "previous_buffer_sub_index": 0x2574,
    "previous_camera_id": 0x2578,
    "previous_buffer_sub_flag": 0x257C,
    "update_guard": 0x269C,
    "active_camera_id": 0x26A0,
    "active_group": 0x26A4,
    "current_mode": 0x26A8,
    "previous_mode": 0x26AC,
}

OBJECT_BUFFERS = (
    {
        "name": "CCameraView",
        "first_offset": 0x20,
        "second_offset": 0xBE0,
        "stride": 0xBC0,
        "constructor": "FUN_0081cba0",
    },
    {
        "name": "StaticCamera",
        "first_offset": 0x17A0,
        "second_offset": 0x1A20,
        "stride": 0x280,
        "constructor": "FUN_00814f60",
    },
    {
        "name": "TrackingCamera",
        "first_offset": 0x1CA0,
        "second_offset": 0x2100,
        "stride": 0x460,
        "constructor": "FUN_0081fac0",
    },
)


def camera_manager_constructor_state() -> dict[str, Any]:
    """Expose the exact raw writes visible in FUN_0080f740."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-manager-constructor",
        "vtable": "PTR_FUN_00b15858",
        "object_groups": list(OBJECT_BUFFERS),
        "writes": {
            "+0x2564": "FUN_0080bfb0()",
            "+0x2568": 0,
            "+0x256c": 0,
            "+0x2570": 0,
            "+0x2574": 0xFFFFFFFF,
            "+0x2578": 0xFFFFFFFF,
            "+0x257c": 0,
            "+0x2688": 0,
            "+0x268c": 0x3FAAAAAB,
            "+0x2690": 0,
            "+0x2694": 0,
            "+0x2698": 0,
            "+0x269c": 0,
            "+0x26a0": 0xFFFFFFFF,
            "+0x26a4": 0xFFFFFFFF,
            "+0x26a8": 0,
            "+0x26ac": 0,
            "+0x29e0": 0xFFFFFFFF,
            "+0x29e4": 0,
            "+0x29e8": 0xFFFFFFFF,
            "+0x29ec": 0,
            "+0x29f0": 3,
            "+0x29f4": 0,
            "+0x29f8": 0xFFFFFFFF,
            "+0x29fc": 0xFFFFFFFF,
            "+0x2a00": 0xFFFFFFFF,
            "+0x2a04": 0xFFFFFFFF,
            "+0x2a08": 0,
            "+0x2a0c": 0xFFFFFFFF,
            "+0x2a10": 0,
            "+0x2a14": 3,
            "+0x2a18": 0,
            "+0x2a1c": 0xFFFFFFFF,
            "+0x2a20": 0xFFFFFFFF,
            "+0x2a24": 0xFFFFFFFF,
            "+0x2a70": 0,
            "+0x2a80": 0,
        },
        "delegates": [
            {
                "constructor": "FUN_0081cba0",
                "base_offset": 0x20,
                "count": 2,
                "stride": 0xBC0,
            },
            {
                "constructor": "FUN_00814f60",
                "base_offset": 0x17A0,
                "count": 2,
                "stride": 0x280,
            },
            {
                "constructor": "FUN_0081fac0",
                "base_offset": 0x1CA0,
                "count": 2,
                "stride": 0x460,
            },
            {
                "constructor": "FUN_0080e3a0",
                "base_offset": 0x2600,
            },
            {
                "constructor": "FUN_0080e960",
                "purpose": "initialize active camera buffer",
            },
        ],
        "evidence": {
            "function": "FUN_0080f740",
            "double_buffer_views": "+0x20/+0xbe0",
            "double_buffer_static": "+0x17a0/+0x1a20",
            "double_buffer_tracking": "+0x1ca0/+0x2100",
        },
        "limitations": [
            "FUN_0080e3a0 and FUN_0080e960 remain opaque initialization helpers",
            "the +0x26b8/+0x2780 configuration-state arrays are not interpreted here",
        ],
    }


def describe_camera_manager_buffer_copy(
    *,
    old_buffer: int,
    new_buffer: int,
) -> dict[str, Any]:
    """Relate constructor layout to FUN_0080cd40's copy targets."""
    old_index = int(old_buffer) & 1
    new_index = int(new_buffer) & 1
    if old_index == new_index:
        raise ValueError("double-buffer copy requires different buffer indices")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-manager-buffer-layout",
        "old_buffer": old_index,
        "new_buffer": new_index,
        "copies": [
            {
                "name": "camera-data",
                "source": 0xBE0 if old_index else 0x20,
                "destination": 0x20 if old_index else 0xBE0,
                "stride": 0xBC0,
                "helper": "FUN_0081e6c0",
            },
            {
                "name": "static-camera",
                "source": 0x1A20 if old_index else 0x17A0,
                "destination": 0x17A0 if old_index else 0x1A20,
                "stride": 0x280,
                "helper": "FUN_00815eb0",
            },
            {
                "name": "tracking-camera",
                "source": 0x2100 if old_index else 0x1CA0,
                "destination": 0x1CA0 if old_index else 0x2100,
                "stride": 0x460,
                "helper": "FUN_00815eb0",
            },
        ],
        "evidence": {
            "constructor": "FUN_0080f740",
            "copy_function": "FUN_0080cd40",
        },
    }
