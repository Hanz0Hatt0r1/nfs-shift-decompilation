"""StaticCamera input/state ABI around FUN_008163e0..008165e0."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.StaticCameraInputStateRuntime/1"


def load_static_camera_entry(
    *,
    source_entry: Any,
    manager_service_present: bool,
    property_setup_succeeded: bool,
) -> dict[str, Any]:
    """Trace FUN_008163e0's XML/object factory lifecycle."""
    actions = [
        {"action": "FUN_0080cc60"},
        {"action": "FUN_00641d30"},
        {"action": "FUN_00640000", "temporary_buffer_words": 0x190},
    ]
    if not manager_service_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "load-static-entry",
            "status": "buffer-setup-failed",
            "actions": actions,
        }
    actions.append({
        "action": "manager vtable +0x20",
        "arguments": [source_entry, "FUN_00823a60", "temporary-config"],
    })
    if not property_setup_succeeded:
        actions.append({"action": "FUN_0063fdd0", "result": 0})
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "load-static-entry",
            "status": "property-setup-failed",
            "actions": actions,
        }
    actions.extend([
        {"action": "FUN_0063fdd0", "result": 1},
        {"action": "manager vtable +0x24"},
        {"action": "FUN_00640b90"},
        {"action": "FUN_00641e70"},
    ])
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "load-static-entry",
        "status": "loaded",
        "actions": actions,
        "evidence": {"function": "FUN_008163e0", "factory": "FUN_00823a60"},
    }


def copy_static_camera_runtime_state(source_words: Sequence[Any]) -> dict[str, Any]:
    """Reproduce FUN_008164a0's sequential 11-dword copy."""
    if len(source_words) < 11:
        raise ValueError("source_words requires at least eleven values")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "copy-runtime-state",
        "count": 11,
        "values": list(source_words[:11]),
        "offset_range": ["+0x00", "+0x28"],
        "evidence": {"function": "FUN_008164a0"},
    }


def update_static_camera_controller(
    *,
    controller_present: bool,
    parameter: Any,
    reverse_flag: bool,
    controller_result: Any = None,
    mode_value: Any = None,
) -> dict[str, Any]:
    """Trace FUN_008164f0's external controller dispatch."""
    if not controller_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "controller-update",
            "status": "controller-missing",
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "controller-update",
        "status": "updated",
        "actions": [
            {
                "action": "controller vtable +0x5c",
                "argument": parameter,
                "result": controller_result,
            },
            {
                "action": "controller vtable +0x94" if reverse_flag else "controller vtable +0x98",
                "target": "+0x10",
            },
            {
                "action": "copy controller +0x280 -> this +0x338",
                "result": mode_value,
            },
        ],
        "evidence": {
            "function": "FUN_008164f0",
            "controller_field": "+0x334",
            "forward_method": "+0x98",
            "reverse_method": "+0x94",
        },
    }


def lookup_static_camera_slot(
    *,
    state_offset: int,
) -> dict[str, Any]:
    """Reproduce FUN_00816550: element address = index*0x34 + 0xd4."""
    offset = int(state_offset)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-lookup",
        "index": offset,
        "source_offset": 0xD4 + offset * 0x34,
        "evidence": {"function": "FUN_00816550", "stride": 0x34},
    }


def reset_static_camera_input_state(
    *,
    camera_slot_index: int,
    slot_count: int,
) -> dict[str, Any]:
    """Reproduce FUN_00816570's reset writes."""
    slot_lookup = lookup_static_camera_slot(state_offset=camera_slot_index)
    reset = {
        "+0x258": 0,
        "+0x280(controller)": 0,
        "+0x33c": 0,
        "+0x340": 0,
        "+0x344": 0,
        "+0x348": 0,
        "+0x34c": 0,
        "+0x25c": 0,
        "+0x350": 0,
        "+0x378": 0,
        "+0x354": 0,
        "+0x264": 0,
        "+0x37c": int(slot_count) - 1,
    }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reset-input-state",
        "writes": reset,
        "slot_lookup": slot_lookup,
        "evidence": {
            "function": "FUN_00816570",
            "slot_count_source": "FUN_00816550(this, +0x244)",
        },
    }


def clamp_static_camera_direction_input(
    *,
    camera_type: int,
    value: float,
    opposite_value: float,
) -> dict[str, Any]:
    """Reproduce FUN_008165e0's camera-type gate and [-1,1] clamps."""
    if 2 < (int(camera_type) - 3) & 0xFFFFFFFF:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "direction-input-clamp",
            "status": "unsupported-camera-type",
            "writes": {
                "+0x33c": 0,
                "+0x340": 0,
            },
        }

    a = max(-1.0, min(1.0, float(value)))
    b = max(-1.0, min(1.0, -float(opposite_value)))
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "direction-input-clamp",
        "status": "clamped",
        "writes": {
            "+0x33c": a,
            "+0x340": b,
        },
        "evidence": {
            "function": "FUN_008165e0",
            "camera_type_field": "+0x244",
            "range": [-1.0, 1.0],
        },
    }
