"""Exact built-in camera preset defaults from FUN_00810950 and FUN_00810710.

FUN_00810950 builds nine CameraConfigSnapshot records using FUN_00823760 as
the baseline constructor, then applies only the observed per-preset overrides.
This module preserves overrides as raw 32-bit values/bytes so no unit conversion
or semantic relabeling is required.
"""

from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.BuiltinCameraPresetsRuntime/1"


def u32(value: int) -> int:
    return int(value) & 0xFFFFFFFF


def f32_from_bits(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", u32(bits)))[0]


BUILTIN_PRESETS: tuple[dict[str, Any], ...] = (
    {
        "name": "BumperCam",
        "overrides": {
            "+0x10": 0x43B40000, "+0x14": 0x43B40000, "+0x18": 0x43B40000,
            "+0x2c": 0, "+0x30": 0x3E4CCCCD, "+0x34": 0xBFE66666,
            "+0x38": 0, "+0x3c": 0, "+0x40": 0,
            "+0x44": 0x3F800000, "+0x48": 0x3F800000, "+0x4c": 0x3F800000,
            "+0x64": 0x3E4CCCCD, "+0x68": 0x447A0000, "+0xb4": 1,
        },
        "byte_overrides": {"+0xad": 1, "+0xb0": 1},
    },
    {
        "name": "BonnetCam",
        "overrides": {
            "+0x10": 0x42B40000, "+0x14": 0x42B40000, "+0x18": 0x42B40000,
            "+0x2c": 0, "+0x30": 0x3ECCCCCD, "+0x34": 0xBECCCCCD,
            "+0x38": 0xBDBEDFA4, "+0x3c": 0, "+0x40": 0,
            "+0x44": 0x3F800000, "+0x48": 0x3F800000, "+0x4c": 0x3F800000,
            "+0x68": 0x44610000, "+0xb4": 1,
        },
        "byte_overrides": {"+0xad": 1, "+0xae": 1},
    },
    {
        "name": "CockpitCam",
        "overrides": {
            "+0x10": 0x43B40000, "+0x14": 0x43B40000, "+0x18": 0x43B40000,
            "+0x2c": 0, "+0x30": 0, "+0x34": 0,
            "+0x38": 0xBD8F5C29, "+0x3c": 0, "+0x40": 0,
            "+0x44": 0x3F800000, "+0x48": 0x3F800000, "+0x4c": 0x3F800000,
            "+0x68": 0x44480000, "+0xb4": 1,
        },
        "byte_overrides": {"+0xad": 1, "+0xae": 1},
    },
    {
        "name": "ChaseCam",
        "overrides": {
            "+0x10": 0x3FC66666, "+0x14": 0x40500000, "+0x18": 0,
            "+0x2c": 0, "+0x30": 0x3E19999A, "+0x34": 0x3E1FBE77,
            "+0x38": 0xBE4CCCCD, "+0x3c": 0, "+0x40": 0,
            "+0x50": 0x40900000, "+0x54": 0x3F8C0831,
            "+0x44": 0, "+0x48": 0x40000000, "+0x4c": 0x40800000,
            "+0x64": 0x3F800000, "+0x68": 0x44480000,
            "+0xb4": 2,
        },
        "byte_overrides": {"+0xb0": 1},
    },
    {
        "name": "ShotgunCam",
        "overrides": {
            "+0x10": 0x43B40000, "+0x14": 0x43B40000, "+0x18": 0x43B40000,
            "+0x2c": 0, "+0x30": 0, "+0x34": 0, "+0x38": 0xBC23D70A,
            "+0x3c": 0, "+0x40": 0,
            "+0x44": 0x3F800000, "+0x48": 0x3F800000, "+0x4c": 0x3F800000,
            "+0x68": 0x44480000, "+0xb4": 1,
        },
        "byte_overrides": {"+0xad": 1, "+0xae": 1, "+0xaf": 0},
    },
    {
        "name": "Local_Bow",
        "overrides": {
            "+0x10": 0x3FC66666, "+0x14": 0x40500000, "+0x18": 0,
            "+0x2c": 0, "+0x30": 0x3E19999A, "+0x34": 0x3E1FBE77,
            "+0x38": 0xBE4CCCCD, "+0x3c": 0x40490FDB, "+0x40": 0,
            "+0x50": 0x40900000, "+0x54": 0x3F8C0831,
            "+0x64": 0x3F800000, "+0x68": 0x44480000,
            "+0xb4": 2, "+0x44": 0, "+0x48": 0x40000000, "+0x4c": 0x40800000,
        },
        "byte_overrides": {"+0xaf": 0},
    },
    {
        "name": "Local_Starboard",
        "overrides": {
            "+0x10": 0x3FC66666, "+0x14": 0x40500000, "+0x18": 0,
            "+0x2c": 0, "+0x30": 0x3E19999A, "+0x34": 0x3E1FBE77,
            "+0x38": 0xBE4CCCCD, "+0x3c": None, "+0x40": 0,
            "+0x50": 0x40900000, "+0x54": 0x3F8C0831,
            "+0x64": 0x3F800000, "+0x68": 0x44480000,
            "+0xb4": 2, "+0x44": 0, "+0x48": 0x40000000, "+0x4c": 0x40800000,
        },
        "symbolic_overrides": {
            "+0x3c": "_DAT_00b8de1c + 3.1415927",
        },
        "byte_overrides": {"+0xaf": 0},
    },
    {
        "name": "Local_Port",
        "overrides": {
            "+0x10": 0x3FC66666, "+0x14": 0x40500000, "+0x18": 0,
            "+0x2c": 0, "+0x30": 0x3E19999A, "+0x34": 0x3E1FBE77,
            "+0x38": 0xBE4CCCCD, "+0x3c": None, "+0x40": 0,
            "+0x50": 0x40900000, "+0x54": 0x3F8C0831,
            "+0x64": 0x3F800000, "+0x68": 0x44480000,
            "+0xb4": 2, "+0x44": 0, "+0x48": 0x40000000, "+0x4c": 0x40800000,
        },
        "symbolic_overrides": {
            "+0x3c": "_DAT_00b8de1c",
        },
        "byte_overrides": {"+0xaf": 0},
    },
    {
        "name": "Local_Aft",
        "overrides": {
            "+0x10": 0x3FC66666, "+0x14": 0x40500000, "+0x18": 0,
            "+0x2c": 0, "+0x30": 0x3E19999A, "+0x34": 0x3E1FBE77,
            "+0x38": 0xBECCCCCD, "+0x3c": 0, "+0x40": 0,
            "+0x50": 0x40900000, "+0x54": 0x3F8C0831,
            "+0x64": 0x3F800000, "+0x68": 0x44480000,
            "+0xb4": 2, "+0x44": 0, "+0x48": 0x40000000, "+0x4c": 0x40800000,
        },
        "byte_overrides": {},
    },
)


def free_look_and_pitch_limits() -> dict[str, Any]:
    """Reproduce FUN_00810950's global limit writes plus FUN_00810710 names."""
    raw = {
        "FreeLookYawLimits": (0xC2700000, 0x42700000),
        "FreeLookPitchLimits": (0xC2200000, 0x41A00000),
        "RotateChaseCamPitchLimits": (0xC28C0000, 0x00000000),
    }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "global-camera-limits",
        "limits": {
            name: {
                "raw_bits": [a, b],
                "float_values": [f32_from_bits(a), f32_from_bits(b)],
            }
            for name, (a, b) in raw.items()
        },
        "property_offsets": {
            "FreeLookYawLimits": 0x2B8,
            "FreeLookPitchLimits": 0x2C0,
            "RotateChaseCamPitchLimits": 0x2C8,
        },
        "evidence": {
            "defaults": "FUN_00810950",
            "registration": "FUN_00810710",
        },
    }


def builtin_camera_preset_table() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "builtin-camera-presets",
        "baseline_constructor": "FUN_00823760",
        "presets": list(BUILTIN_PRESETS),
        "selection_order": [p["name"] for p in BUILTIN_PRESETS],
        "evidence": {
            "function": "FUN_00810950",
            "append_target": "+0x44 camera config list",
            "constructor": "FUN_00823760",
        },
        "limitations": [
            "offsets are preserved from ConfigSnapshot ABI; values are not assigned new gameplay semantics",
            "Local_Starboard/Local_Port dynamic values retain their global expression text",
        ],
    }
