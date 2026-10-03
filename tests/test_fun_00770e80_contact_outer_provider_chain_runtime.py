from __future__ import annotations

import pytest

from fun_00770e80_contact_outer_provider_chain_runtime import (
    PhysicsPassCallbacks,
    contract,
    execute_fun_00770e80_contact_outer_provider_chain_runtime,
)


def _typed_provider(events: list[str]):
    def provider(pass_index: int) -> PhysicsPassCallbacks:
        suffix = str(pass_index)
        return PhysicsPassCallbacks(
            contact_factor=lambda: events.append(f"FUN_00765c40:{suffix}"),
            wheel_update=lambda: events.append(f"FUN_00758b50:{suffix}"),
            contact_response=lambda: events.append(f"FUN_00766510:{suffix}"),
            contact_outer_input_provider=lambda: {"pass": pass_index},
            motion_read_gate=lambda: events.append(f"FUN_007682c0:{suffix}"),
        )

    return provider


def test_phase693_preserves_two_pass_order_and_executes_native_contact_outer() -> None:
    events: list[str] = []
    native_inputs: list[object] = []

    def phase691_executor(pass_provider):
        for pass_index in range(2):
            callbacks = pass_provider(pass_index)
            callbacks.contact_factor()
            callbacks.wheel_update()
            callbacks.contact_response()
            callbacks.contact_outer()
            callbacks.motion_read_gate()
        return "phase691-result"

    def native_contact_outer(value: object) -> None:
        native_inputs.append(value)
        events.append(f"FUN_007675f0:{value['pass']}")

    result = execute_fun_00770e80_contact_outer_provider_chain_runtime(
        phase691_executor,
        _typed_provider(events),
        native_contact_outer,
    )

    assert result.joined_result == "phase691-result"
    assert result.physics_pass_provider_call_counts == (1, 1)
    assert result.contact_outer_input_provider_call_counts == (1, 1)
    assert result.contact_outer_native_call_counts == (1, 1)
    assert native_inputs == [{"pass": 0}, {"pass": 1}]
    assert events == [
        "FUN_00765c40:0",
        "FUN_00758b50:0",
        "FUN_00766510:0",
        "FUN_007675f0:0",
        "FUN_007682c0:0",
        "FUN_00765c40:1",
        "FUN_00758b50:1",
        "FUN_00766510:1",
        "FUN_007675f0:1",
        "FUN_007682c0:1",
    ]
    assert result.events == (
        "contact-outer-input-provider:0",
        "contact-outer-native:0",
        "contact-outer-input-provider:1",
        "contact-outer-native:1",
    )


def test_phase693_rejects_missing_boundaries_before_anchor_side_effects() -> None:
    events: list[str] = []

    with pytest.raises(ValueError, match="typed physics-pass provider"):
        execute_fun_00770e80_contact_outer_provider_chain_runtime(
            lambda provider: None,
            None,
            lambda value: None,
        )

    def missing_contact_provider(_pass_index: int) -> PhysicsPassCallbacks:
        return PhysicsPassCallbacks(
            contact_factor=lambda: events.append("factor"),
            wheel_update=lambda: events.append("wheel"),
            contact_response=lambda: events.append("response"),
            contact_outer_input_provider=None,  # type: ignore[arg-type]
            motion_read_gate=lambda: events.append("motion"),
        )

    def execute_one(pass_provider):
        callbacks = pass_provider(0)
        callbacks.contact_factor()

    with pytest.raises(ValueError, match="typed input provider"):
        execute_fun_00770e80_contact_outer_provider_chain_runtime(
            execute_one,
            missing_contact_provider,
            lambda value: None,
        )
    assert events == []


def test_phase693_rejects_duplicate_or_incomplete_pass_execution() -> None:
    events: list[str] = []

    def duplicate(pass_provider):
        pass_provider(0)
        pass_provider(0)

    with pytest.raises(ValueError, match="repeated one pass"):
        execute_fun_00770e80_contact_outer_provider_chain_runtime(
            duplicate,
            _typed_provider(events),
            lambda value: None,
        )

    def incomplete(pass_provider):
        callbacks = pass_provider(0)
        callbacks.contact_factor()
        callbacks.wheel_update()
        callbacks.contact_response()
        callbacks.contact_outer()
        callbacks.motion_read_gate()

    with pytest.raises(ValueError, match="provider cardinality mismatch"):
        execute_fun_00770e80_contact_outer_provider_chain_runtime(
            incomplete,
            _typed_provider(events),
            lambda value: None,
        )


def test_phase693_contract_keeps_unproven_producers_external() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.Fun00770e80ContactOuterProviderChainRuntime/1"
    assert payload["phase691_scalar_provider_outer_chain_reused"] is True
    assert payload["fun_007675f0_typed_input_provider"] is True
    assert payload["fun_007675f0_native_kernel_internal"] is True
    assert payload["fun_007675f0_arbitrary_callback_external"] is False
    assert payload["fun_007675f0_input_production_external"] is True
    assert payload["machine_scalar_production_external"] is True
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["complete_fun_007675f0_semantics"] is False
