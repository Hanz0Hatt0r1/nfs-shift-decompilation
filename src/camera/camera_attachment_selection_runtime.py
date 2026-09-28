"""Evidence-backed camera attachment-name and selected-config helpers.

Recovered from FUN_00811390, FUN_00811570, FUN_008115a0, FUN_008115c0 and
FUN_00811640.

The canonical attachment table is preserved from the executable string data.
The helper predicates used by FUN_00811390 remain opaque rather than being
reduced to a guessed strlen/substring rule.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraAttachmentSelectionRuntime/1"
NO_MATCH_INDEX = 0x0F

CAMERA_ATTACHMENT_NAMES = (
    "BumperPos",
    "BonnetPos",
    "CockpitPos",
    "ChasePos",
    "ShotgunPos",
    "CockpitRearPos",
    "DefaultTargetPos",
    "PivotPos",
    "FrontLeftWheelPos",
    "FrontRightWheelPos",
    "RearLeftWheelPos",
    "RearRightWheelPos",
    "LeftFuelIntakePos",
    "RightFuelIntakePos",
    "SocketForArJackPos",
)

SPECIAL_ALIASES = {
    "fuelIntakePos": 12,
    "driverPos": 2,
}


def describe_attachment_name_table() -> dict[str, Any]:
    """Expose the 15 canonical names and the two observed aliases."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "attachment-name-table",
        "canonical_names": list(CAMERA_ATTACHMENT_NAMES),
        "aliases": dict(SPECIAL_ALIASES),
        "no_match_index": NO_MATCH_INDEX,
        "evidence": {
            "function": "FUN_00811390",
            "table_base": "PTR_s_BumperPos_00b8de48",
            "comparison_helper": "FUN_00471f20",
            "length_helper": "FUN_00408150",
        },
        "limitations": [
            "FUN_00471f20 and FUN_00408150 semantics are not reimplemented",
        ],
    }


def resolve_attachment_name_index(name: str) -> dict[str, Any]:
    """Resolve only the source-proven exact table entries and aliases."""
    value = str(name)
    if value in SPECIAL_ALIASES:
        index = SPECIAL_ALIASES[value]
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "attachment-name-resolve",
            "status": "alias",
            "name": value,
            "index": index,
            "evidence": {"function": "FUN_00811390"},
        }
    try:
        index = CAMERA_ATTACHMENT_NAMES.index(value)
    except ValueError:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "attachment-name-resolve",
            "status": "no-match",
            "name": value,
            "index": NO_MATCH_INDEX,
            "evidence": {"function": "FUN_00811390"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "attachment-name-resolve",
        "status": "canonical",
        "name": value,
        "index": index,
        "evidence": {"function": "FUN_00811390"},
    }


def describe_selected_camera_config_query(
    *,
    object_or_none: Any,
    selected_index: int,
) -> dict[str, Any]:
    """Trace FUN_00811570 and FUN_008115a0 manager boundaries."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "selected-camera-config-query",
        "selected_index": int(selected_index),
        "manager": "+0x298",
        "actions": [
            {
                "action": "FUN_00810430",
                "arguments": {
                    "manager_config_list": "camera-manager +0x298",
                    "object": object_or_none,
                },
                "result": int(selected_index),
            },
            {
                "action": "FUN_00810410",
                "arguments": {
                    "manager_config_list": "camera-manager +0x298",
                    "index": int(selected_index),
                },
                "result": "object" if object_or_none is not None else None,
            },
        ],
        "evidence": {
            "get_index": "FUN_00811570",
            "get_object": "FUN_008115a0",
            "manager_field": "+0x298",
        },
    }


def resolve_selected_camera_property(
    *,
    selected_object: Any | None,
    selected_index: int,
    vtable_result: Any | None,
    fallback_value: Any = "DAT_00c259e4",
) -> dict[str, Any]:
    """Trace FUN_008115c0's selected-object/vtable/fallback branch."""
    if selected_object is None:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "selected-camera-property",
            "status": "fallback",
            "selected_index": int(selected_index),
            "value": fallback_value,
            "actions": [
                {
                    "action": "FUN_00810410",
                    "arguments": {
                        "manager_config_list": "+0x298",
                        "index": int(selected_index),
                    },
                },
                {
                    "action": "lazy fallback",
                    "value": fallback_value,
                },
            ],
            "evidence": {
                "function": "FUN_008115c0",
                "fallback": "DAT_00c259e4",
            },
        }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "selected-camera-property",
        "status": "resolved",
        "selected_index": int(selected_index),
        "value": vtable_result,
        "actions": [
            {
                "action": "FUN_00810410",
                "arguments": {
                    "manager_config_list": "+0x298",
                    "index": int(selected_index),
                },
            },
            {
                "action": "selected_object.vtable +0x10",
                "result": vtable_result,
            },
        ],
        "evidence": {
            "function": "FUN_008115c0",
            "object_property_vtable": "+0x10",
        },
    }


def build_spline_endpoint_output(
    *,
    record_position: Sequence[float],
    spline_object_value: Any,
    record_scalar_20: Any,
    param2_fallback: Any,
) -> dict[str, Any]:
    """Reproduce FUN_00811640's exact nine-word endpoint record."""
    if len(record_position) != 3:
        raise ValueError("record_position requires exactly three values")

    value_20 = float(record_scalar_20)
    terminal_value = param2_fallback if value_20 == 0.0 else record_scalar_20
    words = [
        float(record_position[0]),
        float(record_position[1]),
        float(record_position[2]),
        0.0,
        0.0,
        spline_object_value,
        0.0,
        0.0,
        terminal_value,
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "spline-endpoint-output",
        "words": words,
        "evidence": {
            "function": "FUN_00811640",
            "position": "+0x10/+0x14/+0x18",
            "middle_value": "this +0x10",
            "terminal_source": "record +0x20 or param_2 fallback",
        },
    }
