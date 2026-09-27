"""Evidence-backed PhysicsParticipant runtime facts from retail SHIFT.exe.c.

This module records the spawn configuration and control-flow boundary recovered
from FUN_0074d640, FUN_0074ddc3, FUN_0074e1a0 and FUN_0074e340.
"""
from __future__ import annotations
import struct
from typing import Any

FORMAT = "SHIFT.PhysicsParticipantRuntime/1"
SOURCE_FILE = ".\\Source\\System\\PhysicsParticipant.cpp"

MODES = {
    0: {"source": "FUN_0079c920", "apply": "FUN_007927c0", "finalize": "FUN_00792920"},
    1: {"source": "FUN_0079c970", "apply": "FUN_007927c0", "finalize": "FUN_00792920"},
    2: {"source": "FUN_0079c8f0", "apply": "FUN_007927c0", "finalize": "FUN_00792920"},
    3: {"source": "slot BArray via FUN_0074dc40/FUN_00773e10", "apply": "FUN_00793a80", "finalize": None},
    4: {"source": "config +0x28..+0x3c", "apply": "FUN_007927c0", "finalize": None},
}


def _f32(word: int) -> float:
    return struct.unpack("<f", struct.pack("<I", word & 0xFFFFFFFF))[0]


def build_config_evidence() -> dict[str, Any]:
    return {
        "format": "SHIFT.PhysicsParticipantConfigRuntime/1",
        "initializer": "FUN_0074d640",
        "source": SOURCE_FILE,
        "paths": {
            "cdf": {"field_offset": 0x04, "suffix": ".cdf"},
            "driver_head": {"field_offset": 0x08, "suffix": "driverhead.txt"},
        },
        "defaults": {
            "0x14": 0,
            "0x18_raw": 0x3F570A3D,
            "0x18_f32": _f32(0x3F570A3D),
            "0x1c_raw": 0xBE4CCCCD,
            "0x1c_f32": _f32(0xBE4CCCCD),
        },
        "status": "field-level evidence only",
    }


def build_spawn_evidence() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "source": SOURCE_FILE,
        "functions": ["FUN_0074d640", "FUN_0074ddc3", "FUN_0074e1a0", "FUN_0074e340"],
        "input_offsets": {
            "mode": 0x1C,
            "type_or_role_unknown": 0x10,
            "parameter": 0x20,
            "position": [0x28, 0x2C, 0x30],
            "rotation": [0x34, 0x38, 0x3C],
            "flags": [0x0C, 0x68, 0x69, 0x6C, 0x70],
        },
        "modes": MODES,
        "common_calls": [
            "FUN_00797fd0(vehicle+0x340, index, 0, 1)",
            "FUN_00798df0(vehicle+0x340, flag)",
            "FUN_007b8ed0(vehicle+0x700)",
            "FUN_0074d4a0(participant, config+0x0c, 0)",
            "FUN_007839f0(vehicle+0x340, config+0x68, config+0x69, config+0x6c, config+0x70)",
        ],
        "post_calls": [
            "FUN_00746e50(vehicle, physics+700, mode, config+0x20, 1.4013e-45)",
            "FUN_0073d790(vehicle, 1)",
        ],
        "mode_3_extra": [
            "FUN_00728670(vehicle, FUN_0074dc50(FUN_00773e10()+0x354, slot))",
            "FUN_00713f40(&DAT_00c109e0, slot, state, 1)",
            "FUN_00713ec0(&DAT_00c109e0, slot, state)",
        ],
        "non_mode_3_extra": "FUN_0073bcc0(vehicle)",
        "observable": {
            "zero_xz_log": "Car %d tried to spawn at 0,0,0 - was attempting to spawn to grid spot %d",
            "ready_byte_offset": 0x4E,
            "registration_ready_byte_offset": 0x4F,
            "registration_active_byte_offset": 0x4D,
        },
        "unknowns": [
            "semantic meaning of mode values 0..4",
            "transform conventions of FUN_0079c920/970/8f0/9c0",
            "semantic meaning of helper calls and numeric participant fields",
        ],
    }
