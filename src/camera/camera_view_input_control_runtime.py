"""Evidence-backed control/flag boundary of FUN_0081c460.

FUN_0081c460 is a large CCameraView input update. This module captures the
deterministic guard and state writes before/around its unresolved numeric
smoothing branches. The source's decompiler-byte tests are represented as
explicit low-byte predicates rather than renamed gameplay booleans.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.CameraViewInputControlRuntime/1"


def low_byte_nonzero(value: int) -> bool:
    return (int(value) & 0xFF) != 0


def describe_camera_input_control(
    *,
    camera_service_ready: bool,
    profile_present: bool,
    profile_cockpit_flag: bool,
    action1_bit1: bool,
    action2_bit1: bool,
    action5_bit0: bool,
    param4_low_byte_nonzero: bool,
    param5_low_byte_zero: bool,
    current_cockpit_state: bool,
    profile_has_cockpit_semantics: bool,
    global_gate_c25f08: bool,
) -> dict[str, Any]:
    """Trace the flag/guard portions of FUN_0081c460 in source order."""
    actions: list[dict[str, Any]] = []

    if camera_service_ready:
        actions.append({
            "action": "FUN_00675a70(this + 0x180)",
            "condition": "FUN_0080be30(manager) != 0",
        })
        frame_stack_state = "enabled"
    else:
        actions.append({
            "action": "FUN_00675c20(this + 0x180)",
            "condition": "FUN_0080be30(manager) == 0",
        })
        frame_stack_state = "disabled"

    if (
        param5_low_byte_zero
        and action1_bit1
        and not global_gate_c25f08
    ):
        actions.append({
            "action": "write manager +0x2a74",
            "value": 1,
            "condition": "param5.low8 == 0 && action[1]+0x28 bit1 && DAT_00c25f08 == 0",
        })

    computed_cockpit = bool(
        action2_bit1
        and not param4_low_byte_nonzero
        and profile_cockpit_flag
    )
    if current_cockpit_state != computed_cockpit:
        actions.append({
            "action": "write manager +0x2a75",
            "value": int(computed_cockpit),
            "condition": "current +0xd2 differs from computed action/profile state",
        })
        cockpit_state_changed = True
    else:
        cockpit_state_changed = False

    actions.append({
        "action": "write +0xd3",
        "value": int(bool(action5_bit0)),
        "source": "action[5] +0x28 bit0",
    })

    actions.append({
        "action": "FUN_0081bdb0",
        "arguments": {
            "target": "+0x2d0",
            "output": "+0x84",
        },
    })

    if not profile_has_cockpit_semantics:
        if profile_present:
            actions.append({
                "action": "profile-name check",
                "name": "CockpitCam",
                "lookup": "FUN_00811570",
                "compare": "+0xc4",
            })
        if profile_present and not profile_has_cockpit_semantics:
            numeric_branch = "non-cockpit-profile"
        else:
            numeric_branch = "no-profile"
    else:
        numeric_branch = "cockpit-profile"

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-input-control",
        "frame_stack_state": frame_stack_state,
        "cockpit_state_computed": computed_cockpit,
        "cockpit_state_changed": cockpit_state_changed,
        "numeric_branch": numeric_branch,
        "actions": actions,
        "evidence": {
            "function": "FUN_0081c460",
            "service_gate": "FUN_0080be30",
            "frame_stack": "+0x180",
            "look_behind_flag": "manager +0x2a74",
            "cockpit_output": "manager +0x2a75",
            "cockpit_state": "+0xd2",
            "action5_state": "+0xd3",
            "shake_target": "+0x84",
            "cockpit_profile_offset": "+0xb8",
            "cockpit_profile_scale": "+0x14",
            "global_guard": "DAT_00c25f08",
        },
        "limitations": [
            "the large numeric smoothing branch is not collapsed into guessed gameplay names",
            "FUN_0081bdb0 output and FUN_00823*/FUN_0090* helpers remain separate runtime boundaries",
            "profile-name equality with CockpitCam is retained as a raw selector check",
        ],
    }


def describe_cockpit_profile_blend(
    *,
    has_cockpit_semantics: bool,
    local_c: float,
    local_8: float,
    current_84: float,
    current_88: float,
    delta: float,
) -> dict[str, Any]:
    """Expose the exact high-level branch predicates around c460's cockpit path."""
    abs_local_c = abs(float(local_c))
    abs_local_8 = abs(float(local_8))
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "cockpit-profile-branch",
        "has_cockpit_semantics": bool(has_cockpit_semantics),
        "predicates": {
            "local_c_abs_gt_0.1": abs_local_c > 0.1,
            "local_8_abs_le_0.1": abs_local_8 <= 0.1,
            "delta": float(delta),
        },
        "state_before": {
            "+0x84": float(current_84),
            "+0x88": float(current_88),
        },
        "branch_actions": (
            [
                {
                    "condition": "abs(local_c) > 0.1",
                    "action": "+0x88 -= delta * 2.0 * local_c; FUN_0081b610(+0x88)",
                },
                {
                    "condition": "abs(local_8) <= 0.1 and abs(param2) > 3 and !action5.bit0 and param4.low8 == 0",
                    "action": "blend +0x84/+0x88 toward FUN_0081bdb0 target",
                },
                {
                    "condition": "abs(local_8) > 0.1",
                    "action": "+0x84 += delta * 2.0 * local_8; FUN_0040f3e0(+0x84, limits +0x560/+0x564)",
                },
            ]
            if has_cockpit_semantics
            else [
                {
                    "condition": "profile absent or profile +0xb8 == 0",
                    "action": "use non-cockpit branch",
                }
            ]
        ),
        "helper_boundaries": [
            "FUN_0081b610",
            "FUN_0040f3e0",
            "FUN_0081bdb0",
        ],
        "evidence": {
            "function": "FUN_0081c460",
            "dead_zone": 0.1,
            "threshold": 3.0,
            "orientation_gain": 2.0,
            "global_limit_degrees": ["manager +0x560", "manager +0x564"],
        },
    }
