"""Exact StaticCamera reference-record traversal primitives.

Recovered from FUN_008136d0, FUN_00813710, FUN_00814690 and FUN_008146e0.

The helpers copy the 25-dword camera-config record, set its terminal/index
word from owner +0x64, and conditionally step +/-1 through the linked record
space via opaque FUN_007025a0/FUN_00702580. The paired 14690/146e0 helpers
wrap the result into a three-word transition record.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.StaticCameraReferenceTraversalRuntime/1"
RECORD_DWORDS = 25
INDEX_OFFSET = 0x64


def copy_reference_record(source_words: Sequence[Any]) -> list[Any]:
    if len(source_words) != RECORD_DWORDS:
        raise ValueError("camera reference record contains exactly 25 dwords")
    return list(source_words)


def advance_reference_record(
    source_words: Sequence[Any],
    *,
    owner_index: int,
    boundary_hit: bool,
) -> dict[str, Any]:
    """Reproduce FUN_008136d0."""
    record = copy_reference_record(source_words)
    record[0x19] = int(owner_index)
    if int(owner_index) == 0 and bool(boundary_hit):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "advance-reference-record",
            "status": "boundary-stop",
            "record": record,
            "index": record[0x19],
            "actions": [
                {"action": "FUN_00812a00", "record_dwords": RECORD_DWORDS},
                {"action": "FUN_007025a0", "result": True},
            ],
            "evidence": {
                "function": "FUN_008136d0",
                "owner_index_offset": "+0x64",
            },
        }
    record[0x19] += 1
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "advance-reference-record",
        "status": "advanced",
        "record": record,
        "index": record[0x19],
        "actions": [
            {"action": "FUN_00812a00", "record_dwords": RECORD_DWORDS},
            {"action": "write record[0x19]", "value": record[0x19]},
        ],
        "evidence": {
            "function": "FUN_008136d0",
            "owner_index_offset": "+0x64",
            "step": 1,
        },
    }


def retreat_reference_record(
    source_words: Sequence[Any],
    *,
    owner_index: int,
    boundary_hit: bool,
) -> dict[str, Any]:
    """Reproduce FUN_00813710."""
    record = copy_reference_record(source_words)
    record[0x19] = int(owner_index)
    if int(owner_index) == 0 and bool(boundary_hit):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "retreat-reference-record",
            "status": "boundary-stop",
            "record": record,
            "index": record[0x19],
            "actions": [
                {"action": "FUN_00812a00", "record_dwords": RECORD_DWORDS},
                {"action": "FUN_00702580", "result": True},
            ],
            "evidence": {
                "function": "FUN_00813710",
                "owner_index_offset": "+0x64",
            },
        }
    record[0x19] -= 1
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "retreat-reference-record",
        "status": "retreated",
        "record": record,
        "index": record[0x19],
        "actions": [
            {"action": "FUN_00812a00", "record_dwords": RECORD_DWORDS},
            {"action": "write record[0x19]", "value": record[0x19]},
        ],
        "evidence": {
            "function": "FUN_00813710",
            "owner_index_offset": "+0x64",
            "step": -1,
        },
    }


def describe_forward_transition(
    *,
    next_record_exists: bool,
    next_record_id: Any,
    current_record_id: Any,
) -> dict[str, Any]:
    """Reproduce FUN_00814690 output when a previous-record transition exists."""
    if not next_record_exists:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "forward-transition",
            "status": "no-transition",
            "return_low_byte": 0,
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "forward-transition",
        "status": "transition",
        "output_words": [next_record_id, current_record_id, 0],
        "output_scalar": 1.0,
        "action": "FUN_00813710",
        "evidence": {
            "function": "FUN_00814690",
            "source": "this + 0x04",
            "step_helper": "FUN_00813710",
        },
    }


def describe_backward_transition(
    *,
    previous_record_exists: bool,
    previous_record_id: Any,
    current_record_id: Any,
) -> dict[str, Any]:
    """Reproduce FUN_008146e0 output when a next-record transition exists."""
    if not previous_record_exists:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "backward-transition",
            "status": "no-transition",
            "return_low_byte": 0,
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "backward-transition",
        "status": "transition",
        "output_words": [previous_record_id, current_record_id, 0x3F800000],
        "output_scalar": 1.0,
        "action": "FUN_00813710",
        "evidence": {
            "function": "FUN_008146e0",
            "source": "this",
            "step_helper": "FUN_00813710",
        },
    }


def describe_static_camera_reference_layout() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "reference-layout",
        "record_dwords": RECORD_DWORDS,
        "record_bytes": RECORD_DWORDS * 4,
        "index_offset": INDEX_OFFSET,
        "evidence": {
            "record_copy": "FUN_00812a00",
            "forward_step": "FUN_008136d0",
            "backward_step": "FUN_00813710",
            "forward_transition": "FUN_00814690",
            "backward_transition": "FUN_008146e0",
        },
    }
