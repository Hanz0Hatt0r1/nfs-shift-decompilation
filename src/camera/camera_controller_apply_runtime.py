"""Evidence-backed camera-controller application from SHIFT.exe.

FUN_0080d300 applies a resolved camera source and mode to one CameraManager
slot. It sets the active/refresh fields, stores the manager back-reference into
the source, calls the source vtable method at +0x64, applies mode-1 buffer state
through FUN_0081c920/FUN_0081cb60 when a sub-index is provided, then copies a
three-dword state tuple via FUN_0080ce30.

FUN_0080d4a0 restores the saved switch state: it reinstates +0x26a8, calls
FUN_0080d3d0 with the saved mode/sub-index/sub-flag/camera id, then reapplies the
saved camera source through FUN_0080d300.

Camera math and source object behavior remain opaque.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORMAT = "SHIFT.CameraControllerApplyRuntime/1"


@dataclass(frozen=True)
class CameraControllerApplyState:
    """Runtime state written by FUN_0080d300 when a camera source is present."""

    enabled: bool = False  # +0x2690
    camera_source: Any = None  # +0x2568
    mode: int = 0  # +0x26a8
    refresh_requested: bool = False  # +0x2698


@dataclass(frozen=True)
class CameraSourceState:
    """Fields read from camera_source after the vtable callback."""

    mode: int  # camera_source[0x44] -> +0x26a8
    buffer_sub_index: int  # active buffer +0xe4
    owner_before: Any = None


@dataclass(frozen=True)
class CameraControllerRollback:
    """Saved fields consumed by FUN_0080d4a0."""

    previous_mode: int  # +0x26ac
    previous_camera_source: Any  # +0x256c
    previous_buffer_sub_index: int  # +0x2574
    previous_buffer_sub_flag: int  # +0x257c
    previous_camera_id: int  # +0x2578


def _signed_i8(value: int) -> int:
    value = int(value) & 0xFF
    return value if value < 0x80 else value - 0x100


def apply_camera_controller(
    state: CameraControllerApplyState,
    *,
    camera_source_present: bool,
    camera_source: Any,
    mode: int,
    buffer_sub_index: int,
    buffer_sub_flag: int,
    source_state_after_callback: CameraSourceState | None,
    manager_marker: Any = "this",
) -> tuple[CameraControllerApplyState, dict[str, Any]]:
    """Model the field writes and helper-call order in FUN_0080d300."""
    if not camera_source_present:
        return state, {
            "format": FORMAT,
            "version": 1,
            "status": "no-camera-source",
            "changed": False,
            "state_after": {
                "enabled": state.enabled,
                "camera_source": state.camera_source,
                "mode": state.mode,
                "refresh_requested": state.refresh_requested,
            },
            "evidence": {"function": "FUN_0080d300", "null_source_branch": "return"},
        }

    requested_mode = int(mode)
    requested_sub_index = int(buffer_sub_index)
    requested_sub_flag = _signed_i8(buffer_sub_flag)

    state_after = CameraControllerApplyState(
        enabled=True,
        camera_source=camera_source,
        mode=requested_mode,
        refresh_requested=False,
    )

    actions: list[dict[str, Any]] = [
        {"action": "+0x2690 = 1"},
        {"action": "+0x2568 = camera_source"},
        {
            "action": "camera_source[0x44] owner/back-reference = this",
            "source_offset": 0x44,
            "source_index_0x11": 0x11,
            "value": manager_marker,
        },
        {"action": "+0x26a8 = mode", "value": requested_mode},
        {"action": "+0x2698 = 0"},
        {
            "action": "camera_source.vtable[0x64]()",
            "evidence": "FUN_0080d300",
        },
    ]

    if requested_mode == 1 and requested_sub_index != -1:
        actions.extend(
            [
                {
                    "action": "FUN_0081c920(active_buffer+0x20, sub_index, 0)",
                    "sub_index": requested_sub_index,
                },
                {
                    "action": "FUN_0081cb60(active_buffer+0x20, sub_flag)",
                    "sub_flag_signed_i8": requested_sub_flag,
                },
            ]
        )
    else:
        actions.append(
            {
                "action": "no mode-1 buffer apply",
                "reason": (
                    "mode != 1"
                    if requested_mode != 1
                    else "sub_index == -1"
                ),
            }
        )

    post_state: dict[str, Any] | None = None
    if source_state_after_callback is not None:
        post_state = {
            "word0_plus_0x2a14": "manager +0x26b0",
            "word1_plus_0x2a18": int(source_state_after_callback.mode),
            "word2_plus_0x2a1c": int(source_state_after_callback.buffer_sub_index),
        }
        actions.append(
            {
                "action": "FUN_0080ce30",
                "writes": {
                    "+0x2a14": "manager +0x26b0",
                    "+0x2a18": int(source_state_after_callback.mode),
                    "+0x2a1c": int(source_state_after_callback.buffer_sub_index),
                },
            }
        )
    else:
        post_state = {
            "word0_plus_0x2a14": "manager +0x26b0",
            "word1_plus_0x2a18": None,
            "word2_plus_0x2a1c": None,
        }
        actions.append(
            {
                "action": "FUN_0080ce30",
                "status": "source-state-unresolved",
                "writes": {
                    "+0x2a14": "manager +0x26b0",
                    "+0x2a18": "camera_source+0x44 -> referenced +0x26a8",
                    "+0x2a1c": "camera_source active buffer +0xe4",
                },
            }
        )

    return state_after, {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "changed": True,
        "state_after": {
            "enabled": state_after.enabled,
            "camera_source": state_after.camera_source,
            "mode": state_after.mode,
            "refresh_requested": state_after.refresh_requested,
        },
        "actions": actions,
        "post_apply_state": post_state,
        "evidence": {
            "apply_function": "FUN_0080d300",
            "enabled_field": "+0x2690",
            "camera_source_field": "+0x2568",
            "mode_field": "+0x26a8",
            "refresh_field": "+0x2698",
            "source_back_reference": "camera_source[0x11] = this",
            "source_callback": "vtable +0x64",
            "mode1_select": "FUN_0081c920",
            "mode1_flag": "FUN_0081cb60",
            "post_state_copy": "FUN_0080ce30",
        },
        "limitations": [
            "camera_source vtable behavior is unresolved",
            "FUN_0081c920/FUN_0081cb60 semantics are preserved as helper boundaries",
            "the manager +0x26b0 source value is intentionally retained as an opaque reference",
        ],
    }


def restore_camera_controller(
    rollback: CameraControllerRollback,
    *,
    gate_state: dict[str, Any],
) -> dict[str, Any]:
    """Trace FUN_0080d4a0's exact rollback call ordering."""
    return {
        "format": FORMAT,
        "version": 1,
        "status": "restore-prepared",
        "state_write": {
            "action": "+0x26a8 = +0x26ac",
            "mode": int(rollback.previous_mode),
        },
        "gate": {
            "action": "FUN_0080d3d0",
            "arguments": {
                "mode": int(rollback.previous_mode),
                "sub_index": int(rollback.previous_buffer_sub_index),
                "sub_flag_signed_i8": _signed_i8(rollback.previous_buffer_sub_flag),
                "camera_id": int(rollback.previous_camera_id),
            },
            "nested_gate_result": gate_state,
        },
        "reapply": {
            "action": "FUN_0080d300",
            "arguments": {
                "mode": int(rollback.previous_mode),
                "camera_source": rollback.previous_camera_source,
                "sub_index": int(rollback.previous_buffer_sub_index),
                "sub_flag_signed_i8": _signed_i8(rollback.previous_buffer_sub_flag),
            },
        },
        "evidence": {
            "restore_function": "FUN_0080d4a0",
            "mode_field": "+0x26a8",
            "saved_mode": "+0x26ac",
            "saved_camera_source": "+0x256c",
            "saved_sub_index": "+0x2574",
            "saved_sub_flag": "+0x257c",
            "saved_camera_id": "+0x2578",
        },
        "limitations": [
            "FUN_0080d3d0 is represented by the nested gate boundary and not reimplemented here",
        ],
    }
