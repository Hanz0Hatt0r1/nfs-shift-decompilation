"""Evidence-backed reconstruction of the SHIFT CSM collision-record consumer.

FUN_00750080 establishes the stream/version boundary and calls FUN_0074e880 for
each record. FUN_0074e880 reads one discriminator plus six u32 fields when the
discriminator is below 2, then allocates three runtime arrays and registers them
through the stream object's vtable. Array element semantics remain unresolved.
"""
from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.CollisionStreamRuntime/1"
RECORD_FORMAT = "SHIFT.CollisionStreamRecord/1"
CSM_VERSION = 0x0AFB


class CollisionStreamDecodeError(ValueError):
    pass


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise CollisionStreamDecodeError(
            f"collision record truncated at 0x{offset:x}"
        )
    return struct.unpack_from("<I", data, offset)[0]


def parse_collision_record(data: bytes, *, strict: bool = True) -> dict[str, Any]:
    """Decode the record boundary proven by FUN_0074e880."""
    try:
        discriminator = _u32(data, 0)
        fields: list[int] = []
        if discriminator < 2:
            fields = [_u32(data, 4 + index * 4) for index in range(6)]
        counts = {
            "buffer_0": fields[3] if fields else None,
            "buffer_1": fields[4] if fields else None,
            "buffer_2": fields[5] if fields else None,
        }
        consumed = 28 if discriminator < 2 else 4
        return {
            "format": RECORD_FORMAT,
            "version": 1,
            "status": "decoded-record-boundary",
            "discriminator": discriminator,
            "raw_fields_u32": fields,
            "field_offsets": {
                "0x04": fields[0] if fields else None,
                "0x08": fields[1] if fields else None,
                "0x0c": fields[2] if fields else None,
                "0x10": fields[3] if fields else None,
                "0x14": fields[4] if fields else None,
                "0x18": fields[5] if fields else None,
            },
            "allocated_buffers": [
                {
                    "runtime_pointer_field": "0x1c",
                    "count_field": "0x10",
                    "count": counts["buffer_0"],
                    "stream_register_vtable_offset": 0x18,
                },
                {
                    "runtime_pointer_field": "0x20",
                    "count_field": "0x14",
                    "count": counts["buffer_1"],
                    "stream_register_vtable_offset": 0x18,
                },
                {
                    "runtime_pointer_field": "0x24",
                    "count_field": "0x18",
                    "count": counts["buffer_2"],
                    "stream_register_vtable_offset": 0x18,
                },
            ] if discriminator < 2 else [],
            "consumed_bytes": consumed,
            "unknowns": [
                "semantic meaning of discriminator 0/1",
                "semantic meaning of fields 0x04..0x18",
                "element formats of allocated arrays",
                "meaning of the stream vtable +0x18 registration call",
            ],
            "evidence": {
                "reader": "FUN_0074e880",
                "loader": "FUN_00750080",
                "csm_version": CSM_VERSION,
            },
        }
    except CollisionStreamDecodeError:
        if strict:
            raise
        return {
            "format": RECORD_FORMAT,
            "version": 1,
            "status": "blocked",
            "consumed_bytes": 0,
            "blockers": ["collision-record:truncated"],
            "evidence": {"reader": "FUN_0074e880", "csm_version": CSM_VERSION},
        }


def build_collision_stream_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "source": ".\\Source\\System\\PhysicsSystem.cpp",
        "loader": "FUN_00750080",
        "record_consumer": "FUN_0074e880",
        "version_check": {"expected": CSM_VERSION, "hex": f"0x{CSM_VERSION:08x}"},
        "load_modes": {
            "required": {"argument": 1, "error_on_missing": True},
            "optional": {"argument": 0, "error_on_missing": False},
        },
        "record": {
            "format": RECORD_FORMAT,
            "discriminator_condition": "discriminator < 2 reads six additional u32 fields",
            "record_size_when_lt_2": 28,
            "record_size_when_ge_2": 4,
            "allocation_count_offsets": [0x10, 0x14, 0x18],
            "allocation_pointer_offsets": [0x1C, 0x20, 0x24],
        },
        "status": "record-boundary-reconstructed; element grammar unresolved",
    }
