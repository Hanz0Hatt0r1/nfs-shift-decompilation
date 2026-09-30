"""Source-backed decoder for inline SGB NODE/SUMM object payloads.

The binary runtime enters these payloads through FUN_0069bc50 and dispatches in
FUN_0069a6c0.  NODE/SUMM record +0x1c is the payload itself; the dword string
references inside the payload are offsets from the SGB file base.

The production binary dispatcher handles LOD, HIERARCHY and OBJECT.  DAMAGE is
constructed by the parallel XML object loader but is not claimed as a binary
NODE/SUMM branch.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any


FORMAT = "SHIFT.SGBObjectRuntime/1"
BINARY_KINDS = {"LOD", "HIERARCHY", "OBJECT"}
ALTERNATE_RUNTIME_KINDS = {"DAMAGE"}
KINDS = BINARY_KINDS | ALTERNATE_RUNTIME_KINDS

MATRIX_RECORD_BYTES = 0x24
MATRIX_RUNTIME_ELEMENT_BYTES = 0x28
MATRIX_RUNTIME_DESTINATION_WORDS = {
    0x00: 6,
    0x04: 3,
    0x08: 4,
    0x0C: 5,
    0x10: 0,
    0x14: 1,
    0x18: 2,
    0x1C: 7,
    0x20: 8,
}

# Compatibility aliases for older callers.  The records are matrices rather
# than generic hierarchy children; Phase 543 corrects the semantic label.
HIERARCHY_RUNTIME_ELEMENT_BYTES = MATRIX_RUNTIME_ELEMENT_BYTES
HIERARCHY_RUNTIME_DESTINATION_WORDS = MATRIX_RUNTIME_DESTINATION_WORDS


class SGBObjectDecodeError(ValueError):
    pass


RUNTIME_WRAPPERS = {
    "LOD": {
        "constructor": "FUN_00698a90",
        "vtable": 0x00AF8660,
        "allocation_bytes": 0xA0,
        "binary_node_dispatch": True,
        "proven_fields": {
            "subobjects": 0x80,
            "matrices": 0x84,
            "runtime_matrix_array": 0x88,
            "runtime_subobject_array": 0x8C,
            "matrix_number": 0x94,
            "distance_array": 0x98,
        },
    },
    "HIERARCHY": {
        "constructor": "FUN_00698a20",
        "vtable": 0x00AF8620,
        "allocation_bytes": 0xA0,
        "binary_node_dispatch": True,
        "proven_fields": {
            "subobjects": 0x80,
            "matrices": 0x84,
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
        "binary_node_dispatch": True,
        "proven_fields": {
            "resource_object": 0x80,
            "matrix_number": 0x84,
            "orientation": 0x88,
            "offset": 0x98,
            "scale": 0xA4,
        },
    },
    "DAMAGE": {
        "constructor": "FUN_00698b00",
        "vtable": 0x00AF7C88,
        "allocation_bytes": 0xA0,
        "binary_node_dispatch": False,
        "alternate_loader": "FUN_00699b10/FUN_0069b1c0",
        "proven_fields": {},
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
    reference_base: int,
    rel: int,
) -> dict[str, Any]:
    absolute = reference_base + rel
    text = None
    if rel and 0 <= absolute < len(data):
        stop = data.find(b"\0", absolute)
        if stop >= 0:
            text = data[absolute:stop].decode("utf-8", "replace")
    return {
        "relative_offset": rel,
        "reference_base_offset": reference_base,
        "absolute_offset": absolute if text is not None else None,
        "text": text,
    }


def parse_matrix_records(
    data: bytes,
    start: int,
    end: int,
    count: int,
) -> list[dict[str, Any]]:
    """Decode the 9-dword MATRIX records copied by FUN_0069a6c0."""
    rows: list[dict[str, Any]] = []
    cursor = start
    for index in range(count):
        if cursor + MATRIX_RECORD_BYTES > end:
            raise SGBObjectDecodeError(
                f"MATRIX record {index} exceeds object payload"
            )
        words = [_u32(data, cursor + 4 * i) for i in range(9)]
        floats = [_f32(data, cursor + 4 * i) for i in range(8)]
        rows.append({
            "index": index,
            "offset": cursor,
            "record_bytes": MATRIX_RECORD_BYTES,
            "raw_u32": words,
            "offset_xyz": floats[0:3],
            "orientation_serialized": floats[3:7],
            "orientation_runtime_order": [
                floats[6],
                floats[3],
                floats[4],
                floats[5],
            ],
            "scale": floats[7],
            "parent": _i32(data, cursor + 0x20),
            "runtime_copy_order": [6, 3, 4, 5, 0, 1, 2, 7, 8],
            "runtime_element_bytes": MATRIX_RUNTIME_ELEMENT_BYTES,
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
            "semantic_evidence": {
                "offset": "FUN_006990d0 XML field Offset",
                "orientation": "FUN_006990d0 XML field Orientation",
                "scale": "FUN_006990d0 XML field Scale",
                "parent": "FUN_006990d0 XML field parent",
            },
        })
        cursor += MATRIX_RECORD_BYTES
    return rows


def parse_hierarchy_children(
    data: bytes,
    start: int,
    end: int,
    count: int,
) -> list[dict[str, Any]]:
    """Compatibility alias for the Phase 521 matrix-record decoder."""
    return parse_matrix_records(data, start, end, count)


def _child_bounds(
    absolute_refs: list[int],
    parent_start: int,
    parent_end: int,
    data_end: int,
) -> dict[int, int]:
    unique = sorted({value for value in absolute_refs if value})
    bounds: dict[int, int] = {}
    for index, value in enumerate(unique):
        next_value = unique[index + 1] if index + 1 < len(unique) else None
        if parent_start <= value < parent_end:
            bounds[value] = (
                next_value
                if next_value is not None
                and value < next_value <= parent_end
                else parent_end
            )
        else:
            bounds[value] = (
                next_value
                if next_value is not None and value < next_value <= data_end
                else data_end
            )
    return bounds


def parse_sgb_object_payload(
    data: bytes,
    *,
    base_offset: int = 0,
    end_offset: int | None = None,
    reference_base_offset: int | None = None,
    strict: bool = True,
    max_depth: int = 16,
    _depth: int = 0,
    _visited: frozenset[int] | None = None,
) -> dict[str, Any]:
    """Decode one inline binary object payload and its proven subobject graph."""
    end = len(data) if end_offset is None else end_offset
    reference_base = (
        base_offset
        if reference_base_offset is None
        else reference_base_offset
    )
    if not 0 <= base_offset < end <= len(data):
        raise SGBObjectDecodeError("invalid object payload bounds")
    if base_offset + 36 > end:
        raise SGBObjectDecodeError(
            "object payload is smaller than the 0x24-byte common header"
        )
    if _depth > max_depth:
        raise SGBObjectDecodeError(
            "object payload exceeded maximum recursion depth"
        )

    visited = _visited or frozenset()
    if base_offset in visited:
        raise SGBObjectDecodeError(
            f"recursive object cycle at 0x{base_offset:x}"
        )
    visited = visited | {base_offset}

    kind = _string(
        data,
        reference_base,
        _i32(data, base_offset),
    )
    source = _string(
        data,
        reference_base,
        _i32(data, base_offset + 4),
    )
    aux = _string(
        data,
        reference_base,
        _i32(data, base_offset + 8),
    )
    words = [_u32(data, base_offset + 4 * i) for i in range(9)]
    matrix_number = struct.unpack_from(
        "<b", data, base_offset + 0x20
    )[0]
    control_byte_21 = data[base_offset + 0x21]
    matrices = data[base_offset + 0x22]
    subobjects = data[base_offset + 0x23]

    kind_text = kind["text"]
    if kind_text in BINARY_KINDS:
        kind_status = "recognized-binary-kind"
        decoded = True
        blockers: list[str] = []
    elif kind_text in ALTERNATE_RUNTIME_KINDS:
        kind_status = "alternate-runtime-kind-not-binary-node"
        decoded = False
        blockers = [f"object-kind:not-in-binary-dispatch:{kind_text}"]
    else:
        kind_status = (
            "unknown-kind" if kind_text else "kind-unresolved"
        )
        decoded = False
        blockers = [
            f"object-kind:{kind_status}:{kind_text or '<null>'}"
        ]

    report: dict[str, Any] = {
        "format": FORMAT,
        "version": 1,
        "base_offset": base_offset,
        "end_offset": end,
        "reference_base_offset": reference_base,
        "size_bound": end - base_offset,
        "header_bytes": 0x24,
        "header_words": words,
        "kind": kind,
        "source_string": source,
        "aux_string": aux,
        "instances": words[3],
        "matrix_number": matrix_number,
        "control_byte_21": control_byte_21,
        "matrices": matrices,
        "subobjects": subobjects,
        "kind_status": kind_status,
        "hash_sha256": hashlib.sha256(
            data[base_offset:end]
        ).hexdigest(),
        "decoded": decoded,
        "status": "decoded" if decoded else "blocked",
        "blockers": blockers,
        "runtime_wrapper": (
            {
                **RUNTIME_WRAPPERS[kind_text],
                "kind": kind_text,
            }
            if kind_text in RUNTIME_WRAPPERS
            else {"kind": kind_text, "resolved": False}
        ),
        "evidence": {
            "entry": "FUN_0069bc50",
            "binary_dispatcher": "FUN_0069a6c0",
            "xml_cross_path": "FUN_00699b10/FUN_0069b1c0",
            "matrix_record_loader": "FUN_006990d0/FUN_0069a6c0",
            "runtime_wrapper_constructors": {
                "LOD": "FUN_00698a90",
                "HIERARCHY": "FUN_00698a20",
                "OBJECT": "FUN_00698dc0/FUN_00698dd0",
                "DAMAGE": "FUN_00698b00 (XML path only)",
            },
            "field_names": {
                "matrix_number": (
                    "XML MatrixNumber -> binary byte +0x20"
                ),
                "matrices": (
                    "XML matrices -> binary byte +0x22"
                ),
                "subobjects": (
                    "XML subobjects -> binary byte +0x23"
                ),
            },
        },
        "limitations": [
            (
                "The semantic role of source_string and aux_string is "
                "kept generic outside branch-specific consumers."
            ),
            (
                "DAMAGE has a concrete alternate/XML runtime wrapper but "
                "is not present in the binary FUN_0069a6c0 dispatch."
            ),
        ],
    }

    if not decoded:
        return report

    if kind_text in {"LOD", "HIERARCHY"}:
        matrix_start = base_offset + 0x24
        matrix_end = matrix_start + matrices * MATRIX_RECORD_BYTES
        if matrix_end > end:
            message = (
                f"{kind_text} matrix table requires "
                f"{matrices * MATRIX_RECORD_BYTES} bytes"
            )
            if strict:
                raise SGBObjectDecodeError(message)
            report["decoded"] = False
            report["status"] = "blocked"
            report["blockers"].append(f"matrix-table:{message}")
            return report

        matrix_records = parse_matrix_records(
            data, matrix_start, matrix_end, matrices
        )
        report["matrix_records"] = matrix_records
        report["matrix_table_offset"] = matrix_start
        report["matrix_table_size"] = (
            matrices * MATRIX_RECORD_BYTES
        )

        cursor = matrix_end
        if kind_text == "LOD":
            distance_end = cursor + subobjects * 4
            if distance_end > end:
                message = (
                    "LOD distance table exceeds object payload"
                )
                if strict:
                    raise SGBObjectDecodeError(message)
                report["decoded"] = False
                report["status"] = "blocked"
                report["blockers"].append(
                    f"lod-distance-table:{message}"
                )
                return report
            report["lod_distances_serialized"] = [
                _f32(data, cursor + 4 * i)
                for i in range(subobjects)
            ]
            report["lod_distance_table_offset"] = cursor
            report["lod_distance_table_size"] = subobjects * 4
            report["lod_distance_runtime_rule"] = {
                "consumer": "FUN_0069a6c0",
                "zero_value_fallback": (
                    "FUN_006993f0(name,index) or "
                    "(1<<index)*100, then global scale"
                ),
            }
            cursor = distance_end

        reference_end = cursor + subobjects * 4
        if reference_end > end:
            message = (
                f"{kind_text} subobject reference table exceeds "
                "object payload"
            )
            if strict:
                raise SGBObjectDecodeError(message)
            report["decoded"] = False
            report["status"] = "blocked"
            report["blockers"].append(
                f"subobject-reference-table:{message}"
            )
            return report

        serialized_refs = [
            _u32(data, cursor + 4 * i)
            for i in range(subobjects)
        ]
        absolute_refs = [
            reference_base + value if value else 0
            for value in serialized_refs
        ]
        bounds = _child_bounds(
            absolute_refs,
            base_offset,
            end,
            len(data),
        )

        subobject_rows: list[dict[str, Any]] = []
        for index, (serialized, absolute) in enumerate(
            zip(serialized_refs, absolute_refs)
        ):
            row: dict[str, Any] = {
                "index": index,
                "serialized_offset": serialized,
                "reference_base_offset": reference_base,
                "absolute_offset": absolute if serialized else None,
                "contained_in_parent_record": bool(
                    serialized
                    and base_offset <= absolute < end
                ),
                "decoded": False,
            }
            if serialized:
                if not 0 <= absolute < len(data):
                    message = (
                        f"subobject {index} points outside SGB: "
                        f"0x{absolute:x}"
                    )
                    if strict:
                        raise SGBObjectDecodeError(message)
                    row["decode_error"] = message
                else:
                    child_end = bounds[absolute]
                    try:
                        child = parse_sgb_object_payload(
                            data,
                            base_offset=absolute,
                            end_offset=child_end,
                            reference_base_offset=reference_base,
                            strict=strict,
                            max_depth=max_depth,
                            _depth=_depth + 1,
                            _visited=visited,
                        )
                        row["report"] = child
                        row["decoded"] = bool(child.get("decoded"))
                    except SGBObjectDecodeError as exc:
                        row["decode_error"] = str(exc)
                        if strict:
                            raise
            subobject_rows.append(row)

        report["subobject_reference_table_offset"] = cursor
        report["subobject_reference_table_size"] = subobjects * 4
        report["subobject_references"] = subobject_rows
        report["recursive_subobject_decoder"] = "FUN_0069bc50"

    if kind_text == "OBJECT":
        if base_offset + 0x28 <= end:
            report["user_flags_word"] = _u32(
                data, base_offset + 0x24
            )
        if matrix_number == -1:
            explicit_end = base_offset + 0x48
            if explicit_end > end:
                message = (
                    "OBJECT MatrixNumber=-1 explicit matrix exceeds "
                    "object payload"
                )
                if strict:
                    raise SGBObjectDecodeError(message)
                report["decoded"] = False
                report["status"] = "blocked"
                report["blockers"].append(
                    f"object-explicit-matrix:{message}"
                )
                return report
            report["explicit_matrix"] = {
                "offset_xyz": [
                    _f32(data, base_offset + 0x28 + 4 * i)
                    for i in range(3)
                ],
                "orientation_serialized": [
                    _f32(data, base_offset + 0x34 + 4 * i)
                    for i in range(4)
                ],
                "orientation_runtime_order": [
                    _f32(data, base_offset + 0x40),
                    _f32(data, base_offset + 0x34),
                    _f32(data, base_offset + 0x38),
                    _f32(data, base_offset + 0x3C),
                ],
                "scale": _f32(data, base_offset + 0x44),
                "source": "FUN_00698f40/FUN_0069a6c0",
            }

    return report
