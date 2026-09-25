"""Evidence-backed CCameraView matrix-build boundary from FUN_00820a80.

The function consumes the quaternion produced by FUN_008207c0, converts it with
FUN_00445ec0, applies the observed matrix normalization helper FUN_00630a50,
constructs the depth coefficients from NearZ/FarZ at +0x3c/+0x40, computes a
rate ratio from FUN_00900b10/FUN_00900c40 when the supplied scalar is nonzero,
then composes the final matrix through FUN_00401610 and FUN_00401d10.

No row/column or projection handedness convention is inferred here.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraViewMatrixBuildRuntime/1"


def compute_depth_coefficients(*, near_z: float, far_z: float) -> dict[str, float]:
    """Reproduce the explicit NearZ/FarZ arithmetic in FUN_00820a80."""
    near = float(near_z)
    far = float(far_z)
    span = far - near
    if span == 0.0:
        raise ValueError("NearZ and FarZ must not be equal")
    return {
        "span": span,
        "far_over_span": far / span,
        "minus_near_times_far_over_span": (-near * far) / span,
    }


def compute_rate_ratio(
    *,
    input_scalar: float,
    helper_00900b10: float,
    helper_00900c40: float,
) -> dict[str, Any]:
    """Reproduce the zero/nonzero scalar branch and helper ratio."""
    scalar = float(input_scalar)
    if scalar == 0.0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "rate-ratio",
            "status": "zero-input",
            "half_scalar": 0.0,
            "ratio": 0.0,
            "evidence": {"function": "FUN_00820a80"},
        }

    denominator = float(helper_00900c40)
    if denominator == 0.0:
        raise ValueError("FUN_00900c40 result must be non-zero for rate ratio")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "rate-ratio",
        "status": "computed",
        "half_scalar": scalar * 0.5,
        "helper_00900b10": float(helper_00900b10),
        "helper_00900c40": denominator,
        "ratio": float(helper_00900b10) / denominator,
        "evidence": {
            "function": "FUN_00820a80",
            "helper_a": "FUN_00900b10",
            "helper_b": "FUN_00900c40",
        },
    }


def describe_camera_view_matrix_build(
    *,
    orientation_quaternion: Sequence[float],
    position: Sequence[float],
    near_z: float,
    far_z: float,
    input_scalar: float,
    helper_00900b10: float = 0.0,
    helper_00900c40: float = 1.0,
    converted_matrix: Sequence[float] | None = None,
    transformed_matrix: Sequence[float] | None = None,
    final_matrix: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Trace FUN_00820a80 without inventing matrix-helper semantics."""
    if len(orientation_quaternion) != 4:
        raise ValueError("orientation_quaternion requires four values")
    if len(position) != 3:
        raise ValueError("position requires three values")

    q = [float(v) for v in orientation_quaternion]
    p = [float(v) for v in position]
    depth = compute_depth_coefficients(near_z=near_z, far_z=far_z)
    ratio = compute_rate_ratio(
        input_scalar=input_scalar,
        helper_00900b10=helper_00900b10,
        helper_00900c40=helper_00900c40,
    )

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-view-matrix-build",
        "inputs": {
            "orientation_quaternion": q,
            "position": p,
            "near_z": float(near_z),
            "far_z": float(far_z),
            "input_scalar": float(input_scalar),
        },
        "depth": depth,
        "rate_ratio": ratio,
        "helper_boundaries": {
            "FUN_008207c0": {
                "orientation_output": q,
            },
            "FUN_00445ec0": {
                "input": q,
                "result": list(map(float, converted_matrix))
                if converted_matrix is not None else None,
                "output_shape": 12,
            },
            "FUN_00630a50": {
                "input": "converted 3x4 matrix",
                "result": list(map(float, transformed_matrix))
                if transformed_matrix is not None else None,
            },
            "FUN_00401610": {
                "input": "view/depth components",
                "result": list(map(float, final_matrix))
                if final_matrix is not None else None,
            },
            "FUN_00401d10": {
                "input": "final matrix",
                "result": list(map(float, final_matrix))
                if final_matrix is not None else None,
            },
        },
        "source_order": [
            "FUN_008207c0",
            "FUN_00445ec0",
            "FUN_00630a50",
            "compute rate ratio if input_scalar != 0",
            "construct depth coefficients",
            "FUN_00401610",
            "FUN_00401d10",
        ],
        "evidence": {
            "function": "FUN_00820a80",
            "position_offsets": ["+0x10", "+0x14", "+0x18"],
            "near_offset": "+0x3c",
            "far_offset": "+0x40",
            "camera_data_scalar": "manager +0x268c",
        },
        "limitations": [
            "FUN_00445ec0/FUN_00630a50/FUN_00401610/FUN_00401d10 remain opaque matrix helpers",
            "the 12-float intermediate matrix layout is not given a global row/column label",
        ],
    }
