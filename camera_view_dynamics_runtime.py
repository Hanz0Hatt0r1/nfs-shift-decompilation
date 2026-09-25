"""Evidence-backed CCameraView input/shake dynamics.

Recovered from FUN_0081b260, FUN_0081b330, FUN_0081b340, FUN_0081b6e0,
FUN_0081bc70, FUN_0081bcd0, FUN_0081bdb0, FUN_0081c100 and FUN_0081c180.

The arithmetic which is explicit in the decompiler is reproduced. Complex
FUN_00823* state-machine operations and global service hooks remain named
boundaries instead of inferred physical meanings.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

FORMAT = "SHIFT.CameraViewDynamicsRuntime/1"
DEG_TO_RAD = 0.017453292


def update_input_direction_counters(
    *,
    counter_0x2bc: float,
    counter_0x2c0: float,
    device_active: bool,
) -> dict[str, Any]:
    """Reproduce FUN_0081b260's pair of directional counters."""
    first = float(counter_0x2bc)
    second = float(counter_0x2c0)
    if device_active:
        first += 1.0
    else:
        first -= 1.0

    if device_active:
        second += 1.0
    else:
        second -= 1.0

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "input-direction-counters",
        "values": {
            "+0x2bc": first,
            "+0x2c0": second,
        },
        "evidence": {
            "function": "FUN_0081b260",
            "counter_a": "+0x2bc",
            "counter_b": "+0x2c0",
            "device_probe": "FUN_0064a010/FUN_00649f20",
        },
    }


def set_input_rate_values(
    *,
    pitch_rate: Any,
    yaw_rate: Any,
) -> dict[str, Any]:
    """Trace FUN_0081b6e0's conversion of stored degrees to radians."""
    result = {
        "pitch_rate_radians": float(pitch_rate) * DEG_TO_RAD,
        "yaw_rate_radians": float(yaw_rate) * DEG_TO_RAD,
    }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "input-rate-radians",
        "result": result,
        "evidence": {
            "function": "FUN_0081b6e0",
            "pitch_source": "+0x2b8",
            "pitch_multiplier_source": "+0x2c4",
            "yaw_source": "+0x2c0",
            "yaw_multiplier_source": "+0x2c4",
        },
    }


def seed_velocity_offset_state(
    *,
    profile_present: bool,
    profile_scale: float,
    vehicle_velocity: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_0081bc70's six-field velocity/offset state setup."""
    if len(vehicle_velocity) < 3:
        raise ValueError("vehicle_velocity requires three values")
    if not profile_present or float(profile_scale) <= 0.0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "seed-velocity-offset",
            "status": "skipped",
            "actions": [],
            "evidence": {
                "function": "FUN_0081bc70",
                "guard": "profile exists and profile +0x20 > 0",
            },
        }
    values = [
        float(vehicle_velocity[0]),
        float(vehicle_velocity[1]),
        float(vehicle_velocity[2]),
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "seed-velocity-offset",
        "status": "seeded",
        "state": {
            "+0x9c": 0.0,
            "+0xa0": 0.0,
            "+0xa4": 0.0,
            "+0xa8": values[0],
            "+0xac": values[1],
            "+0xb0": values[2],
        },
        "evidence": {
            "function": "FUN_0081bc70",
            "source_fields": ["vehicle +0x1c", "vehicle +0x20", "vehicle +0x24"],
        },
    }


def resolve_view_input_axes(
    *,
    action3_available: bool,
    action4_available: bool,
    action3_axis: float = 0.0,
    action4_axis: float = 0.0,
    service_axis0: float = 0.0,
    service_axis1: float = 0.0,
    accumulator_0x2c0: float = 0.0,
    counter_0x2bc: float = 0.0,
    reverse_direction: bool = False,
) -> dict[str, Any]:
    """Reproduce FUN_0081bcd0's explicit input/service/accumulator arithmetic."""
    raw0 = float(action3_axis) if action3_available and action4_available else 0.0
    raw1 = float(action4_axis) if action3_available and action4_available else 0.0

    # FUN_0080bfb0 vtable +0x50 can modify both output values. Treat its result
    # as the explicit post-hook values supplied to this model.
    hooked0 = float(service_axis0)
    hooked1 = float(service_axis1)
    adjusted0 = hooked0 - float(accumulator_0x2c0)
    if reverse_direction:
        adjusted1 = hooked1 - float(counter_0x2bc)
    else:
        adjusted1 = float(counter_0x2bc) - hooked1

    zero = adjusted0 == 0.0 and adjusted1 == 0.0
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "resolve-input-axes",
        "raw_action_axes": [raw0, raw1],
        "service_hook_result": [hooked0, hooked1],
        "result_axes": [adjusted0, adjusted1],
        "changed": not zero,
        "evidence": {
            "function": "FUN_0081bcd0",
            "action_slots": [3, 4],
            "action_value_offset": "+0x2c",
            "service_hook": "FUN_0080bfb0().+0x50",
            "horizontal_accumulator": "+0x2c0",
            "vertical_counter": "+0x2bc",
            "direction_flag": "global service +0x82d",
        },
        "limitations": [
            "the service vtable +0x50 mutation is supplied as an input result",
            "action availability is represented by booleans rather than Apt object internals",
        ],
    }


def compute_input_shake_angles(
    *,
    profile_active: bool,
    profile_orientation_flag: bool,
    axis0: float,
    axis1: float,
    positive_pitch_rate_deg: float,
    negative_pitch_rate_deg: float,
    positive_yaw_rate_deg: float,
    negative_yaw_rate_deg: float,
) -> dict[str, Any]:
    """Reproduce FUN_0081bdb0's no-profile shake-angle branch."""
    if profile_active:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "compute-shake-angles",
            "status": "profile-branch",
            "angles_radians": None,
            "evidence": {
                "function": "FUN_0081bdb0",
                "profile_flag": "profile +0xb8",
            },
        }

    a0 = float(axis0)
    a1 = float(axis1)
    pitch_deg = a1 * (
        float(positive_pitch_rate_deg)
        if a1 >= 0.0
        else -float(negative_pitch_rate_deg)
    )
    yaw_deg = a0 * (
        float(positive_yaw_rate_deg)
        if a0 >= 0.0
        else -float(negative_yaw_rate_deg)
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "compute-shake-angles",
        "status": "input-rate-branch",
        "angles_radians": [pitch_deg * DEG_TO_RAD, yaw_deg * DEG_TO_RAD],
        "angles_degrees": [pitch_deg, yaw_deg],
        "evidence": {
            "function": "FUN_0081bdb0",
            "positive_pitch_rate": "service +0x55c",
            "negative_pitch_rate": "service +0x558",
            "positive_yaw_rate": "service +0x554",
            "negative_yaw_rate": "service +0x550",
        },
        "limitations": [
            "profile-active branch contains vehicle-dependent pitch handling and is not synthesized here",
        ],
    }


def integrate_head_shake_step(
    *,
    delta: float,
    position: Sequence[float],
    orientation: Sequence[float],
    helper_position_delta: Sequence[float],
    helper_orientation_delta: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_0081c100's final vector accumulation after FUN_00823*."""
    if len(position) != 3 or len(orientation) != 3:
        raise ValueError("position and orientation require three values")
    if len(helper_position_delta) != 3 or len(helper_orientation_delta) != 3:
        raise ValueError("helper deltas require three values")
    _ = float(delta)  # consumed by opaque FUN_00823be0
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "integrate-head-shake",
        "position": [
            float(position[0]) + float(helper_position_delta[0]),
            float(position[1]) + float(helper_position_delta[1]),
            float(position[2]) + float(helper_position_delta[2]),
        ],
        "orientation": [
            float(orientation[0]) + float(helper_orientation_delta[0]),
            float(orientation[1]) + float(helper_orientation_delta[1]),
            float(orientation[2]) + float(helper_orientation_delta[2]),
        ],
        "helper_boundary": {
            "advance": "FUN_00823be0(this+0xd8, delta)",
            "position_read": "FUN_00823cb0",
            "orientation_read": "FUN_00823cd0",
        },
        "evidence": {"function": "FUN_0081c100"},
    }


def integrate_profile_shake_step(
    *,
    profile_present: bool,
    profile_frequency_factor: Any,
    input_scale: Any,
    helper_position_delta: Sequence[float],
    helper_orientation_delta: Sequence[float],
    position: Sequence[float],
    orientation: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_0081c180's setup and accumulation boundary."""
    if len(position) != 3 or len(orientation) != 3:
        raise ValueError("position and orientation require three values")
    if len(helper_position_delta) != 3 or len(helper_orientation_delta) != 3:
        raise ValueError("helper deltas require three values")
    if not profile_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "integrate-profile-shake",
            "status": "no-profile",
            "position": list(map(float, position)),
            "orientation": list(map(float, orientation)),
        }

    scale = float(input_scale)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "integrate-profile-shake",
        "status": "profile-active",
        "state_setup": {
            "noise": profile_frequency_factor,
            "input_scale": scale,
            "noise_accumulator": "this +0x12c",
        },
        "position": [
            float(position[0]) + float(helper_position_delta[0]),
            float(position[1]) + float(helper_position_delta[1]),
            float(position[2]) + float(helper_position_delta[2]),
        ],
        "orientation": [
            float(orientation[0]) + float(helper_orientation_delta[0]),
            float(orientation[1]) + float(helper_orientation_delta[1]),
            float(orientation[2]) + float(helper_orientation_delta[2]),
        ],
        "helper_boundary": {
            "setup": [
                "FUN_00823a80(this+0x12c, profile+0x84)",
                "FUN_006bbf10(this+0x12c, this+0xb4)",
            ],
            "advance": "FUN_00823be0(this+0x12c, delta)",
            "position_read": "FUN_00823cb0",
            "orientation_read": "FUN_00823cd0",
        },
        "evidence": {"function": "FUN_0081c180"},
        "limitations": [
            "FUN_00823a80/FUN_006bbf10/FUN_00823be0 remain opaque procedural helpers",
        ],
    }


def normalize_angle_with_pi(
    angle: float,
    *,
    seed: float,
) -> float:
    """Reproduce FUN_0081b610's sign-dependent pi adjustment."""
    value = float(angle)
    seed_value = float(seed)
    if not math.isnan(value) and value > 0.0:
        return seed_value - math.pi
    return -(seed_value - math.pi)


def describe_free_look_registry() -> dict[str, Any]:
    """Expose the proven FUN_0081c220 input action registry."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "free-look-registry",
        "actions": [
            {"index": 1, "name": "Driving View", "binding": "type3/0/1/0x0f", "vtable": "FUN_006712a0"},
            {"index": 2, "name": "Look Behind", "binding": "type3/0/1/0x0d", "vtable": "FUN_00671230"},
            {"index": 3, "name": "Free Look Left/Right", "binding": "type3/0/4/2", "vtable": "FUN_00671230"},
            {"index": 4, "name": "Free Look Up/Down", "binding": "type3/0/4/3", "vtable": "FUN_00671230"},
        ],
        "evidence": {
            "function": "FUN_0081c220",
            "slots": "this + 0x2a0..+0x2b8",
        },
    }
