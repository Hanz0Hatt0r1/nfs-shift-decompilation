"""Scheduling oracle for the typed FUN_007682c0 effect-provider outer-chain join.

The oracle narrows the previous arbitrary FUN_007682c0 callback to a typed
source-visible effect boundary. It deliberately does not reproduce the recovered
sqrt/x87 response arithmetic: exact machine scalar production remains external.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable

FORMAT = "SHIFT.Fun00770e80MotionReadEffectProviderChainRuntime/1"
PASS_COUNT = 2


@dataclass(frozen=True)
class MotionReadEffect:
    gate_open: bool
    accumulator_y_delta: float


@dataclass(frozen=True)
class PhysicsPassCallbacks:
    contact_factor: Callable[[], None]
    wheel_update: Callable[[], None]
    contact_response: Callable[[], None]
    contact_outer_input_provider: Callable[[], Any]
    motion_read_effect_provider: Callable[[], MotionReadEffect]
    motion_read_delta_consumer: Callable[[float], None]


@dataclass(frozen=True)
class AdaptedPhysicsPassCallbacks:
    contact_factor: Callable[[], None]
    wheel_update: Callable[[], None]
    contact_response: Callable[[], None]
    contact_outer_input_provider: Callable[[], Any]
    motion_read_gate: Callable[[], None]


@dataclass(frozen=True)
class MotionReadEffectProviderChainRuntimeResult:
    joined_result: Any
    physics_pass_provider_call_counts: tuple[int, int]
    motion_read_effect_provider_call_counts: tuple[int, int]
    motion_read_delta_consumer_call_counts: tuple[int, int]
    motion_read_gate_open_count: int
    events: tuple[str, ...]


def _require_callable(value: object, label: str) -> None:
    if not callable(value):
        raise ValueError(f"Phase 696 requires {label}")


def _validate_effect(effect: MotionReadEffect) -> None:
    if not isfinite(float(effect.accumulator_y_delta)):
        raise ValueError("Phase 696 FUN_007682c0 effect delta must be finite")
    if not effect.gate_open and float(effect.accumulator_y_delta) != 0.0:
        raise ValueError("Phase 696 closed FUN_007682c0 gate cannot carry delta")


def execute_fun_00770e80_motion_read_effect_provider_chain_runtime(
    phase693_executor: Callable[[Callable[[int], AdaptedPhysicsPassCallbacks]], Any] | None,
    physics_pass_provider: Callable[[int], PhysicsPassCallbacks] | None,
) -> MotionReadEffectProviderChainRuntimeResult:
    if phase693_executor is None:
        raise ValueError("Phase 696 requires the Phase 693 executor")
    if physics_pass_provider is None:
        raise ValueError("Phase 696 requires the typed physics-pass provider")

    pass_calls = [0, 0]
    effect_calls = [0, 0]
    consumer_calls = [0, 0]
    gate_open_count = 0
    events: list[str] = []

    def adapted_provider(pass_index: int) -> AdaptedPhysicsPassCallbacks:
        if pass_index < 0 or pass_index >= PASS_COUNT:
            raise ValueError("Phase 696 pass index exceeds proven domain")
        if pass_calls[pass_index] != 0:
            raise ValueError("Phase 696 physics-pass provider repeated one pass")

        typed = physics_pass_provider(pass_index)
        pass_calls[pass_index] += 1
        _require_callable(typed.contact_factor, "FUN_00765c40 callback")
        _require_callable(typed.wheel_update, "FUN_00758b50 callback")
        _require_callable(typed.contact_response, "FUN_00766510 callback")
        _require_callable(
            typed.contact_outer_input_provider,
            "FUN_007675f0 typed input provider",
        )
        _require_callable(
            typed.motion_read_effect_provider,
            "FUN_007682c0 typed effect provider",
        )
        _require_callable(
            typed.motion_read_delta_consumer,
            "FUN_007682c0 typed accumulator consumer",
        )

        def motion_read_gate() -> None:
            nonlocal gate_open_count
            events.append(f"motion-read-effect-provider:{pass_index}")
            effect_calls[pass_index] += 1
            effect = typed.motion_read_effect_provider()
            _validate_effect(effect)
            if effect.gate_open:
                typed.motion_read_delta_consumer(float(effect.accumulator_y_delta))
                consumer_calls[pass_index] += 1
                gate_open_count += 1
                events.append(f"motion-read-delta-consumer:{pass_index}")

        return AdaptedPhysicsPassCallbacks(
            contact_factor=typed.contact_factor,
            wheel_update=typed.wheel_update,
            contact_response=typed.contact_response,
            contact_outer_input_provider=typed.contact_outer_input_provider,
            motion_read_gate=motion_read_gate,
        )

    joined_result = phase693_executor(adapted_provider)

    if pass_calls != [1, 1]:
        raise ValueError("Phase 696 physics-pass provider cardinality mismatch")
    if effect_calls != [1, 1]:
        raise ValueError("Phase 696 FUN_007682c0 effect-provider cardinality mismatch")
    if any(value not in (0, 1) for value in consumer_calls):
        raise ValueError("Phase 696 FUN_007682c0 consumer cardinality mismatch")

    return MotionReadEffectProviderChainRuntimeResult(
        joined_result=joined_result,
        physics_pass_provider_call_counts=(pass_calls[0], pass_calls[1]),
        motion_read_effect_provider_call_counts=(effect_calls[0], effect_calls[1]),
        motion_read_delta_consumer_call_counts=(consumer_calls[0], consumer_calls[1]),
        motion_read_gate_open_count=gate_open_count,
        events=tuple(events),
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "phase693_contact_outer_provider_chain_reused": True,
        "fun_007682c0_typed_effect_provider": True,
        "fun_007682c0_typed_accumulator_delta_consumer": True,
        "fun_007682c0_arbitrary_callback_external": False,
        "fun_007682c0_effect_production_external": True,
        "fun_007682c0_body_identity_application_external": True,
        "fun_007682c0_machine_scalar_production_external": True,
        "host_sqrt_substitution_allowed": False,
        "host_trig_substitution_allowed": False,
        "persistent_body_bytes_preserved": True,
        "fixed_step_auto_schedule": False,
        "complete_fun_007682c0_semantics": False,
        "complete_fun_0076d100_semantics": False,
        "complete_fun_00770e80_semantics": False,
    }


__all__ = [
    "FORMAT",
    "PASS_COUNT",
    "MotionReadEffect",
    "PhysicsPassCallbacks",
    "AdaptedPhysicsPassCallbacks",
    "MotionReadEffectProviderChainRuntimeResult",
    "execute_fun_00770e80_motion_read_effect_provider_chain_runtime",
    "contract",
]
