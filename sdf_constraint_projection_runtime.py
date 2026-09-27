"""Source-backed JOINT/HINGE scalar projection primitives for SHIFT SDF physics."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFConstraintProjectionRuntime/1"


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return float(values[0]), float(values[1]), float(values[2])


def evaluate_joint_cross_terms(
    sample: Sequence[float | int],
    body: Sequence[float | int],
) -> dict[str, float]:
    """Evaluate the three JOINT cross-product terms proven in FUN_007bac60."""
    sx, sy, sz = _vec3(sample, name="sample")
    bx, by, bz = _vec3(body, name="body")
    return {
        "d2": sz * by - sy * bz,
        "d3": bz * sx - sz * bx,
        "d5": sy * bx - by * sx,
    }


def build_joint_scalar_lanes(
    *,
    d2: float,
    d4: float,
    d6: float,
    sign: int = 1,
) -> dict[str, Any]:
    """Materialize the scalar lane outputs documented for FUN_007bac60."""
    if int(sign) not in (-1, 1):
        raise ValueError("sign must be +1 or -1")
    lanes = [
        int(sign) * float(d4),
        int(sign) * float(d6),
        int(sign) * float(d2),
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bac60",
        "sign": int(sign),
        "inputs": {
            "d2": float(d2),
            "d4": float(d4),
            "d6": float(d6),
        },
        "lanes": lanes,
        "lane_mapping": {
            "lane0": "sign*d4",
            "lane1": "sign*d6",
            "lane2": "sign*d2",
        },
        "destination": {
            "status": "opaque",
            "reason": "destination storage cannot be reconciled with the body +0x158 pointer-table layout without the direct function-body source slice",
        },
    }


def describe_joint_projection_provenance() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-partial",
        "ready": True,
        "function": "FUN_007bac60",
        "sample_stride": 0x40,
        "side_flag_offset": "+0x34",
        "scalar_base_offset": "+0x30",
        "proven_terms": {
            "d2": "sample[+0x28]*body[+0x20] - sample[+0x20]*body[+0x28]",
            "d3": "body[+0x28]*sample[+0x18] - sample[+0x28]*body[+0x18]",
            "d5": "sample[+0x20]*body[+0x18] - body[+0x20]*sample[+0x18]",
        },
        "lane_outputs": [
            "sign*d4",
            "sign*d6",
            "sign*d2",
        ],
        "unresolved_terms": ["d4", "d6"],
        "sign_rule": "side flag zero => +1; nonzero => -1",
        "destination_layout": {
            "status": "opaque",
            "do_not_alias_to": ["body +0x158 row-pointer table", "body +0x15c row-index vector"],
        },
    }


def describe_hinge_projection_provenance() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-partial",
        "ready": True,
        "function": "FUN_007bae40",
        "sample_stride": 0xA0,
        "scalar_base_offset": "+0x94",
        "side_flag_offset": "+0x98",
        "known_inputs": {
            "sample_frame_terms": [
                "+0x48/+0x50/+0x58",
                "+0x60/+0x68/+0x70",
            ],
            "negative_body_transform": "FUN_007aefb0(body +0xd4, sample-derived vector)",
        },
        "branch_rule": {
            "flag_zero": "add transformed velocity terms",
            "flag_nonzero": "transform through body +0xd4 and subtract transformed terms",
        },
        "unresolved": [
            "exact coefficient expressions for all scalar lanes",
            "final matrix destination slots",
        ],
    }
