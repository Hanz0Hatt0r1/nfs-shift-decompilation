"""Evidence-backed camera pose-basis and external-source helpers.

Recovered from FUN_0081af90, FUN_0081b170 and FUN_0081b230.

The af90 routine constructs an orthonormal basis from two 3-vectors using the
same cross/normalize ordering as the executable and writes it to the embedded
orientation at +0x1c via FUN_004f8040/FUN_00449930.

The b170 routine preserves external camera-source state and delegates the
actual source values to the +0x1c/+0x20/+0x34 vtable methods.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraPoseBasisRuntime/1"


def _vec3(values: Sequence[float], name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} requires three values")
    return float(values[0]), float(values[1]), float(values[2])


def _normalize(values: Sequence[float]) -> tuple[tuple[float, float, float], float]:
    x, y, z = _vec3(values, "values")
    length = (x * x + y * y + z * z) ** 0.5
    if length == 0.0:
        return (0.0, 0.0, 0.0), 0.0
    inv = 1.0 / length
    return (x * inv, y * inv, z * inv), length


def _af90_cross(left: Sequence[float], right: Sequence[float]) -> tuple[float, float, float]:
    lx, ly, lz = _vec3(left, "left")
    rx, ry, rz = _vec3(right, "right")
    return (
        lz * ry - ly * rz,
        lx * rz - rx * lz,
        ly * rx - ry * lx,
    )


def build_pose_basis(
    first_vector: Sequence[float],
    second_vector: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_0081af90's three normalize/cross stages."""
    first, first_len = _normalize(first_vector)
    second_raw = _af90_cross(first, second_vector)
    second, second_len = _normalize(second_raw)
    third_raw = _af90_cross(first, second)
    third, third_len = _normalize(third_raw)

    basis = [
        *second,
        *third,
        *first,
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "pose-basis",
        "basis_3x3_source_order": basis,
        "stages": {
            "first": {"vector": first, "length": first_len},
            "second": {"raw": second_raw, "vector": second, "length": second_len},
            "third": {"raw": third_raw, "vector": third, "length": third_len},
        },
        "actions": [
            {"action": "FUN_00442310", "target": "first vector"},
            {"action": "cross first × second"},
            {"action": "FUN_00442310", "target": "second vector"},
            {"action": "cross first/second basis"},
            {"action": "FUN_00442310", "target": "third vector"},
            {"action": "FUN_004f8040", "target": "local +0x38"},
            {"action": "FUN_00449930", "target": "this +0x1c"},
        ],
        "evidence": {
            "function": "FUN_0081af90",
            "destination": "+0x1c",
            "first_vector": "param_1",
            "second_vector": "param_2",
            "normalizer": "FUN_00442310",
        },
        "limitations": [
            "the resulting source-order nine floats are not assigned an engine-wide row/column convention",
        ],
    }


def describe_external_source_state(
    *,
    external_id: Any,
    source_position: Sequence[float],
    source_orientation: Sequence[float],
    source_fov: float,
    source_position_valid: bool = True,
    service_object_present: bool = True,
    global_angle_offset: float = 0.0,
    helper_90285a_value: float = 0.0,
    source_vtable_fov_result: float = 0.0,
) -> dict[str, Any]:
    """Trace FUN_0081b170 without inventing vtable-return semantics."""
    position = _vec3(source_position, "source_position")
    orientation = _vec3(source_orientation, "source_orientation")
    if not service_object_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "external-source-state",
            "status": "service-unavailable",
            "actions": [],
        }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "external-source-state",
        "status": "active" if external_id != 0 else "disabled",
        "writes": {
            "+0x4c": 0,
            "+0x50": external_id,
            "+0x10": list(position),
            "+0x1c": float(source_orientation[0]) - float(global_angle_offset),
            "+0x20": float(helper_90285a_value),
            "+0x24": 0.0,
            "+0x34": float(source_vtable_fov_result),
        },
        "actions": [
            {
                "action": "write +0x4c",
                "value": 0,
            },
            {
                "action": "write +0x50",
                "value": external_id,
            },
            {
                "action": "source slot +0x1c()",
                "condition": "external_id != 0",
            },
            {
                "action": "source slot +0x20()",
                "condition": "external_id != 0",
            },
            {
                "action": "FUN_0090285a",
                "result": float(helper_90285a_value),
            },
            {
                "action": "FUN_009024d0",
                "result": float(global_angle_offset),
            },
            {
                "action": "source slot +0x34()",
                "result": float(source_vtable_fov_result),
            },
        ],
        "evidence": {
            "function": "FUN_0081b170",
            "external_id": "+0x50",
            "active_flag": "+0x4c",
            "position": "+0x10",
            "orientation": "+0x1c/+0x20/+0x24",
            "fov": "+0x34",
            "service_source": "manager +0x2580",
        },
        "limitations": [
            "source vtable +0x1c/+0x20/+0x34 meanings remain opaque",
            "FUN_0090285a/FUN_009024d0 are preserved as helper results",
        ],
    }


def resolve_profile_scale_or_default(
    profile_present: bool,
    profile_scale: float,
) -> dict[str, Any]:
    """Reproduce FUN_0081b230's profile +0xe8 lookup."""
    if profile_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "profile-scale",
            "value": float(profile_scale),
            "source": "profile +0xe8",
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "profile-scale",
        "value": 1.0,
        "source": "constant 1.0",
    }
