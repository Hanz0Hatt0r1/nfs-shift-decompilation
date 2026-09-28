"""Evidence-backed StaticCamera data runtime.

Recovered from FUN_00813180, FUN_00813300, FUN_00813500, FUN_00813550 and
FUN_008156b0. Property registration preserves the executable's overlapping
ShakeFrequency/ShakeScreenVelocity offsets rather than normalizing them.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.StaticCameraRuntime/1"


def static_camera_defaults() -> dict[str, Any]:
    """Expose exact raw default fields from FUN_00813180."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-defaults",
        "vtable": "PTR_FUN_00b15d08",
        "raw": {
            "+0x64": 0x3F490FDB,
            "+0x68": 1,
            "+0x6c": 0x3F800000,
            "+0x70": 0x443B8000,
            "+0x78": 6,
            "+0x80": 6,
            "+0x84": 0,
            "+0x88": 0,
            "+0x8c": 0,
            "+0x90": 0,
            "+0x94": 0,
            "+0x98": 0,
            "+0x9c": 0x41400000,
            "+0xa0": 0,
            "+0xa4": 0x40800000,
            "+0xa8": 0x41A00000,
            "+0xac": 0x41A00000,
            "+0xb0": 0x42200000,
            "+0xb4": 0,
            "+0xb8": 0x41400000,
            "+0xbc": 0,
            "+0xc0": 0,
            "+0xc8": 0x3F800000,
            "+0xd0": 0x3F800000,
            "+0xe0": 0,
        },
        "integer_defaults": {
            "+0x1d": 0xFFFFFFFF,
            "+0x1f": 0xFFFFFFFF,
            "+0x1e": 6,
            "+0x20": 6,
        },
        "string_defaults": {
            "+0x33": "",
            "+0x35": "",
            "+0x37": "",
        },
        "evidence": {"function": "FUN_00813180"},
    }



def describe_static_camera_constructor() -> dict[str, Any]:
    """Reproduce FUN_00814f60's derived StaticCamera initialization."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-constructor",
        "actions": [
            {"action": "FUN_0081aeb0"},
            {"action": "write vtable", "value": "PTR_FUN_00b15d60"},
            {"action": "FUN_00814460", "target": "+0x48"},
            {"action": "FUN_00675c60", "target": "+0x140"},
            {"action": "FUN_00812c00", "target": "+0x260..+0x278"},
            {"action": "FUN_00823a80", "target": "+0x84", "rate_bits": 0x40C00000},
            {"action": "FUN_00823ab0", "target": "+0x84", "target_bits": [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A]},
            {"action": "FUN_00823a80", "target": "+0xD8", "rate_bits": 0x41800000},
            {"action": "FUN_00823ab0", "target": "+0xD8", "target_bits": [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A]},
        ],
        "writes": {
            "+0x3c": 0x3F000000,
            "+0x48..+0x60": [0] * 7,
            "+0x260..+0x278": [0] * 7,
        },
        "shake": {
            "+0x84": {"rate": 0x40C00000, "target": [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A]},
            "+0xD8": {"rate": 0x41800000, "target": [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A]},
        },
        "evidence": {"function": "FUN_00814f60"},
    }


def describe_static_camera_reset() -> dict[str, Any]:
    """Reproduce FUN_00815070."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-reset",
        "actions": [
            {"action": "FUN_00813f70"},
            {"action": "FUN_00886930", "condition": "param_1 & 1"},
        ],
        "evidence": {"function": "FUN_00815070"},
    }


def set_static_camera_runtime_pair(
    *,
    pair_a: Sequence[Any],
    pair_b: Sequence[Any],
    target_pair_a_offset: str = "+0x324/+0x328",
    target_pair_b_offset: str = "+0x32c/+0x330",
) -> dict[str, Any]:
    if len(pair_a) != 2 or len(pair_b) != 2:
        raise ValueError("each runtime pair requires exactly two values")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "runtime-pair-set",
        "writes": {
            target_pair_a_offset: list(pair_a),
            target_pair_b_offset: list(pair_b),
        },
        "evidence": {
            "functions": ["FUN_00815ee0", "FUN_00815f00"],
        },
    }


def set_static_camera_function_bindings(
    *,
    slot_380: Any,
    slot_384: Any,
    slot_388: Any,
    slot_34c: Any,
) -> dict[str, Any]:
    """Trace FUN_00815f20/F30/F40/FE0 setters."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "function-binding-set",
        "writes": {
            "+0x380": slot_380,
            "+0x384": slot_384,
            "+0x388": slot_388,
            "+0x34c": slot_34c,
        },
        "evidence": {
            "functions": ["FUN_00815f20", "FUN_00815f30", "FUN_00815f40", "FUN_00815fe0"],
        },
    }


def copy_static_camera_runtime_payload(
    *,
    destination: str,
    source: str,
) -> dict[str, Any]:
    """Reproduce FUN_00815eb0's two-stage StaticCamera copy path."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-runtime-copy",
        "actions": [
            {
                "action": "FUN_0081af70",
                "destination": destination,
                "source": source,
            },
            {
                "action": "FUN_00815620",
                "destination": f"{destination}+0x48",
                "source": f"{source}+0x48",
            },
        ],
        "evidence": {
            "function": "FUN_00815eb0",
            "base_copy": "FUN_0081af70",
            "camera_data_copy": "FUN_00815620",
            "camera_data_offset": "+0x48",
        },
    }


def copy_config_record(
    source_words: Mapping[int, Any],
) -> dict[str, Any]:
    """Reproduce FUN_00812a00's exact 25-dword copy range."""
    offsets = [i * 4 for i in range(25)]
    missing = [offset for offset in offsets if offset not in source_words]
    if missing:
        raise ValueError(f"missing config-record offsets: {missing}")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "config-record-copy",
        "count": 25,
        "range": ["+0x00", "+0x60"],
        "values": {f"+0x{offset:02x}": source_words[offset] for offset in offsets},
        "evidence": {"function": "FUN_00812a00"},
    }


def copy_static_camera_state(
    source: Mapping[int, Any],
) -> dict[str, Any]:
    """Reproduce FUN_00813300's field-by-field copy boundary."""
    copy_offsets = list(range(0x10, 0x30, 4)) + [0x60] + list(range(0x64, 0xC9, 4))
    copy_offsets += [0xCC, 0xD0, 0xDC] + list(range(0xE0, 0xF0, 4))
    missing = [offset for offset in copy_offsets if offset not in source]
    if missing:
        raise ValueError(f"missing static-camera source offsets: {missing}")

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-copy",
        "copied_offsets": [f"+0x{o:02x}" for o in copy_offsets],
        "string_helpers": ["+0x60", "+0xcc", "+0xdc"],
        "special_writes": {
            "+0xd8": 0xFFFFFFFF,
        },
        "evidence": {
            "function": "FUN_00813300",
            "vtable": "PTR_FUN_00b15d08",
        },
    }


def reset_static_camera_state(*, destroy_flag: int | None = None) -> dict[str, Any]:
    """Reproduce FUN_00813500 reset/destruction boundary."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-reset",
        "actions": [
            {"action": "write vtable", "value": "PTR_FUN_00b15d08"},
            {
                "action": "FUN_00688010",
                "target": "+0x2c",
                "argument": destroy_flag,
            },
            {"action": "FUN_006310c0", "target": "+0xdc"},
            {"action": "FUN_006310c0", "target": "+0xd4"},
            {"action": "FUN_006310c0", "target": "+0xcc"},
            {"action": "FUN_006310c0", "target": "+0x60"},
            {"action": "FUN_004f0050", "target": "+0x2c"},
            {"action": "FUN_006383f0", "target": "base object"},
        ],
        "evidence": {
            "function": "FUN_00813500",
            "released_strings": ["+0x60", "+0xcc", "+0xd4", "+0xdc"],
        },
    }


def static_camera_property_registration() -> dict[str, Any]:
    """Reproduce FUN_008156b0 property registrations exactly as emitted."""
    properties = [
        ("Pos", 0x10, 0x20),
        ("QuatOri", 0x19, 0x10),
        ("FOV", 10, 0x64),
        ("Type", 3, 0x68),
        ("NearZ", 10, 0x6C),
        ("FarZ", 10, 0x70),
        ("Target", 0x0D, 0x78),
        ("LookAt", 0x0D, 0x80),
        ("TargetOffset", 0x10, 0x84),
        ("LookAtOffset", 0x10, 0x90),
        ("ProximityShakeFrequency", 10, 0x9C),
        ("ProximityShakeMagnitude", 10, 0xA0),
        ("ProximityShakeMinDistance", 10, 0xA4),
        ("ProximityShakeMaxDistance", 10, 0xA8),
        ("ProximityShakeMinSpeed", 10, 0xAC),
        ("ProximityShakeMaxSpeed", 10, 0xB0),
        ("ShakeMagnitude", 10, 0xC0),
        ("ShakeMagnitudeMin", 10, 0xBC),
        ("ShakeFrequency", 10, 0xB8),
        ("ShakeFrequencyMin", 10, 0xB4),
        ("ShakeScreenVelocity", 10, 0xB8),
        ("ShakeScreenVelocityMin", 10, 0xB4),
        ("SoundEffect", 0, 0xCC),
        ("LODDistanceMultiplier", 10, 0xD0),
        ("OverridedBy", 0, 0xD4),
        ("UserDataName", 0, 0xDC),
        ("UserDataValue", 10, 0xE0),
        ("ActiveAreas", 6, 0x2C),
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-property-registration",
        "registration_object": "DAT_00b8ded8",
        "properties": [
            {
                "name": name,
                "type_id": type_id,
                "offset": offset,
                "flags": 3,
            }
            for name, type_id, offset in properties
        ],
        "evidence": {
            "function": "FUN_008156b0",
            "registration_helper": "FUN_0063a280",
        },
        "limitations": [
            "The executable intentionally/observably registers both ShakeFrequency and ShakeScreenVelocity at +0xb8",
            "The executable intentionally/observably registers both minimum fields at +0xb4",
        ],
    }


def interpolate_static_camera_records(
    *,
    first: Sequence[float],
    second: Sequence[float],
    alpha: float,
    wrap_y_first: float = 0.0,
    wrap_y_second: float = 0.0,
) -> dict[str, Any]:
    """Reproduce the vector interpolation part of FUN_008135b0."""
    if len(first) != 3 or len(second) != 3:
        raise ValueError("first and second require three values")
    t = float(alpha)
    a = list(map(float, first))
    b = list(map(float, second))
    # The source removes an integer multiple of eight from each Y sample before
    # interpolation. The rounded integer is supplied as the helper-side value.
    y0 = a[1] - float(wrap_y_first) * 8.0
    y1 = b[1] - float(wrap_y_second) * 8.0
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-interpolate",
        "value": [
            (1.0 - t) * a[0] + t * b[0],
            (1.0 - t) * y0 + t * y1,
            (1.0 - t) * a[2] + t * b[2],
        ],
        "evidence": {
            "function": "FUN_008135b0",
            "first_record": "index 0",
            "second_record": "index 1",
            "y_wrap_period": 8.0,
        },
        "limitations": [
            "FUN_00813550/FUN_00702540 record lookup is not reimplemented",
            "the rounded-Y helper values are caller-supplied",
        ],
    }



def resolve_static_camera_record(
    *,
    source_pointer: Any | None,
    record_helper_success: bool,
    record_snapshot: Mapping[int, Any] | None = None,
) -> dict[str, Any]:
    """Reproduce FUN_00813550's indexed record lookup/copy boundary."""
    if source_pointer in (None, 0) or not record_helper_success:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "static-camera-record-lookup",
            "status": "unavailable",
            "output": None,
            "actions": [
                {
                    "action": "FUN_00702540",
                    "result": False,
                }
            ],
        }
    snapshot = dict(record_snapshot or {})
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-record-lookup",
        "status": "resolved",
        "output": snapshot,
        "actions": [
            {"action": "FUN_00702540", "result": True},
            {"action": "FUN_00812a00", "source": "local record snapshot"},
            {"action": "write +0x64", "value": 0},
        ],
        "evidence": {
            "function": "FUN_00813550",
            "source_selection": "this + param_2*4",
            "record_copy": "FUN_00812a00",
            "output_aux": "+0x64",
        },
    }


def blend_static_camera_records(
    *,
    first_value: Sequence[float],
    second_value: Sequence[float],
    alpha: float,
    first_wrap_count: int = 0,
    second_wrap_count: int = 0,
) -> dict[str, Any]:
    """Reproduce FUN_008135b0's exact three-component blend."""
    if len(first_value) != 3 or len(second_value) != 3:
        raise ValueError("first_value and second_value require three values")
    t = float(alpha)
    a = list(map(float, first_value))
    b = list(map(float, second_value))
    first_y = a[1] - abs(int(first_wrap_count)) * 8.0
    second_y = b[1] - abs(int(second_wrap_count)) * 8.0
    value = [
        (1.0 - t) * a[0] + t * b[0],
        (1.0 - t) * first_y + t * second_y,
        (1.0 - t) * a[2] + t * b[2],
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-blend",
        "alpha": t,
        "value": value,
        "evidence": {
            "function": "FUN_008135b0",
            "first_record": "index 0",
            "second_record": "index 1",
            "y_wrap_period": 8.0,
            "y_wrap_operation": "subtract abs(integer_count) * 8",
        },
    }
