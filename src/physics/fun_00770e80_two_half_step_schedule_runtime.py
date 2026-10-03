"""Source/static-backed anchor schedule for FUN_00770e80.

This freezes only the direct-call order proven by Process 1. Callback bodies stay
external; the module does not claim complete FUN_00770e80 or rendered-frame
scheduler parity.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

FORMAT = "SHIFT.Fun00770e80TwoHalfStepScheduleRuntime/1"
OUTER = "FUN_00770e80"
PHYSICS_PASS = "FUN_0076d100"
HALF_STEP = "FUN_00765470"
POST_HALF_STEP = "FUN_007b8810"
PASS_COUNT = 2


@dataclass(frozen=True)
class ScheduleEvent:
    function: str
    pass_index: int
    timestep: float | None = None


@dataclass(frozen=True)
class ScheduleResult:
    outer_timestep: float
    half_timestep: float
    events: tuple[ScheduleEvent, ...]


def execute_two_half_step_schedule(
    outer_timestep: float,
    physics_pass: Callable[[int], None] | None,
    half_step: Callable[[int, float], None] | None,
    post_half_step: Callable[[int], None] | None,
) -> ScheduleResult:
    if not math.isfinite(outer_timestep):
        raise ValueError("FUN_00770e80 outer timestep must be finite")
    if physics_pass is None or half_step is None or post_half_step is None:
        raise ValueError("FUN_00770e80 proven schedule requires all callback boundaries")

    half_timestep = outer_timestep * 0.5
    if not math.isfinite(half_timestep):
        raise ValueError("FUN_00770e80 half timestep must be finite")

    events: list[ScheduleEvent] = []
    for pass_index in range(PASS_COUNT):
        physics_pass(pass_index)
        events.append(ScheduleEvent(PHYSICS_PASS, pass_index))
        half_step(pass_index, half_timestep)
        events.append(ScheduleEvent(HALF_STEP, pass_index, half_timestep))
        post_half_step(pass_index)
        events.append(ScheduleEvent(POST_HALF_STEP, pass_index))

    return ScheduleResult(outer_timestep, half_timestep, tuple(events))


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "outer_function": OUTER,
        "pass_count": PASS_COUNT,
        "half_timestep_expression": "outer_timestep * 0.5_f64",
        "per_pass_order": [PHYSICS_PASS, HALF_STEP, POST_HALF_STEP],
        "complete_fun_00770e80_semantics": False,
        "rendered_frame_cadence_proven": False,
        "callback_bodies_external": True,
    }
