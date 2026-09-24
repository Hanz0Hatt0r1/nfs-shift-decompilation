"""Capture a reproducible D3D9 declaration slice from a loaded-memory dump.

The capture layer preserves byte provenance, virtual-address arithmetic,
endianness and the exact declaration bytes before delegating semantic decoding
to SHIFT.D3D9DeclarationInstanceEvidence/1.

It does not authenticate the dump as an original-game capture and it does not
infer MEB 460/461 mappings.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from d3d9_declaration_instance import decode_d3d9_declaration_records

FORMAT = "SHIFT.D3D9MemoryDeclarationEvidence/1"
RECORD_STRIDE = 8
MAX_U64 = (1 << 64) - 1


def _validate_u64(value: int, name: str) -> int:
    if value < 0 or value > MAX_U64:
        raise ValueError(f"{name} must be in 0..0xffffffffffffffff")
    return value


def _validate_range(payload_length: int, offset: int, length: int | None) -> tuple[int, int]:
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if offset > payload_length:
        raise ValueError("offset is outside the input dump")
    if length is None:
        return offset, payload_length
    if length < 0:
        raise ValueError("length must be non-negative or None")
    end = offset + length
    if end > payload_length:
        raise ValueError(
            f"requested range exceeds input dump: offset=0x{offset:x}, "
            f"length=0x{length:x}, dump_size=0x{payload_length:x}"
        )
    return offset, end


def capture_d3d9_memory_declaration(
    payload: bytes,
    *,
    base_address: int,
    offset: int = 0,
    length: int | None = None,
    count: int | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Capture one virtual-addressed memory slice and decode its declaration array."""

    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    base_address = _validate_u64(base_address, "base_address")
    start_offset, end_offset = _validate_range(len(payload), offset, length)

    slice_bytes = payload[start_offset:end_offset]
    slice_start = _validate_u64(base_address + start_offset, "slice_start_address")
    slice_end_exclusive = _validate_u64(
        base_address + end_offset,
        "slice_end_exclusive",
    )

    probe = decode_d3d9_declaration_records(slice_bytes, count=count)
    end_index = probe["validation"]["end_sentinel_index"]
    if end_index is None:
        declaration_instance = probe
        array_status = "mismatch" if probe["status"] == "mismatch" else "partial"
        array_byte_length = len(slice_bytes)
        post_sentinel_bytes = 0
    else:
        array_byte_length = (end_index + 1) * RECORD_STRIDE
        declaration_instance = decode_d3d9_declaration_records(
            slice_bytes[:array_byte_length]
        )
        post_sentinel_bytes = len(slice_bytes) - array_byte_length
        array_status = declaration_instance["status"]
        if declaration_instance["validation"]["end_sentinel_index"] != end_index:
            array_status = "not-proven"

    source_sha256 = hashlib.sha256(payload).hexdigest()
    slice_sha256 = hashlib.sha256(slice_bytes).hexdigest()

    report_status = array_status
    if report_status == "match" and end_index is None:
        report_status = "partial"

    return {
        "format": FORMAT,
        "status": report_status,
        "endianness": "little",
        "memory": {
            "dump_base_address": f"0x{base_address:016x}",
            "slice_offset": f"0x{start_offset:x}",
            "slice_start_address": f"0x{slice_start:016x}",
            "slice_end_address_exclusive": f"0x{slice_end_exclusive:016x}",
            "slice_length": len(slice_bytes),
        },
        "provenance": {
            "kind": "raw-loaded-memory-dump",
            "source_name": source_name,
            "source_bytes": len(payload),
            "source_sha256": source_sha256,
            "slice_sha256": slice_sha256,
        },
        "bytes": {
            "hex": slice_bytes.hex(),
            "length": len(slice_bytes),
        },
        "extraction": {
            "record_stride": RECORD_STRIDE,
            "requested_count": probe["payload"]["requested_records"],
            "decoded_records_in_slice": probe["payload"]["decoded_records"],
            "end_sentinel_index": end_index,
            "end_sentinel_status": (
                "observed" if end_index is not None else "not-present"
            ),
            "declaration_array_records": declaration_instance["payload"]["decoded_records"],
            "declaration_array_bytes": array_byte_length,
            "post_sentinel_bytes": post_sentinel_bytes,
            "complete_array": array_status == "match" and end_index is not None,
        },
        "declaration_instance": declaration_instance,
        "evidence_boundary": {
            "runtime_memory_dump": "supplied",
            "runtime_declaration_array": (
                "observed" if array_status == "match" and end_index is not None else array_status
            ),
            "provenance_hashes": "observed",
            "source_authenticity": "not-authenticated",
        },
        "meb_property_mapping": {
            "status": "not-proven",
            "detail": "The captured declaration bytes do not establish MEB 460/461 linkage.",
        },
    }


def capture_d3d9_memory_declaration_file(
    path: str | Path,
    *,
    base_address: int,
    offset: int = 0,
    length: int | None = None,
    count: int | None = None,
) -> dict[str, Any]:
    source_path = Path(path)
    payload = source_path.read_bytes()
    return capture_d3d9_memory_declaration(
        payload,
        base_address=base_address,
        offset=offset,
        length=length,
        count=count,
        source_name=str(source_path),
    )
