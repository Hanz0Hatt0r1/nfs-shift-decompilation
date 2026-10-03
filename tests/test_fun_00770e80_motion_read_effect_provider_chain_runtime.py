from __future__ import annotations

import pytest

from fun_00770e80_motion_read_effect_provider_chain_runtime import (
    MotionReadEffect,
    PhysicsPassCallbacks,
    contract,
    execute_fun_00770e80_motion_read_effect_provider_chain_runtime,
)


def _typed_provider(events: list[str], *, closed_second: bool = False):
    def provider(pass_index: int) -> PhysicsPassCallbacks:
        suffix = str(pass_index)
        gate_open = not (closed_second and pass_index == 1)
        return PhysicsPassCallbacks(
            contact_factor=lambda: events.append(f"FUN_00765c40:{suffix}"),
            wheel_update=lambda: events.append(f"FUN_00758b50:{suffix}"),
            contact_response=lambda: events.append(f"FUN_00766510:{suffix}"),
            contact_outer_input_provider=lambda: {"pass": pass_index},
            motion_read_effect_provider=lambda: MotionReadEffect(
                gate_open=gate_open,
                accumulator_y_delta=(-2.5 - pass_index) if gate_open else 0.0,
            ),
            motion_read_delta_consumer=lambda value: events.append(
                f"FUN_007682c0-delta:{suffix}:{value}"
            ),
        )

    return provider


def test_phase696_preserves_anchor_order_and_applies_only_open_gate_effects() -> None:
    events: list[str] = []

    def phase693_executor(pass_provider):
        for pass_index in range(2):
            callbacks = pass_provider(pass_index)
            callbacks.contact_factor()
            callbacks.wheel_update()
            callbacks.contact_response()
            callbacks.contact_outer_input_provider()
            events.append(f"FUN_007675f0:{pass_index}")
            callbacks.motion_read_gate()
        return "phase693-result"

    result = execute_fun_00770e80_motion_read_effect_provider_chain_runtime(
        phase693_executor,
        _typed_provider(events, closed_second=True),
    )

    assert result.joined_result == "phase693-result"
    assert result.physics_pass_provider_call_counts == (1, 1)
    assert result.motion_read_effect_provider_call_counts == (1, 1)
    assert result.motion_read_delta_consumer_call_counts == (1, 0)
    assert result.motion_read_gate_open_count == 1
    assert events == [
        "FUN_00765c40:0",
        "FUN_00758b50:0",
        "FUN_00766510:0",
        "FUN_007675f0:0",
        "FUN_007682c0-delta:0:-2.5",
        "FUN_00765c40:1",
        "FUN_00758b50:1",
        "FUN_00766510:1",
        "FUN_007675f0:1",
    ]
    assert result.events == (
        "motion-read-effect-provider:0",
        "motion-read-delta-consumer:0",
        "motion-read-effect-provider:1",
    )


def test_phase696_rejects_invalid_effects_before_delta_consumer() -> None:
    events: list[str] = []

    def execute_one(pass_provider):
        callbacks = pass_provider(0)
        callbacks.contact_factor()
        callbacks.wheel_update()
        callbacks.contact_response()
        callbacks.contact_outer_input_provider()
        callbacks.motion_read_gate()

    def closed_nonzero(_pass_index: int) -> PhysicsPassCallbacks:
        return PhysicsPassCallbacks(
            contact_factor=lambda: events.append("factor"),
            wheel_update=lambda: events.append("wheel"),
            contact_response=lambda: events.append("response"),
            contact_outer_input_provider=lambda: object(),
            motion_read_effect_provider=lambda: MotionReadEffect(False, 1.0),
            motion_read_delta_consumer=lambda value: events.append("consumer"),
        )

    with pytest.raises(ValueError, match="closed FUN_007682c0 gate"):
        execute_fun_00770e80_motion_read_effect_provider_chain_runtime(
            execute_one,
            closed_nonzero,
        )
    assert "consumer" not in events

    events.clear()

    def nonfinite(_pass_index: int) -> PhysicsPassCallbacks:
        callbacks = closed_nonzero(_pass_index)
        return PhysicsPassCallbacks(
            contact_factor=callbacks.contact_factor,
            wheel_update=callbacks.wheel_update,
            contact_response=callbacks.contact_response,
            contact_outer_input_provider=callbacks.contact_outer_input_provider,
            motion_read_effect_provider=lambda: MotionReadEffect(True, float("nan")),
            motion_read_delta_consumer=callbacks.motion_read_delta_consumer,
        )

    with pytest.raises(ValueError, match="must be finite"):
        execute_fun_00770e80_motion_read_effect_provider_chain_runtime(
            execute_one,
            nonfinite,
        )
    assert "consumer" not in events


def test_phase696_rejects_missing_typed_boundaries_before_anchor_side_effects() -> None:
    events: list[str] = []

    with pytest.raises(ValueError, match="typed physics-pass provider"):
        execute_fun_00770e80_motion_read_effect_provider_chain_runtime(
            lambda provider: None,
            None,
        )

    def missing_provider(_pass_index: int) -> PhysicsPassCallbacks:
        return PhysicsPassCallbacks(
            contact_factor=lambda: events.append("factor"),
            wheel_update=lambda: events.append("wheel"),
            contact_response=lambda: events.append("response"),
            contact_outer_input_provider=lambda: object(),
            motion_read_effect_provider=None,  # type: ignore[arg-type]
            motion_read_delta_consumer=lambda value: events.append("consumer"),
        )

    def execute_one(pass_provider):
        callbacks = pass_provider(0)
        callbacks.contact_factor()

    with pytest.raises(ValueError, match="typed effect provider"):
        execute_fun_00770e80_motion_read_effect_provider_chain_runtime(
            execute_one,
            missing_provider,
        )
    assert events == []


def test_phase696_rejects_duplicate_or_incomplete_pass_execution() -> None:
    events: list[str] = []

    def duplicate(pass_provider):
        pass_provider(0)
        pass_provider(0)

    with pytest.raises(ValueError, match="repeated one pass"):
        execute_fun_00770e80_motion_read_effect_provider_chain_runtime(
            duplicate,
            _typed_provider(events),
        )

    def incomplete(pass_provider):
        callbacks = pass_provider(0)
        callbacks.contact_factor()
        callbacks.wheel_update()
        callbacks.contact_response()
        callbacks.contact_outer_input_provider()
        callbacks.motion_read_gate()

    with pytest.raises(ValueError, match="provider cardinality mismatch"):
        execute_fun_00770e80_motion_read_effect_provider_chain_runtime(
            incomplete,
            _typed_provider(events),
        )


def test_phase696_contract_keeps_machine_and_identity_producers_external() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.Fun00770e80MotionReadEffectProviderChainRuntime/1"
    assert payload["phase693_contact_outer_provider_chain_reused"] is True
    assert payload["fun_007682c0_typed_effect_provider"] is True
    assert payload["fun_007682c0_typed_accumulator_delta_consumer"] is True
    assert payload["fun_007682c0_arbitrary_callback_external"] is False
    assert payload["fun_007682c0_effect_production_external"] is True
    assert payload["fun_007682c0_body_identity_application_external"] is True
    assert payload["fun_007682c0_machine_scalar_production_external"] is True
    assert payload["host_sqrt_substitution_allowed"] is False
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["complete_fun_007682c0_semantics"] is False
