"""Exact positive/negative body accumulator primitives from SHIFT.exe.c.

FUN_007baa70 and FUN_007baaf0 add or subtract a vector contribution from the
body linear accumulator (+0x60/+0x68/+0x70) and angular accumulator
(+0x48/+0x50/+0x58). The angular update is the cross product of the first
argument with the contribution vector.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFBodyImpulseRuntime/1"

ACCUMULATOR_OFFSETS = {
    "angular": ["+0x48", "+0x50", "+0x58"],
    "linear": ["+0x60", "+0x68", "+0x70"],
}


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly 3 components")
    return float(values[0]), float(values[1]), float(values[2])


def body_accumulator_delta(
    lever_arm: Sequence[float | int],
    contribution: Sequence[float | int],
    *,
    sign: int = 1,
) -> dict[str, Any]:
    """Return the exact six-channel delta of FUN_007baa70/baaf0."""
    if int(sign) not in (-1, 1):
        raise ValueError("sign must be +1 or -1")
    px, py, pz = _vec3(lever_arm, name="lever_arm")
    vx, vy, vz = _vec3(contribution, name="contribution")
    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "sign": int(sign),
        "lever_arm": [px, py, pz],
        "contribution": [vx, vy, vz],
        "linear_delta": [
            int(sign) * vx,
            int(sign) * vy,
            int(sign) * vz,
        ],
        "angular_delta": [
            int(sign) * (py * vz - pz * vy),
            int(sign) * (pz * vx - px * vz),
            int(sign) * (px * vy - py * vx),
        ],
        "storage_offsets": ACCUMULATOR_OFFSETS,
        "source_function": (
            "FUN_007baa70" if int(sign) == 1 else "FUN_007baaf0"
        ),
    }


def apply_body_accumulator_delta(
    state: Mapping[str, Sequence[float | int]],
    lever_arm: Sequence[float | int],
    contribution: Sequence[float | int],
    *,
    sign: int = 1,
) -> dict[str, Any]:
    """Apply the exact six-channel delta to a neutral body state mapping."""
    angular = [float(value) for value in state.get("angular", (0.0, 0.0, 0.0))]
    linear = [float(value) for value in state.get("linear", (0.0, 0.0, 0.0))]
    if len(angular) != 3 or len(linear) != 3:
        raise ValueError("state angular and linear values must both be vec3")

    delta = body_accumulator_delta(lever_arm, contribution, sign=sign)
    return {
        "format": "SHIFT.SDFBodyAccumulatorDeltaResult/1",
        "version": 1,
        "status": "applied",
        "ready": True,
        "angular": [
            angular[index] + delta["angular_delta"][index]
            for index in range(3)
        ],
        "linear": [
            linear[index] + delta["linear_delta"][index]
            for index in range(3)
        ],
        "delta": delta,
        "evidence": {
            "positive_helper": "FUN_007baa70",
            "negative_helper": "FUN_007baaf0",
            "angular_rule": "lever_arm x contribution",
            "linear_rule": "contribution",
        },
    }


def describe_sdf_body_impulse_primitives() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "positive": {
            "function": "FUN_007baa70",
            "sign": 1,
            "linear": "+contribution",
            "angular": "+(lever_arm x contribution)",
        },
        "negative": {
            "function": "FUN_007baaf0",
            "sign": -1,
            "linear": "-contribution",
            "angular": "-(lever_arm x contribution)",
        },
        "storage": ACCUMULATOR_OFFSETS,
        "callers": [
            "FUN_007bc680 -> FUN_007bac60",
            "FUN_007bc680 -> FUN_007bb090",
            "FUN_007bbb80",
        ],
        "limitations": [
            "The six accumulator channels retain source offsets; no force/torque unit is inferred.",
        ],
    }
