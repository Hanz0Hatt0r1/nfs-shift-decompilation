"""Scheduling oracle for the typed FUN_007675f0 provider outer-chain join.

The oracle models only provider cardinality and anchor ordering. The recovered
FUN_007675f0 arithmetic remains covered by the existing Phase 662 native kernel;
this module deliberately does not duplicate that arithmetic with host math.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

FORMAT = "SHIFT.Fun00770e80ContactOuterProviderChainRuntime/1"
PASS_COUNT = 2


@dataclass(frozen=True)
class PhysicsPassCallbacks:
    contact_factor: Callable[[], None]
    wheel_update: Callable[[], None]
    contact_response: Callable[[], None]
    contact_outer_input_provider: Callable[[], Any]
    motion_read_gate: Callable[[], None]


@dataclass(frozen=True)
class AdaptedPhysicsPassCallbacks:
    contact_factor: Callable[[], None]
    wheel_update: Callable[[], None]
    contact_response: Callable[[], None]
    contact_outer: Callable[[], None]
    motion_read_gate: Callable[[], None]


@dataclass(frozen=True)
class ContactOuterProviderChainRuntimeResult:
    joined_result: Any
    physics_pass_provider_call_counts: tuple[int, int]
    contact_outer_input_provider_call_counts: tuple[int, int]
    contact_outer_native_call_counts: tuple[int, int]
    events: tuple[str, ...]


def _require_callable(value: object, label: str) -> None:
    if not callable(value):
        raise ValueError(f"Phase 693 requires {label}")


def execute_fun_00770e80_contact_outer_provider_chain_runtime(
    phase691_executor: Callable[[Callable[[int], AdaptedPhysicsPassCallbacks]], Any] | None,
    physics_pass_provider: Callable[[int], PhysicsPassCallbacks] | None,
    contact_outer_executor: Callable[[Any], Any] | None,
) -> ContactOuterProviderChainRuntimeResult:
    if phase691_executor is None:
        raise ValueError("Phase 693 requires the Phase 691 executor")
    if physics_pass_provider is None:
        raise ValueError("Phase 693 requires the typed physics-pass provider")
    if contact_outer_executor is None:
        raise ValueError("Phase 693 requires the native FUN_007675f0 executor")

    pass_calls = [0, 0]
    input_calls = [0, 0]
    native_calls = [0, 0]
    events: list[str] = []

    def adapted_provider(pass_index: int) -> AdaptedPhysicsPassCallbacks:
        if pass_index < 0 or pass_index >= PASS_COUNT:
            raise ValueError("Phase 693 pass index exceeds proven domain")
        if pass_calls[pass_index] != 0:
            raise ValueError("Phase 693 physics-pass provider repeated one pass")

        typed = physics_pass_provider(pass_index)
        pass_calls[pass_index] += 1
        _require_callable(typed.contact_factor, "FUN_00765c40 callback")
        _require_callable(typed.wheel_update, "FUN_00758b50 callback")
        _require_callable(typed.contact_response, "FUN_00766510 callback")
        _require_callable(
            typed.contact_outer_input_provider,
            "FUN_007675f0 typed input provider",
        )
        _require_callable(typed.motion_read_gate, "FUN_007682c0 callback")

        def contact_outer() -> None:
            events.append(f"contact-outer-input-provider:{pass_index}")
            input_calls[pass_index] += 1
            value = typed.contact_outer_input_provider()
            contact_outer_executor(value)
            native_calls[pass_index] += 1
            events.append(f"contact-outer-native:{pass_index}")

        return AdaptedPhysicsPassCallbacks(
            contact_factor=typed.contact_factor,
            wheel_update=typed.wheel_update,
            contact_response=typed.contact_response,
            contact_outer=contact_outer,
            motion_read_gate=typed.motion_read_gate,
        )

    joined_result = phase691_executor(adapted_provider)

    if pass_calls != [1, 1]:
        raise ValueError("Phase 693 physics-pass provider cardinality mismatch")
    if input_calls != [1, 1] or native_calls != [1, 1]:
        raise ValueError("Phase 693 FUN_007675f0 execution cardinality mismatch")

    return ContactOuterProviderChainRuntimeResult(
        joined_result=joined_result,
        physics_pass_provider_call_counts=(pass_calls[0], pass_calls[1]),
        contact_outer_input_provider_call_counts=(input_calls[0], input_calls[1]),
        contact_outer_native_call_counts=(native_calls[0], native_calls[1]),
        events=tuple(events),
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "phase691_scalar_provider_outer_chain_reused": True,
        "fun_007675f0_typed_input_provider": True,
        "fun_007675f0_native_kernel_internal": True,
        "fun_007675f0_arbitrary_callback_external": False,
        "fun_007675f0_input_production_external": True,
        "other_fun_0076d100_anchor_callbacks_external": True,
        "machine_scalar_production_external": True,
        "post_half_step_fun_007b8810_external": True,
        "persistent_body_bytes_preserved": True,
        "fixed_step_auto_schedule": False,
        "complete_fun_007675f0_semantics": False,
        "complete_fun_0076d100_semantics": False,
        "complete_fun_00770e80_semantics": False,
    }


__all__ = [
    "FORMAT",
    "PASS_COUNT",
    "PhysicsPassCallbacks",
    "AdaptedPhysicsPassCallbacks",
    "ContactOuterProviderChainRuntimeResult",
    "execute_fun_00770e80_contact_outer_provider_chain_runtime",
    "contract",
]
