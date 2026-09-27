"""Exact body point transforms implemented by FUN_007537b0 and FUN_00753810."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

FORMAT = "SHIFT.BodyPointTransformRuntime/1"
FUNCTION = "FUN_007537b0"
VARIANT = "FUN_00753810"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 749425
VARIANT_SOURCE_LINE = 749442

ANGULAR_X_OFFSET = 0x18
ANGULAR_Y_OFFSET = 0x20
ANGULAR_Z_OFFSET = 0x28
BODY_POSITION_X_OFFSET = 0x00
BODY_POSITION_Y_OFFSET = 0x08
BODY_POSITION_Z_OFFSET = 0x10
BODY_TRANSLATION_X_OFFSET = 0x78
BODY_TRANSLATION_Y_OFFSET = 0x80
BODY_TRANSLATION_Z_OFFSET = 0x88


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
class BodyTransform:
    angular: Vec3
    body_position: Vec3
    translation: Vec3


def _vec(values: Sequence[float], name: str) -> Vec3:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return Vec3(*(float(v) for v in values))


def cross_transform(angular: Vec3, point: Vec3, translation: Vec3) -> Vec3:
    return Vec3(
        point.z * angular.y - point.y * angular.z + translation.x,
        point.x * angular.z - angular.x * point.z + translation.y,
        angular.x * point.y - point.x * angular.y + translation.z,
    )


def transform_point(body: BodyTransform, point: Sequence[float]) -> Vec3:
    """Exact FUN_007537b0: angular x point + translation."""
    return cross_transform(body.angular, _vec(point, "point"), body.translation)


def transform_point_relative(body: BodyTransform, point: Sequence[float]) -> Vec3:
    """Exact FUN_00753810: angular x (point - body_position) + translation."""
    p = _vec(point, "point")
    relative = Vec3(
        p.x - body.body_position.x,
        p.y - body.body_position.y,
        p.z - body.body_position.z,
    )
    return cross_transform(body.angular, relative, body.translation)


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "variant": VARIANT,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "variant_source_line": VARIANT_SOURCE_LINE,
        "body_fields": {
            "angular": ["+0x18", "+0x20", "+0x28"],
            "body_position": ["+0x00", "+0x08", "+0x10"],
            "translation": ["+0x78", "+0x80", "+0x88"],
        },
        "fun_007537b0": {
            "formula": "angular x point + translation",
            "x": "point.z * angular.y - point.y * angular.z + translation.x",
            "y": "point.x * angular.z - angular.x * point.z + translation.y",
            "z": "angular.x * point.y - point.x * angular.y + translation.z",
        },
        "fun_00753810": {
            "preprocess": "point -= body_position",
            "formula": "angular x relative_point + translation",
        },
        "status": "instruction-stream exact cross-product transform; field semantics remain unnamed",
    }


__all__ = [
    "FORMAT", "FUNCTION", "VARIANT", "SOURCE_FILE", "SOURCE_LINE",
    "VARIANT_SOURCE_LINE", "ANGULAR_X_OFFSET", "ANGULAR_Y_OFFSET",
    "ANGULAR_Z_OFFSET", "BODY_POSITION_X_OFFSET", "BODY_POSITION_Y_OFFSET",
    "BODY_POSITION_Z_OFFSET", "BODY_TRANSLATION_X_OFFSET",
    "BODY_TRANSLATION_Y_OFFSET", "BODY_TRANSLATION_Z_OFFSET",
    "Vec3", "BodyTransform", "cross_transform", "transform_point",
    "transform_point_relative", "build_contract",
]
