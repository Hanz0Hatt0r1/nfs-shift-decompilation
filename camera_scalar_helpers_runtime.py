"""Exact scalar camera-control helpers from FUN_0081b820 and FUN_0081b8a0.

These functions operate on a signed input value with a dead-zone threshold.
The second helper only emits its correction when the computed correction would
cross the input sign; this is preserved literally without assigning a gameplay
name.
"""

from __future__ import annotations

import math
from typing import Any

FORMAT = "SHIFT.CameraScalarHelpersRuntime/1"


def signed_unit(value: float) -> float:
    """Return the source-compatible sign classification for a non-NaN float."""
    value = float(value)
    if value > 0.0:
        return 1.0
    if value < 0.0:
        return -1.0
    return 0.0


def deadzone_response(
    value: float,
    bias: float,
    threshold: float,
    gain: float,
    bias_scale: float,
) -> dict[str, Any]:
    """Reproduce FUN_0081b820 exactly."""
    x = float(value)
    magnitude_minus_threshold = abs(x) - float(threshold)
    if magnitude_minus_threshold <= 0.0:
        result = 0.0
    else:
        sign = signed_unit(x)
        result = -sign * magnitude_minus_threshold * float(gain) - float(bias) * float(bias_scale)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "deadzone-response",
        "result": result,
        "intermediate": {
            "abs_minus_threshold": magnitude_minus_threshold,
            "sign": signed_unit(x),
        },
        "evidence": {
            "function": "FUN_0081b820",
            "expression": "-sign*(abs(value)-threshold)*gain - bias*bias_scale",
        },
    }


def corrective_response(
    value: float,
    bias: float,
    threshold: float,
    gain: float,
    bias_scale: float,
) -> dict[str, Any]:
    """Reproduce FUN_0081b8a0 including its sign-reversal acceptance test."""
    x = float(value)
    overshoot = abs(x) - float(threshold)
    if overshoot <= 0.0:
        result = 0.0
        candidate = 0.0
        accepted = False
    else:
        sign = signed_unit(x)
        candidate = -sign * overshoot * float(gain) - float(bias) * float(bias_scale)
        candidate_sign = signed_unit(candidate)
        accepted = not math.isnan(candidate) and candidate_sign != 0.0 and candidate_sign != sign
        result = candidate if accepted else 0.0
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "corrective-response",
        "result": result,
        "candidate": candidate,
        "accepted": accepted,
        "intermediate": {
            "abs_minus_threshold": overshoot,
            "input_sign": signed_unit(x),
        },
        "evidence": {
            "function": "FUN_0081b8a0",
            "acceptance_condition": "candidate sign differs from input sign",
        },
    }
