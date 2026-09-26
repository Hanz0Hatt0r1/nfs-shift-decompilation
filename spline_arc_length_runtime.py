"""Evidence-backed arc-length traversal state machine for the spline runtime.

Recovered from FUN_00822220, FUN_008222f0, FUN_00822620 and FUN_008226a0.
The traversal cursor is treated as raw state; callback results from target
sampling, endpoint handlers and the finished predicate remain explicit inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping, Sequence

FORMAT = "SHIFT.SplineArcLengthRuntime/1"


@dataclass(frozen=True)
class SplineCursor:
    x: float = 0.0          # +0x00
    y: float = 0.0          # +0x04
    z: float = 0.0          # +0x08
    progress: float = 0.0   # +0x0c
    state_10: float = 0.0   # +0x10
    state_14: float = 0.0   # +0x14
    segment_t: float = 0.0  # +0x18
    remainder: float = 0.0 # +0x1c
    sample_scalar: float = 0.0  # +0x20
    boundary_mode: int = 0      # +0x24
    external_scalar: float = 0.0  # +0x28


def describe_parameter_normalization(
    *,
    segment_index: float,
    parameter: float,
) -> dict[str, Any]:
    """Reproduce FUN_00822220's while-loop normalization."""
    index = float(segment_index)
    t = float(parameter)
    steps = []
    while t < 0.0:
        index -= 1.0
        t += 1.0
        steps.append("decrement-index")
    while t > 1.0:
        index += 1.0
        t -= 1.0
        steps.append("increment-index")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "parameter-normalization",
        "segment_index": index,
        "parameter": t,
        "steps": steps,
        "evidence": {"function": "FUN_00822220"},
    }


def early_boundary_result(
    *,
    spline_length: float,
    cursor_progress: float,
    proposed_distance: float,
    normalized_progress: float,
    reverse: bool,
    external_scalar: float,
    spline_loop_flag: bool,
    endpoint_handler_result: float | None,
) -> dict[str, Any] | None:
    """Trace FUN_008222f0's explicit spline-boundary early exits."""
    if float(spline_length) == 0.0:
        return None
    if float(external_scalar) != 0.0 or bool(spline_loop_flag):
        return None
    if reverse and float(normalized_progress) < 0.0:
        value = (
            float(endpoint_handler_result)
            if endpoint_handler_result is not None
            else float(spline_length) * float(cursor_progress)
        )
        return {
            "format": FORMAT,
            "version": 1,
            "status": "reverse-boundary",
            "remaining": value,
            "action": "FUN_00811640",
            "evidence": {"condition": "normalized progress < 0"},
        }
    if (not reverse) and float(normalized_progress) >= 1.0:
        value = (
            float(endpoint_handler_result)
            if endpoint_handler_result is not None
            else (1.0 - float(cursor_progress)) * float(spline_length)
        )
        return {
            "format": FORMAT,
            "version": 1,
            "status": "forward-boundary",
            "remaining": value,
            "action": "FUN_00816120",
            "evidence": {"condition": "normalized progress >= 1"},
        }
    return None


def advance_spline_cursor(
    cursor: SplineCursor,
    *,
    spline_length: float,
    param3: float,
    distance_delta: float,
    boundary_callback_enabled: bool,
    sampler: Callable[[float, float, float, float], Mapping[str, Any]],
    finished_predicate: Callable[[SplineCursor], bool] | None = None,
    reverse_endpoint_result: float | None = None,
    forward_endpoint_result: float | None = None,
    max_outer_steps: int = 100000,
) -> tuple[SplineCursor, dict[str, Any]]:
    """Reproduce FUN_008222f0's traversal with explicit sampler callbacks.

    sampler(segment_index, segment_t, param3, mode) must return:
      position: 3-float sequence
      state_10: float
      state_14: float, used as normalization denominator
      param3_out: float
    """
    signed_total = float(distance_delta)
    state = cursor
    initial_offset = float(signed_total) + float(cursor.remainder)
    reverse = initial_offset < 0.0
    local_c = abs(initial_offset)

    normalized_progress = (
        initial_offset / float(spline_length) + float(cursor.progress)
        if float(spline_length) != 0.0
        else float(cursor.progress)
    )
    if boundary_callback_enabled:
        boundary = early_boundary_result(
            spline_length=float(spline_length),
            cursor_progress=float(cursor.progress),
            proposed_distance=initial_offset,
            normalized_progress=normalized_progress,
            reverse=reverse,
            external_scalar=float(cursor.external_scalar),
            spline_loop_flag=False,
            endpoint_handler_result=(
                reverse_endpoint_result if reverse else forward_endpoint_result
            ),
        )
        if boundary is not None:
            return state, boundary

    if local_c <= 0.0:
        remaining = signed_total
        if float(spline_length) != 0.0:
            state = replace(
                state,
                progress=state.progress + remaining / float(spline_length),
                remainder=remaining,
            )
        return state, {
            "format": FORMAT,
            "version": 1,
            "status": "no-distance",
            "remaining": remaining,
        }

    step_sign = -1.0 if reverse else 1.0
    outer_steps = 0
    accepted_steps = 0
    refinement_steps = 0
    sampler_calls: list[dict[str, Any]] = []

    while local_c > 0.0 and outer_steps < int(max_outer_steps):
        outer_steps += 1
        step = 0.02 * step_sign
        while True:
            trial_t = state.segment_t + step
            sample = sampler(
                state.state_10,
                trial_t,
                float(param3),
                int(state.external_scalar),
            )
            position = [float(v) for v in sample["position"]]
            if len(position) != 3:
                raise ValueError("sampler position requires three values")
            denominator = float(sample.get("denominator", 1.0))
            if denominator == 0.0:
                raise ValueError("sampler denominator must be non-zero")

            dx = position[0] - state.x
            dy = position[1] - state.y
            dz = position[2] - state.z
            travelled = (dx * dx + dy * dy + dz * dz) ** 0.5 / denominator
            remainder_after = local_c - travelled
            sampler_calls.append({
                "segment_index": state.state_10,
                "segment_t": trial_t,
                "sample_position": position,
                "travelled": travelled,
                "remaining_after": remainder_after,
                "denominator": denominator,
            })

            if remainder_after >= 0.0:
                state = replace(
                    state,
                    x=position[0],
                    y=position[1],
                    z=position[2],
                    segment_t=float(sample.get("segment_t_out", trial_t)),
                    remainder=step_sign * remainder_after,
                    sample_scalar=float(sample.get("param3_out", param3)),
                )
                local_c = remainder_after
                accepted_steps += 1
                break

            step *= 0.5
            refinement_steps += 1
            if abs(step) < 1e-8:
                break

        if abs(step) < 0.02:
            break
        if finished_predicate is not None and finished_predicate(state):
            break
        # Source outer loop also checks FUN_008160f0(cursor); retaining that as
        # an explicit finished_predicate keeps the control boundary exact.

    remaining_signed = signed_total - step_sign * local_c
    if float(spline_length) != 0.0:
        state = replace(
            state,
            progress=state.progress + remaining_signed / float(spline_length),
            remainder=remaining_signed,
        )

    terminalized = False
    if boundary_callback_enabled and state.boundary_mode and state.external_scalar == 0.0:
        p = min(1.0, max(0.0, state.progress))
        state = replace(state, progress=p, remainder=0.0)
            terminalized = True

    return state, {
        "format": FORMAT,
        "version": 1,
        "status": "updated",
        "remaining": remaining_signed,
        "outer_steps": outer_steps,
        "accepted_steps": accepted_steps,
        "refinement_steps": refinement_steps,
        "terminalized": terminalized,
        "sampler_calls": sampler_calls,
        "evidence": {
            "function": "FUN_008222f0",
            "step_size": 0.02,
            "refinement_floor": 1e-8,
            "progress_offset": "+0x0c",
            "segment_state": "+0x18",
            "remainder_state": "+0x1c",
            "sample_scalar": "+0x20",
            "boundary_mode": "+0x24",
            "external_scalar": "+0x28",
        },
    }


def clamp_and_dispatch_offset(
    *,
    cursor_progress: float,
    spline_length: float,
    param3: float,
    param4: float,
) -> dict[str, Any]:
    """Reproduce FUN_00822620's offset clamp before FUN_008222f0."""
    p = max(0.0, float(param3))
    offset = (p - float(cursor_progress)) * float(spline_length)
    limit = float(param4)
    if offset < 0.0:
        limit = -limit
        selected = limit if offset <= limit else offset
    else:
        selected = limit if limit >= offset else offset
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "offset-dispatch",
        "param3_clamped": p,
        "raw_offset": offset,
        "selected_delta": selected,
        "action": "FUN_008222f0",
        "evidence": {"function": "FUN_00822620"},
    }


def rebuild_spline_length(
    *,
    node_count: int,
    sample_returns: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_008226a0's repeated +0x18 accumulation."""
    if int(node_count) <= 1:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "rebuild-length",
            "status": "zero-length",
            "length": 0.0,
            "iterations": 0,
        }
    total = 0.0
    iterations = 0
    for value in sample_returns:
        v = float(value)
        if v <= 0.0:
            break
        total += v
        iterations += 1
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "rebuild-length",
        "status": "rebuilt",
        "length": total,
        "iterations": iterations,
        "actions": [
            {"action": "write +0x18", "value": total},
            {"action": "temporary +0x1c = 1"},
            {"action": "FUN_008222f0", "delta": 10.0, "param3": 1.0},
        ],
        "evidence": {"function": "FUN_008226a0"},
    }
