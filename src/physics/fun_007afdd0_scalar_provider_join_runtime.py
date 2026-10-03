"""Reference orchestration for the Phase 682 FUN_007afdd0 scalar-provider join.

The recovered source core is executable, but retail production of its four f32
scalar boundaries remains machine-gated. This module composes only the proven
per-BODY order and requires those scalar values from a caller-supplied provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from fun_007afdd0_source_core import (
    Fun007afdd0ScalarBoundary,
    Fun007afdd0SourceCoreResult,
    execute_fun_007afdd0_source_core,
)

FORMAT = "SHIFT.Fun007afdd0ScalarProviderJoinRuntime/1"
BODY_ARRAY_FUNCTION = "FUN_007b2270"
BODY_INTEGRATOR_FUNCTION = "FUN_007bab70"
BASIS_FUNCTION = "FUN_007afdd0"
MACHINE_SCALAR_PRODUCTION_READY = False


@dataclass(frozen=True)
class ProviderJoinBodyInput:
    basis: tuple[float, ...]
    rotation_increment: tuple[float, float, float]


@dataclass(frozen=True)
class ProviderJoinResult:
    bodies: tuple[Fun007afdd0SourceCoreResult, ...]
    provider_call_order: tuple[int, ...]
    applied_rotation_count: int
    zero_noop_count: int


ScalarProvider = Callable[
    [int, tuple[float, ...], tuple[float, float, float]],
    Fun007afdd0ScalarBoundary,
]


def execute_scalar_provider_join(
    bodies: Sequence[ProviderJoinBodyInput],
    provider: ScalarProvider | None,
) -> ProviderJoinResult:
    if provider is None:
        raise ValueError("FUN_007afdd0 source-core integration requires a scalar provider")

    outputs: list[Fun007afdd0SourceCoreResult] = []
    call_order: list[int] = []
    applied = 0
    zero = 0
    for body_index, body in enumerate(bodies):
        if len(body.basis) != 9:
            raise ValueError("FUN_007afdd0 basis must contain exactly 9 f32 values")
        if len(body.rotation_increment) != 3:
            raise ValueError("FUN_007afdd0 rotation increment must contain exactly 3 f64 values")
        scalars = provider(body_index, body.basis, body.rotation_increment)
        call_order.append(body_index)
        result = execute_fun_007afdd0_source_core(
            body.basis,
            body.rotation_increment,
            scalars,
        )
        outputs.append(result)
        if result.applied:
            applied += 1
        else:
            zero += 1

    return ProviderJoinResult(
        bodies=tuple(outputs),
        provider_call_order=tuple(call_order),
        applied_rotation_count=applied,
        zero_noop_count=zero,
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "body_array_function": BODY_ARRAY_FUNCTION,
        "body_integrator_function": BODY_INTEGRATOR_FUNCTION,
        "basis_function": BASIS_FUNCTION,
        "provider_invocation": "once per BODY, after pre-basis rotation_increment production",
        "source_core_used": True,
        "host_math_used": False,
        "machine_scalar_production_ready": MACHINE_SCALAR_PRODUCTION_READY,
        "production_basis_callback_replacement_ready": False,
        "scope_note": (
            "The provider supplies the unresolved retail f32 magnitude-test, sqrt, sine and cosine "
            "boundaries. Phase 682 does not synthesize or approximate those values."
        ),
    }
