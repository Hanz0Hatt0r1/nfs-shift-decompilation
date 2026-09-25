"""Evidence-backed CameraManager frame/update timing from SHIFT.exe.

FUN_0080c920 computes the manager's current timestamp, suppresses repeated
updates inside a 0x14-tick window once +0x824 is set, advances +0x828, marks
+0x824 set, then dispatches FUN_0080c710 and forwards the unsigned 32-bit
elapsed value to FUN_0080c510.

No timing-source frequency or absolute time unit is inferred here. The source
only proves the arithmetic and the 0x14 suppression threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.CameraUpdateRuntime/1"
SUPPRESSION_WINDOW = 0x14


@dataclass(frozen=True)
class CameraUpdateState:
    """The fields consumed/updated by FUN_0080c920."""

    time_cursor: int = 0  # +0x828
    time_initialized: bool = False  # +0x824


def resolve_camera_timestamp(
    base_timestamp: int,
    *,
    high_resolution_enabled: bool = False,
    high_resolution_delta: int = 0,
) -> int:
    """Reproduce the timestamp selection before FUN_0080c920's gate.

    With +0x4c bit 2 clear the executable uses +0x44 directly. With the bit
    set it calls FUN_0040f0d0(+0x3c) and adds that result to +0x44.
    """
    base = int(base_timestamp)
    if not high_resolution_enabled:
        return base
    return base + int(high_resolution_delta)


def elapsed_u32(current_timestamp: int, previous_timestamp: int) -> int:
    """Return the uint32 subtraction actually consumed by FUN_0080c510."""
    return (int(current_timestamp) - int(previous_timestamp)) & 0xFFFFFFFF


def step_camera_update_timing(
    state: CameraUpdateState,
    *,
    current_timestamp: int,
    events: Iterable[Mapping[str, Any]] = (),
    active_channel: int = 0,
) -> tuple[CameraUpdateState, dict[str, Any]]:
    """Model FUN_0080c920's timing gate and event/update ordering.

    Event dispatch reuses the already reconstructed FUN_0080c710 boundary. The
    camera controller itself remains the separate FUN_0080c510 boundary.
    """
    current = int(current_timestamp)
    elapsed = elapsed_u32(current, state.time_cursor)
    if state.time_initialized and elapsed < SUPPRESSION_WINDOW:
        return state, {
            "format": FORMAT,
            "version": 1,
            "status": "suppressed",
            "current_timestamp": current,
            "previous_timestamp": int(state.time_cursor),
            "elapsed_u32": elapsed,
            "event_dispatch": None,
            "controller_update": None,
            "side_effects": ["FUN_00649780(0,1)"],
            "evidence": {
                "update_wrapper": "FUN_0080c920",
                "guard_field": "+0x824",
                "cursor_field": "+0x828",
                "window": "0x14",
            },
        }

    previous = int(state.time_cursor)
    new_state = CameraUpdateState(time_cursor=current, time_initialized=True)

    from camera_event_stream_runtime import dispatch_camera_event_stream

    event_dispatch = dispatch_camera_event_stream(
        events,
        active_channel=int(active_channel) & 0xFF,
    )
    return new_state, {
        "format": FORMAT,
        "version": 1,
        "status": "updated",
        "current_timestamp": current,
        "previous_timestamp": previous,
        "elapsed_u32": elapsed,
        "event_dispatch": event_dispatch,
        "controller_update": {
            "target_function": "FUN_0080c510",
            "elapsed_u32": elapsed,
        },
        "side_effects": [
            "+0x828 = current_timestamp",
            "+0x824 = 1",
            "FUN_0080c710()",
            "FUN_0080c510(elapsed_u32)",
        ],
        "evidence": {
            "update_wrapper": "FUN_0080c920",
            "time_source_base": "+0x44",
            "high_resolution_flag": "+0x4c bit 2",
            "high_resolution_helper": "FUN_0040f0d0(+0x3c)",
            "cursor_field": "+0x828",
            "initialized_field": "+0x824",
            "event_dispatcher": "FUN_0080c710",
            "controller_update": "FUN_0080c510",
        },
        "limitations": [
            "FUN_0040f0d0 is treated as an opaque timestamp source",
            "the absolute time unit/frequency is unresolved",
            "FUN_0080c510 controller semantics are represented by its own runtime boundary",
        ],
    }
