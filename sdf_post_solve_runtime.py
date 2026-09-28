"""Executable post-solve scalar application recovered from FUN_007b4110."""
from __future__ import annotations

from typing import Any, Sequence

from sdf_body_impulse_runtime import apply_body_accumulator_delta

FORMAT = "SHIFT.SDFPostSolveRuntime/1"


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return float(values[0]), float(values[1]), float(values[2])


def apply_joint_solution(
    positive_body: dict[str, Sequence[float | int]],
    negative_body: dict[str, Sequence[float | int]],
    *,
    positive_point: Sequence[float | int],
    negative_point: Sequence[float | int],
    solved: Sequence[float | int],
) -> dict[str, Any]:
    """Apply three consecutive JOINT solved scalars through +/− body helpers."""
    if len(solved) != 3:
        raise ValueError("JOINT solution must contain exactly three scalars")
    point_pos = _vec3(positive_point, name="positive_point")
    point_neg = _vec3(negative_point, name="negative_point")
    contribution = [float(value) for value in solved]
    pos = apply_body_accumulator_delta(
        positive_body,
        point_pos,
        contribution,
        sign=1,
    )
    neg = apply_body_accumulator_delta(
        negative_body,
        point_neg,
        contribution,
        sign=-1,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "ready": True,
        "constraint": "JOINT",
        "solved": contribution,
        "positive": pos,
        "negative": neg,
        "evidence": {
            "function": "FUN_007b4110",
            "scalar_width": 3,
            "scalar_base": "+0x30",
            "positive_apply": "FUN_007baa70",
            "negative_apply": "FUN_007baaf0",
        },
    }


def apply_hinge_solution(
    positive_body: dict[str, Sequence[float | int]],
    negative_body: dict[str, Sequence[float | int]],
    *,
    sample_angular: Sequence[float | int],
    sample_linear: Sequence[float | int],
    solved: Sequence[float | int],
) -> dict[str, Any]:
    """Apply the two HINGE solved scalars to positive/negative angular state."""
    if len(solved) != 2:
        raise ValueError("HINGE solution must contain exactly two scalars")
    angular = [float(value) for value in positive_body.get("angular", (0.0, 0.0, 0.0))]
    negative_angular = [float(value) for value in negative_body.get("angular", (0.0, 0.0, 0.0))]
    if len(angular) != 3 or len(negative_angular) != 3:
        raise ValueError("body angular values must be vec3")
    a = _vec3(sample_angular, name="sample_angular")
    l = _vec3(sample_linear, name="sample_linear")
    s0, s1 = float(solved[0]), float(solved[1])
    delta = [
        s0 * a[index] + s1 * l[index]
        for index in range(3)
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "ready": True,
        "constraint": "HINGE",
        "solved": [s0, s1],
        "angular_delta": delta,
        "positive": {
            "angular": [angular[index] + delta[index] for index in range(3)],
            "linear": [float(value) for value in positive_body.get("linear", (0.0, 0.0, 0.0))],
        },
        "negative": {
            "angular": [negative_angular[index] - delta[index] for index in range(3)],
            "linear": [float(value) for value in negative_body.get("linear", (0.0, 0.0, 0.0))],
        },
        "evidence": {
            "function": "FUN_007b4110",
            "scalar_width": 2,
            "scalar_base": "+0x94",
            "positive_body_pointer": "+0x78",
            "negative_body_pointer": "+0x80",
            "sample_angular": "+0x48/+0x50/+0x58",
            "sample_linear": "+0x60/+0x68/+0x70",
        },
    }


def apply_bar_solution(
    positive_body: dict[str, Sequence[float | int]],
    negative_body: dict[str, Sequence[float | int]],
    *,
    positive_point: Sequence[float | int],
    negative_point: Sequence[float | int],
    direction: Sequence[float | int],
    solved: float | int,
) -> dict[str, Any]:
    """Apply one BAR solved scalar through +/− body helper primitives."""
    scalar = float(solved)
    direction_vec = _vec3(direction, name="direction")
    contribution = [component * scalar for component in direction_vec]
    pos = apply_body_accumulator_delta(
        positive_body,
        positive_point,
        contribution,
        sign=1,
    )
    neg = apply_body_accumulator_delta(
        negative_body,
        negative_point,
        contribution,
        sign=-1,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "ready": True,
        "constraint": "BAR",
        "solved": scalar,
        "direction": list(direction_vec),
        "contribution": contribution,
        "positive": pos,
        "negative": neg,
        "evidence": {
            "function": "FUN_007b4110",
            "scalar_width": 1,
            "scalar_base": "+0x30",
            "positive_apply": "FUN_007baa70",
            "negative_apply": "FUN_007baaf0",
            "direction_source": "+0x40/+0x48/+0x50",
        },
    }


def describe_post_solve_application_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007b4110",
        "solver_vector": "PhysicsSystem +0x40",
        "constraints": {
            "JOINT": {
                "width": 3,
                "base": "+0x30",
                "sample_stride": 0xA0,
                "positive_helper": "FUN_007baa70",
                "negative_helper": "FUN_007baaf0",
            },
            "HINGE": {
                "width": 2,
                "base": "+0x94",
                "sample_stride": 0xA0,
                "positive_rule": "angular += solved0*sample.angular + solved1*sample.linear",
                "negative_rule": "angular -= solved0*sample.angular + solved1*sample.linear",
            },
            "BAR": {
                "width": 1,
                "base": "+0x30",
                "sample_stride": 0xB8,
                "positive_helper": "FUN_007baa70",
                "negative_helper": "FUN_007baaf0",
                "contribution": "direction * solved_scalar",
            },
        },
        "order": ["JOINT", "HINGE", "BAR"],
        "limitations": [
            "Body channels retain raw storage semantics.",
        ],
    }


__all__ = [
    "FORMAT",
    "apply_joint_solution",
    "apply_hinge_solution",
    "apply_bar_solution",
    "describe_post_solve_application_contract",
]
