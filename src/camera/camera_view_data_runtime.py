"""Evidence-backed camera-view data init/reset/copy contracts.

Recovered from FUN_0081c3b0, FUN_0081c8f0, and FUN_0081d180.

This layer describes the storage ABI of the nested camera-view data object.
Known semantic property names come from the executable registration, but raw
copy/reset boundaries are preserved where the helper semantics are opaque.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.CameraViewDataRuntime/1"

DWORD_COPY_OFFSETS = tuple(range(0x00, 0x50, 4))
BYTE_COPY_OFFSETS = (0x50, 0x51, 0x52, 0x53)
TAIL_DWORD_OFFSET = 0x54


def initialize_camera_view_data() -> dict[str, Any]:
    """Reproduce FUN_0081c3b0's explicit initialization footprint."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "initialize",
        "writes": {
            **{f"+0x{offset:02x}": 0 for offset in DWORD_COPY_OFFSETS},
            "+0x40": 0xFFFFFFFF,
            "+0x44": 0xFFFFFFFF,
            "+0x48": 0xFFFFFFFF,
            "+0x4c": 0,
            "+0x50": 1,
            "+0x51": 0,
            "+0x52": 0,
            "+0x53": 0,
            "+0x54": 0,
            "+0x60_container": "FUN_00823bc0",
            "+0xac_container": "FUN_00823bc0",
        },
        "evidence": {
            "function": "FUN_0081c3b0",
            "vector_or_container_helpers": "FUN_00823bc0",
        },
        "limitations": [
            "the two FUN_00823bc0 containers are preserved as opaque constructed values",
        ],
    }


def reset_camera_view_data(
    *,
    frame_stack_base: int | str,
    property_stack_size: int = 0x100,
) -> dict[str, Any]:
    """Reproduce FUN_0081c8f0's reset calls."""
    if int(property_stack_size) != 0x100:
        raise ValueError("FUN_0081c8f0 clears exactly 0x100 bytes")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reset",
        "actions": [
            {
                "action": "FUN_00403cc0",
                "target": frame_stack_base,
                "size": 0x100,
            },
            {"action": "write +0x80", "value": 0},
            {"action": "write +0x60", "value": 0},
        ],
        "evidence": {
            "function": "FUN_0081c8f0",
            "frame_stack": "+0x60",
            "selected_profile_object": "+0x80",
        },
    }


def copy_camera_view_data(
    source_words: Mapping[int, Any],
    *,
    source_bytes: Mapping[int, int] | None = None,
    tail_word: Any = None,
) -> dict[str, Any]:
    """Reproduce FUN_0081d180's raw copy pattern."""
    missing = [offset for offset in DWORD_COPY_OFFSETS if offset not in source_words]
    if missing:
        raise ValueError(f"missing source dwords at offsets: {missing}")

    bytes_in = source_bytes or {}
    missing_bytes = [offset for offset in BYTE_COPY_OFFSETS if offset not in bytes_in]
    if missing_bytes:
        raise ValueError(f"missing source bytes at offsets: {missing_bytes}")

    dwords = {
        f"+0x{offset:02x}": source_words[offset] for offset in DWORD_COPY_OFFSETS
    }
    bytes_out = {
        f"+0x{offset:02x}": int(bytes_in[offset]) & 0xFF
        for offset in BYTE_COPY_OFFSETS
    }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "copy",
        "dword_copies": dwords,
        "byte_copies": bytes_out,
        "tail_dword": {
            "destination": "+0x54",
            "value": source_words.get(TAIL_DWORD_OFFSET, tail_word),
        },
        "helper_copies": [
            {
                "helper": "FUN_00814340",
                "destination": "+0x58",
                "source": "+0x58",
            },
            {
                "helper": "FUN_00814340",
                "destination": "+0xac",
                "source": "+0xac",
            },
        ],
        "evidence": {
            "function": "FUN_0081d180",
            "dword_range": ["+0x00", "+0x4c"],
            "byte_range": ["+0x50", "+0x53"],
            "tail_dword": "+0x54",
        },
        "limitations": [
            "FUN_00814340 copy semantics are opaque; only source/destination offsets are retained",
        ],
    }


def camera_view_property_offsets() -> dict[str, int]:
    """Return known semantic offsets from the executable's profile registration."""
    return {
        "OriRate": 0x10,
        "VelocityOriRatio": 0x1C,
        "TargetPertubationScale": 0x20,
        "RearPos": 0x28,
        "PosOffset": 0x2C,
        "OriOffset": 0x38,
        "HeadPhysicsScale": 0x44,
        "Radius": 0x50,
        "FOV": 0x54,
        "FOVMax": 0x58,
        "FOVMaxSpeedMPH": 0x5C,
        "AspectRatio": 0x60,
        "NearZ": 0x64,
        "FarZ": 0x68,
        "ImpactShakePositionalExtents": 0x6C,
        "ImpactShakeOrientationalExtents": 0x78,
        "ImpactShakeFrequencyFactor": 0x84,
        "SpeedShakePositionalExtents": 0x88,
        "SpeedShakeOrientationalExtents": 0x94,
        "SpeedShakeFrequencyFactor": 0xA0,
        "SpeedShakeMinSpeed": 0xA4,
        "SpeedShakeMaxSpeed": 0xA8,
        "HideCar": 0xAC,
        "HideCarRearLook": 0xAD,
        "RenderCockpit": 0xAE,
        "AllowCycle": 0xAF,
    }
