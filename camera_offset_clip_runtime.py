"""Evidence-backed camera offset/clip helper FUN_00820bc0.

The function:
- consumes TrackingCamera state at +0x128..+0x138,
- derives a scalar from FUN_009030d0/FUN_00902770,
- calls FUN_00820a80 and FUN_0081f370 to constrain an offset,
- transforms and blends a point into the camera matrix state at +0x2f0..+0x2fc,
- maintains timer/blend state +0x300/+0x304/+0x308,
- and applies a final direction-dependent scalar offset.

Matrix/distance helper results remain opaque inputs.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraOffsetClipRuntime/1"


def compute_tracking_offset_scalar(
    *,
    camera_fov: float,
    tracking_magnitude: float,
    helper_9030d0: float,
    helper_902770: float,
) -> dict[str, Any]:
    """Reproduce the nested scalar replacement sequence in FUN_00820bc0."""
    half_fov = float(camera_fov) * 0.5
    scaled = float(helper_9030d0) * abs(float(tracking_magnitude))
    resolved = float(helper_902770)
    offset_scalar = resolved * 2.0
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-offset-scalar",
        "half_fov": half_fov,
        "scaled_magnitude": scaled,
        "resolved_scalar": resolved,
        "offset_scalar": offset_scalar,
        "evidence": {
            "function": "FUN_00820bc0",
            "fov_source": "+0x34",
            "tracking_magnitude": "+0x128",
            "helper_a": "FUN_009030d0",
            "helper_b": "FUN_00902770",
        },
    }


def clip_camera_offset(
    *,
    initial_lower: float,
    initial_upper: float,
    clipped_lower: float,
    clipped_upper: float,
    positive_tracking_magnitude: bool,
) -> dict[str, Any]:
    """Trace FUN_0081f370 result selection used by FUN_00820bc0."""
    selected = float(clipped_lower) if positive_tracking_magnitude else float(clipped_upper)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "clip-camera-offset",
        "initial_bounds": [float(initial_lower), float(initial_upper)],
        "clipped_bounds": [float(clipped_lower), float(clipped_upper)],
        "positive_tracking_magnitude": bool(positive_tracking_magnitude),
        "selected_offset": selected,
        "evidence": {
            "caller": "FUN_00820bc0",
            "clip_helper": "FUN_0081f370",
            "positive_branch": "tracking +0x128 > 0 -> lower bound",
        },
    }


def describe_camera_offset_blend(
    *,
    transformed_point: Sequence[float],
    direction: Sequence[float],
    prior_matrix_quaternion: Sequence[float],
    depth_w: float,
    blend_source: float,
    camera_offset: float,
    tracking_frequency: float,
    tracking_correction_speed: float,
    tracking_ratio: float,
    current_300: float,
    current_304: float,
    current_308: float,
    delta: float,
    helper_eb20_reset: float = 0.0,
    helper_9_02e40: float = 0.0,
    blended_quaternion: Sequence[float] | None = None,
    final_inverse_transformed_point: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Reproduce the state/update arithmetic in FUN_00820bc0."""
    if len(transformed_point) != 3:
        raise ValueError("transformed_point requires three values")
    if len(direction) != 3:
        raise ValueError("direction requires three values")
    if len(prior_matrix_quaternion) != 4:
        raise ValueError("prior_matrix_quaternion requires four values")

    point = [float(v) for v in transformed_point]
    dirv = [float(v) for v in direction]
    f = float(blend_source)
    depth = float(depth_w)
    if depth <= 0.0:
        normalized_point = [0.0, 0.0, 0.0, 1.0]
    else:
        normalized_point = [
            point[0] / depth,
            point[1] / depth,
            point[2] / depth,
            1.0,
        ]

    mix_factor = 1.0 - float(tracking_correction_speed)
    blend = [
        normalized_point[i] * mix_factor
        for i in range(4)
    ]
    prior = [float(v) for v in prior_matrix_quaternion]
    if blended_quaternion is None:
        blended = [
            prior[i] * f + blend[i]
            for i in range(4)
        ]
    else:
        if len(blended_quaternion) != 4:
            raise ValueError("blended_quaternion requires four values")
        blended = [float(v) for v in blended_quaternion]

    scaled_time = float(delta)
    timer = float(current_308) - scaled_time
    timer_reset = False
    updated_304 = float(current_304)
    if timer < 0.0:
        updated_304 = float(helper_eb20_reset)
        timer = 1.0 / float(tracking_ratio) if float(tracking_ratio) != 0.0 else 0.0
        timer_reset = True

    local_1c = 1.0
    if float(tracking_frequency) != 0.0 and float(delta) != 0.0:
        local_1c = max(1.0, 1.0 / (float(tracking_frequency) * float(delta)))

    inverse_factor = 1.0 / local_1c
    blended_scalar = (
        (1.0 - float(helper_9_02e40)) * updated_304
        + float(current_300) * float(helper_9_02e40)
    )
    direction_offset = (blended_scalar - 0.5) * float(camera_offset)

    final_point = final_inverse_transformed_point
    if final_point is not None:
        if len(final_point) != 3:
            raise ValueError("final_inverse_transformed_point requires three values")
        final_point = [float(v) for v in final_point]
    else:
        final_point = [
            direction_offset * dirv[0],
            direction_offset * dirv[1],
            direction_offset * dirv[2],
        ]

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-offset-blend",
        "normalized_point": normalized_point,
        "blended_quaternion": blended,
        "timer": {
            "before": float(current_308),
            "after": timer,
            "updated_304": updated_304,
            "reset": timer_reset,
        },
        "inverse_factor": inverse_factor,
        "blended_scalar": blended_scalar,
        "direction_offset": direction_offset,
        "final_point": final_point,
        "state_writes": {
            "+0x2f0": blended[0],
            "+0x2f4": blended[1],
            "+0x2f8": blended[2],
            "+0x2fc": blended[3],
            "+0x300": blended_scalar,
            "+0x304": updated_304,
            "+0x308": timer,
        },
        "evidence": {
            "function": "FUN_00820bc0",
            "matrix_position": "+0x2f0..+0x2fc",
            "timer_state": "+0x300/+0x304/+0x308",
            "tracking_frequency": "+0x12c",
            "tracking_correction_speed": "+0x130",
            "tracking_ratio": "+0x134",
            "tracking_magnitude": "+0x138",
            "blend_helper": "FUN_00902e40",
        },
        "limitations": [
            "FUN_004011f0/FUN_004eeda0/FUN_004edfa0/FUN_006303b0 outputs are passed through as helper results",
            "the intermediate quaternion/matrix meaning is not inferred",
        ],
    }
