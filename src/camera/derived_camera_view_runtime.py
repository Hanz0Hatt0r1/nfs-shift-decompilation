"""Evidence-backed derived CCameraView variant constructor.

Recovered from FUN_0081b0c0, FUN_0081b100 and FUN_0081b140.
"""

from __future__ import annotations

FORMAT = "SHIFT.DerivedCameraViewRuntime/1"


def describe_derived_camera_view_constructor() -> dict:
    """Reproduce FUN_0081b0c0's exact post-base-constructor writes."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "constructor",
        "actions": [
            {
                "action": "FUN_0081aeb0",
                "purpose": "construct base CCameraView",
            },
            {
                "action": "write +0x48",
                "value": 0x3F000000,
            },
            {
                "action": "write +0x50",
                "value": 0,
            },
            {
                "action": "write +0x4c",
                "value": 0,
            },
            {
                "action": "write +0x5c",
                "value": 0,
            },
            {
                "action": "write vtable",
                "value": "PTR_FUN_00b162e8",
            },
            {
                "action": "write +0x34",
                "value": 0x3F860A92,
            },
        ],
        "writes": {
            "+0x34": 0x3F860A92,
            "+0x48": 0x3F000000,
            "+0x4c": 0,
            "+0x50": 0,
            "+0x5c": 0,
        },
        "evidence": {
            "constructor": "FUN_0081b0c0",
            "base_constructor": "FUN_0081aeb0",
            "final_vtable": "PTR_FUN_00b162e8",
        },
    }


def describe_derived_camera_view_reset() -> dict:
    """Reproduce FUN_0081b100's reset sequence."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reset",
        "actions": [
            {
                "action": "write vtable",
                "value": "PTR_FUN_00b162e8",
            },
            {
                "action": "FUN_0081ac60",
            },
        ],
        "evidence": {
            "function": "FUN_0081b100",
            "base_reset": "FUN_0081ac60",
        },
    }


def describe_derived_camera_view_delete() -> dict:
    """Reproduce FUN_0081b140's destructor/deallocation delegation."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "delete",
        "actions": [
            {
                "action": "FUN_0081b100",
            },
            {
                "action": "FUN_00886930",
                "condition": "param_1 & 1",
            },
        ],
        "evidence": {
            "function": "FUN_0081b140",
            "base_delete": "FUN_0081b100",
        },
    }
