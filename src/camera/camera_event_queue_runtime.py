"""Evidence-backed CameraManager event-queue producer boundary.

Recovered from FUN_0080c340, FUN_0080c400, FUN_0080c440, FUN_0080c8f0,
FUN_0080cae0, and FUN_0080cb50.

The generic container internals remain opaque. This module records allocation
sizes, exact copy footprints, record construction order, and the enqueue
boundary without guessing ownership/refcount semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

FORMAT = "SHIFT.CameraEventQueueRuntime/1"


@dataclass(frozen=True)
class QueueRecordSpec:
    allocation_size: int
    copied_offsets: tuple[int, ...]
    copy_helper: str
    producer_helper: str


TYPE5_RECORD = QueueRecordSpec(
    allocation_size=0x18,
    copied_offsets=(0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20),
    copy_helper="FUN_0080c400",
    producer_helper="FUN_0080b9b0",
)

TYPE3_RECORD = QueueRecordSpec(
    allocation_size=0x24,
    copied_offsets=(0x0C, 0x10, 0x14),
    copy_helper="FUN_0080c8f0",
    producer_helper="FUN_0080ccb0",
)


def describe_record_allocator(record_type: int) -> dict[str, Any]:
    """Trace the size/vtable contract of FUN_0080c340/FUN_0080c440."""
    kind = int(record_type)
    if kind == 5:
        spec = TYPE5_RECORD
        initializer = "FUN_0080c340"
    elif kind == 3:
        spec = TYPE3_RECORD
        initializer = "FUN_0080c440"
    else:
        raise ValueError("supported queue records are event types 3 and 5")

    return {
        "format": FORMAT,
        "version": 1,
        "event_type": kind,
        "allocation_size": spec.allocation_size,
        "vtable_initialized": "PTR_FUN_00abfc10",
        "copy_footprint": {
            "offsets": list(spec.copied_offsets),
            "bytes": max(spec.copied_offsets) + 4 - 0x0C,
            "helper": spec.copy_helper,
        },
        "allocator": initializer,
        "evidence": {
            "record_vtable": "PTR_FUN_00abfc10",
            "allocation_helper": "FUN_00633290",
            "allocation_copy_helper": "FUN_00632ff0",
        },
    }


def describe_type5_producer(command: Sequence[Any]) -> dict[str, Any]:
    """Trace FUN_0080cae0: allocate, build six-word type-5 record, enqueue."""
    if len(command) != 6:
        raise ValueError("type-5 command producer requires six dwords")

    allocation = describe_record_allocator(5)
    payload = [int(value) & 0xFFFFFFFF for value in command]
    return {
        "format": FORMAT,
        "version": 1,
        "event_type": 5,
        "producer": "FUN_0080cae0",
        "allocation": allocation,
        "actions": [
            {
                "action": "FUN_0080c340",
                "queue": "+0x5a0",
                "size": 0x18,
            },
            {
                "action": "FUN_0080b9b0",
                "payload_words": payload,
                "payload_offsets": [0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20],
            },
            {
                "action": "FUN_0080c7e0",
                "record": "type-5 record",
            },
        ],
        "enqueue_helper": "FUN_0080c7e0",
        "limitations": [
            "FUN_0080c7e0 generic-container ownership/refcount path is unresolved",
        ],
    }


def describe_type3_producer(
    *,
    first: Any,
    second: Any,
    byte_parameter: int,
) -> dict[str, Any]:
    """Trace FUN_0080ccb0: allocate/copy/finalize a type-3 record then enqueue."""
    byte_parameter = int(byte_parameter)
    if not 0 <= byte_parameter <= 0xFF:
        raise ValueError("byte_parameter must fit one byte")

    allocation = describe_record_allocator(3)
    return {
        "format": FORMAT,
        "version": 1,
        "event_type": 3,
        "producer": "FUN_0080ccb0",
        "allocation": allocation,
        "actions": [
            {
                "action": "FUN_0080c340",
                "queue": "+0x5a0",
                "size": 0x18,
                "note": "allocator helper is shared even though the record is 0x24 bytes",
            },
            {
                "action": "write temporary record fields",
                "payload": {
                    "+0x0c": int(first) & 0xFFFFFFFF,
                    "+0x10": int(second) & 0xFFFFFFFF,
                    "+0x14": byte_parameter,
                },
            },
            {
                "action": "record header finalization",
                "vtable": "PTR_FUN_00abfc10",
                "type": 3,
                "channel_source": "manager +0x7e4",
            },
            {
                "action": "FUN_0080cb50",
                "record": "type-3 record",
            },
        ],
        "enqueue_helper": "FUN_0080cb50",
        "limitations": [
            "FUN_0080cb50 generic-container ownership/refcount path is unresolved",
            "the 0x24-byte allocator helper and its 0x18-byte shared constructor boundary are intentionally kept separate",
        ],
    }


def describe_type3_copy(
    *,
    source_payload_words: Sequence[Any],
    source_byte: int,
) -> dict[str, Any]:
    """Trace FUN_0080c8f0's three-field copy constructor."""
    if len(source_payload_words) < 2:
        raise ValueError("type-3 source needs at least two payload words")
    return {
        "format": FORMAT,
        "version": 1,
        "event_type": 3,
        "copy_helper": "FUN_0080c8f0",
        "actions": [
            {
                "action": "FUN_00403d00",
                "purpose": "base record copy boundary",
            },
            {
                "action": "copy dword",
                "offset": 0x0C,
                "value": int(source_payload_words[0]) & 0xFFFFFFFF,
            },
            {
                "action": "copy dword",
                "offset": 0x10,
                "value": int(source_payload_words[1]) & 0xFFFFFFFF,
            },
            {
                "action": "copy byte",
                "offset": 0x14,
                "value": int(source_byte) & 0xFF,
            },
        ],
        "evidence": {
            "copy_offsets": ["+0x0c", "+0x10", "+0x14"],
        },
    }


def describe_enqueue_boundary(
    *,
    container_is_same_as_record: bool,
    record_type: int,
) -> dict[str, Any]:
    """Summarize only the observable fork in FUN_0080c7e0/FUN_0080cb50."""
    allocator = describe_record_allocator(int(record_type))
    if container_is_same_as_record:
        path = {
            "action": "FUN_006333f0",
            "meaning": "generic container path used when FUN_00632fe0(record) == queue",
        }
    else:
        path = {
            "action": "allocate container copy",
            "sequence": [
                "FUN_0080c440(queue,&local_8,0)",
                (
                    "FUN_0080c400(local_8,record)"
                    if int(record_type) == 5
                    else "FUN_0080c8f0(local_8,record)"
                ),
                "FUN_006333f0(queue,local_8)",
            ],
        }

    return {
        "format": FORMAT,
        "version": 1,
        "record_type": int(record_type),
        "record_allocation_size": allocator["allocation_size"],
        "ownership_probe": "FUN_00632fe0(record)",
        "enqueue_path": path,
        "evidence": {
            "type5_enqueue_wrapper": "FUN_0080c7e0",
            "type3_enqueue_wrapper": "FUN_0080cb50",
        },
        "limitations": [
            "generic container operation names are not inferred beyond source helper symbols",
        ],
    }
