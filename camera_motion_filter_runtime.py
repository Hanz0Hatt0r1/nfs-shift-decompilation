"""Exact CCameraView motion-filter integration from FUN_0081b980.

The decompiled function updates six scalar/vector components at +0x9c..+0xb0
from a target vector, delta time, and the profile scale at selected camera
data +0x20. It uses FUN_0081b820/FUN_0081b8a0 with fixed constants.

The output vector is incremented by profile_scale * (+0x9c,+0xa0,+0xa4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from camera_scalar_helpers_runtime import corrective_response, deadzone_response

FORMAT = "SHIFT.CameraMotionFilterRuntime/1"


@dataclass(frozen=True)
class CameraMotionFilterState:
    response_x: float = 0.0  # +0x9c
    response_y: float = 0.0  # +0xa0
    response_z: float = 0.0  # +0xa4
    target_x: float = 0.0  # +0xa8
    target_y: float = 0.0  # +0xac
    target_z: float = 0.0  # +0xb0


def update_motion_filter(
    state: CameraMotionFilterState,
    *,
    delta: float,
    reference_vector: Sequence[float],
    profile_scale: float,
    output_vector: Sequence[float],
) -> tuple[CameraMotionFilterState, list[float], dict]:
    """Reproduce FUN_0081b980's state and output arithmetic."""
    if len(reference_vector) != 3:
        raise ValueError("reference_vector requires three values")
    if len(output_vector) != 3:
        raise ValueError("output_vector requires three values")

    scale = float(profile_scale)
    out = [float(v) for v in output_vector]
    if scale <= 0.0:
        return state, out, {
            "format": FORMAT,
            "version": 1,
            "status": "profile-scale-disabled",
            "evidence": {"function": "FUN_0081b980", "guard": "profile +0x20 > 0"},
        }

    dt = float(delta)
    rx = float(state.response_x)
    ry = float(state.response_y)
    rz = float(state.response_z)
    tx = float(state.target_x)
    ty = float(state.target_y)
    tz = float(state.target_z)
    vx = float(reference_vector[0])
    vy = float(reference_vector[1])
    vz = float(reference_vector[2])

    error_x = tx - vx
    error_y = ty - vy
    error_z = tz - vz

    spring_x = deadzone_response(rx, error_x, 0.0, 10.0, 1.0)["result"]
    spring_y = deadzone_response(ry, error_y, 0.0, 2.0, 1.0)["result"]
    extra_y = deadzone_response(ry, error_y, 0.05, 400.0, 4.0)["result"]
    spring_z = deadzone_response(rz, error_z, 0.0, 10.0, 1.0)["result"]

    correction_x = corrective_response(rx, error_x, 0.02, 1000.0, 10.0)["result"]
    correction_y = corrective_response(ry, error_y, 0.06, 1000.0, 10.0)["result"]
    correction_z = corrective_response(rz, error_z, 0.02, 1000.0, 10.0)["result"]

    new_tx = tx + dt * (correction_x + spring_x)
    new_ty = ty + dt * (correction_y + extra_y + spring_y)
    new_tz = tz + dt * (correction_z + spring_z)

    new_rx = rx + dt * (new_tx - vx)
    new_ry = ry + dt * (new_ty - vy)
    new_rz = rz + dt * (new_tz - vz)

    out = [
        out[0] + scale * new_rx,
        out[1] + scale * new_ry,
        out[2] + scale * new_rz,
    ]

    new_state = CameraMotionFilterState(
        response_x=new_rx,
        response_y=new_ry,
        response_z=new_rz,
        target_x=new_tx,
        target_y=new_ty,
        target_z=new_tz,
    )
    return new_state, out, {
        "format": FORMAT,
        "version": 1,
        "status": "updated",
        "errors": [error_x, error_y, error_z],
        "first_stage": {
            "x": spring_x,
            "y": spring_y,
            "y_extra": extra_y,
            "z": spring_z,
        },
        "second_stage": {
            "x": correction_x,
            "y": correction_y,
            "z": correction_z,
        },
        "state_after": {
            "+0x9c": new_rx,
            "+0xa0": new_ry,
            "+0xa4": new_rz,
            "+0xa8": new_tx,
            "+0xac": new_ty,
            "+0xb0": new_tz,
        },
        "output_delta": [
            scale * new_rx,
            scale * new_ry,
            scale * new_rz,
        ],
        "evidence": {
            "function": "FUN_0081b980",
            "delta": "param_1",
            "reference_vector": "param_2 +0x1c/+0x20/+0x24",
            "output_vector": "param_3",
            "profile_scale": "camera profile +0x20",
            "response_state": ["+0x9c", "+0xa0", "+0xa4"],
            "target_state": ["+0xa8", "+0xac", "+0xb0"],
        },
    }
