from __future__ import annotations

from dataclasses import replace

import pytest

from native_vehicle_provider_session_runtime import (
    ProviderBundle,
    ProviderSessionState,
    contract,
    execute_provider_session_step,
)


def _bundle(events: list[str]) -> ProviderBundle:
    def scalar_factory(pass_index: int):
        events.append(f"scalar-factory:{pass_index}")

        def scalar_provider(*_args):
            return (0.0, 0.0, 0.0, 1.0)

        return scalar_provider

    return ProviderBundle(
        contact_factor=lambda p: events.append(f"contact-factor:{p}"),
        wheel_update=lambda p: events.append(f"wheel-update:{p}"),
        contact_response=lambda p: events.append(f"contact-response:{p}"),
        contact_outer_input=lambda p: events.append(f"contact-input:{p}") or {"pass": p},
        motion_read_effect=lambda p: events.append(f"motion-effect:{p}") or {"gate_open": True, "delta": -2.5},
        motion_read_delta_consumer=lambda p, d: events.append(f"motion-delta:{p}:{d}"),
        scalar_provider_factory=scalar_factory,
        half_step_refresh=lambda p, dt, body: events.append(f"half-refresh:{p}:{dt}:{body.decode()}") or {"pass": p},
        post_half_step=lambda p: events.append(f"post-half:{p}"),
    )


def _phase697_executor(events: list[str]):
    def execute(pass_provider, half_step_provider, post_half_step):
        body = b"body0"
        for pass_index in range(2):
            callbacks = pass_provider(pass_index)
            callbacks["contact_factor"]()
            callbacks["wheel_update"]()
            callbacks["contact_response"]()
            callbacks["contact_outer_input"]()
            effect = callbacks["motion_read_effect"]()
            if effect["gate_open"]:
                callbacks["motion_read_delta_consumer"](effect["delta"])
            _refresh, scalar = half_step_provider(pass_index, 0.25, body)
            scalar()
            post_half_step(pass_index)
            body = f"body{pass_index + 1}".encode()
        events.append("phase697-commit")
        return "joined"

    return execute


def test_session_adapts_all_nine_boundaries_and_commits_telemetry() -> None:
    events: list[str] = []
    state = ProviderSessionState()
    result = execute_provider_session_step(
        state,
        _bundle(events),
        outer_timestep=0.5,
        phase697_executor=_phase697_executor(events),
    )

    assert result == "joined"
    assert state.step_count == 1
    assert state.last_telemetry is not None
    telemetry = state.last_telemetry
    assert telemetry.contact_factor_call_count == 2
    assert telemetry.wheel_update_call_count == 2
    assert telemetry.contact_response_call_count == 2
    assert telemetry.contact_outer_input_call_count == 2
    assert telemetry.motion_read_effect_call_count == 2
    assert telemetry.motion_read_delta_consumer_call_count == 2
    assert telemetry.scalar_provider_factory_call_count == 2
    assert telemetry.half_step_refresh_call_count == 2
    assert telemetry.post_half_step_call_count == 2
    assert events[-1] == "phase697-commit"


def test_missing_boundary_is_rejected_before_executor_or_provider_side_effects() -> None:
    events: list[str] = []
    bundle = replace(_bundle(events), contact_response=None)  # type: ignore[arg-type]
    executor_calls = 0

    def executor(*_args):
        nonlocal executor_calls
        executor_calls += 1
        raise AssertionError("executor must not run")

    with pytest.raises(ValueError, match="contact_response"):
        execute_provider_session_step(
            ProviderSessionState(),
            bundle,
            outer_timestep=0.5,
            phase697_executor=executor,
        )
    assert executor_calls == 0
    assert events == []


def test_failed_step_does_not_commit_session_owned_telemetry() -> None:
    events: list[str] = []
    state = ProviderSessionState(step_count=4)

    def failing_executor(pass_provider, *_args):
        callbacks = pass_provider(0)
        callbacks["contact_factor"]()
        raise RuntimeError("injected failure")

    with pytest.raises(RuntimeError, match="injected failure"):
        execute_provider_session_step(
            state,
            _bundle(events),
            outer_timestep=0.5,
            phase697_executor=failing_executor,
        )
    assert state.step_count == 4
    assert state.last_telemetry is None
    assert events == ["contact-factor:0"]


def test_empty_scalar_provider_factory_result_fails_closed_without_session_commit() -> None:
    events: list[str] = []
    state = ProviderSessionState()
    bundle = replace(
        _bundle(events),
        scalar_provider_factory=lambda p: events.append(f"empty-scalar:{p}"),
    )  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="scalar provider factory"):
        execute_provider_session_step(
            state,
            bundle,
            outer_timestep=0.5,
            phase697_executor=_phase697_executor(events),
        )
    assert state.step_count == 0
    assert state.last_telemetry is None


def test_contract_preserves_phase699_and_negative_boundaries() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.NativeVehicleProviderSession/1"
    assert payload["phase699_external_provider_count"] == 9
    assert len(payload["provider_boundaries"]) == 9
    assert payload["provider_semantics_promoted"] is False
    assert payload["machine_scalar_math_internalized"] is False
    assert payload["vehicle_body_identity_proven"] is False
    assert payload["vehicle_world_transform_proven"] is False
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["deep_outer_update_executable_schedule_enabled"] is False
    assert payload["original_game_executed"] is False
    assert payload["new_runtime_capture_required"] is False
