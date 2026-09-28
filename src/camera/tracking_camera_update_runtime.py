"""Evidence-backed TrackingCamera update pipeline.

Recovered from FUN_00821000 and FUN_00821080. The module records target-id
selection, camera position synchronization, AutoZoom/FOV logic, shake-state
updates, and final orientation handoff. Complex transform/service helpers are
kept opaque.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

FORMAT = "SHIFT.TrackingCameraUpdateRuntime/1"


def select_tracking_camera_target(
    *,
    target_id: int,
    entries: Iterable[Mapping[str, Any]],
    param2: int,
) -> dict[str, Any]:
    """Reproduce FUN_00821000's target-list scan."""
    if int(param2) == 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "target-selection",
            "status": "reset",
            "actions": [{"action": "FUN_0081ea70"}],
        }

    for ordinal, entry in enumerate(entries):
        entry_id = int(entry.get("vtable_plus_0x14_result", -1))
        if entry_id == int(param2):
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "target-selection",
                "status": "matched",
                "matched_entry": ordinal,
                "actions": [
                    {
                        "action": "FUN_0081ea70",
                        "reason": "entry.vtable +0x14 == param2",
                    }
                ],
                "evidence": {
                    "function": "FUN_00821000",
                    "enumerator": "FUN_0052cce0",
                    "comparison": "entry.vtable +0x14",
                },
            }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "target-selection",
        "status": "not-found",
        "actions": [],
        "evidence": {"function": "FUN_00821000"},
    }


def compute_autozoom_update(
    *,
    current_zoom: float,
    distance: float,
    update_enabled: bool,
    write_initial_zoom: bool,
    previous_zoom: float,
    delta: float,
) -> dict[str, Any]:
    """Reproduce FUN_00821080's explicit AutoZoom smoothing arithmetic."""
    if not update_enabled:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "autozoom",
            "status": "disabled",
            "value": float(current_zoom),
            "actions": [],
        }

    distance_f = float(distance)
    desired = 35.0 / math.sqrt(distance_f) if distance_f > 0.0 else float("inf")
    desired = max(0.1, min(1.0, desired))
    if write_initial_zoom:
        previous = desired
    else:
        previous = float(previous_zoom)

    diff = desired - previous
    abs_diff = abs(diff)
    step = float(delta) * 0.25
    if abs_diff < 0.02:
        step *= 0.5
    if desired <= previous:
        step = -min(abs_diff, step)
    else:
        step = min(abs_diff, step)

    value = previous + step
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "autozoom",
        "status": "updated",
        "distance": distance_f,
        "desired": desired,
        "previous": previous,
        "step": step,
        "value": value,
        "evidence": {
            "function": "FUN_00821080",
            "guard": "tracking +0x100",
            "initial_field": "+0x284",
            "clamp_range": [0.1, 1.0],
            "step_scale": 0.25,
            "near_difference_threshold": 0.02,
        },
    }


def compute_speed_fov_blend(
    *,
    distance: float,
    speed: float,
    fov_min_speed: float,
    fov_max_speed: float,
    fov_min: float,
    fov_max: float,
    shake_min_speed: float,
    shake_max_speed: float,
    shake_min_scale: float,
    shake_max_scale: float,
) -> dict[str, Any]:
    """Reproduce FUN_00821080's speed-normalized FOV/shake blend inputs."""
    fov_span = float(fov_max_speed) - float(fov_min_speed)
    if fov_span == 0.0:
        fov_t = 1.0
    else:
        fov_t = (float(speed) - float(fov_min_speed)) / fov_span
        fov_t = max(0.0, min(1.0, fov_t))

    shake_span = float(shake_max_speed) - float(shake_min_speed)
    if shake_span == 0.0:
        shake_t = 1.0
    else:
        shake_t = (float(distance) - float(shake_min_speed)) / shake_span
        shake_t = max(0.0, min(1.0, shake_t))

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "speed-fov-blend",
        "fov_t": fov_t,
        "fov_value": float(fov_min) * (1.0 - fov_t) + float(fov_max) * fov_t,
        "distance": float(distance),
        "shake_t": shake_t,
        "shake_scale": float(shake_min_scale) * (1.0 - shake_t)
        + float(shake_max_scale) * shake_t,
        "evidence": {
            "function": "FUN_00821080",
            "fov_speed_bounds": ["tracking +0xc4", "tracking +0xc8"],
            "fov_values": ["tracking +0xbc", "tracking +0xc0"],
            "shake_speed_bounds": ["tracking +0xa4", "tracking +0xa8"],
            "shake_values": ["tracking +0xb4", "tracking +0xb8"],
        },
    }


def describe_tracking_camera_update(
    *,
    delta: float,
    input_position: Sequence[float],
    target_position: Sequence[float],
    tracking_position: Sequence[float],
    target_mode: int,
    target_spline_id: int,
    static_direction: bool,
    autozoom: bool,
    speed: float,
    current_fov: float,
    service_available: bool,
    target_query_available: bool,
    cockpit_query_result: bool,
    autozoom_previous: float,
    autozoom_initialized: bool,
    fov_blend: Mapping[str, float] | None = None,
    shake_enabled: bool = False,
    final_orientation: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Trace FUN_00821080 in source order."""
    if len(input_position) != 3 or len(target_position) != 3 or len(tracking_position) != 3:
        raise ValueError("all position vectors require three values")

    actions: list[dict[str, Any]] = [
        {
            "action": "copy tracking camera position",
            "source": "tracking target +0x20/+0x24/+0x28",
            "destination": "+0x10/+0x14/+0x18",
            "value": list(map(float, tracking_position)),
        }
    ]

    effective_position = [float(v) for v in tracking_position]

    if int(target_mode) == 1 and int(target_spline_id) < 0:
        actions.append({
            "action": "FUN_00814030",
            "arguments": {
                "camera_position": effective_position,
                "target_position": list(map(float, target_position)),
                "target_id": "tracking +0x74",
            },
        })
    else:
        actions.append({
            "action": "FUN_00820100",
            "arguments": {
                "speed": float(speed),
                "target": "param_4",
                "service": "param_7",
            },
        })

    direction = [
        float(input_position[i]) - effective_position[i]
        for i in range(3)
    ]

    if static_direction:
        actions.append({
            "action": "FUN_00445ec0",
            "source": "tracking orientation +0x04",
            "purpose": "static-direction basis",
        })
        actions.append({
            "action": "project direction onto stored orientation basis",
        })

    autozoom_result = None
    if autozoom:
        actions.extend([
            {"action": "FUN_00633980"},
            {"action": "FUN_00633960"},
        ])
        autozoom_result = compute_autozoom_update(
            current_zoom=current_fov,
            distance=math.sqrt(sum(v * v for v in direction)),
            update_enabled=True,
            write_initial_zoom=not autozoom_initialized,
            previous_zoom=autozoom_previous,
            delta=delta,
        )
        actions.append({
            "action": "AutoZoom",
            "result": autozoom_result["value"],
        })

    actions.append({
        "action": "write +0x34",
        "value": autozoom_result["value"] if autozoom_result else float(current_fov),
    })

    if target_query_available:
        actions.append({
            "action": "FUN_0081f330",
            "result": "target position query",
        })
        actions.append({
            "action": "FUN_00820bc0",
            "result": "camera offset",
        })

    if service_available:
        actions.append({
            "action": "query camera-system vtable +0x18",
            "result": bool(cockpit_query_result),
        })

    if fov_blend is not None and service_available and not cockpit_query_result:
        blend = compute_speed_fov_blend(**dict(fov_blend), distance=math.sqrt(sum(v * v for v in direction)), speed=speed)
        actions.append({
            "action": "speed-dependent FOV/shake blend",
            "result": blend,
        })
    else:
        blend = None

    if shake_enabled and service_available and not cockpit_query_result:
        actions.extend([
            {"action": "FUN_00823a80", "target": "+0x84"},
            {"action": "FUN_006bbf10", "target": "+0x84"},
            {"action": "FUN_00823be0", "target": "+0x84", "delta": delta},
            {"action": "FUN_00823a80", "target": "+0xd8"},
            {"action": "FUN_00823ab0", "target": "+0xd8"},
            {"action": "FUN_006bbf10", "target": "+0xd8"},
            {"action": "FUN_00823be0", "target": "+0xd8", "delta": delta},
        ])
    elif not cockpit_query_result:
        actions.extend([
            {"action": "zero shake state", "targets": ["+0x84", "+0xd8"]},
        ])

    actions.extend([
        {
            "action": "FUN_008207c0",
            "target": "output orientation",
            "result": list(map(float, final_orientation))
            if final_orientation is not None else None,
        },
        {
            "action": "clear +0x68",
            "value": 0,
        },
        {
            "action": "FUN_00449930",
            "target": "output quaternion",
        },
    ])

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-camera-update",
        "status": "updated",
        "delta": float(delta),
        "direction": direction,
        "state": {
            "+0x10/+0x14/+0x18": effective_position,
            "+0x34": autozoom_result["value"] if autozoom_result else float(current_fov),
        },
        "autozoom": autozoom_result,
        "fov_blend": blend,
        "actions": actions,
        "evidence": {
            "function": "FUN_00821080",
            "position_state": ["+0x10", "+0x14", "+0x18"],
            "fov_state": "+0x34",
            "autozoom_state": "+0x284",
            "target_query": "FUN_0081f330",
            "offset_clip": "FUN_00820bc0",
            "orientation_output": "FUN_008207c0",
        },
        "limitations": [
            "FUN_00814030/FUN_00820100/FUN_00820bc0 remain opaque orchestration boundaries",
            "matrix and shake helper implementations are not re-synthesized here",
        ],
    }
