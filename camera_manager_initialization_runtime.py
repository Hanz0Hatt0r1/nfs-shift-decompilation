"""Exact CameraManager initialization helpers FUN_0080e960/FUN_0080ea10.

This module captures the source-visible back-references, double-buffer state,
profile-slot initialization, and reset fields. External runtime helpers remain
opaque.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.CameraManagerInitializationRuntime/1"


def describe_camera_manager_global_init(
    *,
    existing_hash_value: int = 0,
    generated_hash_value: int = 0,
) -> dict[str, Any]:
    """Reproduce FUN_0080e960's initialization boundary."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "global-init",
        "existing_hash_value": int(existing_hash_value),
        "generated_hash_value": int(generated_hash_value),
        "actions": [
            {"action": "FUN_00403cc0", "target": "+0x2a80", "size": 0x100},
            {"action": "FUN_0080e800", "target": "+0x2580"},
            {
                "action": "initialize +0x2688",
                "condition": "+0x2688 == 0",
                "source": "DAT_00c26058.vtable +0x1c4",
                "value": int(generated_hash_value),
            },
        ],
        "writes": {
            "+0x2560": 0,
            "+0x2568": 0,
            "+0x256c": 0,
            "+0x2570": 0,
            "+0x2574": 0xFFFFFFFF,
            "+0x2578": 0xFFFFFFFF,
            "+0x257c": 0,
            "+0x2690": 0,
            "+0x2694": 0,
            "+0x2698": 0,
            "+0x269c": 0,
            "+0x269d": 0,
            "+0x2a80": 0,
        },
        "evidence": {
            "function": "FUN_0080e960",
            "hash_field": "+0x2688",
            "scratch": "+0x2a80",
        },
    }


def describe_camera_manager_slot_init() -> dict[str, Any]:
    """Reproduce FUN_0080ea10's source-order initialization footprint."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-init",
        "back_references": [
            "+0x64",
            "+0xc24",
            "+0x17e4",
            "+0x1a64",
            "+0x1ce4",
            "+0x2144",
        ],
        "actions": [
            {"action": "FUN_00403cc0", "target": "+0x2a80", "size": 0x100},
            {
                "action": "set self back-references",
                "targets": [
                    "+0x64",
                    "+0xc24",
                    "+0x17e4",
                    "+0x1a64",
                    "+0x1ce4",
                    "+0x2144",
                ],
            },
            {"action": "FUN_0081c8f0", "target": "+0x20"},
            {"action": "FUN_0081c8f0", "target": "+0xbe0"},
            {"action": "FUN_0081caa0", "target": "+0x20", "profile_id": -1},
            {"action": "FUN_0081caa0", "target": "+0xbe0", "profile_id": -1},
            {
                "action": "camera-source.vtable +0x90",
                "targets": ["+0x17a0", "+0x1a20", "+0x1ca0", "+0x2100"],
                "argument": 0,
            },
            {
                "action": "initialize profile blocks",
                "targets": ["+0x26b8", "+0x2780", "+0x2848", "+0x2910"],
                "constructor": "FUN_0080d880",
            },
        ],
        "writes": {
            "+0x2560": 0,
            "+0x2568": 0,
            "+0x256c": 0,
            "+0x2570": 0,
            "+0x2574": 0xFFFFFFFF,
            "+0x2578": 0xFFFFFFFF,
            "+0x257c": 0,
            "+0x2690": 0,
            "+0x2694": 0,
            "+0x2698": 0,
            "+0x269c": 0,
            "+0x269d": 0,
            "+0x26a0": 0xFFFFFFFF,
            "+0x26a4": 0xFFFFFFFF,
            "+0x26a8": 0,
            "+0x26ac": 0,
            "+0x29d8": 0,
            "+0x29dc": 0,
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
            "+0x2a28": 0,
            "+0x2a2c": 0,
            "+0x2a30": 0,
            "+0x2a34": 0,
            "+0x2a38": 0,
            "+0x2a3c": 0,
            "+0x2a40": 0,
            "+0x2a44": 0,
            "+0x2a48": 0,
            "+0x2a4c": 0,
            "+0x2a50": 0,
            "+0x2a54": 0,
            "+0x2a58": 0,
            "+0x2a5c": 0,
            "+0x2a60": 0,
            "+0x2a64": 0,
            "+0x2a68": 0,
            "+0x2a6c": 0,
            "+0x2a70": 0,
            "+0x2a74": 0,
            "+0x2a75": 0,
            "+0x2a76": 0,
            "+0x2a80": 0,
        },
        "tail_actions": [
            {"action": "FUN_0080e800", "target": "+0x2580", "form": "thunk"},
            {"action": "write +0x2a80", "value": 0},
        ],
        "evidence": {
            "function": "FUN_0080ea10",
            "view_blocks": ["+0x20", "+0xbe0"],
            "static_blocks": ["+0x17a0", "+0x1a20"],
            "tracking_blocks": ["+0x1ca0", "+0x2100"],
            "profile_blocks": ["+0x26b8", "+0x2780", "+0x2848", "+0x2910"],
        },
    }


def describe_double_buffer_selector(
    *,
    old_index: int,
) -> dict[str, Any]:
    """Expose the source-visible active-buffer flip rule."""
    old = int(old_index)
    if old not in (0, 1):
        raise ValueError("active buffer index must be 0 or 1")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "buffer-selector",
        "old_index": old,
        "new_index": 1 - old,
        "formula": "new = 1 - old",
        "evidence": {
            "function": "FUN_0080cd40",
            "active_buffer_field": "+0x2560",
        },
    }
