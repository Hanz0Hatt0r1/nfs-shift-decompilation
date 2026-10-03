"""Reference oracle for the proven FUN_007b2270 per-BODY basis callback schedule.

This phase deliberately does not implement FUN_007afdd0.  It freezes only the
source-backed array order and the requirement that the basis provider is invoked
inside each FUN_007bab70 element boundary before advancing to the next BODY.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import math

FORMAT = "SHIFT.NativeBodyArrayBasisCallback/1"
BODY_ARRAY_FUNCTION = "FUN_007b2270"
BODY_INTEGRATOR_FUNCTION = "FUN_007bab70"
BASIS_FUNCTION = "FUN_007afdd0"
BODY_STRIDE = 0x170

Basis3f = tuple[float, float, float, float, float, float, float, float, float]
Vector3d = tuple[float, float, float]
BasisRotationProvider = Callable[[Basis3f, Vector3d], Sequence[float]]


@dataclass(frozen=True)
class BodyBasisCallbackInput:
    basis: Basis3f
    rotation_increment: Vector3d


def _require_finite(values: Sequence[float], label: str) -> None:
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError(f"{label} contains non-finite value")


def _require_basis(values: Sequence[float], label: str) -> Basis3f:
    if len(values) != 9:
        raise ValueError(f"{label} must contain exactly 9 values")
    _require_finite(values, label)
    return tuple(float(value) for value in values)  # type: ignore[return-value]


def execute_body_array_basis_callback_schedule(
    bodies: Sequence[BodyBasisCallbackInput],
    basis_rotation: BasisRotationProvider,
) -> tuple[Basis3f, ...]:
    if not callable(basis_rotation):
        raise ValueError("FUN_007b2270 requires a basis-rotation provider")

    result: list[Basis3f] = []
    for index, body in enumerate(bodies):
        basis = _require_basis(body.basis, f"BODY[{index}] basis")
        if len(body.rotation_increment) != 3:
            raise ValueError(f"BODY[{index}] rotation increment must contain 3 values")
        _require_finite(body.rotation_increment, f"BODY[{index}] rotation increment")
        updated = basis_rotation(basis, body.rotation_increment)
        result.append(_require_basis(updated, f"BODY[{index}] updated basis"))
    return tuple(result)


def build_body_array_basis_callback_contract() -> dict:
    return {
        "format": FORMAT,
        "body_array_function": BODY_ARRAY_FUNCTION,
        "body_integrator_function": BODY_INTEGRATOR_FUNCTION,
        "basis_rotation_function": BASIS_FUNCTION,
        "body_stride": BODY_STRIDE,
        "retail_iteration_order_proven": True,
        "basis_provider_inside_each_body_proven": True,
        "basis_rotation_arithmetic_external": True,
        "render_frame_scheduler_proven": False,
        "game_launched": False,
        "runtime_capture_used": False,
    }
