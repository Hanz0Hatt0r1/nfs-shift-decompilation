"""Evidence-backed CameraManager controller-update boundary from SHIFT.exe.

FUN_0080c510 consumes an unsigned 32-bit elapsed value, converts it to float,
iterates exactly three camera-manager slots, performs an optional refresh through
FUN_0080d300, handles mode-specific FUN_0080c230/FUN_00812050 paths, decrements
+0x810 by elapsed*0.001 with a zero clamp, and updates a special bound object
when DAT_00c25f0c is present in its linked list.

Helper functions whose internal camera math is not reconstructed remain named
opaque calls. In particular FUN_00438f30 and FUN_0081bf00 results are inputs to
the trace rather than guessed meanings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

FORMAT = "SHIFT.CameraControllerUpdateRuntime/1"
SLOT_COUNT = 3
SLOT_STRIDE = 0x2AA0
TIME_SCALE = 0.001


@dataclass(frozen=True)
class CameraControllerInstance:
    """Fields of one 0x2aa0 camera-manager slot used by FUN_0080c510."""

    slot_index: int
    enabled: bool  # +0x2690 != 0
    busy: bool  # +0x2694 != 0
    refresh_requested: bool  # +0x2698 != 0
    mode: int  # +0x26a8
    camera_source: Any = None  # +0x2568
    active_buffer_sub_index: int = -1  # active buffer +0xe4
    active_group: int = -1  # +0x26a4
    view_check_c4: bool | None = None
    view_check_sub_index: bool | None = None


def elapsed_float_from_u32(elapsed_u32: int) -> dict[str, Any]:
    """Reproduce FUN_0080c510's uint32 -> float conversion boundary."""
    value = int(elapsed_u32) & 0xFFFFFFFF
    return {
        "elapsed_u32": value,
        "signed_int_view": value if value < 0x80000000 else value - 0x100000000,
        "float_elapsed": float(value),
        "scaled_delta": float(value) * TIME_SCALE,
        "scale_expression": "elapsed_u32 * 0.001",
    }


def _signed_low_byte(value: int) -> int:
    low = int(value) & 0xFF
    return low if low < 0x80 else low - 0x100


def _refresh_trace(instance: CameraControllerInstance) -> dict[str, Any]:
    if instance.mode == 1:
        controller_sub_index = _signed_low_byte(instance.active_buffer_sub_index)
    else:
        controller_sub_index = -1
    return {
        "action": "FUN_0080d300",
        "arguments": {
            "camera_type": "FUN_00438f30(instance, +0x2568)",
            "mode": int(instance.mode),
            "camera_source": instance.camera_source,
            "sub_index": controller_sub_index,
        },
        "source_helpers": ["FUN_00438f30", "FUN_0080d300"],
    }


def describe_camera_controller_update(
    instances: Sequence[CameraControllerInstance],
    *,
    elapsed_u32: int,
    feedback_flag: bool,
    timer: float,
    special_binding_present: bool = False,
) -> dict[str, Any]:
    """Trace the source-controlled update flow without inventing helper semantics."""
    if len(instances) != SLOT_COUNT:
        raise ValueError(f"FUN_0080c510 iterates exactly {SLOT_COUNT} camera slots")

    timing = elapsed_float_from_u32(elapsed_u32)
    shared_flag = bool(feedback_flag)
    rows: list[dict[str, Any]] = []

    for instance in instances:
        if int(instance.slot_index) not in range(SLOT_COUNT):
            raise ValueError("slot_index must be 0, 1, or 2")
        row: dict[str, Any] = {
            "slot_index": int(instance.slot_index),
            "slot_offset": int(instance.slot_index) * SLOT_STRIDE,
            "status": "eligible" if instance.enabled and not instance.busy else "skipped",
            "actions": [],
        }
        if not instance.enabled or instance.busy:
            rows.append(row)
            continue

        if instance.refresh_requested:
            row["actions"].append(_refresh_trace(instance))

        mode = int(instance.mode)
        if mode in (2, 3):
            mode23: dict[str, Any] = {
                "mode": mode,
                "post_refresh_mode": "re-read +0x26a8 after any FUN_0080c230",
                "conditional_reissue": None,
                "post_reissue_branches": [
                    {
                        "condition": "current runtime mode is 2 or 3",
                        "action": "FUN_00812050(+0x568, elapsed_u32 * 0.001, instance)",
                    },
                    {
                        "condition": "current runtime mode is 1",
                        "action": "execute mode-1 feedback branch described below",
                    },
                ],
            }
            if shared_flag:
                if instance.view_check_c4 is True:
                    mode23["conditional_reissue"] = {
                        "condition": "FUN_0081bf00(active_buffer+0x20, active_buffer+0xc4) != 0",
                        "action": "FUN_0080c230(outer_manager, +0x26a4, +0x26a4)",
                        "result": "re-read current +0x26a8 before next branch",
                    }
                elif instance.view_check_c4 is False:
                    mode23["conditional_reissue"] = {
                        "condition": "FUN_0081bf00(active_buffer+0x20, active_buffer+0xc4) == 0",
                        "action": "no FUN_0080c230 reissue",
                    }
                else:
                    mode23["conditional_reissue"] = {
                        "condition": "+0x82e != 0, then query FUN_0081bf00(active_buffer+0x20, active_buffer+0xc4)",
                        "action_if_true": "FUN_0080c230(outer_manager, +0x26a4, +0x26a4)",
                        "action_if_false": "continue",
                        "result": "current +0x26a8 is re-read after the helper",
                    }
            else:
                mode23["conditional_reissue"] = {
                    "condition": "+0x82e == 0",
                    "action": "no FUN_0080c230 reissue",
                }
            row["actions"].append(mode23)
        elif mode == 1:
            mode1: dict[str, Any] = {
                "mode": 1,
                "actions": ["+0x82e = 0"],
                "view_check": "FUN_0081bf00(active_buffer+0x20, active_buffer+0xe4)",
            }
            if instance.view_check_sub_index is False:
                shared_flag = True
                mode1["fallback"] = {
                    "condition": "FUN_0081bf00(...) == 0",
                    "action": "FUN_0080c230(outer_manager, +0x26a4, +0x26a4)",
                    "then": "+0x82e = 1",
                }
            elif instance.view_check_sub_index is True:
                mode1["fallback"] = {
                    "condition": "FUN_0081bf00(...) != 0",
                    "action": "no FUN_0080c230 fallback",
                }
            else:
                mode1["fallback"] = {
                    "condition": "FUN_0081bf00(...) == 0",
                    "action": "FUN_0080c230(outer_manager, +0x26a4, +0x26a4)",
                    "then": "+0x82e = 1",
                    "result": "view-check result unresolved",
                }
            row["actions"].append(mode1)
        else:
            row["actions"].append({
                "mode": mode,
                "action": "no mode-1/2/3 controller branch observed",
            })

        rows.append(row)

    timer_before = float(timer)
    timer_after = timer_before - timing["scaled_delta"]
    timer_clamped = timer_after <= 0.0
    if timer_clamped:
        timer_after = 0.0

    special_action = None
    if special_binding_present:
        special_action = {
            "condition": "linked-list contains DAT_00c25f0c",
            "actions": [
                "FUN_0081b340(FUN_0080bdd0(this,0), +0x810)",
                "FUN_0081b330(FUN_0080bdd0(this,0), +0x814)",
            ],
        }

    return {
        "format": FORMAT,
        "version": 1,
        "slot_count": SLOT_COUNT,
        "slot_stride": SLOT_STRIDE,
        "timing": timing,
        "feedback_flag_before": bool(feedback_flag),
        "feedback_flag_after_observed_mode1_fallback": bool(shared_flag),
        "instances": rows,
        "timer": {
            "before": timer_before,
            "after_subtract": timer_before - timing["scaled_delta"],
            "after_clamp": timer_after,
            "clamped_to_zero": timer_clamped,
            "field": "+0x810",
            "other_field": "+0x814",
        },
        "special_binding": special_action,
        "evidence": {
            "controller_update": "FUN_0080c510",
            "slot_base": "+0x290",
            "slot_stride": "0x2aa0",
            "slot_end_exclusive": "0x7fe0",
            "enabled_field": "+0x2690",
            "busy_field": "+0x2694",
            "refresh_field": "+0x2698",
            "mode_field": "+0x26a8",
            "camera_source_field": "+0x2568",
            "active_group_field": "+0x26a4",
            "feedback_flag": "+0x82e",
            "timer": "+0x810",
            "special_lookup": "FUN_0080bdd0(this,0)",
            "special_symbol": "DAT_00c25f0c",
        },
        "limitations": [
            "FUN_00438f30 and FUN_0081bf00 remain opaque helpers",
            "FUN_0080c230 may change +0x26a8, so the source re-read is reported as a branch boundary rather than guessed",
            "FUN_00812050 camera math is not synthesized",
            "linked-list ownership of DAT_00c25f0c remains unresolved",
        ],
    }
