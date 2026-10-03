"""Reference orchestration for the Phase 701 persistent provider session.

This module models provider admission, adaptation, cardinality and transactional
session telemetry only. Physics arithmetic remains in the existing native/source-
backed Phase 697 path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

FORMAT = "SHIFT.NativeVehicleProviderSession/1"
PASS_COUNT = 2
PROVIDER_NAMES = (
    "contact_factor",
    "wheel_update",
    "contact_response",
    "contact_outer_input",
    "motion_read_effect",
    "motion_read_delta_consumer",
    "scalar_provider_factory",
    "half_step_refresh",
    "post_half_step",
)


@dataclass(frozen=True)
class ProviderBundle:
    contact_factor: Callable[[int], None]
    wheel_update: Callable[[int], None]
    contact_response: Callable[[int], None]
    contact_outer_input: Callable[[int], Any]
    motion_read_effect: Callable[[int], Any]
    motion_read_delta_consumer: Callable[[int, float], None]
    scalar_provider_factory: Callable[[int], Callable[..., Any]]
    half_step_refresh: Callable[[int, float, bytes], Any]
    post_half_step: Callable[[int], None]


@dataclass
class SessionTelemetry:
    contact_factor_call_count: int = 0
    wheel_update_call_count: int = 0
    contact_response_call_count: int = 0
    contact_outer_input_call_count: int = 0
    motion_read_effect_call_count: int = 0
    motion_read_delta_consumer_call_count: int = 0
    scalar_provider_factory_call_count: int = 0
    half_step_refresh_call_count: int = 0
    post_half_step_call_count: int = 0


@dataclass
class ProviderSessionState:
    step_count: int = 0
    last_telemetry: SessionTelemetry | None = None


def _require_bundle(bundle: ProviderBundle) -> None:
    for name in PROVIDER_NAMES:
        if not callable(getattr(bundle, name, None)):
            raise ValueError(
                f"Phase 701 requires all nine Phase 699 provider boundaries: {name}"
            )


def execute_provider_session_step(
    state: ProviderSessionState,
    bundle: ProviderBundle,
    *,
    outer_timestep: float,
    phase697_executor: Callable[[Callable[..., Any], Callable[..., Any], Callable[..., Any]], Any],
) -> Any:
    """Execute one explicit Phase 697 step through a persistent provider bundle."""
    _require_bundle(bundle)
    if not callable(phase697_executor):
        raise ValueError("Phase 701 requires the Phase 697 executor")

    telemetry = SessionTelemetry()

    def pass_provider(pass_index: int) -> dict[str, Callable[..., Any]]:
        if pass_index < 0 or pass_index >= PASS_COUNT:
            raise ValueError("Phase 701 pass index exceeds proven domain")

        def contact_factor() -> None:
            telemetry.contact_factor_call_count += 1
            bundle.contact_factor(pass_index)

        def wheel_update() -> None:
            telemetry.wheel_update_call_count += 1
            bundle.wheel_update(pass_index)

        def contact_response() -> None:
            telemetry.contact_response_call_count += 1
            bundle.contact_response(pass_index)

        def contact_outer_input() -> Any:
            telemetry.contact_outer_input_call_count += 1
            return bundle.contact_outer_input(pass_index)

        def motion_read_effect() -> Any:
            telemetry.motion_read_effect_call_count += 1
            return bundle.motion_read_effect(pass_index)

        def motion_read_delta_consumer(delta: float) -> None:
            telemetry.motion_read_delta_consumer_call_count += 1
            bundle.motion_read_delta_consumer(pass_index, delta)

        return {
            "contact_factor": contact_factor,
            "wheel_update": wheel_update,
            "contact_response": contact_response,
            "contact_outer_input": contact_outer_input,
            "motion_read_effect": motion_read_effect,
            "motion_read_delta_consumer": motion_read_delta_consumer,
        }

    def half_step_provider(pass_index: int, half_timestep: float, body_bytes: bytes):
        telemetry.half_step_refresh_call_count += 1
        refresh = bundle.half_step_refresh(pass_index, half_timestep, body_bytes)
        telemetry.scalar_provider_factory_call_count += 1
        scalar_provider = bundle.scalar_provider_factory(pass_index)
        if not callable(scalar_provider):
            raise ValueError("Phase 701 scalar provider factory returned no provider")
        return refresh, scalar_provider

    def post_half_step(pass_index: int) -> None:
        telemetry.post_half_step_call_count += 1
        bundle.post_half_step(pass_index)

    result = phase697_executor(pass_provider, half_step_provider, post_half_step)

    state.step_count += 1
    state.last_telemetry = telemetry
    return result


def contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "phase697_persistent_outer_path_reused": True,
        "phase699_external_provider_count": 9,
        "provider_boundaries": list(PROVIDER_NAMES),
        "all_top_level_provider_boundaries_required_before_execution": True,
        "session_telemetry_committed_after_success": True,
        "external_provider_side_effects_transactional": False,
        "provider_semantics_promoted": False,
        "machine_scalar_math_internalized": False,
        "vehicle_body_identity_proven": False,
        "vehicle_world_transform_proven": False,
        "fixed_step_auto_schedule": False,
        "deep_outer_update_executable_schedule_enabled": False,
        "original_game_executed": False,
        "new_runtime_capture_required": False,
    }


__all__ = [
    "FORMAT",
    "PASS_COUNT",
    "PROVIDER_NAMES",
    "ProviderBundle",
    "SessionTelemetry",
    "ProviderSessionState",
    "execute_provider_session_step",
    "contract",
]
