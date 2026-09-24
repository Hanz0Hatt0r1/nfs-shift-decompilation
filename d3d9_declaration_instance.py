"""Decode and validate raw 8-byte D3D9 declaration records.

The recovered SHIFT loader emits a D3DVERTEXELEMENT9-shaped record:
<Stream: WORD, Offset: WORD, Type: BYTE, Method: BYTE,
 Usage: BYTE, UsageIndex: BYTE>.

This module is intentionally instance-level: it consumes supplied bytes and
does not infer MEB property mappings or undocumented Usage semantics.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from d3d9_type_profile import TYPE_PROFILE, TYPE_UNUSED

FORMAT = "SHIFT.D3D9DeclarationInstanceEvidence/1"
RECORD_STRIDE = 8

def decode_d3d9_declaration_records(
    payload: bytes,
    *,
    count: int | None = None,
) -> dict[str, Any]:
    """Decode raw little-endian 8-byte declaration records."""

    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    if count is not None and count < 0:
        raise ValueError("count must be non-negative or None")

    available_records = len(payload) // RECORD_STRIDE
    trailing_bytes = len(payload) % RECORD_STRIDE
    requested_count = available_records if count is None else count
    decoded_count = min(requested_count, available_records)
    terminator_index: int | None = None

    records: list[dict[str, Any]] = []
    malformed_type_count = 0
    nonzero_method_count = 0
    terminator_indices: list[int] = []

    for index in range(decoded_count):
        offset = index * RECORD_STRIDE
        stream, element_offset, type_code, method, usage, usage_index = struct.unpack_from(
            "<HHBBBB",
            payload,
            offset,
        )
        if (
            stream == 0xFFFF
            and element_offset == 0
            and type_code == TYPE_UNUSED
            and method == 0
            and usage == 0
            and usage_index == 0
        ):
            terminator_index = index

        if type_code not in TYPE_PROFILE and type_code != TYPE_UNUSED:
            malformed_type_count += 1
            type_name = None
            type_status = "unrecognized"
        elif type_code == TYPE_UNUSED:
            type_name = "D3DDECLTYPE_UNUSED"
            type_status = "observed"
            terminator_indices.append(index)
        else:
            type_name = TYPE_PROFILE[type_code][0]
            type_status = "observed"

        method_status = "observed" if method == 0 else "not-proven"
        if method != 0:
            nonzero_method_count += 1

        records.append(
            {
                "index": index,
                "byte_offset": offset,
                "stream": stream,
                "offset": element_offset,
                "type": type_code,
                "type_name": type_name,
                "type_status": type_status,
                "method": method,
                "method_status": method_status,
                "usage": usage,
                "usage_index": usage_index,
            }
        )

    insufficient_count = requested_count > available_records
    if malformed_type_count or nonzero_method_count:
        status = "mismatch"
    elif insufficient_count or trailing_bytes:
        status = "partial"
    else:
        status = "match"

    return {
        "format": FORMAT,
        "status": status,
        "record_stride": RECORD_STRIDE,
        "field_layout": {
            "stream": {"offset": 0, "width": 2},
            "offset": {"offset": 2, "width": 2},
            "type": {"offset": 4, "width": 1},
            "method": {"offset": 5, "width": 1},
            "usage": {"offset": 6, "width": 1},
            "usage_index": {"offset": 7, "width": 1},
        },
        "payload": {
            "bytes": len(payload),
            "available_records": available_records,
            "requested_records": requested_count,
            "decoded_records": decoded_count,
            "trailing_bytes": trailing_bytes,
        },
        "records": records,
        "validation": {
            "type_codes_recognized": malformed_type_count == 0,
            "nonzero_method_count": nonzero_method_count,
            "terminator_indices": terminator_indices,
            "end_sentinel_index": terminator_index,
            "end_sentinel_status": (
                "observed" if terminator_index is not None else "not-present"
            ),
            "terminator_policy": (
                "D3DDECL_END-shaped sentinel is Stream=0xffff, Offset=0, "
                "Type=0x11, Method=0, Usage=0, UsageIndex=0"
            ),
        },
        "semantic_links": {
            "d3dvertexelement9_shape": {
                "status": "observed",
                "detail": "raw bytes decode into the six-field 8-byte D3DVERTEXELEMENT9 layout",
            },
            "type_code_to_profile": {
                "status": "observed" if malformed_type_count == 0 else "mismatch",
                "detail": "Type codes 0..16 use the recovered semantic profile; Type 0x11 is exposed as UNUSED",
            },
            "method_zero": {
                "status": "observed" if nonzero_method_count == 0 else "not-proven",
                "detail": "the recovered STREAM builder initializes Method to zero",
            },
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "raw declaration bytes do not establish MEB property 460/461 linkage",
        },
    }


def decode_d3d9_declaration_records_file(
    path: str | Path,
    *,
    count: int | None = None,
) -> dict[str, Any]:
    source_path = Path(path)
    result = decode_d3d9_declaration_records(
        source_path.read_bytes(),
        count=count,
    )
    result["payload"]["path"] = str(source_path)
    return result
