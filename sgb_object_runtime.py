"""Decoder for the embedded SGB NODE object payload.

The runtime enters this structure through FUN_0069bc50 and dispatches in
FUN_0069a6c0 by an inline string whose relative offset is stored at word 0.
The handlers establish OBJECT/HIERARCHY/DAMAGE branches and a HIERARCHY child
record size of 9 dwords. Semantic names for most fields remain unresolved.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any


FORMAT = "SHIFT.SGBObjectRuntime/1"
KINDS = {"OBJECT", "HIERARCHY", "DAMAGE"}


class SGBObjectDecodeError(ValueError):
    pass


def _u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise SGBObjectDecodeError(f"u32 out of range at 0x{off:x}")
    return struct.unpack_from("<I", data, off)[0]


def _i32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise SGBObjectDecodeError(f"i32 out of range at 0x{off:x}")
    return struct.unpack_from("<i", data, off)[0]


def _string(data: bytes, base: int, end: int, rel: int) -> dict[str, Any]:
    absolute = base + rel
    text = None
    if rel and base <= absolute < end:
        stop = data.find(b"\0", absolute, end)
        if stop >= 0:
            text = data[absolute:stop].decode("utf-8", "replace")
    return {
        "relative_offset": rel,
        "absolute_offset": absolute if text is not None else None,
        "text": text,
    }


def parse_hierarchy_children(
    data: bytes,
    start: int,
    end: int,
    count: int,
) -> list[dict[str, Any]]:
    """Decode the 9-dword child records copied by FUN_0069a6c0."""
    rows = []
    cursor = start
    for index in range(count):
        if cursor + 36 > end:
            raise SGBObjectDecodeError(
                f"HIERARCHY child {index} exceeds object payload"
            )
        words = [_u32(data, cursor + 4 * i) for i in range(9)]
        rows.append({
            "index": index,
            "offset": cursor,
            "raw_u32": words,
            "runtime_copy_order": [6, 3, 4, 5, 1, 2, 0, 7, 8],
            "record_bytes": 36,
        })
        cursor += 36
    return rows


def parse_sgb_object_payload(
    data: bytes,
    *,
    base_offset: int = 0,
    end_offset: int | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Decode the common header and proven HIERARCHY child table."""
    end = len(data) if end_offset is None else end_offset
    if not 0 <= base_offset < end <= len(data):
        raise SGBObjectDecodeError("invalid object payload bounds")
    if base_offset + 36 > end:
        raise SGBObjectDecodeError("object payload is smaller than the common header")

    kind = _string(data, base_offset, end, _i32(data, base_offset))
    source = _string(data, base_offset, end, _i32(data, base_offset + 4))
    aux = _string(data, base_offset, end, _i32(data, base_offset + 8))
    words = [_u32(data, base_offset + 4 * i) for i in range(10)]
    mode = struct.unpack_from("<b", data, base_offset + 32)[0]
    hierarchy_type = struct.unpack_from("<B", data, base_offset + 35)[0]
    hierarchy_count = struct.unpack_from("<B", data, base_offset + 34)[0]

    kind_text = kind["text"]
    if kind_text and kind_text not in KINDS:
        status = "unknown-kind"
    else:
        status = "recognized-kind" if kind_text else "kind-unresolved"

    report: dict[str, Any] = {
        "format": FORMAT,
        "version": 1,
        "base_offset": base_offset,
        "end_offset": end,
        "size": end - base_offset,
        "header_words": words,
        "kind": kind,
        "source_string": source,
        "aux_string": aux,
        "mode": mode,
        "hierarchy_type": hierarchy_type,
        "hierarchy_count": hierarchy_count,
        "kind_status": status,
        "hash_sha256": hashlib.sha256(data[base_offset:end]).hexdigest(),
        "decoded": status == "recognized-kind",
        "evidence": {
            "entry": "FUN_0069bc50",
            "dispatcher": "FUN_0069a6c0",
            "hierarchy_child_copy": "FUN_0069a6c0",
        },
        "limitations": [
            "OBJECT and DAMAGE transform/material fields are preserved as raw words.",
            "HIERARCHY child words are preserved in source copy order; semantic field names are not yet proven.",
        ],
    }

    if kind_text == "HIERARCHY":
        child_start = base_offset + 36
        child_end = child_start + hierarchy_count * 36
        if child_end > end:
            message = (
                f"HIERARCHY child table requires {hierarchy_count * 36} bytes "
                f"after common header"
            )
            if strict:
                raise SGBObjectDecodeError(message)
            report["decoded"] = False
            report["status"] = "blocked"
            report["blockers"] = [f"hierarchy:{message}"]
            return report
        report["children"] = parse_hierarchy_children(
            data, child_start, child_end, hierarchy_count
        )
        report["child_table_offset"] = child_start
        report["child_table_size"] = hierarchy_count * 36
    return report
