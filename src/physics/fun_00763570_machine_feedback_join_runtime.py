"""Reference/orchestration oracle for Phase 688 FUN_00763570 machine transforms.

Phase 687 machine-backed helpers close the operand-width and operation-order
boundary for FUN_007af0a0 and FUN_007af010.  This module composes those helpers
with the Phase 686 precomputed feedback join without promoting the remaining x87
control-word or higher-level scheduling unknowns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from matrix_vector_transform_runtime import (
    Matrix3x3,
    transform_fun_007af010,
    transform_fun_007af0a0,
)

FORMAT = "SHIFT.Fun00763570MachineFeedbackJoinRuntime/1"
PROVIDER = "machine-transform-input-provider"
TRANSFORMS = "FUN_007af0a0/FUN_007af010-machine-transforms"
PHASE686 = "phase686-precomputed-feedback-join"
WHEEL_COUNT = 4


@dataclass(frozen=True)
class MachineWheelInput:
    wheel_index: int
    body_frame: Matrix3x3
    shared_velocity: tuple[float, float, float]


@dataclass(frozen=True)
class MachineBatchInput:
    wheels: tuple[MachineWheelInput, ...]
    rear_pair_average_enabled: bool = False
    mode: int = 0
    global_config_byte: bool = False


@dataclass(frozen=True)
class MachineFeedbackJoinRuntimeResult:
    machine_payload: MachineBatchInput
    precomputed_payload: dict[str, Any]
    phase686_result: Any
    events: tuple[str, ...]


def _vec3(values: Sequence[float]) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError("shared velocity must contain exactly three values")
    result = tuple(float(value) for value in values)
    # The machine-backed transform helpers perform the finite checks.
    return result  # type: ignore[return-value]


def build_machine_precomputed_payload(
    machine: MachineBatchInput,
) -> dict[str, Any]:
    if len(machine.wheels) != WHEEL_COUNT:
        raise ValueError("FUN_00763570 machine input must contain exactly four wheels")

    wheels: list[dict[str, Any]] = []
    for expected_index, wheel in enumerate(machine.wheels):
        if wheel.wheel_index != expected_index:
            raise ValueError("FUN_00763570 machine wheel order must be 0,1,2,3")
        shared = _vec3(wheel.shared_velocity)
        local = transform_fun_007af0a0(wheel.body_frame, shared)
        reconstructed = transform_fun_007af010(wheel.body_frame, local.x)
        wheels.append(
            {
                "wheel_index": wheel.wheel_index,
                "shared_velocity": shared,
                "local_velocity": local.as_tuple(),
                "reconstructed_world_velocity": reconstructed.as_tuple(),
            }
        )

    return {
        "wheels": wheels,
        "rear_pair_average_enabled": bool(machine.rear_pair_average_enabled),
        "mode": int(machine.mode),
        "global_config_byte": bool(machine.global_config_byte),
    }


def execute_fun_00763570_machine_feedback_join_runtime(
    provider: Callable[[], MachineBatchInput] | None,
    phase686_executor: Callable[[dict[str, Any]], Any] | None,
) -> MachineFeedbackJoinRuntimeResult:
    if provider is None:
        raise ValueError("Phase 688 requires a machine transform input provider")
    if phase686_executor is None:
        raise ValueError("Phase 688 requires the Phase 686 continuation")

    events: list[str] = []
    machine_payload = provider()
    events.append(PROVIDER)
    precomputed_payload = build_machine_precomputed_payload(machine_payload)
    events.append(TRANSFORMS)
    phase686_result = phase686_executor(precomputed_payload)
    events.append(PHASE686)
    return MachineFeedbackJoinRuntimeResult(
        machine_payload=machine_payload,
        precomputed_payload=precomputed_payload,
        phase686_result=phase686_result,
        events=tuple(events),
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "source_function": "FUN_00763570",
        "source_child_function": "FUN_00755f80",
        "machine_helpers": ["FUN_007af0a0", "FUN_007af010"],
        "event_order": [PROVIDER, TRANSFORMS, PHASE686],
        "retail_wheel_order": [0, 1, 2, 3],
        "machine_vector_operand_width_bits": 64,
        "matrix_component_width_bits": 32,
        "native_machine_transforms_used": True,
        "phase686_join_reused": True,
        "precomputed_reconstructed_vector_provider_removed": True,
        "ambient_x87_control_word_proven": False,
        "complete_fun_00755f80_semantics": False,
        "complete_fun_00763570_semantics": False,
        "complete_fun_00765470_semantics": False,
    }
