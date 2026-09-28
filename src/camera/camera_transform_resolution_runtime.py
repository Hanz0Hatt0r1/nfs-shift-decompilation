"""Camera target transform/output resolver runtime.

Recovered from FUN_00814030, FUN_008140c0, FUN_00814180, FUN_00814210 and
FUN_008142c0. These wrappers all converge on the shared target-service helpers
from camera_target_service_runtime.py.
"""

from __future__ import annotations

from typing import Any, Sequence

from camera_target_service_runtime import (
    forward_target_value,
    query_target_metadata,
    resolve_target_transform,
)

FORMAT = "SHIFT.CameraTransformResolutionRuntime/1"


def apply_external_camera_offset(
    *,
    base_output: Sequence[float],
    external_offset: Sequence[float],
    service_query_succeeded: bool,
) -> dict[str, Any]:
    """Reproduce FUN_00814030's post-resolver vector addition."""
    if len(base_output) != 3 or len(external_offset) != 3:
        raise ValueError("base_output and external_offset require three values")
    output = list(map(float, base_output))
    offset = list(map(float, external_offset))
    if not service_query_succeeded:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "external-offset",
            "status": "resolver-failed",
            "output": output,
            "evidence": {"function": "FUN_00814030"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "external-offset",
        "status": "applied",
        "output": [output[i] + offset[i] for i in range(3)],
        "actions": [
            {"action": "FUN_004394a0", "offset": offset},
            {"action": "FUN_00812d20"},
            {"action": "vector-add"},
        ],
        "evidence": {
            "function": "FUN_00814030",
            "external_source_method": "+0x1c",
        },
    }


def resolve_position(
    *,
    active_target_data: Any,
    target_id: int,
    type_selector: int,
    transform_payload: Any,
    service_available: bool,
    fallback_position: Sequence[float],
    local_fallback_enabled: bool,
    service_result: Any = None,
) -> dict[str, Any]:
    """Trace FUN_008140c0's position selection."""
    if active_target_data in (None, 0):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "resolve-position",
            "status": "no-active-target",
            "result": [0.0, 0.0, 0.0],
        }

    resolved_id = int(target_id)
    resolved_type = int(type_selector)
    if resolved_type == 6:
        resolved_type = int(active_target_data.get("type_0x78", 6))

    query_id = resolved_id
    if query_id == -1 and not local_fallback_enabled:
        query_id = int(active_target_data.get("fallback_id", -1))

    return resolve_target_transform(
        service_available=service_available,
        target_id=query_id,
        param3=resolved_type,
        param4=transform_payload,
        this_has_fallback_position=local_fallback_enabled,
        fallback_position=fallback_position,
        service_call_result=service_result,
    )


def resolve_orientation(
    *,
    active_target_data: Any,
    target_id: int,
    type_selector: int,
    value: Any,
    service_available: bool,
    service_result: Any = None,
) -> dict[str, Any]:
    """Trace FUN_00814210 through FUN_00812da0."""
    if active_target_data in (None, 0):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "resolve-orientation",
            "status": "no-active-target",
            "result": [0.0, 0.0, 0.0, 0.0],
        }
    resolved_type = int(type_selector)
    if resolved_type == 6:
        resolved_type = int(active_target_data.get("type_0x78", 6))
    return forward_target_value(
        service_available=service_available,
        target_id=int(target_id),
        value={"type": resolved_type, "payload": value},
        service_result=service_result,
    )


def resolve_metadata(
    *,
    active_target_data: Any,
    target_id: int,
    service_available: bool,
    metadata: Sequence[float] | None,
) -> dict[str, Any]:
    """Trace FUN_008142c0 through FUN_00812de0."""
    if active_target_data in (None, 0):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "resolve-metadata",
            "status": "no-active-target",
            "result": [0.0, 0.0, 0.0],
        }
    return query_target_metadata(
        service_available=service_available,
        target_id=int(target_id),
        metadata=metadata,
    )


def resolve_camera_outputs(
    *,
    active_target_data: Any,
    target_id: int,
    position_type_selector: int,
    orientation_type_selector: int,
    transform_payload: Any,
    orientation_payload: Any,
    metadata: Sequence[float] | None,
    service_available: bool,
    fallback_position: Sequence[float] = (0.0, 0.0, 0.0),
    local_fallback_enabled: bool = False,
    position_service_result: Any = None,
    orientation_service_result: Any = None,
) -> dict[str, Any]:
    """Compose the three output wrappers in source-level order."""
    position = resolve_position(
        active_target_data=active_target_data,
        target_id=target_id,
        type_selector=position_type_selector,
        transform_payload=transform_payload,
        service_available=service_available,
        fallback_position=fallback_position,
        local_fallback_enabled=local_fallback_enabled,
        service_result=position_service_result,
    )
    orientation = resolve_orientation(
        active_target_data=active_target_data,
        target_id=target_id,
        type_selector=orientation_type_selector,
        value=orientation_payload,
        service_available=service_available,
        service_result=orientation_service_result,
    )
    meta = resolve_metadata(
        active_target_data=active_target_data,
        target_id=target_id,
        service_available=service_available,
        metadata=metadata,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-outputs",
        "position": position,
        "orientation": orientation,
        "metadata": meta,
        "source_order": [
            "FUN_008140c0",
            "FUN_00814210",
            "FUN_008142c0",
        ],
    }
