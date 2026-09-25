"""Evidence-backed CameraManager snapshot and double-buffer transition.

FUN_0080e040 serializes the current camera-manager state for rollback/update
handling. FUN_0080cd40 toggles the active camera-data buffer and copies the
opposite buffer's camera/static/tracking state into the new active buffer.

The copy helpers are treated as opaque data-preserving operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORMAT = "SHIFT.CameraStateSnapshotRuntime/1"
BUFFER_COUNT = 2


@dataclass(frozen=True)
class CameraBufferState:
    index: int = 0
    sub_index: int = -1
    sub_flag: int = 0
    camera_source: Any = None


@dataclass(frozen=True)
class CameraManagerState:
    active_buffer_index: int = 0
    camera_source: Any = None
    mode: int = 0
    sub_index: int = -1
    camera_id: int = -1
    active_group: int = -1
    group_restore_value: int | None = None
    sub_flag: int = 0


def snapshot_camera_state(
    state: CameraManagerState,
    *,
    group_restore_value: int | None = None,
) -> dict[str, Any]:
    """Model FUN_0080e040's six-word rollback/update snapshot."""
    restore_group = (
        state.group_restore_value
        if group_restore_value is None
        else int(group_restore_value)
    )
    return {
        "format": FORMAT,
        "version": 1,
        "snapshot": {
            "camera_source": state.camera_source,
            "mode": int(state.mode),
            "buffer_sub_index": int(state.sub_index),
            "camera_id": int(state.camera_id),
            "active_group": int(state.active_group),
            "group_restore_value": restore_group,
            "buffer_index": int(state.active_buffer_index),
            "buffer_sub_flag": int(state.sub_flag),
        },
        "evidence": {
            "snapshot_function": "FUN_0080e040",
            "source_pointer": "+0x2568",
            "mode": "+0x26a8",
            "buffer_sub_index": "active buffer +0xe4",
            "camera_id": "+0x26a0",
            "active_group": "+0x26a4",
            "group_restore_value": "type-dependent active object +0x7c, otherwise +0x26a4",
            "active_buffer_index": "+0x2560",
            "buffer_sub_flag": "active buffer byte +0xf2",
        },
        "limitations": [
            "camera_source is preserved as an opaque runtime reference",
            "type-dependent group_restore_value selection is not inferred here",
        ],
    }


def begin_camera_buffer_swap(
    state: CameraBufferState,
    *,
    update_in_progress: bool = False,
) -> dict[str, Any]:
    """Model FUN_0080cd40's guarded double-buffer flip and copy directions."""
    old_index = int(state.index)
    if old_index not in (0, 1):
        raise ValueError("camera buffer index must be 0 or 1")
    if update_in_progress:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "busy",
            "changed": False,
            "old_index": old_index,
            "new_index": old_index,
            "update_in_progress": True,
            "evidence": {"swap": "FUN_0080cd40", "guard": "+0x269c"},
        }

    new_index = 1 - old_index
    return {
        "format": FORMAT,
        "version": 1,
        "status": "swapped",
        "changed": True,
        "old_index": old_index,
        "new_index": new_index,
        "update_in_progress": True,
        "copy_edges": {
            "camera_data": {
                "dst_base": f"buffer[{new_index}]+0x20",
                "src_base": f"buffer[{old_index}]+0xbe0",
                "helper": "FUN_0081e6c0",
            },
            "static_camera_state": {
                "dst_base": f"buffer[{new_index}]+0x17a0",
                "src_base": f"buffer[{old_index}]+0x1a20",
                "stride": "0x280",
                "helper": "FUN_00815eb0",
            },
            "tracking_camera_state": {
                "dst_base": f"buffer[{new_index}]+0x1ca0",
                "src_base": f"buffer[{old_index}]+0x2100",
                "stride": "0x460",
                "helper": "FUN_00815eb0",
            },
        },
        "evidence": {
            "swap": "FUN_0080cd40",
            "active_buffer_field": "+0x2560",
            "reentrancy_guard": "+0x269c",
        },
    }


def complete_camera_buffer_update(state: CameraBufferState) -> dict[str, Any]:
    """Represent the externally observed completion of a guarded update."""
    index = int(state.index)
    if index not in (0, 1):
        raise ValueError("camera buffer index must be 0 or 1")
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "active_index": index,
        "update_in_progress": False,
        "evidence": {
            "completion_sites": ["FUN_0080ec80", "FUN_0080e650"],
            "guard_field": "+0x269c",
        },
    }
