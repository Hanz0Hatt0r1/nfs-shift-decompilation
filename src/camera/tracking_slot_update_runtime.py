"""TrackingCamera slot/sample update contract from FUN_00817440.

The helper validates a collection index, resolves the current TrackingCamera
object, dispatches its external controller, optionally resynchronizes target
state, and reads up to two spline endpoint records. The record data itself is
supplied by opaque endpoint callbacks.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.TrackingSlotUpdateRuntime/1"


def _vec3(values: Sequence[Any], name: str) -> list[Any]:
    if len(values) != 3:
        raise ValueError(f"{name} requires three values")
    return list(values)


def validate_collection_slot(
    *,
    selected_index: int,
    per_mode_count: int,
) -> dict[str, Any]:
    """Reproduce FUN_00817440's out-of-range-to-zero selection."""
    idx = int(selected_index)
    count = int(per_mode_count)
    valid = 0 <= idx < count
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "validate-slot",
        "input_index": idx,
        "count": count,
        "selected_index": idx if valid else 0,
        "reset_to_zero": not valid,
        "evidence": {"function": "FUN_00817440"},
    }


def update_tracking_slot(
    *,
    selected_index: int,
    per_mode_count: int,
    object_controller_id: int,
    object_secondary_spline_id: int,
    object_metadata: Sequence[Any],
    reverse_mode: bool,
    controller_present: bool,
    needs_resync: bool,
    primary_endpoint_result: Mapping[str, Any] | None = None,
    secondary_endpoint_result: Mapping[str, Any] | None = None,
    wheel_property_name: str | None = None,
    wheel_property_value_degrees: float = 0.0,
) -> dict[str, Any]:
    """Trace FUN_00817440 source order with endpoint/helper outputs as inputs."""
    metadata = _vec3(object_metadata, "object_metadata")
    slot = validate_collection_slot(
        selected_index=selected_index,
        per_mode_count=per_mode_count,
    )
    actions: list[dict[str, Any]] = [
        {
            "action": "select camera collection entry",
            "input_index": int(selected_index),
            "selected_index": slot["selected_index"],
        },
        {
            "action": "resolve RTTI",
            "rtti": "0xc25fb8",
        },
        {
            "action": "write +0x2e8",
            "value": object_controller_id,
        },
    ]

    if not controller_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-slot-update",
            "status": "controller-unavailable",
            "slot": slot,
            "actions": actions,
        }

    actions.append({
        "action": "FUN_008164f0",
        "arguments": {
            "controller": object_controller_id,
            "reverse_mode": bool(reverse_mode),
        },
    })

    if needs_resync:
        actions.append({
            "action": "FUN_00817120",
            "argument": 0,
        })

    selected = int(slot["selected_index"])
    primary = None
    if int(object_controller_id) >= 0:
        if primary_endpoint_result is not None:
            primary = dict(primary_endpoint_result)
            actions.append({
                "action": "FUN_00811640" if reverse_mode else "FUN_00816120",
                "spline_id": int(object_controller_id),
                "result": primary,
                "destination": "+0x2b0",
            })
        else:
            actions.append({
                "action": "endpoint callback",
                "status": "opaque",
                "destination": "+0x2b0",
            })

    secondary = None
    if int(object_secondary_spline_id) >= 0:
        if secondary_endpoint_result is not None:
            secondary = dict(secondary_endpoint_result)
            actions.append({
                "action": "FUN_00811640" if reverse_mode else "FUN_00816120",
                "spline_id": int(object_secondary_spline_id),
                "result": secondary,
                "destination": "+0x2ec",
            })
        else:
            actions.append({
                "action": "endpoint callback",
                "status": "opaque",
                "destination": "+0x2ec",
            })

    state_writes: dict[str, Any] = {}
    if primary is not None:
        record = primary.get("record")
        if record is not None and len(record) >= 3:
            state_writes.update({
                "+0x2dc": record[0],
                "+0x2e0": record[1],
                "+0x2e4": record[2],
            })
        state_writes["+0x2e8"] = primary.get("scalar", object_controller_id)

    if secondary is not None:
        record = secondary.get("record")
        if record is not None and len(record) >= 3:
            state_writes.update({
                "+0x318": record[0],
                "+0x31c": record[1],
                "+0x320": record[2],
            })

    wheel_output = None
    wheel_valid = False
    if wheel_property_name is not None and str(wheel_property_name).lower() == "wheelangle":
        wheel_output = float(wheel_property_value_degrees) * 0.017453292
        wheel_valid = True
        actions.append({
            "action": "WheelAngle conversion",
            "degrees": float(wheel_property_value_degrees),
            "radians": wheel_output,
        })
    elif wheel_property_name is not None:
        actions.append({
            "action": "WheelAngle property check",
            "matched": False,
        })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-slot-update",
        "status": "updated",
        "slot": slot,
        "state_writes": state_writes,
        "wheel_angle_radians": wheel_output,
        "wheel_angle_valid": wheel_valid,
        "actions": actions,
        "evidence": {
            "function": "FUN_00817440",
            "controller_dispatch": "FUN_008164f0",
            "resync": "FUN_00817120",
            "primary_endpoint_forward": "FUN_00816120",
            "primary_endpoint_reverse": "FUN_00811640",
            "secondary_endpoint_forward": "FUN_00816120",
            "secondary_endpoint_reverse": "FUN_00811640",
            "wheel_angle_scale": 0.017453292,
        },
    }
