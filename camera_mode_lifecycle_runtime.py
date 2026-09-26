"""Camera mode lifecycle state machine recovered from FUN_00818250..008186a0."""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.CameraModeLifecycleRuntime/1"
INACTIVE_MODE = 0x7FFFFFFF


def enter_camera_mode(
    *,
    mode: int,
    collection_present: bool,
    reverse: bool,
    wheel_output_requested: bool = False,
    wheel_output_value: Any = None,
    extra_mode_value: Any = None,
) -> dict[str, Any]:
    """Trace the common active-mode branch used by 182f0/18380/18450/18540/18630/186a0."""
    actions: list[dict[str, Any]] = []
    if not collection_present:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "enter-mode",
            "status": "ignored",
            "mode": int(mode),
            "actions": actions,
        }

    actions.extend([
        {"action": "write +0x240", "value": 1},
        {"action": "write +0x244", "value": int(mode)},
        {"action": "FUN_00816570"},
        {"action": "write +0x24c", "value": 0},
        {"action": "write +0x248", "value": 0},
        {"action": "FUN_00817440", "args": [0, 1 if reverse else 0]},
    ])

    if wheel_output_requested:
        actions.append({
            "action": "write +0x260",
            "value": extra_mode_value if extra_mode_value is not None else wheel_output_value,
        })
    actions.extend([
        {
            "action": "clear output matrix",
            "helper": "FUN_00401d10",
            "target": "+0x324",
        },
        {
            "action": "set output-valid",
            "target": "+0x328",
            "value": 1,
        },
        {
            "action": "set flags",
            "writes": {
                "+0x265": 1,
                "+0x266": 1,
            },
        },
    ])

    state = {
        "+0x240": 1,
        "+0x244": int(mode),
        "+0x248": 0,
        "+0x24c": 0,
        "+0x265": 1,
        "+0x266": 1,
    }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "enter-mode",
        "status": "entered",
        "mode": int(mode),
        "state": state,
        "actions": actions,
        "wheel_output_value": wheel_output_value,
        "evidence": {
            "entry_helpers": [
                "FUN_008182f0",
                "FUN_00818380",
                "FUN_00818450",
                "FUN_00818540",
                "FUN_00818630",
                "FUN_008186a0",
            ],
        },
    }


def leave_camera_mode(
    *,
    mode: int,
    collection_present: bool,
    clear_output: bool,
    reset_collection: bool,
    reset_selector: bool,
    reset_helper: int | None = None,
) -> dict[str, Any]:
    """Trace 18250/18400/184e0/185d0 mode-exit patterns."""
    actions: list[dict[str, Any]] = []
    if collection_present:
        actions.extend([
            {"action": "write +0x240", "value": 0},
            {"action": "write +0x244", "value": INACTIVE_MODE},
            {"action": "FUN_00816570"},
        ])
        if reset_selector:
            actions.extend([
                {"action": "write +0x24c", "value": 0},
                {"action": "write +0x248", "value": 0},
            ])
        if reset_helper is not None:
            actions.append({
                "action": "FUN_00818000",
                "argument": int(reset_helper),
            })
        actions.append({
            "action": "write mode-specific flag",
            "value": 1,
        })
    if clear_output:
        actions.extend([
            {"action": "clear output matrix", "helper": "FUN_00401d10"},
            {"action": "set output-valid", "value": 0},
        ])
    actions.append({
        "action": "FUN_00818250",
        "argument": 0 if not reset_selector else 1,
    })
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "leave-mode",
        "status": "processed",
        "mode": int(mode),
        "actions": actions,
        "evidence": {
            "mode_reset": "FUN_00816570",
            "inactive_mode": INACTIVE_MODE,
            "entry_reset": "FUN_00818250",
        },
    }


def describe_mode_command(mode: int) -> dict[str, Any]:
    """Map the source functions to raw mode IDs without assigning gameplay labels."""
    m = int(mode)
    active = {1: "FUN_008182f0", 2: "FUN_00818380", 3: "FUN_00818450", 4: "FUN_00818540", 5: "FUN_008186a0"}
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "mode-command",
        "mode": m,
        "function": active.get(m),
        "inactive_function": "FUN_00818400" if m == 0 else None,
        "evidence": {"mode_ids": sorted(active)},
    }
