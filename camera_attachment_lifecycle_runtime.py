"""Evidence-backed CCameraView attachment and lifecycle helpers.

Recovered from FUN_0081b680, FUN_0081b6b0, FUN_0081c420 and FUN_0081d250.

The two attachment helpers return a 3-float result block. Their source records
contain function pointers and an attached index; when either is unavailable or
the index is -1, the output block is cleared. The destructor/reset path restores
the vtable, resets input state, clears the Apt frame stack, and calls the camera
view-data reset.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraAttachmentLifecycleRuntime/1"


def resolve_attachment_result(
    *,
    resolver_present: bool,
    attached_index: int,
    resolver_slot: str,
    resolver_arguments: Sequence[Any],
) -> dict[str, Any]:
    """Reproduce FUN_0081b680/FUN_0081b6b0 result selection."""
    if len(resolver_arguments) != 2:
        raise ValueError("attachment resolver requires exactly two runtime arguments")
    index = int(attached_index)
    if resolver_present and index != -1:
        output = [0.0, 0.0, 0.0]
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "attachment-resolve",
            "status": "resolved",
            "resolver_slot": str(resolver_slot),
            "attached_index": index,
            "actions": [
                {
                    "action": "invoke resolver function pointer",
                    "slot": str(resolver_slot),
                    "arguments": [
                        "output + 0x18" if resolver_slot == "+0x00" else "output + 0x24",
                        index,
                        resolver_arguments[0],
                    ],
                },
            ],
            "output": output,
            "evidence": {
                "helper": "FUN_0081b680" if resolver_slot == "+0x00" else "FUN_0081b6b0",
                "index_field": "+0x10" if resolver_slot == "+0x04" else "+0x10",
            },
            "limitations": [
                "the resolver's written three-float values are external to this boundary",
            ],
        }

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "attachment-resolve",
        "status": "zero-result",
        "resolver_slot": str(resolver_slot),
        "attached_index": index,
        "actions": [
            {"action": "clear result vec3", "values": [0.0, 0.0, 0.0]},
        ],
        "output": [0.0, 0.0, 0.0],
        "evidence": {
            "helper": "FUN_0081b680" if resolver_slot == "+0x00" else "FUN_0081b6b0",
            "guard": "function pointer != 0 && attached index != -1",
        },
    }


def describe_view_reset() -> dict[str, Any]:
    """Trace FUN_0081c420."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "view-reset",
        "actions": [
            {
                "action": "write vtable",
                "value": "PTR_FUN_00b163c0",
            },
            {
                "action": "FUN_0081b350",
                "target": "camera-view input/runtime state",
            },
            {
                "action": "FUN_00675d70",
                "target": "+0x180",
            },
            {
                "action": "FUN_0081ac60",
                "target": "CCameraView base/projection state",
            },
        ],
        "evidence": {
            "function": "FUN_0081c420",
            "input_state_reset": "FUN_0081b350",
            "frame_stack_reset": "FUN_00675d70(+0x180)",
            "base_state_reset": "FUN_0081ac60",
        },
    }


def describe_view_data_destroy_copy(
    source_words: Sequence[Any],
    source_bytes: Sequence[int],
) -> dict[str, Any]:
    """Summarize FUN_0081d250's script-event dispatch boundary."""
    if len(source_words) < 2:
        raise ValueError("source_words requires at least two words")
    if len(source_bytes) < 4:
        raise ValueError("source_bytes requires at least four bytes")

    path = {
        "action": "FUN_00630fe0",
        "source": "param_1 + 0x04",
        "fallback": "DAT_00aa9b60",
    }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "script-dispatch",
        "actions": [
            path,
            {
                "action": "FUN_0069d8f0",
                "target": "+0x180",
                "name_source": "resolved string or DAT_00aa9b60",
            },
            {
                "action": "FUN_006310c0",
                "target": "temporary string reference",
            },
            {
                "action": "FUN_00671100",
                "condition": "FUN_0069d8f0 returned nonzero",
                "arguments": [
                    "resolved event object",
                    "original param_1",
                ],
            },
        ],
        "evidence": {
            "function": "FUN_0081d250",
            "frame_stack": "+0x180",
            "string_pointer_source": "param_1 + 0x04",
            "fallback_string": "DAT_00aa9b60",
        },
        "limitations": [
            "FUN_0069d8f0 matching semantics are not inferred",
            "the script event object identity is opaque",
        ],
    }
