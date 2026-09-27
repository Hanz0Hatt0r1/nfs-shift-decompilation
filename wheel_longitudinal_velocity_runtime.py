"""Evidence-backed wheel longitudinal-velocity extraction.

FUN_00755f80 converts the vehicle velocity vector into the active wheel's local
frame through FUN_007af0a0, retains the first component, reconstructs a vector
through FUN_007af010, and subtracts that reconstructed vector from the shared
vehicle velocity state.

The transform semantics of FUN_007af0a0/FUN_007af010 stay external. This module
therefore exposes their exact scalar/vector handoff instead of inventing matrix
or axis conventions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

FORMAT = "SHIFT.WheelLongitudinalVelocityRuntime/1"
FUNCTION = "FUN_00755f80"
CALLER = "FUN_00763570"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 751033

WHEEL_BASE = 0x400
WHEEL_STRIDE = 0xA80
WHEEL_COUNT = 4
PHYSICS_VELOCITY_OFFSET = 0x48
PHYSICS_POSE_OFFSET = 0xD4

PAIR_AVERAGE_FLAG_OFFSET = 0x3EE0
PAIR_AVERAGE_MODE_OFFSET = 0x3EB8
ALTITUDE_REAR_AVERAGE_CONDITION = "global config byte 0xc1286e != 0"


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def sub(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass(frozen=True)
class WheelLongitudinalObservation:
    wheel_index: int
    wheel_object_offset: int
    input_velocity: Vec3
    local_velocity: Vec3
    longitudinal_component: float
    reconstructed_world_velocity: Vec3
    shared_velocity_after: Vec3


@dataclass(frozen=True)
class WheelLongitudinalBatch:
    observations: tuple[WheelLongitudinalObservation, ...]
    reported_components: tuple[float, float, float, float]


def _vec(values: Sequence[float] | Vec3) -> Vec3:
    if isinstance(values, Vec3):
        return values
    if len(values) != 3:
        raise ValueError("vector requires exactly 3 components")
    return Vec3(float(values[0]), float(values[1]), float(values[2]))


def extract_wheel_longitudinal(
    *,
    wheel_index: int,
    shared_velocity: Sequence[float] | Vec3,
    local_velocity: Sequence[float] | Vec3,
    reconstructed_world_velocity: Sequence[float] | Vec3,
) -> WheelLongitudinalObservation:
    if not 0 <= wheel_index < WHEEL_COUNT:
        raise ValueError("wheel_index must be in [0, 3]")
    input_velocity = _vec(shared_velocity)
    local = _vec(local_velocity)
    reconstructed = _vec(reconstructed_world_velocity)
    return WheelLongitudinalObservation(
        wheel_index=wheel_index,
        wheel_object_offset=WHEEL_BASE + wheel_index * WHEEL_STRIDE,
        input_velocity=input_velocity,
        local_velocity=local,
        longitudinal_component=local.x,
        reconstructed_world_velocity=reconstructed,
        shared_velocity_after=input_velocity.sub(reconstructed),
    )


def apply_longitudinal_subtraction(
    *,
    shared_velocity: Sequence[float] | Vec3,
    reconstructed_world_velocity: Sequence[float] | Vec3,
) -> Vec3:
    return _vec(shared_velocity).sub(_vec(reconstructed_world_velocity))


def batch_from_precomputed_wheels(
    observations: Sequence[WheelLongitudinalObservation],
    *,
    rear_pair_average_enabled: bool = False,
    mode: int = 0,
    global_config_byte: bool = False,
) -> WheelLongitudinalBatch:
    if len(observations) != WHEEL_COUNT:
        raise ValueError("exactly four wheel observations are required")
    ordered = tuple(sorted(observations, key=lambda row: row.wheel_index))
    if tuple(row.wheel_index for row in ordered) != tuple(range(WHEEL_COUNT)):
        raise ValueError("wheel indices must be exactly 0,1,2,3")
    components = [row.longitudinal_component for row in ordered]

    if rear_pair_average_enabled and mode == 0 and global_config_byte:
        rear = (components[2] + components[3]) * 0.5
        components[2] = rear
        components[3] = rear

    return WheelLongitudinalBatch(
        observations=ordered,
        reported_components=tuple(components),
    )


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "caller": CALLER,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "wheel_layout": {
            "base": WHEEL_BASE,
            "stride": WHEEL_STRIDE,
            "count": WHEEL_COUNT,
        },
        "shared_physics": {
            "velocity_offset": PHYSICS_VELOCITY_OFFSET,
            "pose_offset": PHYSICS_POSE_OFFSET,
        },
        "transform_chain": {
            "localize": "FUN_007af0a0(pose+0xd4, velocity+0x48, local_vec3)",
            "extract": "longitudinal_component = local_vec3.x",
            "reconstruct": "FUN_007af010(pose+0xd4, longitudinal_component, reconstructed_vec3)",
            "subtract": "velocity+0x48 -= reconstructed_vec3",
        },
        "caller_batch": {
            "function": "FUN_00763570",
            "loops": 4,
            "increments": "0xA80",
            "component_storage": "local_c0[0..3]",
            "rear_pair_average": {
                "enabled_when": [
                    "object+0x3ee0 != 0",
                    "object+0x3eb8 == 0",
                    "global config 0xc1286e != 0",
                ],
                "formula": "(component[2] + component[3]) * 0.5",
                "writes": [2, 3],
            },
        },
        "explicit_unknowns": [
            "axis semantics of FUN_007af0a0/FUN_007af010",
            "physical interpretation of the reconstructed subtraction",
        ],
        "status": "exact scalar/vector handoff; transform implementation externalized",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "CALLER",
    "SOURCE_LINE",
    "WHEEL_BASE",
    "WHEEL_STRIDE",
    "WHEEL_COUNT",
    "PHYSICS_VELOCITY_OFFSET",
    "PHYSICS_POSE_OFFSET",
    "PAIR_AVERAGE_FLAG_OFFSET",
    "PAIR_AVERAGE_MODE_OFFSET",
    "Vec3",
    "WheelLongitudinalObservation",
    "WheelLongitudinalBatch",
    "extract_wheel_longitudinal",
    "apply_longitudinal_subtraction",
    "batch_from_precomputed_wheels",
    "build_contract",
]
