from __future__ import annotations

import math

import pytest

from fun_00763570_machine_feedback_join_runtime import (
    PHASE686,
    PROVIDER,
    TRANSFORMS,
    MachineBatchInput,
    MachineWheelInput,
    build_machine_precomputed_payload,
    contract,
    execute_fun_00763570_machine_feedback_join_runtime,
)
from matrix_vector_transform_runtime import Matrix3x3


def diagonal_frame() -> Matrix3x3:
    return Matrix3x3(
        2.0, 0.0, 0.0,
        0.0, 3.0, 0.0,
        0.0, 0.0, 4.0,
    )


def machine_input() -> MachineBatchInput:
    return MachineBatchInput(
        wheels=tuple(
            MachineWheelInput(
                wheel_index=index,
                body_frame=diagonal_frame(),
                shared_velocity=(1.0 + index, 2.0, 3.0),
            )
            for index in range(4)
        ),
        rear_pair_average_enabled=True,
        mode=0,
        global_config_byte=True,
    )


def test_machine_payload_uses_phase687_transforms() -> None:
    payload = build_machine_precomputed_payload(machine_input())
    assert [wheel["wheel_index"] for wheel in payload["wheels"]] == [0, 1, 2, 3]
    first = payload["wheels"][0]
    assert first["local_velocity"] == pytest.approx((2.0, 6.0, 12.0))
    assert first["reconstructed_world_velocity"] == pytest.approx((4.0, 0.0, 0.0))
    assert payload["rear_pair_average_enabled"] is True
    assert payload["mode"] == 0
    assert payload["global_config_byte"] is True


def test_machine_join_preserves_provider_transform_phase686_order() -> None:
    seen: list[object] = []

    def provider() -> MachineBatchInput:
        seen.append(PROVIDER)
        return machine_input()

    def phase686(payload: dict[str, object]) -> str:
        seen.append((PHASE686, payload))
        return "continued"

    result = execute_fun_00763570_machine_feedback_join_runtime(provider, phase686)
    assert result.events == (PROVIDER, TRANSFORMS, PHASE686)
    assert result.phase686_result == "continued"
    assert seen[0] == PROVIDER
    assert seen[1][0] == PHASE686


def test_machine_payload_rejects_wrong_wheel_order() -> None:
    bad = list(machine_input().wheels)
    bad[1] = MachineWheelInput(
        wheel_index=3,
        body_frame=diagonal_frame(),
        shared_velocity=(2.0, 2.0, 3.0),
    )
    with pytest.raises(ValueError, match="wheel order"):
        build_machine_precomputed_payload(
            MachineBatchInput(wheels=tuple(bad))
        )


def test_machine_payload_rejects_non_finite_consumed_vector() -> None:
    bad = list(machine_input().wheels)
    bad[0] = MachineWheelInput(
        wheel_index=0,
        body_frame=diagonal_frame(),
        shared_velocity=(math.inf, 2.0, 3.0),
    )
    with pytest.raises(ValueError):
        build_machine_precomputed_payload(MachineBatchInput(wheels=tuple(bad)))


def test_machine_join_requires_both_boundaries() -> None:
    with pytest.raises(ValueError, match="provider"):
        execute_fun_00763570_machine_feedback_join_runtime(None, lambda payload: payload)
    with pytest.raises(ValueError, match="Phase 686"):
        execute_fun_00763570_machine_feedback_join_runtime(machine_input, None)


def test_contract_keeps_remaining_precision_and_scheduler_gates_explicit() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.Fun00763570MachineFeedbackJoinRuntime/1"
    assert payload["machine_helpers"] == ["FUN_007af0a0", "FUN_007af010"]
    assert payload["native_machine_transforms_used"] is True
    assert payload["phase686_join_reused"] is True
    assert payload["precomputed_reconstructed_vector_provider_removed"] is True
    assert payload["ambient_x87_control_word_proven"] is False
    assert payload["complete_fun_00763570_semantics"] is False
