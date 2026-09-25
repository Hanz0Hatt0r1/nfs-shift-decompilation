"""Exact CCameraView noise-state advance from FUN_0081caf0.

The function normalizes profile time through FUN_0081c090, multiplies it by
camera-data +0xb8, feeds that scalar to FUN_006bbf10 at +0xd8, then scales the
result by profile +0xa0 and advances the same state with FUN_00823a80.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.CameraNoiseStateRuntime/1"


def advance_camera_noise_state(
    *,
    normalized_time: float,
    noise_scale: float,
    profile_scale: float,
    accumulator_before: Any = None,
) -> dict[str, Any]:
    """Reproduce FUN_0081caf0 after FUN_0081c090 has resolved time."""
    normalized = float(normalized_time)
    scale = float(noise_scale)
    frequency = normalized * scale
    amplitude = float(profile_scale) * frequency
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "advance-noise-state",
        "frequency": frequency,
        "amplitude": amplitude,
        "accumulator_before": accumulator_before,
        "actions": [
            {
                "action": "FUN_006bbf10",
                "target": "+0xd8",
                "value": frequency,
            },
            {
                "action": "FUN_00823a80",
                "target": "+0xd8",
                "value": amplitude,
            },
        ],
        "evidence": {
            "function": "FUN_0081caf0",
            "normalized_time_source": "FUN_0081c090",
            "noise_scale": "+0xb8",
            "profile_amplitude": "+0xa0",
            "noise_state": "+0xd8",
        },
        "limitations": [
            "FUN_006bbf10 and FUN_00823a80 retain their runtime state semantics",
        ],
    }


def resolve_and_advance_camera_noise(
    *,
    sample_time: float,
    profile_start: float,
    profile_end: float,
    noise_scale: float,
    profile_scale: float,
) -> dict[str, Any]:
    """Compose the exact c090 normalization and caf0 scalar operations."""
    from camera_view_profile_runtime import normalized_profile_time

    normalized = normalized_profile_time(
        sample_time=sample_time,
        profile_start=profile_start,
        profile_end=profile_end,
    )
    result = advance_camera_noise_state(
        normalized_time=normalized,
        noise_scale=noise_scale,
        profile_scale=profile_scale,
    )
    return {
        **result,
        "normalized_time": normalized,
        "evidence": {
            **result["evidence"],
            "composed_with": "FUN_0081c090",
        },
    }
