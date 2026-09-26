"""Exact shared camera shake/noise primitive FUN_00823a80..00823cd0.

The primitive stores two 3-float states, a rate/countdown triple at +0x48/+0x4c/+0x50,
and produces smoothed 3-float output through a source-order smoothstep interpolation.
Random reseeding is kept deterministic by accepting raw RNG samples from the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Sequence

FORMAT = "SHIFT.CameraShakeRuntime/1"


@dataclass(frozen=True)
class ShakeState:
    first: tuple[float, float, float] = (0.0, 0.0, 0.0)       # +0x00..+0x08
    first_current: tuple[float, float, float] = (0.0, 0.0, 0.0)  # +0x0c..+0x14
    first_target: tuple[float, float, float] = (0.0, 0.0, 0.0)   # +0x18..+0x20
    second: tuple[float, float, float] = (0.0, 0.0, 0.0)        # +0x24..+0x2c
    second_current: tuple[float, float, float] = (0.0, 0.0, 0.0) # +0x30..+0x38
    second_target: tuple[float, float, float] = (0.0, 0.0, 0.0)  # +0x3c..+0x44
    amplitude: float = 0.0   # +0x48
    rate: float = 0.0        # +0x4c
    time: float = 0.0        # +0x50


def smoothstep_cubic(x: float) -> float:
    """Reproduce FUN_00823ad0: 3*x^2 - 2*x^3."""
    value = float(x)
    return value * value * 3.0 - value * value * value * 2.0


def random_unit_vector_from_rng(samples: Sequence[float]) -> tuple[float, float, float]:
    """Reproduce FUN_00823b00's RNG-to-[-1,1] conversion and component order."""
    if len(samples) != 3:
        raise ValueError("samples requires exactly three RNG values")
    a, b, c = (float(v) for v in samples)
    return (
        c * 2.0 - 1.0,
        b * 2.0 - 1.0,
        a * 2.0 - 1.0,
    )


def zero_shake_state() -> dict[str, Any]:
    """Reproduce FUN_00823ba0/FUN_00823bc0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "zero-state",
        "writes": {
            "+0x00..+0x20": [0.0] * 9,
            "+0x24..+0x44": [0.0] * 9,
            "+0x48": 0.0,
            "+0x4c": 0.0,
            "+0x50": 0.0,
        },
        "evidence": {"function": "FUN_00823bc0"},
    }


def set_shake_rate(state: ShakeState, rate: float) -> ShakeState:
    """Reproduce FUN_00823a80."""
    return replace(state, rate=float(rate))


def set_first_target(state: ShakeState, target: Sequence[float]) -> ShakeState:
    """Reproduce FUN_00823a90."""
    if len(target) != 3:
        raise ValueError("target requires three values")
    return replace(state, first=tuple(map(float, target)))


def set_second_target(state: ShakeState, target: Sequence[float]) -> ShakeState:
    """Reproduce FUN_00823ab0."""
    if len(target) != 3:
        raise ValueError("target requires three values")
    return replace(state, second=tuple(map(float, target)))


def reseed_state(
    state: ShakeState,
    *,
    rng_first: Sequence[float],
    rng_second: Sequence[float],
) -> ShakeState:
    """Reproduce one FUN_00823b60 reseed for both state blocks."""
    if len(rng_first) != 3 or len(rng_second) != 3:
        raise ValueError("rng vectors require three values")
    first_target = random_unit_vector_from_rng(rng_first)
    second_target = random_unit_vector_from_rng(rng_second)
    return replace(
        state,
        first_current=state.first_target,
        first_target=first_target,
        second_current=state.second_target,
        second_target=second_target,
    )


def advance_shake_state(
    state: ShakeState,
    *,
    delta: float,
    rng_first: Sequence[float] | None = None,
    rng_second: Sequence[float] | None = None,
) -> ShakeState:
    """Reproduce FUN_00823be0 countdown/reseed transition."""
    dt = float(delta)
    if dt < 0.0:
        return state

    new_time = state.time - state.rate * dt
    if new_time > 0.0:
        return replace(state, time=new_time)

    if rng_first is None or rng_second is None:
        raise ValueError("positive reseed requires deterministic RNG vectors")
    reseeded = reseed_state(state, rng_first=rng_first, rng_second=rng_second)
    return replace(reseeded, time=1.0)


def interpolate_block(
    *,
    current: Sequence[float],
    target: Sequence[float],
    amplitude: float,
    time: float,
) -> list[float]:
    """Reproduce FUN_00823c30's smoothstep interpolation."""
    if len(current) != 3 or len(target) != 3:
        raise ValueError("current and target require three values")
    t = smoothstep_cubic(float(time))
    c = list(map(float, current))
    g = list(map(float, target))
    a = float(amplitude)
    return [
        a * (c[i] + (g[i] - c[i]) * t)
        for i in range(3)
    ]


def sample_first_block(state: ShakeState) -> list[float]:
    """Reproduce FUN_00823cb0."""
    return interpolate_block(
        current=state.first_current,
        target=state.first_target,
        amplitude=state.amplitude,
        time=state.time,
    )


def sample_second_block(state: ShakeState) -> list[float]:
    """Reproduce FUN_00823cd0."""
    return interpolate_block(
        current=state.second_current,
        target=state.second_target,
        amplitude=state.amplitude,
        time=state.time,
    )


def describe_shake_step(
    state: ShakeState,
    *,
    delta: float,
    rng_first: Sequence[float] | None = None,
    rng_second: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Compose countdown/reseed and both output reads."""
    advanced = advance_shake_state(
        state,
        delta=delta,
        rng_first=rng_first,
        rng_second=rng_second,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "shake-step",
        "state_before": state,
        "state_after": advanced,
        "first_output": sample_first_block(advanced),
        "second_output": sample_second_block(advanced),
        "actions": [
            {"action": "FUN_00823be0", "delta": float(delta)},
            {"action": "FUN_00823cb0", "output": sample_first_block(advanced)},
            {"action": "FUN_00823cd0", "output": sample_second_block(advanced)},
        ],
        "evidence": {
            "advance": "FUN_00823be0",
            "reseed": "FUN_00823b60",
            "smoothstep": "FUN_00823ad0",
            "first_output": "FUN_00823cb0",
            "second_output": "FUN_00823cd0",
        },
    }
