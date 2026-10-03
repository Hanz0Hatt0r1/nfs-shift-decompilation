"""Scheduling oracle for Phase 691 FUN_007afdd0 scalar-provider outer join.

This contract narrows the Phase 689/690 basis boundary. The arbitrary basis
callback is replaced by the already-defined four-f32 FUN_007afdd0 scalar
provider; the source-shaped basis update executes inside the native chain.
Retail x87/CRT production of those scalar values remains external.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

FORMAT = "SHIFT.Fun00770e80ScalarProviderAnchorChainRuntime/1"
PASS_COUNT = 2


@dataclass(frozen=True)
class Fun00770e80ScalarProviderAnchorChainRuntimeResult:
    joined_result: Any
    scalar_provider_call_counts: tuple[int, int]
    scalar_provider_call_count: int
    events: tuple[str, ...]


def execute_fun_00770e80_scalar_provider_anchor_chain_runtime(
    phase689_executor: Callable[[Callable[[int, Any, Any], Any]], Any] | None,
    scalar_provider: Callable[[int, int, Any, Any], Any] | None,
    *,
    body_count: int,
) -> Fun00770e80ScalarProviderAnchorChainRuntimeResult:
    if phase689_executor is None:
        raise ValueError("Phase 691 requires the Phase 689 executor")
    if scalar_provider is None:
        raise ValueError("Phase 691 requires the FUN_007afdd0 scalar provider")
    if body_count <= 0:
        raise ValueError("Phase 691 requires a non-zero BODY count")

    counts = [0, 0]
    events: list[str] = []
    current_pass = 0

    def basis_adapter(body_index: int, basis: Any, rotation_increment: Any) -> Any:
        nonlocal current_pass
        if current_pass < 0 or current_pass >= PASS_COUNT:
            raise ValueError("Phase 691 pass index exceeds proven domain")
        if body_index < 0 or body_index >= body_count:
            raise ValueError("Phase 691 BODY index exceeds runtime domain")
        scalars = scalar_provider(current_pass, body_index, basis, rotation_increment)
        counts[current_pass] += 1
        events.append(f"scalar-provider-{current_pass}-{body_index}")
        return scalars

    # The scheduling oracle lets the Phase 689 fixture mark the current pass
    # before it invokes the adapted basis boundary. It intentionally does not
    # reproduce the source-core arithmetic; native/C++ regressions cover that.
    def adapted_provider(pass_index: int, body_index: int, basis: Any, rotation_increment: Any) -> Any:
        nonlocal current_pass
        current_pass = pass_index
        return basis_adapter(body_index, basis, rotation_increment)

    joined_result = phase689_executor(adapted_provider)

    expected = body_count
    if counts != [expected, expected]:
        raise ValueError("Phase 691 scalar-provider BODY cardinality mismatch")

    return Fun00770e80ScalarProviderAnchorChainRuntimeResult(
        joined_result=joined_result,
        scalar_provider_call_counts=(counts[0], counts[1]),
        scalar_provider_call_count=sum(counts),
        events=tuple(events),
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "phase689_composed_anchor_chain_reused": True,
        "fun_007afdd0_source_core_internal": True,
        "arbitrary_basis_callback_external": False,
        "scalar_boundary_fields": [
            "squared_magnitude_test",
            "sqrt_magnitude",
            "sine",
            "cosine",
        ],
        "machine_scalar_production_external": True,
        "host_libm_substitution": False,
        "persistent_body_bytes_preserved": True,
        "fixed_step_auto_schedule": False,
        "rendered_frame_cadence_proven": False,
        "complete_fun_007afdd0_machine_semantics": False,
        "complete_fun_00770e80_semantics": False,
    }
