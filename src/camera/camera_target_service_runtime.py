"""Evidence-backed camera target/service helpers.

Recovered from FUN_00812970/12980/129b0, FUN_00812aa0, FUN_00812b60,
FUN_00812c00, FUN_00812cf0, FUN_00812d20, FUN_00812da0, FUN_00812de0,
FUN_00812e40 and FUN_00812ed0.

These functions are kept at their raw vtable/offset boundaries; no gameplay
meaning is assigned to the target handles or the shake quaternion helpers.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.CameraTargetServiceRuntime/1"
RTTI_TRACKING = "DAT_00c25fb8"
INPUT_SLOT_BASE = 0x260


def set_tracking_target(this_state: Mapping[str, Any], target: Any) -> dict[str, Any]:
    """Reproduce FUN_00812970's single pointer assignment."""
    result = dict(this_state)
    result["+0xe8"] = target
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "set-target",
        "state": result,
        "target": target,
        "evidence": {"function": "FUN_00812970", "target_field": "+0xe8"},
    }


def clear_tracking_input_slots(slots: Sequence[Any]) -> list[Any]:
    """Reproduce FUN_00812980's seven-slot release/clear loop."""
    if len(slots) != 7:
        raise ValueError("tracking camera input registry has seven slots")
    return [None] * 7


def register_tracking_input_action(
    slots: Sequence[Any],
    *,
    action_index: int,
    action_object: Any,
    frame_stack_accepts: bool,
) -> tuple[list[Any], dict[str, Any]]:
    """Reproduce FUN_008129b0 exactly at the container boundary."""
    if len(slots) != 7:
        raise ValueError("tracking camera input registry has seven slots")
    updated = list(slots)
    index = int(action_index)
    if action_object in (None, 0):
        return updated, {"status": "rejected-null", "value": 0}
    if not 1 <= index <= 6:
        return updated, {"status": "rejected-index", "value": 0}
    if updated[index] not in (None, 0):
        return updated, {"status": "rejected-occupied", "value": 0}
    if not frame_stack_accepts:
        return updated, {"status": "rejected-frame-stack", "value": 0}
    updated[index] = action_object
    return updated, {
        "format": FORMAT,
        "version": 1,
        "status": "registered",
        "slot": index,
        "storage_offset": INPUT_SLOT_BASE + index * 4,
        "value": 1,
        "evidence": {
            "function": "FUN_008129b0",
            "frame_stack": "+0x140",
        },
    }


def find_and_assign_tracking_target(
    *,
    target_handle_present: bool,
    target_handle_nonempty: bool,
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reproduce FUN_00812aa0's specialized global-service lookup."""
    actions: list[dict[str, Any]] = [
        {"action": "FUN_0080bfb0"},
        {"action": "FUN_0080b8e0"},
    ]
    if not target_handle_present or not target_handle_nonempty:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "target-acquire",
            "status": "fallback-selector",
            "actions": actions + [
                {"action": "FUN_00811570"},
                {"action": "write +0xd8"},
            ],
            "rtti_type": RTTI_TRACKING,
        }

    for index, candidate in enumerate(candidates):
        matches_rtti = bool(candidate.get("contains_rtti_0xc25fb8", False))
        property_matches = bool(candidate.get("field_0x60_matches_target", False))
        trace = {
            "index": index,
            "contains_rtti_0xc25fb8": matches_rtti,
            "field_0x60_matches_target": property_matches,
        }
        actions.append(trace)
        if matches_rtti and property_matches:
            actions.append({"action": "FUN_00812970", "target": index})
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "target-acquire",
                "status": "assigned",
                "selected": index,
                "actions": actions,
                "evidence": {
                    "function": "FUN_00812aa0",
                    "candidate_property": "+0x60",
                    "rtti_type": RTTI_TRACKING,
                    "setter": "FUN_00812970",
                },
            }

    actions.append({"action": "FUN_00811570", "target": "+0xd8"})
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "target-acquire",
        "status": "fallback-selector",
        "actions": actions,
        "evidence": {
            "function": "FUN_00812aa0",
            "fallback": "FUN_00811570",
        },
    }


def register_tracking_runtime_properties() -> dict[str, Any]:
    """Reproduce FUN_00812b60's two reflected byte properties."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "property-registration",
        "properties": [
            {"name": "NeedsReset", "type_id": 0x20, "offset": 0x68, "flags": 2},
            {"name": "IsShaking", "type_id": 0x20, "offset": 0x69, "flags": 2},
        ],
        "evidence": {
            "function": "FUN_00812b60",
            "registration_helper": "FUN_0063a280",
            "registration_object": "DAT_00b8deb0",
        },
    }


def create_tracking_free_look_actions() -> dict[str, Any]:
    """Reproduce FUN_00812c00's exact action construction/registration."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "free-look-actions",
        "actions": [
            {
                "name": "Free Look Left/Right",
                "factory": "FUN_00671230",
                "binding": [3, 0, 4, 2],
                "registered_index": 3,
            },
            {
                "name": "Free Look Up/Down",
                "factory": "FUN_00671230",
                "binding": [3, 0, 4, 3],
                "registered_index": 4,
            },
            {
                "name": "Chase Look",
                "factory": "FUN_006712a0",
                "binding": [3, 0, 1, 7],
                "registered_index": 5,
            },
        ],
        "evidence": {
            "function": "FUN_00812c00",
            "registry": "FUN_008129b0",
        },
    }


def parse_camera_type_selector(
    *,
    text_value: str,
    opaque_selector_result: int,
) -> dict[str, Any]:
    """Reproduce FUN_00812cf0's 0xf sentinel check."""
    selector = int(opaque_selector_result)
    if selector == 0xF:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "parse-camera-type",
            "status": "rejected-sentinel",
            "input": text_value,
            "result": 0,
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "parse-camera-type",
        "status": "accepted",
        "input": text_value,
        "selector": selector,
        "result": 1,
        "write_offset": 0x6C,
        "evidence": {
            "function": "FUN_00812cf0",
            "parser": "FUN_00811390",
            "destination": "+0x6c",
        },
    }


def resolve_target_transform(
    *,
    service_available: bool,
    target_id: int,
    param3: Any,
    param4: Any,
    this_has_fallback_position: bool,
    fallback_position: Sequence[float],
    service_call_result: Any = None,
    service_fallback_result: Any = None,
) -> dict[str, Any]:
    """Reproduce FUN_00812d20's ID and fallback branches."""
    if not service_available:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "target-transform",
            "status": "service-unavailable",
            "result": None,
        }

    if int(target_id) != -1:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "target-transform",
            "status": "id-query",
            "result": service_call_result,
            "actions": [
                {
                    "action": "service vtable +0x08",
                    "arguments": [param3, int(target_id), param4],
                }
            ],
            "evidence": {
                "function": "FUN_00812d20",
                "method": "+0x08",
            },
        }

    if service_fallback_result is not None:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "target-transform",
            "status": "service-fallback-query",
            "result": service_fallback_result,
            "actions": [
                {
                    "action": "service vtable +0x28",
                    "arguments": ["output", "self-output"],
                }
            ],
        }

    if this_has_fallback_position:
        if len(fallback_position) != 3:
            raise ValueError("fallback_position requires three values")
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "target-transform",
            "status": "local-fallback",
            "result": list(map(float, fallback_position)),
            "actions": [{"action": "copy +0x74/+0x78/+0x7c"}],
        }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "target-transform",
        "status": "unresolved",
        "result": None,
    }


def forward_target_value(
    *,
    service_available: bool,
    target_id: int,
    value: Any,
    service_result: Any = None,
) -> dict[str, Any]:
    """Trace FUN_00812da0's vtable +0x0c call."""
    if not service_available or int(target_id) == -1:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "target-value-forward",
            "status": "not-forwarded",
            "result": value,
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "target-value-forward",
        "status": "forwarded",
        "result": service_result,
        "action": {
            "method": "+0x0c",
            "arguments": [value, int(target_id)],
        },
        "evidence": {"function": "FUN_00812da0"},
    }


def query_target_metadata(
    *,
    service_available: bool,
    target_id: int,
    metadata: Sequence[float] | None,
) -> dict[str, Any]:
    """Trace FUN_00812de0's three-float metadata read."""
    if (
        not service_available
        or int(target_id) == -1
        or metadata is None
    ):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "target-metadata",
            "status": "zero",
            "result": [0.0, 0.0, 0.0],
        }
    if len(metadata) != 3:
        raise ValueError("metadata requires three values")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "target-metadata",
        "status": "read",
        "result": list(map(float, metadata)),
        "source_offsets": ["+0x1c", "+0x20", "+0x24"],
        "evidence": {"function": "FUN_00812de0"},
    }


def combine_shake_orientation(
    *,
    first_output: Sequence[float],
    second_output: Sequence[float],
    opaque_quaternion: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Reproduce FUN_00812e40's vector addition before opaque quaternion build."""
    if len(first_output) != 3 or len(second_output) != 3:
        raise ValueError("shake outputs require three values")
    combined = [
        float(first_output[i]) + float(second_output[i])
        for i in range(3)
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "combine-shake-orientation",
        "combined": combined,
        "quaternion": (
            list(map(float, opaque_quaternion))
            if opaque_quaternion is not None
            else None
        ),
        "action": {
            "action": "FUN_004d8c10",
            "input": combined,
        },
        "evidence": {
            "function": "FUN_00812e40",
            "first_source": "+0xd8",
            "second_source": "+0x84",
        },
        "limitations": [
            "FUN_004d8c10 quaternion construction remains opaque",
        ],
    }


def resolve_active_target_data(
    *,
    target_data: Any,
    nested_target_data: Any = None,
) -> dict[str, Any]:
    """Reproduce FUN_00812ed0's one-level +0xe8 redirection."""
    if target_data in (None, 0):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "active-target-data",
            "status": "none",
            "result": 0,
        }
    if nested_target_data not in (None, 0):
        target_data = nested_target_data
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "active-target-data",
        "status": "resolved",
        "result": target_data,
        "evidence": {
            "function": "FUN_00812ed0",
            "primary_source": "+0x64",
            "redirect_field": "+0xe8",
        },
    }
