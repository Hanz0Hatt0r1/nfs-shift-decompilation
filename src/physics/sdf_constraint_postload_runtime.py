"""Source-backed post-load kinematics for SHIFT SDF constraints.

The retail FUN_007b2da0/FUN_007b2de0/FUN_007b2f70 helpers operate on resolved
body pointers and auxiliary sample records after FUN_007b3150 materialization.
This module exposes the exact visible data movement and the closed vector
algebra while keeping FUN_007aefb0/FUN_007af0a0 as explicit transform helpers.
"""
from __future__ import annotations

import argparse
import json
import math
from typing import Iterable, Sequence

FORMAT = "SHIFT.SDFConstraintPostLoadRuntime/1"

COPY_FIELDS = (
    {"source": "+0x10", "destination": "+0x10", "kind": "u32"},
    {"source": "+0x14", "destination": "+0x14", "kind": "string-ref", "helper": "FUN_00632920"},
    {"source": "+0x18", "destination": "+0x18", "kind": "string-ref", "helper": "FUN_00632920"},
    {"source": "+0x1c", "destination": "+0x1c", "kind": "string-ref", "helper": "FUN_00632920"},
    {"source": "+0x20", "destination": "+0x20", "kind": "string-ref", "helper": "FUN_00632920"},
    {"source": "+0x28", "destination": "+0x28", "kind": "u64"},
    {"source": "+0x30", "destination": "+0x30", "kind": "u64"},
    {"source": "+0x38", "destination": "+0x38", "kind": "u64"},
    {"source": "+0x40", "destination": "+0x40", "kind": "u64"},
    {"source": "+0x48", "destination": "+0x48", "kind": "u64"},
    {"source": "+0x50", "destination": "+0x50", "kind": "u64"},
    {"source": "+0x58", "destination": "+0x58", "kind": "u64"},
    {"source": "+0x60", "destination": "+0x60", "kind": "u64"},
    {"source": "+0x68", "destination": "+0x68", "kind": "u64"},
)

POSTLOAD_CONTRACT = {
    "JOINT": {
        "function": "FUN_007b2da0",
        "transform_helper": "FUN_007aefb0",
        "body_pose_offsets": ["+0xd4", "+0xd4"],
        "sample_inputs": ["+0x7c..+0x94", "+0x7c..+0x94"],
        "purpose": "apply the body transform helper to each resolved endpoint sample",
    },
    "HINGE": {
        "function": "FUN_007b2de0",
        "forward_transform_helper": "FUN_007aefb0",
        "inverse_transform_helper": "FUN_007af0a0",
        "operations": [
            "body1 transform sample1 +0x18..+0x30 -> sample1 +0x48..+0x60",
            "body1 transform sample1 +0x30..+0x48 -> sample1 +0x60..+0x78",
            "body2 inverse-transform sample1 +0x48..+0x60 -> sample2 +0x18..+0x30",
            "sample2 vector0/vector1 cross-product construction",
            "body2 transform sample2 +0x30..+0x48 -> sample2 +0x60..+0x78",
        ],
        "cross_product_stage": {
            "cross": "v0 x v1",
            "orthogonalized_second": "v0 x (v0 x v1)",
            "source_indices": "sample2[0:9 doubles]",
        },
    },
    "BAR": {
        "function": "FUN_007b2f70",
        "transform_helper": "FUN_007aefb0",
        "operations": [
            "transform endpoint sample position through body1/body2",
            "subtract endpoint2 from endpoint1 in transformed space",
            "normalize when squared length is non-zero",
            "write the same normalized direction into both endpoint samples +0x40/+0x48/+0x50",
        ],
    },
}


def _vec3(values: Iterable[float]) -> tuple[float, float, float]:
    value = tuple(float(v) for v in values)
    if len(value) != 3:
        raise ValueError("expected exactly three components")
    return value  # type: ignore[return-value]


def cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    ax, ay, az = _vec3(a)
    bx, by, bz = _vec3(b)
    return (
        ay * bz - az * by,
        az * bx - ax * bz,
        ax * by - ay * bx,
    )


def normalize_or_zero(vector: Sequence[float]) -> tuple[float, float, float]:
    x, y, z = _vec3(vector)
    squared = x * x + y * y + z * z
    if squared == 0.0:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / math.sqrt(squared)
    return (x * inv, y * inv, z * inv)


def compute_hinge_cross_stage(
    first: Sequence[float],
    second: Sequence[float],
) -> dict[str, tuple[float, float, float]]:
    """Reproduce the exact cross-product closure in FUN_007b2de0."""
    v0 = _vec3(first)
    v1 = _vec3(second)
    cross01 = cross(v0, v1)
    orthogonalized_second = cross(v0, cross01)
    return {
        "v0": v0,
        "v1_before": v1,
        "cross01": cross01,
        "v1_after": orthogonalized_second,
    }


def compute_bar_direction(
    body1_position: Sequence[float],
    endpoint1_position: Sequence[float],
    body2_position: Sequence[float],
    endpoint2_position: Sequence[float],
) -> dict[str, tuple[float, float, float]]:
    """Reproduce FUN_007b2f70's transformed-position difference and normalization."""
    p1 = _vec3(body1_position)
    e1 = _vec3(endpoint1_position)
    p2 = _vec3(body2_position)
    e2 = _vec3(endpoint2_position)
    transformed1 = tuple(a + b for a, b in zip(p1, e1))
    transformed2 = tuple(a + b for a, b in zip(p2, e2))
    delta = tuple(a - b for a, b in zip(transformed1, transformed2))
    direction = normalize_or_zero(delta)
    return {
        "endpoint1": transformed1,
        "endpoint2": transformed2,
        "delta": delta,
        "direction": direction,
    }


def build_copy_contract() -> dict:
    return {
        "format": "SHIFT.SDFConstraintRecordCopyRuntime/1",
        "version": 1,
        "function": "FUN_007b2ae0",
        "fields": [dict(field) for field in COPY_FIELDS],
        "string_reference_helper": "FUN_00632920",
        "status": "ready",
    }


def build_postload_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "functions": {
            key: dict(value) for key, value in POSTLOAD_CONTRACT.items()
        },
        "source": ".\\Source\\System\\SDF.cpp",
        "transform_helpers": {
            "forward": "FUN_007aefb0",
            "inverse": "FUN_007af0a0",
        },
        "status": "ready",
        "limitations": [
            "FUN_007aefb0 and FUN_007af0a0 are retained as transform-helper boundaries; their internal matrix semantics are not reimplemented here.",
            "No PhysX type names or physical units are assigned to the auxiliary samples.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit SHIFT SDF post-load runtime contracts.")
    parser.add_argument("--copy", action="store_true")
    parser.add_argument("--postload", action="store_true")
    args = parser.parse_args()
    payload = {}
    if not (args.copy or args.postload):
        args.copy = args.postload = True
    if args.copy:
        payload["copy"] = build_copy_contract()
    if args.postload:
        payload["postload"] = build_postload_contract()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
