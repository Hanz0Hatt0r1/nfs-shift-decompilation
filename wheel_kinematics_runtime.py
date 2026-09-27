"""Evidence-backed wheel kinematics boundary from retail SHIFT.exe.c.

Phase 364 reconstructs the part of FUN_00758b50 that can be made executable
without guessing the downstream tyre/contact force law.

The adapter deliberately separates:
- the exact four-wheel object topology and byte strides;
- exact radial-vector normalization;
- exact distance-error / projection handoff into FUN_00755950;
- exact front/rear pair adjustment formulas;
- the opaque FUN_007555b0 helper result.

No physical units or undocumented force semantics are assigned.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Sequence

from spring_helper_runtime import SpringGapStep, update_spring_gap_state

FORMAT = "SHIFT.WheelKinematicsRuntime/1"
FUNCTION = "FUN_00758b50"
CALLER = "FUN_0076d100"
SOURCE_FILE = "./Source/Vehicle/hdvehicle.cpp"
SOURCE_LINE = 753071

WHEEL_STATE_BASE = 0x848
WHEEL_STATE_STRIDE = 0xA80
WHEEL_RUNTIME_BASE = 0x400
WHEEL_RUNTIME_STRIDE = 0xA80

WHEEL_ACTIVE_FLAG_OFFSET = 0xF8
WHEEL_FINAL_ACTIVE_FLAG_OFFSET = 0x11C

DISTANCE_REFERENCE_OFFSET = 0x138  # runtime +0x538
DISTANCE_ERROR_OFFSET = 0x128      # runtime +0x528
PROJECTION_VALUE_OFFSET = 0x130    # runtime +0x530
HELPER_OUTPUT_OFFSET = 0x148       # runtime +0x548

HELPER_OBJECT_OFFSET = 0x80
HELPER_CURRENT_GAP_OFFSET = HELPER_OBJECT_OFFSET + 0x248
HELPER_PREVIOUS_GAP_OFFSET = HELPER_OBJECT_OFFSET + 0x250
HELPER_CROSSING_FLAG_OFFSET = HELPER_OBJECT_OFFSET + 0x260
HELPER_TRIGGER_VALUE_OFFSET = HELPER_OBJECT_OFFSET + 0x258


@dataclass(frozen=True)
class WheelKinematicObservation:
    """Prepared scalar/vector inputs immediately before FUN_00755950."""

    wheel_index: int
    wheel_state_offset: int
    wheel_runtime_offset: int
    relative_vector: tuple[float, float, float]
    relative_length: float
    relative_unit: tuple[float, float, float]
    reference_length: float
    distance_error: float
    projection_input: float
    stored_projection_value: float


@dataclass(frozen=True)
class PairAdjustmentObservation:
    """Exact pre-helper pair delta used by FUN_00758b50."""

    pair: str
    left_source_a: float
    left_source_b: float
    right_source_a: float
    right_source_b: float
    scale: float
    delta: float

    @property
    def left_after(self) -> float:
        return self.delta

    @property
    def right_after(self) -> float:
        return -self.delta


def normalize_relative_vector(
    relative_vector: Sequence[float],
) -> tuple[float, tuple[float, float, float]]:
    """Match the source normalization of the wheel-to-vehicle relative vector."""
    if len(relative_vector) != 3:
        raise ValueError("relative_vector must contain exactly 3 components")
    vector = tuple(float(value) for value in relative_vector)
    length = sqrt(sum(component * component for component in vector))
    if length == 0.0:
        raise ValueError("FUN_00758b50 normalizes a zero-length relative vector")
    inverse = 1.0 / length
    return length, tuple(component * inverse for component in vector)


def prepare_wheel_kinematic_observation(
    *,
    wheel_index: int,
    relative_vector: Sequence[float],
    reference_length: float,
    projection_input: float,
) -> WheelKinematicObservation:
    """Prepare the exact scalar handoff made to FUN_00755950 for one active wheel."""
    if not 0 <= wheel_index < 4:
        raise ValueError("wheel_index must be in [0, 3]")
    relative_length, relative_unit = normalize_relative_vector(relative_vector)
    reference = float(reference_length)
    projection = float(projection_input)
    return WheelKinematicObservation(
        wheel_index=wheel_index,
        wheel_state_offset=WHEEL_STATE_BASE + wheel_index * WHEEL_STATE_STRIDE,
        wheel_runtime_offset=WHEEL_RUNTIME_BASE + wheel_index * WHEEL_RUNTIME_STRIDE,
        relative_vector=tuple(float(value) for value in relative_vector),
        relative_length=relative_length,
        relative_unit=relative_unit,
        reference_length=reference,
        distance_error=reference - relative_length,
        projection_input=projection,
        stored_projection_value=-projection,
    )


def evaluate_wheel_spring_gap(
    *,
    spring_type: int,
    distance_reference: float,
    relative_length: float,
    lower_boundary: float,
    upper_boundary: float,
    previous_gap: float,
    projection_input: float,
) -> SpringGapStep:
    """Join FUN_00755950 scalar preparation to the decoded gap-state helper."""
    displacement = float(distance_reference) - float(relative_length)
    return update_spring_gap_state(
        spring_type=spring_type,
        displacement=displacement,
        lower_boundary=lower_boundary,
        upper_boundary=upper_boundary,
        previous_gap=previous_gap,
        trigger_value=-float(projection_input),
    )


def compute_pair_delta(
    *,
    source_a_left: float,
    source_b_left: float,
    source_a_right: float,
    source_b_right: float,
    scale: float,
) -> float:
    """Reproduce ((left A-left B)-(right A-right B))*scale exactly."""
    return (
        (float(source_a_left) - float(source_b_left))
        - (float(source_a_right) - float(source_b_right))
    ) * float(scale)


def build_pair_adjustment_observation(
    *,
    pair: str,
    source_a_left: float,
    source_b_left: float,
    source_a_right: float,
    source_b_right: float,
    scale: float,
) -> PairAdjustmentObservation:
    if pair not in {"front", "rear"}:
        raise ValueError("pair must be 'front' or 'rear'")
    delta = compute_pair_delta(
        source_a_left=source_a_left,
        source_b_left=source_b_left,
        source_a_right=source_a_right,
        source_b_right=source_b_right,
        scale=scale,
    )
    return PairAdjustmentObservation(
        pair=pair,
        left_source_a=float(source_a_left),
        left_source_b=float(source_b_left),
        right_source_a=float(source_a_right),
        right_source_b=float(source_b_right),
        scale=float(scale),
        delta=delta,
    )


def build_wheel_kinematics_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "caller": CALLER,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "wheel_state": {
            "base": WHEEL_STATE_BASE,
            "stride": WHEEL_STATE_STRIDE,
            "active_flag_offset": WHEEL_ACTIVE_FLAG_OFFSET,
            "final_transform_flag_offset": WHEEL_FINAL_ACTIVE_FLAG_OFFSET,
            "count": 4,
        },
        "wheel_runtime": {
            "base": WHEEL_RUNTIME_BASE,
            "stride": WHEEL_RUNTIME_STRIDE,
            "pre_helper": "FUN_00755950",
            "helper": "FUN_007555b0",
            "helper_object_offset": HELPER_OBJECT_OFFSET,
            "fields": {
                "distance_reference": DISTANCE_REFERENCE_OFFSET,
                "distance_error": DISTANCE_ERROR_OFFSET,
                "projection_value": PROJECTION_VALUE_OFFSET,
                "helper_output": HELPER_OUTPUT_OFFSET,
                "helper_return": "unresolved",
                "helper_current_gap": HELPER_CURRENT_GAP_OFFSET,
                "helper_previous_gap": HELPER_PREVIOUS_GAP_OFFSET,
                "helper_crossing_flag": HELPER_CROSSING_FLAG_OFFSET,
                "helper_trigger_value": HELPER_TRIGGER_VALUE_OFFSET,
            },
            "field_offsets_absolute": {
                "distance_reference": WHEEL_RUNTIME_BASE + DISTANCE_REFERENCE_OFFSET,
                "distance_error": WHEEL_RUNTIME_BASE + DISTANCE_ERROR_OFFSET,
                "projection_value": WHEEL_RUNTIME_BASE + PROJECTION_VALUE_OFFSET,
                "helper_output": WHEEL_RUNTIME_BASE + HELPER_OUTPUT_OFFSET,
                "helper_current_gap": WHEEL_RUNTIME_BASE + HELPER_CURRENT_GAP_OFFSET,
                "helper_previous_gap": WHEEL_RUNTIME_BASE + HELPER_PREVIOUS_GAP_OFFSET,
                "helper_crossing_flag": WHEEL_RUNTIME_BASE + HELPER_CROSSING_FLAG_OFFSET,
                "helper_trigger_value": WHEEL_RUNTIME_BASE + HELPER_TRIGGER_VALUE_OFFSET,
            },
        },
        "per_wheel_sequence": [
            "skip when wheel-state active flag at block+0xF8 is non-zero",
            "construct the wheel/vehicle relative vector",
            "normalize the relative vector and retain its length",
            "compute reference_length - relative_length",
            "store the negated projection input at runtime +0x530",
            "FUN_00755950 computes displacement=runtime(+0x538)-relative_length",
            "FUN_00755950 calls FUN_007555b0(helper=runtime+0x80, displacement, -projection_input)",
            "store helper x87 return at runtime +0x548",
        ],
        "pair_adjustments": {
            "front": {
                "guard_offsets": [0x940, 0x13C0],
                "delta_sources": [0x928, 0x938, 0x13A8, 0x13B8],
                "scale_offset": 0x2E20,
                "destinations": [0x948, 0x13C8],
                "optional_helper": "FUN_007555b0(+0x2E80, 0, (+0x928 + +0x13A8)*0.5, (+0x13B0 + +0x930)*0.5)",
            },
            "rear": {
                "guard_offsets": [0x1E40, 0x28C0],
                "delta_sources": [0x1E28, 0x1E38, 0x28A8, 0x28B8],
                "scale_offset": 0x2E28,
                "destinations": [0x1E48, 0x28C8],
                "optional_helper": "FUN_007555b0(+0x3100, 2, (+0x1E28 + +0x28A8)*0.5, (+0x28B0 + +0x1E30)*0.5)",
            },
        },
        "final_per_wheel_transform": {
            "guard_flag_offset": 0x11C,
            "input_pointer_offset": 0x00,
            "scale_field_offset": 0x124,
            "wheel_vector_offset": 0x1C,
            "vehicle_vector_offset": 0x4C,
            "wheel_transform_helper": "FUN_007baa70",
            "vehicle_transform_helper": "FUN_007baaf0",
            "condition": "pointer non-zero and block+0x11C == 0",
        },
        "status": (
            "exact wheel-kinematics/control-flow boundary with decoded spring helper; "
            "downstream tyre-force/contact semantics remain unresolved"
        ),
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "CALLER",
    "SOURCE_LINE",
    "WHEEL_STATE_BASE",
    "WHEEL_STATE_STRIDE",
    "WHEEL_RUNTIME_BASE",
    "WHEEL_RUNTIME_STRIDE",
    "WHEEL_ACTIVE_FLAG_OFFSET",
    "WHEEL_FINAL_ACTIVE_FLAG_OFFSET",
    "DISTANCE_REFERENCE_OFFSET",
    "DISTANCE_ERROR_OFFSET",
    "PROJECTION_VALUE_OFFSET",
    "HELPER_OUTPUT_OFFSET",
    "HELPER_OBJECT_OFFSET",
    "HELPER_CURRENT_GAP_OFFSET",
    "HELPER_PREVIOUS_GAP_OFFSET",
    "HELPER_CROSSING_FLAG_OFFSET",
    "HELPER_TRIGGER_VALUE_OFFSET",
    "WheelKinematicObservation",
    "PairAdjustmentObservation",
    "normalize_relative_vector",
    "prepare_wheel_kinematic_observation",
    "compute_pair_delta",
    "build_pair_adjustment_observation",
    "evaluate_wheel_spring_gap",
    "build_wheel_kinematics_contract",
]
