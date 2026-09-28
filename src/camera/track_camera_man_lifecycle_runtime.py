"""Evidence-backed TrackCameraMan loader/lifecycle runtime.

Recovered directly from FUN_008127c0, FUN_00812940, FUN_00812970,
FUN_00812980, FUN_008129b0 and FUN_00812aa0.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

FORMAT = "SHIFT.TrackCameraManLifecycleRuntime/1"
INPUT_SLOT_BASE = 0x260
INPUT_SLOT_COUNT = 7
VALID_INPUT_MIN = 1
VALID_INPUT_MAX = 6


def describe_track_camera_load(
    *,
    param_name_present: bool,
    helper_635e40_nonzero: bool,
    helper_12180_named_result: bool,
    helper_12180_fallback_result: bool,
    local_cams_result: bool,
) -> dict[str, Any]:
    """Trace FUN_008127c0 source order and status accumulation."""
    actions: list[dict[str, Any]] = [
        {"action": "write +0xb4", "value": 0},
        {
            "action": "notify parent vtable +0x14",
            "name": "TrackCameraMan",
        },
    ]

    if not helper_635e40_nonzero:
        actions.extend([
            {
                "action": "FUN_00632920",
                "source": "param_1 +0x08",
                "fallback": "DAT_00aa9b60",
            },
            {
                "action": "FUN_00632920",
                "source": "param_1 +0x14",
            },
            {
                "action": "FUN_00812180",
                "path_mode": "named-path",
                "name_present": bool(param_name_present),
                "result": bool(helper_12180_named_result),
            },
        ])
        main_result = bool(helper_12180_named_result)
        if not main_result:
            actions.append({
                "action": "build path",
                "format": r"Cameras\%s.xml",
            })
            actions.append({
                "action": "FUN_00812180",
                "path_mode": "fallback-path",
                "result": bool(helper_12180_fallback_result),
            })
            main_result = bool(helper_12180_fallback_result)
    else:
        actions.extend([
            {
                "action": "build path",
                "format": r"Cameras\%s.xml",
            },
            {
                "action": "FUN_00812180",
                "path_mode": "fallback-path",
                "result": bool(helper_12180_fallback_result),
            },
        ])
        main_result = bool(helper_12180_fallback_result)

    actions.append({"action": "FUN_00811a90", "argument": 0})
    actions.extend([
        {
            "action": "build path",
            "components": ["Cameras\\", "localCams", ".xml"],
        },
        {
            "action": "FUN_00811ae0",
            "path": r"Cameras\localCams.xml",
            "result": bool(local_cams_result),
        },
        {
            "action": "OR status into +0xb0",
        },
        {
            "action": "notify vtable +0x28",
        },
    ])

    status_word = int(main_result) | int(bool(local_cams_result))
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "track-camera-load",
        "status": status_word,
        "named_loader_result": bool(helper_12180_named_result),
        "fallback_loader_result": bool(helper_12180_fallback_result),
        "local_cams_result": bool(local_cams_result),
        "actions": actions,
        "evidence": {
            "function": "FUN_008127c0",
            "status_field": "+0xb0",
            "dirty_field": "+0xb4",
            "track_file_loader": "FUN_00812180",
            "local_camera_loader": "FUN_00811ae0",
            "pre_local_reload": "FUN_00811a90(0)",
        },
    }


def set_tracking_target(*, target: Any) -> dict[str, Any]:
    """Reproduce FUN_00812970."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "set-tracking-target",
        "action": {
            "action": "write +0xe8",
            "value": target,
        },
        "evidence": {"function": "FUN_00812970"},
    }


def clear_tracking_input_slots(
    slots: Sequence[Any],
    *,
    release_callback: str = "slot-object-vtable[0](1)",
) -> tuple[list[Any], dict[str, Any]]:
    """Reproduce FUN_00812980."""
    if len(slots) != INPUT_SLOT_COUNT:
        raise ValueError("TrackCameraMan input storage contains seven slots")
    released = [slot for slot in slots if slot not in (None, 0)]
    return [None] * INPUT_SLOT_COUNT, {
        "format": FORMAT,
        "version": 1,
        "operation": "clear-tracking-input-slots",
        "released_count": len(released),
        "actions": [
            {
                "action": release_callback,
                "count": len(released),
            },
            {
                "action": "zero seven slots",
                "base_offset": INPUT_SLOT_BASE,
            },
        ],
        "evidence": {
            "function": "FUN_00812980",
            "slot_range": "+0x260..+0x278",
        },
    }


def register_tracking_input_slot(
    slots: Sequence[Any],
    *,
    action_index: int,
    action_object: Any,
    frame_stack_accepts: bool,
) -> tuple[list[Any], dict[str, Any]]:
    """Reproduce FUN_008129b0 exactly, including its zero return on failure."""
    if len(slots) != INPUT_SLOT_COUNT:
        raise ValueError("TrackCameraMan input storage contains seven slots")
    next_slots = list(slots)
    index = int(action_index)

    if action_object in (None, 0):
        return next_slots, {
            "format": FORMAT,
            "version": 1,
            "status": "rejected",
            "return_low_byte": 0,
        }

    shifted = index - 1
    if shifted >= 0 and shifted < 6 and next_slots[index] in (None, 0):
        if frame_stack_accepts:
            next_slots[index] = action_object
            return next_slots, {
                "format": FORMAT,
                "version": 1,
                "status": "registered",
                "slot": index,
                "storage_offset": INPUT_SLOT_BASE + index * 4,
                "return_low_byte": 1,
                "evidence": {
                    "function": "FUN_008129b0",
                    "frame_stack": "+0x140",
                    "valid_range": "1..6",
                },
            }

    return next_slots, {
        "format": FORMAT,
        "version": 1,
        "status": "rejected",
        "return_low_byte": 0,
        "evidence": {
            "function": "FUN_008129b0",
            "valid_range": "1..6",
        },
    }


def resolve_target_from_attachment(
    *,
    target_attachment: Any | None,
    target_attachment_count_nonzero: bool = True,
    service_candidates: Sequence[Mapping[str, Any]],
    target_compare_result_by_candidate: Mapping[int, bool] | None = None,
) -> dict[str, Any]:
    """Trace FUN_00812aa0.

    If a target attachment exists and is non-empty, the service list is scanned
    and each candidate's +0x60 is compared against the attachment. First match
    is stored at +0xe8. Otherwise the selected camera config index is obtained
    through FUN_00811570 and stored at +0xd8.
    """
    if target_attachment not in (None, 0) and bool(target_attachment_count_nonzero):
        compares = target_compare_result_by_candidate or {}
        for ordinal, candidate in enumerate(service_candidates):
            matches = bool(compares.get(ordinal, candidate.get("matches_attachment", False)))
            row = {
                "ordinal": ordinal,
                "candidate": candidate,
                "actions": [
                    {
                        "action": "FUN_00408210",
                        "arguments": {
                            "candidate_field": "+0x60",
                            "attachment": "+0xd4",
                        },
                        "result": matches,
                    },
                ],
            }
            if matches:
                return {
                    "format": FORMAT,
                    "version": 1,
                    "operation": "resolve-target",
                    "status": "service-match",
                    "selected": candidate,
                    "write": {
                        "offset": "+0xe8",
                        "value": candidate,
                    },
                    "actions": [
                        {"action": "FUN_00812aa0"},
                        {"action": "FUN_0081ea70"},
                        *row["actions"],
                        {"action": "FUN_00812970", "value": candidate},
                    ],
                    "evidence": {
                        "function": "FUN_00812aa0",
                        "attachment_field": "+0xd4",
            "attachment_count_field": "short(*(int *)(+0xd4 - 4))",
                        "stored_target": "+0xe8",
                    },
                }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "resolve-target",
        "status": "camera-config-fallback",
        "actions": [
            {"action": "FUN_00630fe0", "target": "temporary attachment string"},
            {"action": "FUN_00811570", "result": "selected camera index"},
            {"action": "write +0xd8", "source": "selected camera index"},
        ],
        "evidence": {
            "function": "FUN_00812aa0",
            "fallback_index_field": "+0xd8",
        },
    }
