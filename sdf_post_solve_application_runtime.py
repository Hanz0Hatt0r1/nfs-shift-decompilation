"""Exact post-solve body-state application from FUN_007b4110."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from sdf_body_impulse_runtime import apply_body_accumulator_delta

FORMAT = "SHIFT.SDFPostSolveApplicationRuntime/1"
SOURCE_LINE = 814168


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three components")
    return float(values[0]), float(values[1]), float(values[2])


def _solved_slice(
    solver_vector: Sequence[float | int],
    base: int,
    width: int,
) -> list[float]:
    start = int(base)
    if start < 0 or start + int(width) > len(solver_vector):
        raise ValueError("solver scalar range is outside solver vector")
    return [float(value) for value in solver_vector[start:start + int(width)]]


def apply_joint_solution(
    *,
    positive_state: Mapping[str, Sequence[float | int]],
    negative_state: Mapping[str, Sequence[float | int]],
    solver_vector: Sequence[float | int],
    scalar_base: int,
    positive_lever_arm: Sequence[float | int],
    negative_lever_arm: Sequence[float | int],
) -> dict[str, Any]:
    """Apply a solved JOINT 3-vector through FUN_007baa70/baaf0."""
    solution = _solved_slice(solver_vector, scalar_base, 3)
    positive = apply_body_accumulator_delta(
        positive_state,
        positive_lever_arm,
        solution,
        sign=1,
    )
    negative = apply_body_accumulator_delta(
        negative_state,
        negative_lever_arm,
        solution,
        sign=-1,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "ready": True,
        "function": "FUN_007b4110",
        "source_line": SOURCE_LINE,
        "constraint": "JOINT",
        "scalar_base": int(scalar_base),
        "solver_width": 3,
        "solution": solution,
        "positive": positive,
        "negative": negative,
        "evidence": {
            "positive_helper": "FUN_007baa70",
            "negative_helper": "FUN_007baaf0",
            "positive_lever_arm_source": "sample +0x18",
            "negative_lever_arm_source": "negative sample +0x84 +0x18",
        },
    }


def hinge_angular_delta(
    solution: Sequence[float | int],
    angular_row: Sequence[float | int],
    linear_row: Sequence[float | int],
    *,
    sign: int = 1,
) -> dict[str, Any]:
    """Evaluate the direct HINGE angular-state update in FUN_007b4110."""
    solved = _vec3(solution, name="solution")
    if len(solution) != 2:
        raise ValueError("HINGE solution must contain exactly two scalars")
    angular = _vec3(angular_row, name="angular_row")
    linear = _vec3(linear_row, name="linear_row")
    if int(sign) not in (-1, 1):
        raise ValueError("sign must be +1 or -1")
    s0, s1 = solved[0], solved[1]
    delta = [
        int(sign) * (angular[0] * s0 + linear[0] * s1),
        int(sign) * (angular[1] * s0 + linear[1] * s1),
        int(sign) * (angular[2] * s0 + linear[2] * s1),
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007b4110",
        "constraint": "HINGE",
        "sign": int(sign),
        "solution": [s0, s1],
        "angular_row": list(angular),
        "linear_row": list(linear),
        "angular_delta": delta,
        "evidence": {
            "angular_row_offsets": ["+0x48", "+0x50", "+0x58"],
            "linear_row_offsets": ["+0x60", "+0x68", "+0x70"],
        },
    }


def apply_hinge_solution(
    *,
    positive_angular: Sequence[float | int],
    negative_angular: Sequence[float | int],
    solver_vector: Sequence[float | int],
    scalar_base: int,
    positive_angular_row: Sequence[float | int],
    positive_linear_row: Sequence[float | int],
    negative_angular_row: Sequence[float | int],
    negative_linear_row: Sequence[float | int],
) -> dict[str, Any]:
    """Apply a solved HINGE 2-vector to positive/negative angular accumulators."""
    solution = _solved_slice(solver_vector, scalar_base, 2)
    positive_delta = hinge_angular_delta(
        solution,
        positive_angular_row,
        positive_linear_row,
        sign=1,
    )
    negative_delta = hinge_angular_delta(
        solution,
        negative_angular_row,
        negative_linear_row,
        sign=-1,
    )

    def add3(
        state: Sequence[float | int],
        delta: Sequence[float | int],
    ) -> list[float]:
        values = _vec3(state, name="angular_state")
        return [values[i] + float(delta[i]) for i in range(3)]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "ready": True,
        "function": "FUN_007b4110",
        "constraint": "HINGE",
        "scalar_base": int(scalar_base),
        "solver_width": 2,
        "solution": solution,
        "positive_angular": add3(
            positive_angular,
            positive_delta["angular_delta"],
        ),
        "negative_angular": add3(
            negative_angular,
            negative_delta["angular_delta"],
        ),
        "positive_delta": positive_delta["angular_delta"],
        "negative_delta": negative_delta["angular_delta"],
        "evidence": {
            "positive_rule": "angular += solved[0]*angular_row + solved[1]*linear_row",
            "negative_rule": "angular -= solved[0]*angular_row + solved[1]*linear_row",
            "sample_stride": "0xa0",
            "scalar_base_offset": "+0x94",
        },
    }


def apply_bar_solution(
    *,
    positive_state: Mapping[str, Sequence[float | int]],
    negative_state: Mapping[str, Sequence[float | int]],
    solver_vector: Sequence[float | int],
    scalar_base: int,
    positive_lever_arm: Sequence[float | int],
    negative_lever_arm: Sequence[float | int],
    bar_direction: Sequence[float | int],
) -> dict[str, Any]:
    """Apply a solved BAR scalar through FUN_007baa70/baaf0."""
    scalar = _solved_slice(solver_vector, scalar_base, 1)[0]
    direction = _vec3(bar_direction, name="bar_direction")
    solution = [direction[i] * scalar for i in range(3)]
    positive = apply_body_accumulator_delta(
        positive_state,
        positive_lever_arm,
        solution,
        sign=1,
    )
    negative = apply_body_accumulator_delta(
        negative_state,
        negative_lever_arm,
        solution,
        sign=-1,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "ready": True,
        "function": "FUN_007b4110",
        "constraint": "BAR",
        "scalar_base": int(scalar_base),
        "solver_width": 1,
        "solution_scalar": scalar,
        "direction": list(direction),
        "vector_solution": solution,
        "positive": positive,
        "negative": negative,
        "evidence": {
            "positive_helper": "FUN_007baa70",
            "negative_helper": "FUN_007baaf0",
            "direction_offsets": ["+0x40", "+0x48", "+0x50"],
            "sample_stride": "0xb8",
            "scalar_base_offset": "+0x30",
        },
    }


def describe_post_solve_application_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007b4110",
        "source_line": SOURCE_LINE,
        "solver_vector": "PhysicsSystem +0x40",
        "constraints": {
            "JOINT": {
                "width": 3,
                "positive_application": "FUN_007baa70",
                "negative_application": "FUN_007baaf0",
                "positive_lever_arm": "sample +0x7c +0x18",
                "negative_lever_arm": "sample +0x84 +0x18",
            },
            "HINGE": {
                "width": 2,
                "positive_update": "direct angular + solved[0]*angular_row + solved[1]*linear_row",
                "negative_update": "direct angular - solved[0]*angular_row - solved[1]*linear_row",
                "angular_offsets": ["+0x48", "+0x50", "+0x58"],
                "linear_offsets": ["+0x60", "+0x68", "+0x70"],
            },
            "BAR": {
                "width": 1,
                "positive_application": "FUN_007baa70",
                "negative_application": "FUN_007baaf0",
                "direction_offsets": ["+0x40", "+0x48", "+0x50"],
                "positive_lever_arm": "sample +0x7c +0x18",
                "negative_lever_arm": "sample +0x84 +0x18",
            },
        },
        "order": ["JOINT", "HINGE", "BAR"],
    }


__all__ = [
    "FORMAT",
    "SOURCE_LINE",
    "apply_joint_solution",
    "hinge_angular_delta",
    "apply_hinge_solution",
    "apply_bar_solution",
    "describe_post_solve_application_contract",
]
