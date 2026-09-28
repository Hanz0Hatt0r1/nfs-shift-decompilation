"""Exact wheel contact-angle factor used by FUN_00765c40.

FUN_00758ad0 is fully recoverable from the retail instruction stream:
abs(input) - global_threshold * 0.5, clamp to [0, 6], convert to radians
through pi/6, evaluate cosine, then return:
    cos(angle) * 0.02500000037252903 + 0.9750000238418579

The global threshold at 0xc10f94 remains a runtime input because it is not a
literal constant in the recovered binary.

FUN_00765c40 stores the result for four wheel records at +0xa78 with 0x150
byte stride and stores a previous/reference value at +0xa70.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite
import struct
from typing import Sequence

FORMAT = "SHIFT.WheelContactFactorRuntime/1"
FUNCTION = "FUN_00758ad0"
CALLER = "FUN_00765c40"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 753056

THRESHOLD_GLOBAL_OFFSET = 0xC10F94
PREVIOUS_VALUE_BASE = 0xA70
FACTOR_VALUE_BASE = 0xA78
WHEEL_STRIDE = 0x150
WHEEL_COUNT = 4

HALF_SCALE = 0.5
ANGLE_LIMIT = 6.0
ANGLE_PI_NUMERATOR = 3.1415927410125732
ANGLE_PI_DENOMINATOR = 6.0
COS_SCALE = 0.02500000037252903
COS_BIAS = 0.9750000238418579


@dataclass(frozen=True)
class WheelContactFactor:
    wheel_index: int
    projected_value: float
    pre_clamp: float
    clamped_value: float
    angle_radians: float
    cosine: float
    factor: float
    previous_value: float
    wheel_factor_offset: int
    previous_value_offset: int


def float32(value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ValueError("value must be finite")
    return struct.unpack("<f", struct.pack("<f", value))[0]


def compute_contact_factor(
    *,
    projected_value: float,
    threshold_value: float,
) -> WheelContactFactor:
    value = float(projected_value)
    threshold = float(threshold_value)
    if not isfinite(value) or not isfinite(threshold):
        raise ValueError("projected_value and threshold_value must be finite")

    pre_clamp = abs(value) - threshold * HALF_SCALE
    clamped = min(ANGLE_LIMIT, max(0.0, pre_clamp))
    angle = clamped * ANGLE_PI_NUMERATOR / ANGLE_PI_DENOMINATOR
    cosine = cos(angle)
    factor = float32(cosine * COS_SCALE + COS_BIAS)
    return WheelContactFactor(
        wheel_index=-1,
        projected_value=value,
        pre_clamp=pre_clamp,
        clamped_value=clamped,
        angle_radians=angle,
        cosine=cosine,
        factor=factor,
        previous_value=0.0,
        wheel_factor_offset=FACTOR_VALUE_BASE,
        previous_value_offset=PREVIOUS_VALUE_BASE,
    )


def build_four_wheel_contact_factors(
    projected_values: Sequence[float],
    *,
    threshold_value: float,
    enabled: bool,
    frame_equal: bool,
    frame_reference: float,
) -> tuple[WheelContactFactor, ...]:
    if len(projected_values) != WHEEL_COUNT:
        raise ValueError("exactly four projected values are required")
    threshold = float(threshold_value)
    reference = float(frame_reference)
    if not isfinite(threshold) or not isfinite(reference):
        raise ValueError("threshold_value and frame_reference must be finite")

    previous = reference if frame_equal else 0.0
    rows = []
    for index, value in enumerate(projected_values):
        result = compute_contact_factor(
            projected_value=value,
            threshold_value=threshold,
        ) if enabled else None
        factor = 1.0 if result is None else result.factor
        row = WheelContactFactor(
            wheel_index=index,
            projected_value=float(value),
            pre_clamp=0.0 if result is None else result.pre_clamp,
            clamped_value=0.0 if result is None else result.clamped_value,
            angle_radians=0.0 if result is None else result.angle_radians,
            cosine=1.0 if result is None else result.cosine,
            factor=factor,
            previous_value=previous,
            wheel_factor_offset=FACTOR_VALUE_BASE + index * WHEEL_STRIDE,
            previous_value_offset=PREVIOUS_VALUE_BASE + index * WHEEL_STRIDE,
        )
        rows.append(row)
    return tuple(rows)


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "caller": CALLER,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "input": {
            "threshold_global": "DAT_00c10f94",
            "threshold_offset": THRESHOLD_GLOBAL_OFFSET,
        },
        "helper_arithmetic": {
            "pre_clamp": "abs(input) - threshold * 0.5",
            "clamp": "[0, 6]",
            "angle": "clamped * 3.1415927410125732 / 6.0",
            "cosine": "FUN_00900b10(angle) reaches x87 FCOS",
            "factor": "float32(cosine * 0.02500000037252903 + 0.9750000238418579)",
        },
        "four_wheel_storage": {
            "previous_base": PREVIOUS_VALUE_BASE,
            "factor_base": FACTOR_VALUE_BASE,
            "stride": WHEEL_STRIDE,
            "count": WHEEL_COUNT,
            "previous_when_global_equal": "DAT_00c12c38",
            "previous_when_global_not_equal": 0.0,
            "disabled_factor": 1.0,
        },
        "status": "instruction-stream backed exact helper arithmetic and four-wheel storage topology",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "CALLER",
    "SOURCE_LINE",
    "THRESHOLD_GLOBAL_OFFSET",
    "PREVIOUS_VALUE_BASE",
    "FACTOR_VALUE_BASE",
    "WHEEL_STRIDE",
    "WHEEL_COUNT",
    "HALF_SCALE",
    "ANGLE_LIMIT",
    "ANGLE_PI_NUMERATOR",
    "ANGLE_PI_DENOMINATOR",
    "COS_SCALE",
    "COS_BIAS",
    "WheelContactFactor",
    "float32",
    "compute_contact_factor",
    "build_four_wheel_contact_factors",
    "build_contract",
]
