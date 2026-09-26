"""TrackingCamera target/controller state synchronization from FUN_00817120."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.TrackingTargetStateSyncRuntime/1"


def _vec3(values: Sequence[Any], name: str) -> list[Any]:
    if len(values) != 3:
        raise ValueError(f"{name} requires three values")
    return list(values)


def synchronize_tracking_target_state(
    *,
    target_metadata: Sequence[Any] | None,
    controller_camera_data: Mapping[int, Any],
    camera_data_fallback: Mapping[int, Any],
    controller_spline_id: int,
    controller_target_spline_id: int,
    controller_object_present: bool,
    controller_call_argument: Any = 0,
    controller_matrix_result: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Reproduce FUN_00817120's target/state copy branches."""
    meta = _vec3(target_metadata, "target_metadata") if target_metadata is not None else [0, 0, 0]
    writes: dict[str, Any] = {
        "+0x74": meta[0],
        "+0x78": meta[1],
        "+0x7c": meta[2],
        "+0x80": 1,
    }
    actions: list[dict[str, Any]] = [
        {
            "action": "resolve target via FUN_0081f2e0",
            "status": "found" if target_metadata is not None else "not-found",
        },
        {
            "action": "write target metadata",
            "writes": {
                "+0x74": meta[0],
                "+0x78": meta[1],
                "+0x7c": meta[2],
                "+0x80": 1,
            },
        },
        {
            "action": "controller vtable +0x60",
            "argument": controller_call_argument,
            "result_matrix": list(controller_matrix_result)
            if controller_matrix_result is not None
            else None,
        },
        {
            "action": "FUN_00445ec0",
            "destination": "+0x270",
            "source": "controller +0x60 result",
        },
    ]

    spline_id = int(controller_spline_id)
    target_spline_id = int(controller_target_spline_id)

    if not controller_object_present:
        writes.update({
            "+0x2dc": camera_data_fallback.get(0x10, 0),
            "+0x2e0": camera_data_fallback.get(0x14, 0),
            "+0x2e4": camera_data_fallback.get(0x18, 0),
            "+0x2e8": camera_data_fallback.get(0x34, 0),
            "+0x2a0": camera_data_fallback.get(0x10, 0),
            "+0x2a4": camera_data_fallback.get(0x14, 0),
            "+0x2a8": camera_data_fallback.get(0x18, 0),
            "+0x2ac": 1.0,
        })
        actions.append({
            "action": "fallback camera-data copy",
            "condition": "controller target object unavailable / +0x3e < 0",
            "source_offsets": ["+0x10", "+0x14", "+0x18", "+0x34"],
        })
    else:
        source_map = {
            0x2b0: 0x294,
            0x2b4: 0x298,
            0x2b8: 0x29c,
            0x2bc: 0x2a0,
            0x2c0: 0x2a4,
            0x2c4: 0x2a8,
            0x2c8: 0x2ac,
            0x2cc: 0x2b0,
            0x2d0: 0x2b4,
            0x2d4: 0x2b8,
            0x2d8: 0x2bc,
            0x2dc: 0x2b0,
            0x2e0: 0x2b4,
            0x2e4: 0x2b8,
        }
        for destination, source in source_map.items():
            writes[f"+0x{destination:02x}"] = controller_camera_data.get(
                source,
                0,
            )
        writes["+0x2e8"] = writes["+0x2d0"]
        writes["+0x2a0"] = writes["+0x2dc"]
        writes["+0x2a4"] = writes["+0x2e0"]
        writes["+0x2a8"] = writes["+0x2e4"]
        writes["+0x2ac"] = 1.0
        actions.append({
            "action": "controller camera-data copy",
            "source_range": "+0x294..+0x2bc",
            "derived_writes": ["+0x2a0..+0x2e8"],
        })

    if target_spline_id >= 0:
        for i, offset in enumerate((0x2c0, 0x2c4, 0x2c8, 0x2cc, 0x2d0, 0x2d4, 0x2d8, 0x2dc, 0x2e0, 0x2e4, 0x2e8)):
            writes[f"+0x{0x2ec + i*4:02x}"] = controller_camera_data.get(offset, 0)
        writes["+0x318"] = writes["+0x2ec"]
        writes["+0x31c"] = writes["+0x2f0"]
        writes["+0x320"] = writes["+0x2f4"]
        actions.append({
            "action": "controller extended-data copy",
            "condition": "+0x3f >= 0",
            "source_range": "+0x2c0..+0x2e8",
            "destination_range": "+0x2ec..+0x314 and +0x318..+0x320",
        })
    elif target_metadata is not None:
        writes["+0x318"] = target_metadata[0]
        writes["+0x31c"] = target_metadata[1]
        writes["+0x320"] = target_metadata[2]
        actions.append({
            "action": "target metadata fallback copy",
            "condition": "+0x3f < 0 and target found",
            "source": "target +0x84/+0x88/+0x8c equivalent",
        })
    else:
        writes["+0x318"] = 0
        writes["+0x31c"] = 0
        writes["+0x320"] = 0
        actions.append({
            "action": "zero extended target state",
            "condition": "+0x3f < 0 and target not found",
        })

    writes["+0x80"] = 0
    actions.append({
        "action": "clear controller +0x80",
        "value": 0,
    })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-target-state-sync",
        "writes": writes,
        "actions": actions,
        "evidence": {
            "function": "FUN_00817120",
            "target_metadata": ["+0x74", "+0x78", "+0x7c", "+0x80"],
            "controller_camera_data": "+0x294..+0x2e8",
            "derived_camera_state": "+0x2a0..+0x320",
            "matrix_output": "+0x270",
        },
        "limitations": [
            "controller target-object lookup and vtable +0x60 output remain opaque",
            "controller +0x3e/+0x3f are supplied as booleans through the two ID arguments",
        ],
    }
