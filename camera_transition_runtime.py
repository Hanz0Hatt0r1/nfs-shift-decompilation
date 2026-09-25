"""Evidence-backed CameraManager transition helpers from SHIFT.exe.

Recovered directly from FUN_0080de00, FUN_0080d520, FUN_0080e0d0,
FUN_0080e140, and FUN_0080dfd0.

These functions orchestrate already-decoded state boundaries:
FUN_0080d3d0 (switch gate), FUN_0080d300 (controller apply), FUN_0080d500
(active-group commit), FUN_0080d4a0 (rollback), and the camera-buffer helpers.
The module records exact argument/order behavior without assigning new
semantics to opaque vtable/helper calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORMAT = "SHIFT.CameraTransitionRuntime/1"


@dataclass(frozen=True)
class CameraTransitionState:
    active_group: int = -1  # +0x26a4
    camera_id: int = -1  # +0x26a0
    active_buffer_index: int = 0  # +0x2560
    tracking_marker: Any = None  # +0x568-owned state/opaque


def describe_static_view_switch(
    state: CameraTransitionState,
    *,
    requested_group: int,
    requested_sub_index: int,
    sub_flag: int,
) -> dict[str, Any]:
    """Trace FUN_0080de00."""
    old_group = int(state.active_group)
    group = int(requested_group)
    sub_index = int(requested_sub_index)
    flag = int(sub_flag) & 0xFF

    actions: list[dict[str, Any]] = []
    if old_group != group and old_group != -1:
        actions.extend([
            {
                "action": "FUN_0080ce10",
                "arguments": {"group": old_group, "enabled": 0},
            },
            {
                "action": "FUN_0080cdf0",
                "arguments": {"group": old_group, "enabled": 1},
            },
        ])

    actions.extend([
        {
            "action": "FUN_0080d3d0",
            "arguments": {
                "mode": 1,
                "sub_index": sub_index,
                "sub_flag": flag,
                "camera_id": -1,
            },
        },
        {
            "action": "FUN_0081caa0",
            "arguments": {
                "target": "active_buffer +0x20",
                "value": group,
            },
        },
        {
            "action": "FUN_0080d300",
            "arguments": {
                "mode": 1,
                "source": "active_buffer +0x20",
                "sub_index": sub_index,
                "sub_flag": flag,
            },
        },
        {
            "action": "FUN_0080d500",
            "arguments": {"group": group},
        },
        {
            "action": "write +0x26a0",
            "value": -1,
        },
    ])

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-view-switch",
        "state_before": {
            "active_group": old_group,
            "camera_id": int(state.camera_id),
        },
        "requested": {
            "group": group,
            "sub_index": sub_index,
            "sub_flag": flag,
        },
        "state_after": {
            "active_group": group,
            "camera_id": -1,
        },
        "actions": actions,
        "evidence": {
            "function": "FUN_0080de00",
            "active_group_field": "+0x26a4",
            "camera_id_field": "+0x26a0",
            "active_buffer_index": "+0x2560",
            "tracking_local_flag": "+0x2a75",
        },
        "limitations": [
            "FUN_0081caa0 is kept as a buffer-selector helper boundary",
            "group deactivation/activation helper semantics remain opaque",
        ],
    }


def describe_static_camera_activation(
    *,
    runtime_argument: Any,
    camera_id: int,
) -> dict[str, Any]:
    """Trace FUN_0080e140's mode-3 application path."""
    return _describe_camera_mode_apply(
        mode=3,
        runtime_argument=runtime_argument,
        camera_id=camera_id,
        source="active_buffer +0x17a0",
    )


def describe_tracking_camera_activation(
    *,
    runtime_argument: Any,
    camera_id: int,
) -> dict[str, Any]:
    """Trace FUN_0080e0d0's mode-2 application path."""
    return _describe_camera_mode_apply(
        mode=2,
        runtime_argument=runtime_argument,
        camera_id=camera_id,
        source="active_buffer +0x1ca0",
    )


def _describe_camera_mode_apply(
    *,
    mode: int,
    runtime_argument: Any,
    camera_id: int,
    source: str,
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-mode-apply",
        "mode": int(mode),
        "camera_id": int(camera_id),
        "actions": [
            {
                "action": "FUN_0080d3d0",
                "arguments": {
                    "mode": int(mode),
                    "sub_index": -1,
                    "sub_flag": 0,
                    "camera_id": int(camera_id),
                },
            },
            {
                "action": f"{source}.vtable +0x90(runtime_argument)",
                "runtime_argument": runtime_argument,
            },
            {
                "action": "FUN_0080d300",
                "arguments": {
                    "mode": int(mode),
                    "source": source,
                    "sub_index": -1,
                    "sub_flag": 0,
                },
            },
        ],
        "evidence": {
            "tracking_mode_function": "FUN_0080e0d0",
            "static_mode_function": "FUN_0080e140",
            "switch_gate": "FUN_0080d3d0",
            "controller_apply": "FUN_0080d300",
            "tracking_source": "+0x1ca0, stride 0x460",
            "static_source": "+0x17a0, stride 0x280",
        },
        "limitations": [
            "the +0x90 vtable operation is not assigned a semantic name",
        ],
    }


def describe_external_view_source(
    *,
    source: Any,
    parameter: int,
    current_source: Any,
) -> dict[str, Any]:
    """Trace FUN_0080d520's external-view/source operation."""
    actions: list[dict[str, Any]] = [
        {
            "action": "FUN_0081b170",
            "arguments": {
                "source": source,
                "parameter": int(parameter),
                "manager": "this",
            },
        }
    ]

    if int(parameter) == 0:
        actions.append({"action": "FUN_0080d4a0"})
        status = "rollback"
    elif current_source is not source:
        actions.extend([
            {
                "action": "FUN_0080d3d0",
                "arguments": {
                    "mode": 4,
                    "sub_index": -1,
                    "sub_flag": 0,
                    "camera_id": -1,
                },
            },
            {
                "action": "FUN_0080d300",
                "arguments": {
                    "mode": 4,
                    "source": source,
                    "sub_index": -1,
                    "sub_flag": 0,
                },
            },
        ])
        status = "external-source-applied"
    else:
        status = "same-source-no-switch"

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "external-view-source",
        "parameter": int(parameter),
        "source": source,
        "current_source": current_source,
        "status": status,
        "actions": actions,
        "evidence": {
            "function": "FUN_0080d520",
            "preapply_helper": "FUN_0081b170",
            "rollback_branch": "parameter == 0",
            "mode_four_gate": "FUN_0080d3d0",
            "mode_four_apply": "FUN_0080d300",
        },
        "limitations": [
            "FUN_0081b170 parameter semantics remain unresolved",
        ],
    }


def describe_tracking_flag_update(
    *,
    update_flag: int,
    manager_busy: bool,
    active_camera_source_present: bool,
    active_sub_index: int,
) -> dict[str, Any]:
    """Trace FUN_0080dfd0's local tracking/sub-view flag update."""
    flag = int(update_flag) & 0xFF
    if manager_busy:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-flag-update",
            "status": "busy-no-op",
            "actions": [],
            "evidence": {
                "function": "FUN_0080dfd0",
                "guard": "+0x269c == 0",
            },
        }

    actions: list[dict[str, Any]] = [{"action": "write +0x2a75", "value": flag}]
    if active_camera_source_present:
        actions.extend([
            {
                "action": "FUN_0080d3d0",
                "arguments": {
                    "mode": 1,
                    "sub_index": int(active_sub_index),
                    "sub_flag": flag,
                    "camera_id": -1,
                },
            },
            {
                "action": "FUN_0080d300",
                "arguments": {
                    "mode": 1,
                    "source": "active_buffer +0x20",
                    "sub_index": int(active_sub_index),
                    "sub_flag": flag,
                },
            },
        ])

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-flag-update",
        "status": "applied",
        "flag": flag,
        "actions": actions,
        "evidence": {
            "function": "FUN_0080dfd0",
            "flag_field": "+0x2a75",
            "active_source": "active buffer +0xa0",
            "active_sub_index": "active buffer +0xe4",
        },
        "limitations": [
            "the checked +0xa0 field is represented only as a presence gate",
        ],
    }
