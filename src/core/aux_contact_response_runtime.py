"""Exact auxiliary contact-response kernel implemented by FUN_00758fc0.

The phase preserves the record fields and transform calls as external boundaries.
It reconstructs the proven scalar/vector arithmetic once the transformed anchor
has been produced.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

FORMAT = "SHIFT.AuxContactResponseRuntime/1"
FUNCTION = "FUN_00758fc0"
CALLER = "FUN_00766510"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 753230

RECORD_POINT_OFFSET = 0x68
RECORD_DIRECTIONAL_CURVE_OFFSET = 0x48
RECORD_GAIN_OFFSET = 0x38
RECORD_SCALE_OFFSET = 0x40
ACTIVE_FLAG_OFFSET = 0x00
BODY_BASE_OFFSET = 0x33A0
BODY_TRANSFORM_OFFSET = 0xD4

OUTPUT_X = 0.0


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (self.x, self.y, self.z)):
            raise ValueError("vector values must be finite")

    def as_tuple(self) -> tuple[float, float, float]:
        return (float(self.x), float(self.y), float(self.z))


@dataclass(frozen=True)
class AuxContactResponse:
    active: bool
    relative_point: Vec3
    square_negative_z: float
    directional_multiplier: float
    local_response: Vec3
    point_source_offset: int = RECORD_POINT_OFFSET
    curve_source_offset: int = RECORD_DIRECTIONAL_CURVE_OFFSET
    gain_source_offset: int = RECORD_GAIN_OFFSET
    scale_source_offset: int = RECORD_SCALE_OFFSET


def build_local_response(
    *,
    record_active: bool,
    transformed_record_point: Sequence[float],
    reference_point: Sequence[float],
    directional_multiplier: float,
    gain: float,
    scale: float,
) -> AuxContactResponse:
    """Reconstruct the scalar/vector stage after the external transforms."""
    if len(transformed_record_point) != 3 or len(reference_point) != 3:
        raise ValueError("points must contain exactly three values")
    point = Vec3(*(float(v) for v in transformed_record_point))
    reference = Vec3(*(float(v) for v in reference_point))
    directional_multiplier = float(directional_multiplier)
    gain = float(gain)
    scale = float(scale)
    if not all(isfinite(v) for v in (directional_multiplier, gain, scale)):
        raise ValueError("response scalars must be finite")

    relative = Vec3(
        point.x - reference.x,
        point.y - reference.y,
        point.z - reference.z,
    )
    if not record_active or relative.z >= 0.0:
        return AuxContactResponse(
            active=record_active,
            relative_point=relative,
            square_negative_z=0.0,
            directional_multiplier=directional_multiplier,
            local_response=Vec3(0.0, 0.0, 0.0),
        )

    square = relative.z * relative.z
    local_response = Vec3(
        OUTPUT_X,
        directional_multiplier * gain * square,
        scale * square,
    )
    return AuxContactResponse(
        active=True,
        relative_point=relative,
        square_negative_z=square,
        directional_multiplier=directional_multiplier,
        local_response=local_response,
    )


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "caller": CALLER,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "record": {
            "active_flag_offset": "+0x00",
            "point_offset": "+0x68",
            "directional_curve_offset": "+0x48",
            "gain_offset": "+0x38",
            "scale_offset": "+0x40",
        },
        "body": {
            "base_offset": "+0x33a0",
            "transform_context": "+0xd4",
        },
        "external_transforms": {
            "first": "FUN_007aefb0(body + 0xd4, record + 0x68, local_78)",
            "second": "FUN_007537b0(body, local_78, local_a8)",
            "third": "FUN_007af0a0(body + 0xd4, local_a8, local_28)",
        },
        "relative_vector": {
            "x": "local_28 - reference.x",
            "y": "local_20 - reference.y",
            "z": "local_18 - reference.z",
        },
        "gate": "record active AND relative.z < 0",
        "response": {
            "x": 0.0,
            "y": "FUN_00755340(record + 0x48, relative.x, relative.z) * (record + 0x38) * relative.z^2",
            "z": "(record + 0x40) * relative.z^2",
        },
        "application": {
            "transform": "FUN_007aefb0(body + 0xd4, local_response, local_90)",
            "consumer": "FUN_007baa70(body, local_78, local_90)",
        },
        "caller_instances": {
            "first": "this + 0x37d8",
            "second": "this + 0x3858",
            "stride": "0x80",
        },
        "unresolved": [
            "semantic name and physical units of all record fields",
            "FUN_007537b0 semantics",
            "FUN_00755340 physical interpretation in this consumer",
        ],
        "status": "instruction-stream exact arithmetic after external coordinate transforms",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "CALLER",
    "SOURCE_FILE",
    "SOURCE_LINE",
    "RECORD_POINT_OFFSET",
    "RECORD_DIRECTIONAL_CURVE_OFFSET",
    "RECORD_GAIN_OFFSET",
    "RECORD_SCALE_OFFSET",
    "ACTIVE_FLAG_OFFSET",
    "BODY_BASE_OFFSET",
    "BODY_TRANSFORM_OFFSET",
    "Vec3",
    "AuxContactResponse",
    "build_local_response",
    "build_contract",
]
