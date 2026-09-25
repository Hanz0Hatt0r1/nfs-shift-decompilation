"""Evidence-backed CCameraView input-action slot registry.

Recovered from FUN_0081b350, FUN_0081b380 and FUN_0081b3d0.

The object owns seven 4-byte slots beginning at +0x2a0, but valid action
indices are exactly 1..6. Registration is allowed only for a nonzero action
object when its slot is empty and FUN_00671180 accepts the object against the
Apt frame stack. Lookup falls back to DAT_00c25f30 for an invalid/empty slot.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraInputRegistryRuntime/1"
SLOT_BASE = 0x2A0
SLOT_STORAGE_COUNT = 7
VALID_INDEX_MIN = 1
VALID_INDEX_MAX = 6
FALLBACK = "DAT_00c25f30"


def clear_input_action_slots(
    slots: Sequence[Any],
) -> list[Any]:
    """Reproduce FUN_0081b350's seven-slot clear loop."""
    if len(slots) != SLOT_STORAGE_COUNT:
        raise ValueError("input action storage contains exactly seven slots")
    return [None] * SLOT_STORAGE_COUNT


def register_input_action(
    slots: Sequence[Any],
    *,
    action_index: int,
    action_object: Any,
    frame_stack_accepts: bool,
) -> tuple[list[Any], dict[str, Any]]:
    """Trace FUN_0081b380."""
    index = int(action_index)
    next_slots = list(slots)
    if len(next_slots) != SLOT_STORAGE_COUNT:
        raise ValueError("input action storage contains exactly seven slots")

    if action_object in (None, 0):
        return next_slots, {
            "format": FORMAT,
            "version": 1,
            "status": "rejected-null-action",
            "actions": [],
        }

    if not VALID_INDEX_MIN <= index <= VALID_INDEX_MAX:
        return next_slots, {
            "format": FORMAT,
            "version": 1,
            "status": "rejected-index",
            "actions": [],
            "valid_range": [VALID_INDEX_MIN, VALID_INDEX_MAX],
        }

    if next_slots[index] not in (None, 0):
        return next_slots, {
            "format": FORMAT,
            "version": 1,
            "status": "rejected-slot-occupied",
            "actions": [],
            "slot": index,
        }

    if not frame_stack_accepts:
        return next_slots, {
            "format": FORMAT,
            "version": 1,
            "status": "rejected-frame-stack",
            "actions": [
                {
                    "action": "FUN_00671180",
                    "accepted": False,
                    "frame_stack": "+0x180",
                }
            ],
        }

    next_slots[index] = action_object
    return next_slots, {
        "format": FORMAT,
        "version": 1,
        "status": "registered",
        "slot": index,
        "storage_offset": SLOT_BASE + index * 4,
        "actions": [
            {
                "action": "FUN_00671180",
                "accepted": True,
                "frame_stack": "+0x180",
            },
            {
                "action": "write action slot",
                "offset": f"+0x{SLOT_BASE + index * 4:02x}",
                "value": action_object,
            },
        ],
        "evidence": {
            "function": "FUN_0081b380",
            "slot_range": "param1 1..6",
            "frame_stack": "+0x180",
        },
    }


def lookup_input_action(
    slots: Sequence[Any],
    *,
    action_index: int,
) -> dict[str, Any]:
    """Trace FUN_0081b3d0."""
    if len(slots) != SLOT_STORAGE_COUNT:
        raise ValueError("input action storage contains exactly seven slots")
    index = int(action_index)
    if not VALID_INDEX_MIN <= index <= VALID_INDEX_MAX:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "fallback",
            "value": FALLBACK,
            "evidence": {
                "function": "FUN_0081b3d0",
                "fallback": FALLBACK,
            },
        }

    value = slots[index]
    if value in (None, 0):
        return {
            "format": FORMAT,
            "version": 1,
            "status": "fallback",
            "value": FALLBACK,
            "slot": index,
        }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "found",
        "slot": index,
        "value": value,
        "storage_offset": SLOT_BASE + index * 4,
        "evidence": {
            "function": "FUN_0081b3d0",
            "fallback": FALLBACK,
        },
    }


def describe_input_action_registry_state(
    slots: Sequence[Any],
) -> dict[str, Any]:
    """Emit the raw seven-slot container layout."""
    if len(slots) != SLOT_STORAGE_COUNT:
        raise ValueError("input action storage contains exactly seven slots")
    return {
        "format": FORMAT,
        "version": 1,
        "slot_base": SLOT_BASE,
        "storage_count": SLOT_STORAGE_COUNT,
        "valid_indices": [1, 2, 3, 4, 5, 6],
        "slots": list(slots),
        "fallback": FALLBACK,
        "evidence": {
            "slot_clear": "FUN_0081b350",
            "slot_register": "FUN_0081b380",
            "slot_lookup": "FUN_0081b3d0",
        },
    }
