"""Reference oracle for the source-backed four-wheel FUN_00758b50 spring-gap batch.

This composes the existing wheel-kinematics and spring-gap references without
promoting the unresolved caller-consumed x87 value at runtime +0x548.  Slot
iteration and the block+0xf8 skip gate follow the recovered retail ordering.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from spring_helper_runtime import SpringGapStep
from wheel_kinematics_runtime import (
    WHEEL_RUNTIME_BASE,
    WHEEL_RUNTIME_STRIDE,
    WHEEL_STATE_BASE,
    WHEEL_STATE_STRIDE,
    WheelKinematicObservation,
    evaluate_wheel_spring_gap,
    prepare_wheel_kinematic_observation,
)

FORMAT = "SHIFT.WheelSpringGapBatchRuntime/1"
FUNCTION = "FUN_00758b50"
PRE_HELPER = "FUN_00755950"
SPRING_HELPER = "FUN_007555b0"
WHEEL_COUNT = 4


@dataclass(frozen=True)
class WheelSpringGapBatchSlotInput:
    skip_flag_nonzero: bool
    relative_vector: tuple[float, float, float]
    reference_length: float
    projection_input: float
    spring_type: int
    lower_boundary: float
    upper_boundary: float
    current_gap_before: float


@dataclass(frozen=True)
class WheelSpringGapBatchSlotResult:
    wheel_index: int
    kinematic: WheelKinematicObservation
    spring_state: SpringGapStep


@dataclass(frozen=True)
class WheelSpringGapBatchResult:
    processed: tuple[bool, bool, bool, bool]
    processed_order: tuple[int, ...]
    slots: tuple[WheelSpringGapBatchSlotResult | None, ...]

    @property
    def processed_count(self) -> int:
        return len(self.processed_order)


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def execute_wheel_spring_gap_batch(
    inputs: Sequence[WheelSpringGapBatchSlotInput],
) -> WheelSpringGapBatchResult:
    """Execute the proven pre-helper -> spring-gap portion for four wheel slots."""
    if len(inputs) != WHEEL_COUNT:
        raise ValueError("FUN_00758b50 batch requires exactly four wheel slots")

    processed = [False] * WHEEL_COUNT
    processed_order: list[int] = []
    slots: list[WheelSpringGapBatchSlotResult | None] = [None] * WHEEL_COUNT

    for wheel_index, slot in enumerate(inputs):
        # The retail +0xf8 gate precedes relative-vector construction and the
        # FUN_00755950 call.  Do not inspect downstream payload for a skipped slot.
        if slot.skip_flag_nonzero:
            continue

        if len(slot.relative_vector) != 3:
            raise ValueError("relative_vector must contain exactly 3 components")
        relative_vector = tuple(
            _finite(f"wheel[{wheel_index}].relative_vector", value)
            for value in slot.relative_vector
        )
        reference_length = _finite(
            f"wheel[{wheel_index}].reference_length", slot.reference_length
        )
        projection_input = _finite(
            f"wheel[{wheel_index}].projection_input", slot.projection_input
        )
        lower_boundary = _finite(
            f"wheel[{wheel_index}].lower_boundary", slot.lower_boundary
        )
        upper_boundary = _finite(
            f"wheel[{wheel_index}].upper_boundary", slot.upper_boundary
        )
        current_gap_before = _finite(
            f"wheel[{wheel_index}].current_gap_before", slot.current_gap_before
        )
        if int(slot.spring_type) < 0:
            raise ValueError("spring_type must be non-negative")

        kinematic = prepare_wheel_kinematic_observation(
            wheel_index=wheel_index,
            relative_vector=relative_vector,
            reference_length=reference_length,
            projection_input=projection_input,
        )
        spring_state = evaluate_wheel_spring_gap(
            spring_type=int(slot.spring_type),
            distance_reference=kinematic.reference_length,
            relative_length=kinematic.relative_length,
            lower_boundary=lower_boundary,
            upper_boundary=upper_boundary,
            previous_gap=current_gap_before,
            projection_input=kinematic.projection_input,
        )

        # Cross-contract identity checks: the composed result must still refer to
        # the source-visible slot and exact scalar handoff.
        if kinematic.wheel_state_offset != WHEEL_STATE_BASE + wheel_index * WHEEL_STATE_STRIDE:
            raise ValueError("mismatched wheel-state topology")
        if kinematic.wheel_runtime_offset != WHEEL_RUNTIME_BASE + wheel_index * WHEEL_RUNTIME_STRIDE:
            raise ValueError("mismatched wheel-runtime topology")
        if spring_state.displacement != kinematic.distance_error:
            raise ValueError("mismatched spring displacement handoff")
        expected_trigger = kinematic.stored_projection_value
        if spring_state.transition_triggered and spring_state.trigger_value != expected_trigger:
            raise ValueError("mismatched spring trigger handoff")

        processed[wheel_index] = True
        processed_order.append(wheel_index)
        slots[wheel_index] = WheelSpringGapBatchSlotResult(
            wheel_index=wheel_index,
            kinematic=kinematic,
            spring_state=spring_state,
        )

    return WheelSpringGapBatchResult(
        processed=tuple(processed),
        processed_order=tuple(processed_order),
        slots=tuple(slots),
    )


def build_wheel_spring_gap_batch_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "pre_helper": PRE_HELPER,
        "spring_helper": SPRING_HELPER,
        "wheel_count": WHEEL_COUNT,
        "iteration_order": [0, 1, 2, 3],
        "skip_gate": "wheel_state(block+0xf8) != 0 skips before downstream payload consumption",
        "composition": [
            "prepare FUN_00758b50 wheel kinematics",
            "distance_error = reference_length - relative_length",
            "stored_projection = -projection_input",
            "FUN_00755950 -> FUN_007555b0 gap/history state",
        ],
        "caller_x87_runtime_0x548": "unresolved_external",
        "final_body_application": "not_in_this_contract",
        "runtime_scheduling": "unproven",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "PRE_HELPER",
    "SPRING_HELPER",
    "WHEEL_COUNT",
    "WheelSpringGapBatchSlotInput",
    "WheelSpringGapBatchSlotResult",
    "WheelSpringGapBatchResult",
    "execute_wheel_spring_gap_batch",
    "build_wheel_spring_gap_batch_contract",
]
