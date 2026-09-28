"""Evidence-backed CameraManager helper/query boundaries.

Recovered from FUN_0080b8b0, FUN_0080b8d0, FUN_0080b8e0, FUN_0080b8f0,
FUN_0080b910, FUN_0080b940, FUN_0080be30, FUN_0080be50, FUN_0080be90,
FUN_0080bec0, FUN_0080c1b0, and FUN_0080c1e0.

The module keeps exact slot addressing and branch conditions while leaving
opaque global services and camera-type helpers unresolved.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.CameraManagerHelpersRuntime/1"
SLOT_STRIDE = 0x2AA0


def slot_address(
    manager_base: int | str,
    slot_index: int,
    *,
    slot_base_offset: int = 0x290,
) -> int | str:
    """Reproduce FUN_0080b8b0's slot-address calculation."""
    index = int(slot_index)
    if isinstance(manager_base, int):
        return manager_base + int(slot_base_offset) + index * SLOT_STRIDE
    return f"{manager_base}+0x{int(slot_base_offset):x}+{index}*0x{SLOT_STRIDE:x}"


def slot_camera_source(
    manager_base: int | str,
    slot_index: int,
    *,
    slot_base_offset: int = 0x290,
) -> dict[str, Any]:
    """Trace FUN_0080bdd0's +0x2568 slot lookup."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-camera-source",
        "slot_index": int(slot_index),
        "field": "+0x2568",
        "address": slot_address(manager_base, slot_index, slot_base_offset=slot_base_offset),
        "evidence": {"function": "FUN_0080bdd0", "stride": "0x2aa0"},
    }


def slot_sync_object(
    manager_base: int | str,
    slot_index: int,
) -> dict[str, Any]:
    """Trace FUN_0080bdf0's +0x2580 slot lookup."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-sync-object",
        "slot_index": int(slot_index),
        "field": "+0x2580",
        "address": slot_address(manager_base, slot_index),
        "evidence": {"function": "FUN_0080bdf0", "stride": "0x2aa0"},
    }


def slot_ready_state(
    manager_base: int | str,
    slot_index: int,
) -> dict[str, Any]:
    """Trace FUN_0080be10's +0x2688 slot lookup."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-ready-state",
        "slot_index": int(slot_index),
        "field": "+0x2688",
        "address": slot_address(manager_base, slot_index),
        "evidence": {"function": "FUN_0080be10", "stride": "0x2aa0"},
    }


def describe_secondary_camera_dispatch(
    *,
    service_enabled: bool,
    requested_first: Any,
    requested_second: Any,
    requested_camera_id: int,
    slot_index: int,
) -> dict[str, Any]:
    """Reproduce FUN_0080be50's global-service gate and dispatch."""
    actions: list[dict[str, Any]] = []
    if service_enabled:
        actions.append({
            "action": "FUN_0080e1b0",
            "arguments": {
                "slot_index": int(slot_index),
                "param_1": requested_first,
                "param_2": requested_second,
                "camera_id": int(requested_camera_id),
            },
        })
        status = "dispatched"
    else:
        status = "service-disabled"

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "secondary-camera-dispatch",
        "status": status,
        "actions": actions,
        "evidence": {
            "function": "FUN_0080be50",
            "service_gate": "manager +0x568 +0xb0 != 0",
            "target": "FUN_0080e1b0",
            "slot_stride": "0x2aa0",
        },
    }


def describe_external_source_to_slot(
    *,
    source: Any,
    parameter: int,
    slot_index: int,
) -> dict[str, Any]:
    """Trace FUN_0080b940's forwarding to FUN_0080d520."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "external-source-to-slot",
        "slot_index": int(slot_index),
        "actions": [
            {
                "action": "FUN_0080d520",
                "target": f"slot[{int(slot_index)}]",
                "arguments": {
                    "source": source,
                    "parameter": int(parameter),
                },
            }
        ],
        "evidence": {
            "function": "FUN_0080b940",
            "manager_external_source": "+0x294",
            "slot_stride": "0x2aa0",
        },
    }


def describe_slot_refresh_request(
    *,
    value: Any,
    slot_index: int,
) -> dict[str, Any]:
    """Trace FUN_0080be90's refresh-request state writes."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "refresh-request",
        "slot_index": int(slot_index),
        "actions": [
            {
                "action": "write +0x268c",
                "value": value,
            },
            {
                "action": "write +0x2698",
                "value": 1,
            },
        ],
        "evidence": {
            "function": "FUN_0080be90",
            "slot_stride": "0x2aa0",
        },
    }


def describe_slot_ready_predicate(
    *,
    busy: bool,
    lifecycle_state: int,
) -> dict[str, Any]:
    """Reproduce FUN_0080bec0's exact boolean predicate."""
    ready = not bool(busy) and int(lifecycle_state) == 1
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-ready-predicate",
        "result": ready,
        "condition": "+0x2694 == 0 and +0x2630 == 1",
        "evidence": {"function": "FUN_0080bec0"},
    }


def describe_camera_service_gate(
    *,
    camera_manager_ready: bool,
) -> dict[str, Any]:
    """Trace FUN_0080be30's dependency gate."""
    if not camera_manager_ready:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "camera-service-gate",
            "result": False,
            "actions": [],
            "evidence": {
                "function": "FUN_0080be30",
                "gate": "+0x820 != 0",
            },
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-service-gate",
        "result": True,
        "actions": [{"action": "FUN_00811380"}],
        "evidence": {
            "function": "FUN_0080be30",
            "gate": "+0x820 != 0",
        },
    }


def describe_camera_input_command(
    *,
    command_id: int,
    command_data: Any,
) -> dict[str, Any]:
    """Trace FUN_0080c1b0."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-input-command",
        "actions": [
            {
                "action": "FUN_008127c0",
                "arguments": {
                    "camera_system": "manager +0x568",
                    "command_id": int(command_id),
                    "command_data": command_data,
                },
            },
            {
                "action": "FUN_0080be50",
                "arguments": {
                    "first": 0,
                    "second": 0,
                    "camera_id": -1,
                    "slot_index": 0,
                },
            },
        ],
        "evidence": {
            "function": "FUN_0080c1b0",
            "camera_system": "+0x568",
            "secondary_dispatch": "FUN_0080be50",
        },
    }


def describe_slot_is_static_camera(
    *,
    busy: bool,
    camera_type_result: int,
) -> dict[str, Any]:
    """Reproduce FUN_0080c1e0's exact predicate with opaque type helper."""
    result = not bool(busy) and int(camera_type_result) == 1
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "slot-static-camera-predicate",
        "result": result,
        "camera_type_result": int(camera_type_result),
        "condition": "+0x2694 == 0 and FUN_00438f30(slot,+0x2568) == 1",
        "evidence": {"function": "FUN_0080c1e0"},
        "limitations": [
            "camera_type_result remains the opaque FUN_00438f30 return value",
        ],
    }
