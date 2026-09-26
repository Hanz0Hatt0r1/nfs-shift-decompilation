"""Evidence-backed StaticCamera collision-sampling and constructor runtime.

Recovered from FUN_00814730, FUN_00814830, FUN_00814670, FUN_00814690,
FUN_008146e0 and FUN_00814f60.

The collision query itself is a camera-record vtable +0x4c call. The forward
path samples the interpolated record at decreasing alpha steps of 0.05; the
reverse path samples increasing alpha steps of 0.05. On a positive query result
the current pair is handed to FUN_00813750.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.StaticCameraCollisionRuntime/1"
SAMPLE_STEP = 0.05


def describe_static_camera_constructor() -> dict[str, Any]:
    """Reproduce FUN_00814f60 constructor writes and shake-state setup."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-constructor",
        "actions": [
            {"action": "FUN_0081aeb0", "purpose": "base CCameraView"},
            {"action": "write vtable", "value": "PTR_FUN_00b15d60"},
            {"action": "FUN_00814460", "target": "+0x48"},
            {"action": "FUN_00675c60", "target": "+0x140"},
            {
                "action": "write +0x3c..+0x60",
                "purpose": "zero StaticCamera runtime state",
            },
            {"action": "write +0x3c", "value": 0x3F000000},
            {"action": "FUN_00812c00", "target": "camera configuration"},
            {
                "action": "FUN_00823a80",
                "target": "+0x84",
                "rate_bits": 0x40C00000,
            },
            {
                "action": "FUN_00823ab0",
                "target": "+0x84",
                "target_bits": [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A],
            },
            {
                "action": "FUN_00823a80",
                "target": "+0xD8",
                "rate_bits": 0x41800000,
            },
            {
                "action": "FUN_00823ab0",
                "target": "+0xD8",
                "target_bits": [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A],
            },
            {
                "action": "write +0x74..+0x7c",
                "value": 0,
            },
        ],
        "writes": {
            "+0x3c": 0x3F000000,
            "+0x98": 0,
            "+0x9c": 0,
            "+0xa0": 0,
            "+0xa4": 0,
            "+0xa8": 0,
            "+0xac": 0,
        },
        "shake": {
            "+0x84": {
                "rate_bits": 0x40C00000,
                "target_bits": [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A],
            },
            "+0xD8": {
                "rate_bits": 0x41800000,
                "target_bits": [0x3C23D70A, 0x3C23D70A, 0x3BA3D70A],
            },
        },
        "evidence": {"function": "FUN_00814f60"},
    }


def interpolate_static_camera_sample(
    *,
    static_camera: Any,
    alpha: float,
) -> dict[str, Any]:
    """Trace FUN_00814670 → FUN_008135b0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "interpolate-sample",
        "alpha": float(alpha),
        "actions": [
            {
                "action": "FUN_00814670",
                "camera": static_camera,
                "output": "vec3",
            },
            {
                "action": "FUN_008135b0",
                "alpha_source": "camera +0x08",
                "result": "vec3",
            },
        ],
        "evidence": {
            "function": "FUN_00814670",
            "interpolator": "FUN_008135b0",
        },
    }


def trace_forward_collision_sampling(
    *,
    initial_alpha: float,
    max_steps: int,
    initial_query_result: float,
    sampled_query_results: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_00814730 control-flow without synthesizing vtable results."""
    alpha = float(initial_alpha)
    steps: list[dict[str, Any]] = [
        {
            "alpha": alpha,
            "query_result": float(initial_query_result),
            "action": "FUN_00814670 -> camera.vtable +0x4c",
        }
    ]
    if initial_query_result > 0.0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "forward-collision-sampling",
            "status": "hit-at-initial-sample",
            "alpha": alpha,
            "action": "FUN_00813750",
            "steps": steps,
            "evidence": {"function": "FUN_00814730", "step": SAMPLE_STEP},
        }

    for query in sampled_query_results[: int(max_steps)]:
        if alpha <= 0.0:
            break
        alpha -= SAMPLE_STEP
        if alpha <= 0.0:
            break
        q = float(query)
        steps.append({
            "alpha": alpha,
            "query_result": q,
            "action": "FUN_00814670 -> camera.vtable +0x4c",
        })
        if q > 0.0:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "forward-collision-sampling",
                "status": "hit",
                "alpha": alpha,
                "action": "FUN_00813750",
                "steps": steps,
                "evidence": {"function": "FUN_00814730"},
            }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "forward-collision-sampling",
        "status": "exhausted",
        "alpha": max(alpha, 0.0),
        "action": "FUN_00814690",
        "steps": steps,
        "evidence": {"function": "FUN_00814730"},
    }


def trace_reverse_collision_sampling(
    *,
    initial_alpha: float,
    max_steps: int,
    initial_query_result: float,
    sampled_query_results: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_00814830 control-flow without synthesizing vtable results."""
    alpha = float(initial_alpha)
    steps: list[dict[str, Any]] = [
        {
            "alpha": alpha,
            "query_result": float(initial_query_result),
            "action": "FUN_00814670 -> camera.vtable +0x4c",
        }
    ]
    if initial_query_result > 0.0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "reverse-collision-sampling",
            "status": "hit-at-initial-sample",
            "alpha": alpha,
            "action": "FUN_00813750",
            "steps": steps,
            "evidence": {"function": "FUN_00814830", "step": SAMPLE_STEP},
        }

    for query in sampled_query_results[: int(max_steps)]:
        if alpha >= 1.0:
            break
        alpha += SAMPLE_STEP
        if alpha >= 1.0:
            break
        q = float(query)
        steps.append({
            "alpha": alpha,
            "query_result": q,
            "action": "FUN_00814670 -> camera.vtable +0x4c",
        })
        if q > 0.0:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "reverse-collision-sampling",
                "status": "hit",
                "alpha": alpha,
                "action": "FUN_00813750",
                "steps": steps,
                "evidence": {"function": "FUN_00814830"},
            }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reverse-collision-sampling",
        "status": "exhausted",
        "alpha": min(alpha, 1.0),
        "action": "FUN_008146e0",
        "steps": steps,
        "evidence": {"function": "FUN_00814830"},
    }
