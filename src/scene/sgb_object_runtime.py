"""Decode embedded SGB NODE object payloads using the retail binary grammar.

FUN_006a4b40 passes the inline payload at NODE record +0x1c to FUN_0069bc50.
FUN_0069a6c0 then dispatches by a kind string whose offset is relative to the
base of the complete SGB resource, not relative to the object payload.

The source and matching XML loader prove four binary kinds: LOD, HIERARCHY,
OBJECT and DAMAGE.  Matrix records are shared by LOD/HIERARCHY and use the
same Offset/Orientation/Scale/parent semantics as FUN_006990d0.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any


FORMAT = "SHIFT.SGBObjectRuntime/1"
KINDS = {"LOD", "HIERARCHY", "OBJECT", "DAMAGE"}

COMMON_HEADER_BYTES = 0x24
MATRIX_RECORD_BYTES = 0x24
RUNTIME_MATRIX_ELEMENT_BYTES = 0x28

# FUN_0069a6c0 copies each serialized MATRIX record (9 dwords / 0x24 bytes)
# into the same 0x28-byte runtime matrix element produced by FUN_006990d0.
MATRIX_RUNTIME_DESTINATION_WORDS = {
    0x00: 6,  # Orientation.w
    0x04: 3,  # Orientation.x
    0x08: 4,  # Orientation.y
    0x0C: 5,  # Orientation.z
    0x10: 0,  # Offset.x
    0x14: 1,  # Offset.y
    0x18: 2,  # Offset.z
    0x1C: 7,  # Scale
    0x20: 8,  # parent
}

# Compatibility aliases for Phase 521 names.  These records are matrix
# records, not child-object records.
HIERARCHY_RUNTIME_ELEMENT_BYTES = RUNTIME_MATRIX_ELEMENT_BYTES
HIERARCHY_RUNTIME_DESTINATION_WORDS = MATRIX_RUNTIME_DESTINATION_WORDS


class SGBObjectDecodeError(ValueError):
    pass


DAMAGE_RUNTIME_PAIR = {
    "constructor": "FUN_00698b00",
    "vtable": 0x00AF7C88,
    "allocation_bytes": 0xA0,
    "destructor": "FUN_0068cf40",
    "consumer": "FUN_0068cfe0",
    "matrix": {
        "count_offset": 0x80,
        "array_offset": 0x84,
        "element_bytes": RUNTIME_MATRIX_ELEMENT_BYTES,
        "consumer": "FUN_0068cfe0",
    },
    "subobject_pair": {
        "array_offset": 0x88,
        "pointer_count_consumed_by_runtime": 2,
        "pointer_stride": 4,
        "destructor_loop_bytes": 8,
        "destructor_child_release_vfunc_offset": 0x00,
    },
    "matrix_number_offset": 0x90,
    "proxy_vfuncs": {
        "0x10": {
            "function": "FUN_0068c6d0",
            "child_vfunc_offset": 0x10,
            "aggregation": "forward-to-both",
        },
        "0x14": {
            "function": "FUN_0068c750",
            "child_vfunc_offset": 0x14,
            "aggregation": "forward-to-both",
        },
        "0x18": {
            "function": "FUN_0068c710",
            "child_vfunc_offset": 0x18,
            "aggregation": "forward-to-both",
        },
        "0x20": {
            "function": "FUN_0068c790",
            "child_vfunc_offset": 0x20,
            "aggregation": "logical-and",
        },
        "0x28": {
            "function": "FUN_0068c7c0",
            "child_vfunc_offset": 0x28,
            "aggregation": "logical-and",
        },
        "0x24": {
            "function": "FUN_0068dea0",
            "child_probe_vfunc_offset": 0x3C,
            "fallback_child_vfunc_offset": 0x24,
            "aggregation": "specialized-two-child-selection",
        },
    },
    "construction": {
        "matrix_stack_builder": "FUN_0068cfe0",
        "matrix_number_index_stride": 0x40,
        "child_output_vfunc_offset": 0x24,
        "child_output_fields": [0xA0, 0xA4],
    },
    "ownership": {
        "matrix_array_free_base_adjust": -8,
        "subobject_pair_array_freed": True,
        "subobject_pair_array_cleared": True,
    },
    "serialized_layout_status": "partial",
}


RUNTIME_WRAPPERS = {
    "LOD": {
        "constructor": "FUN_00698a90",
        "vtable": 0x00AF8660,
        "allocation_bytes": 0xA0,
        "proven_fields": {
            "subobject_count": 0x80,
            "matrix_count": 0x84,
            "runtime_matrix_array": 0x88,
            "runtime_subobject_array": 0x8C,
            "matrix_number": 0x94,
            "lod_distances": 0x98,
        },
    },
    "HIERARCHY": {
        "constructor": "FUN_00698a20",
        "vtable": 0x00AF8620,
        "allocation_bytes": 0xA0,
        "proven_fields": {
            "subobject_count": 0x80,
            "matrix_count": 0x84,
            "runtime_matrix_array": 0x88,
            "runtime_subobject_array": 0x8C,
            "matrix_number": 0x94,
        },
    },
    "OBJECT": {
        "constructor": "FUN_00698dc0",
        "initializer": "FUN_00698dd0",
        "vtable": 0x00AF86B0,
        "allocation_bytes": 0xB0,
        "proven_fields": {
            "resource_object": 0x80,
            "matrix_number": 0x84,
            "orientation_wxyz": 0x88,
            "offset_xyz": 0x98,
            "scale": 0xA4,
        },
    },
    "DAMAGE": {
        "constructor": "FUN_00698b00",
        "vtable": 0x00AF7C88,
        "allocation_bytes": 0xA0,
        "destructor": "FUN_0068cf40",
        "proven_fields": {
            "matrix_count": 0x80,
            "runtime_matrix_array": 0x84,
            "runtime_subobject_pair": 0x88,
            "matrix_number": 0x90,
        },
        "runtime_pair_contract": DAMAGE_RUNTIME_PAIR,
    },
}


def _u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise SGBObjectDecodeError(f"u32 out of range at 0x{off:x}")
    return struct.unpack_from("<I", data, off)[0]


def _i32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise SGBObjectDecodeError(f"i32 out of range at 0x{off:x}")
    return struct.unpack_from("<i", data, off)[0]


def _f32(data: bytes, off: int) -> float:
    if off < 0 or off + 4 > len(data):
        raise SGBObjectDecodeError(f"f32 out of range at 0x{off:x}")
    return struct.unpack_from("<f", data, off)[0]


def _string(
    data: bytes,
    relative_base: int,
    rel: int,
) -> dict[str, Any]:
    absolute = relative_base + rel
    text = None
    if rel and 0 <= absolute < len(data):
        stop = data.find(b"\0", absolute)
        if stop >= 0:
            text = data[absolute:stop].decode("utf-8", "replace")
    return {
        "relative_offset": rel,
        "relative_base": relative_base,
        "absolute_offset": absolute if text is not None else None,
        "text": text,
    }


def parse_matrix_records(
    data: bytes,
    start: int,
    end: int,
    count: int,
) -> list[dict[str, Any]]:
    """Decode the serialized MATRIX records copied by FUN_0069a6c0."""
    rows: list[dict[str, Any]] = []
    cursor = start
    for index in range(count):
        if cursor + MATRIX_RECORD_BYTES > end:
            raise SGBObjectDecodeError(
                f"MATRIX record {index} exceeds object payload"
            )
        words = [_u32(data, cursor + 4 * i) for i in range(9)]
        rows.append({
            "index": index,
            "offset": cursor,
            "record_bytes": MATRIX_RECORD_BYTES,
            "raw_u32": words,
            "offset_xyz": [
                _f32(data, cursor + 0x00),
                _f32(data, cursor + 0x04),
                _f32(data, cursor + 0x08),
            ],
            "orientation_xyzw": [
                _f32(data, cursor + 0x0C),
                _f32(data, cursor + 0x10),
                _f32(data, cursor + 0x14),
                _f32(data, cursor + 0x18),
            ],
            "scale": _f32(data, cursor + 0x1C),
            "parent": _i32(data, cursor + 0x20),
            "runtime_element_bytes": RUNTIME_MATRIX_ELEMENT_BYTES,
            "runtime_destination_word_offsets": {
                f"0x{offset:02x}": source_word
                for offset, source_word
                in MATRIX_RUNTIME_DESTINATION_WORDS.items()
            },
            "runtime_source_word_offsets": {
                str(source_word): offset
                for offset, source_word
                in MATRIX_RUNTIME_DESTINATION_WORDS.items()
            },
            "runtime_orientation_order": "wxyz",
            "runtime_reserved_offset": 0x24,
        })
        cursor += MATRIX_RECORD_BYTES
    return rows


def parse_hierarchy_children(
    data: bytes,
    start: int,
    end: int,
    count: int,
) -> list[dict[str, Any]]:
    """Compatibility alias for the Phase 521 matrix-record parser."""
    return parse_matrix_records(data, start, end, count)


def _subobject_offsets(
    data: bytes,
    start: int,
    end: int,
    count: int,
    *,
    relative_base: int,
) -> tuple[list[int], list[int], int]:
    byte_count = count * 4
    if start + byte_count > end:
        raise SGBObjectDecodeError(
            f"subobject offset table requires {byte_count} bytes"
        )
    raw = [_u32(data, start + 4 * i) for i in range(count)]
    resolved = [relative_base + value for value in raw]
    return raw, resolved, start + byte_count


def _decode_subobjects(
    data: bytes,
    offsets: list[int],
    *,
    parent_start: int,
    parent_end: int,
    relative_base: int,
    strict: bool,
) -> list[dict[str, Any]]:
    if not offsets:
        return []

    valid = [
        value
        for value in offsets
        if parent_start < value < parent_end
    ]
    sorted_unique = sorted(set(valid))
    next_bound = {
        value: (
            sorted_unique[index + 1]
            if index + 1 < len(sorted_unique)
            else parent_end
        )
        for index, value in enumerate(sorted_unique)
    }

    rows: list[dict[str, Any]] = []
    for index, absolute in enumerate(offsets):
        row: dict[str, Any] = {
            "index": index,
            "absolute_offset": absolute,
            "within_parent_span": parent_start < absolute < parent_end,
            "decoded": False,
        }
        if absolute not in next_bound:
            row["blocking_reason"] = "subobject-offset-outside-parent-span"
            if strict:
                raise SGBObjectDecodeError(
                    f"subobject {index} offset 0x{absolute:x} "
                    f"is outside parent span "
                    f"0x{parent_start:x}..0x{parent_end:x}"
                )
        else:
            child_end = next_bound[absolute]
            try:
                row["report"] = parse_sgb_object_payload(
                    data,
                    base_offset=absolute,
                    end_offset=child_end,
                    relative_base=relative_base,
                    strict=strict,
                )
                row["decoded"] = bool(row["report"].get("decoded"))
            except SGBObjectDecodeError as exc:
                row["blocking_reason"] = str(exc)
                if strict:
                    raise
        rows.append(row)
    return rows


def parse_sgb_object_payload(
    data: bytes,
    *,
    base_offset: int = 0,
    end_offset: int | None = None,
    relative_base: int | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Decode one binary NODE object payload and proven recursive layout."""
    end = len(data) if end_offset is None else end_offset
    if not 0 <= base_offset < end <= len(data):
        raise SGBObjectDecodeError("invalid object payload bounds")
    if base_offset + COMMON_HEADER_BYTES > end:
        raise SGBObjectDecodeError(
            "object payload is smaller than the common 0x24-byte header"
        )

    reference_base = base_offset if relative_base is None else relative_base
    words = [_u32(data, base_offset + 4 * i) for i in range(9)]

    kind = _string(data, reference_base, words[0])
    source = _string(data, reference_base, words[1])
    third = _string(data, reference_base, words[2])
    kind_text = kind["text"]

    matrix_number = struct.unpack_from("<b", data, base_offset + 0x20)[0]
    unknown_byte_21 = data[base_offset + 0x21]
    matrix_count = data[base_offset + 0x22]
    subobject_count = data[base_offset + 0x23]

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
        "relative_base": reference_base,
        "common_header_bytes": COMMON_HEADER_BYTES,
        "header_words": words,
        "kind": kind,
        "source_string": source,
        "third_string": third,
        "instances": words[3],
        "sphere": {
            "center_xyz": [
                _f32(data, base_offset + 0x10),
                _f32(data, base_offset + 0x14),
                _f32(data, base_offset + 0x18),
            ],
            "radius": _f32(data, base_offset + 0x1C),
            "source": "SCENE XML SPHERE/Centre + Radius",
        },
        "matrix_number": matrix_number,
        "unknown_byte_21": unknown_byte_21,
        "matrix_count": matrix_count,
        "subobject_count": subobject_count,
        "kind_status": status,
        "hash_sha256": hashlib.sha256(
            data[base_offset:end]
        ).hexdigest(),
        "decoded": status == "recognized-kind",
        "runtime_wrapper": (
            {**RUNTIME_WRAPPERS[kind_text], "kind": kind_text}
            if kind_text in RUNTIME_WRAPPERS
            else {"kind": kind_text, "resolved": False}
        ),
        "evidence": {
            "entry": "FUN_0069bc50",
            "dispatcher": "FUN_0069a6c0",
            "xml_crosscheck": "FUN_0069b1c0",
            "matrix_xml_loader": "FUN_006990d0",
            "matrix_copy": "FUN_0069a6c0",
            "runtime_wrapper_constructors": {
                "LOD": "FUN_00698a90",
                "HIERARCHY": "FUN_00698a20",
                "OBJECT": "FUN_00698dc0",
                "DAMAGE": "FUN_00698b00",
            },
        },
        "limitations": [
            "Byte +0x21 remains unnamed because no direct source consumer is proven.",
            "DAMAGE-specific serialized payload after the common header remains conservative.",
        ],
    }

    if status != "recognized-kind":
        return report

    if kind_text in {"LOD", "HIERARCHY"}:
        matrix_start = base_offset + COMMON_HEADER_BYTES
        matrix_end = matrix_start + matrix_count * MATRIX_RECORD_BYTES
        if matrix_end > end:
            message = (
                f"{kind_text} matrix table requires "
                f"{matrix_count * MATRIX_RECORD_BYTES} bytes"
            )
            if strict:
                raise SGBObjectDecodeError(message)
            report.update({
                "decoded": False,
                "status": "blocked",
                "blockers": [f"{kind_text.lower()}:{message}"],
            })
            return report

        report["matrix_records"] = parse_matrix_records(
            data, matrix_start, matrix_end, matrix_count
        )
        report["matrix_table_offset"] = matrix_start
        report["matrix_table_size"] = (
            matrix_count * MATRIX_RECORD_BYTES
        )
        cursor = matrix_end

        if kind_text == "LOD":
            distance_bytes = subobject_count * 4
            if cursor + distance_bytes > end:
                message = (
                    f"LOD distance table requires {distance_bytes} bytes"
                )
                if strict:
                    raise SGBObjectDecodeError(message)
                report.update({
                    "decoded": False,
                    "status": "blocked",
                    "blockers": [f"lod:{message}"],
                })
                return report
            report["lod_distances"] = [
                _f32(data, cursor + 4 * i)
                for i in range(subobject_count)
            ]
            report["lod_distance_table_offset"] = cursor
            report["lod_distance_table_size"] = distance_bytes
            report["lod_distance_runtime"] = {
                "runtime_field_offset": 0x98,
                "zero_value_fallback": (
                    "FUN_006993f0 or (1 << index) * 100, "
                    "then scaled by DAT_00b89dcc"
                ),
            }
            cursor += distance_bytes

        raw_offsets, resolved_offsets, cursor = _subobject_offsets(
            data,
            cursor,
            end,
            subobject_count,
            relative_base=reference_base,
        )
        report["subobject_offset_table_offset"] = (
            cursor - subobject_count * 4
        )
        report["subobject_offset_table_size"] = (
            subobject_count * 4
        )
        report["subobject_relative_offsets"] = raw_offsets
        report["subobject_absolute_offsets"] = resolved_offsets
        report["subobjects"] = _decode_subobjects(
            data,
            resolved_offsets,
            parent_start=base_offset,
            parent_end=end,
            relative_base=reference_base,
            strict=strict,
        )
        report["serialized_fixed_region_end"] = cursor

    elif kind_text == "OBJECT":
        # Binary OBJECT stores userflags immediately after the 0x24-byte
        # common header.  If MatrixNumber == -1 it then embeds the same
        # MATRIX transform fields as the XML MATRIX element.
        if base_offset + 0x28 > end:
            message = "OBJECT payload has no userflags word"
            if strict:
                raise SGBObjectDecodeError(message)
            report.update({
                "decoded": False,
                "status": "blocked",
                "blockers": [f"object:{message}"],
            })
            return report

        report["resource_filename"] = third
        report["userflags"] = _u32(data, base_offset + 0x24)
        report["userflags_offset"] = 0x24
        report["runtime_wrapper"]["userflags_i64_offset"] = 0x50

        if matrix_number == -1:
            if base_offset + 0x48 > end:
                message = (
                    "OBJECT MatrixNumber=-1 requires embedded "
                    "0x20-byte MATRIX transform"
                )
                if strict:
                    raise SGBObjectDecodeError(message)
                report.update({
                    "decoded": False,
                    "status": "blocked",
                    "blockers": [f"object:{message}"],
                })
                return report
            transform = {
                "offset_xyz": [
                    _f32(data, base_offset + 0x28),
                    _f32(data, base_offset + 0x2C),
                    _f32(data, base_offset + 0x30),
                ],
                "orientation_xyzw": [
                    _f32(data, base_offset + 0x34),
                    _f32(data, base_offset + 0x38),
                    _f32(data, base_offset + 0x3C),
                    _f32(data, base_offset + 0x40),
                ],
                "scale": _f32(data, base_offset + 0x44),
                "source_offsets": {
                    "offset_xyz": 0x28,
                    "orientation_xyzw": 0x34,
                    "scale": 0x44,
                },
                "runtime_offsets": {
                    "orientation_wxyz": 0x88,
                    "offset_xyz": 0x98,
                    "scale": 0xA4,
                },
            }
            report["embedded_matrix"] = transform
            report["serialized_fixed_region_end"] = base_offset + 0x48
        else:
            report["serialized_fixed_region_end"] = base_offset + 0x28

    elif kind_text == "DAMAGE":
        report["damage_serialized_layout"] = {
            "status": "partial",
            "matrix_count_offset": 0x22,
            "subobject_count_offset": 0x23,
            "runtime_matrix_loader": "FUN_00699870",
            "runtime_subobject_pair_offset": 0x88,
            "runtime_pair_pointer_count": 2,
            "binary_subobject_offset_table": "not-normalized",
        }
        report["damage_runtime_pair"] = DAMAGE_RUNTIME_PAIR

    return report
