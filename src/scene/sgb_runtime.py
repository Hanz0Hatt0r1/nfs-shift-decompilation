"""Source-backed decoder for the binary SGB runtime chunk grammar.

Recovered from FUN_006a5270 and its handlers FUN_006a4b40 (NODE),
FUN_006a48d0 (FLAT), FUN_006a4f10 (OCCL), FUN_006a4d10 (PART), and
FUN_006a4900 (SUMM). Unknown fields stay raw/positional rather than guessed.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any

FORMAT = "SHIFT.SGBRuntime/1"
MAGIC = b" \x42\x47\x53"
KNOWN_TAGS = {"NODE", "FLAT", "OCCL", "PART", "SUMM", "END "}

# FUN_006a4b40 creates the runtime NODE wrapper with this concrete vtable.
NODE_RUNTIME_VTABLE = 0x00AF78EC

SUMM_RUNTIME_WRAPPER = {
    "vtable": 0x00AF78EC,
    "instance_bytes": 0x38,
    "source_field_offsets": {
        "name": 0x08,
        "resource": 0x0C,
        "variation_palette": 0x10,
        "instances": 0x14,
        "flags": 0x18,
        "variation_index": 0x1A,
        "object_payload": 0x1C,
    },
    "runtime_field_offsets": {
        "payload": 0x08,
        "resource": 0x18,
        "variation_palette": 0x1C,
        "variation_index": 0x20,
        "instances": 0x24,
        "flag_bit0": 0x15,
        "flag_bit1": 0x16,
        "flag_bit2": 0x17,
        "name_hash_lo": 0x28,
        "name_hash_hi": 0x2C,
    },
}

# FUN_006a4f10 consumes one fixed 0x38-byte OCCL source record.  The same
# runtime object is constructed from SCENE XML by FUN_006a3c40, which names
# the four source vectors PositionTL/TR/BL/BR.  FUN_006b43d0 constructs the
# concrete 0x120-byte object and installs PTR_FUN_00afa2fc.
OCCL_RUNTIME_OBJECT = {
    "constructor": "FUN_006b43d0",
    "vtable": 0x00AFA2FC,
    "instance_bytes": 0x120,
    "source_field_offsets": {
        "name": 0x00,
        "resource": 0x04,
        "position_tl": 0x08,
        "position_tr": 0x14,
        "position_bl": 0x20,
        "position_br": 0x2C,
    },
    "runtime_field_offsets": {
        "name_resource_descriptor": 0x60,
        "position_tl": 0x90,
        "position_tr": 0xA0,
        "position_bl": 0xB0,
        "position_br": 0xC0,
        "secondary_matrix": 0xD0,
        "flag_byte": 0x110,
    },
    "source_vector_components": 3,
    "runtime_vector_components": 4,
    "runtime_w_value": 1.0,
    "xml_constructor": "FUN_006a3c40",
}

OCCL_RUNTIME_WRAPPER = {
    "constructor_path": "FUN_006a4f10",
    "vtable": NODE_RUNTIME_VTABLE,
    "instance_bytes": 0x38,
    "payload_field_offset": 0x08,
}

# FUN_006a4d10 forwards every PART record to FUN_0068a360.  The first
# partition creates the runtime tree root through FUN_00688ef0/FUN_006886a0;
# later records are inserted by FUN_00689a30 by matching their partition_id
# against one of four unresolved child-partition slots.
PART_RUNTIME_TREE = {
    "loader": "FUN_006a4d10",
    "consumer": "FUN_0068a360",
    "insert_consumer": "FUN_00689a30",
    "node_allocator": "FUN_00688ef0 -> FUN_006886a0",
    "node_vtable": 0x00AF7A68,
    "manager_root_field_offset": 0x28,
    "runtime_node_field_offsets": {
        "aabbox_min": 0x04,
        "aabbox_max": 0x10,
        "child_partition_slots": [0x1C, 0x20, 0x24, 0x28],
        "child_object_container": 0x34,
        "child_partition_id_mask": 0x58,
    },
    "scene_wrapper_partition_bounds_field_offset": 0x30,
    "scene_wrapper_list_lookup": "FUN_006885b0",
    "child_object_reference_base": 1,
    "child_object_kind_vfunc_offset": 0x04,
    "child_object_kind_codes": [1, 3, 4],
    "manager_kind3_container_offset": 0x58,
}


class SGBRuntimeDecodeError(ValueError):
    pass


def _u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise SGBRuntimeDecodeError(f"u32 out of range at 0x{off:x}")
    return struct.unpack_from("<I", data, off)[0]


def _i32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise SGBRuntimeDecodeError(f"i32 out of range at 0x{off:x}")
    return struct.unpack_from("<i", data, off)[0]


def _f32(data: bytes, off: int) -> float:
    if off < 0 or off + 4 > len(data):
        raise SGBRuntimeDecodeError(f"f32 out of range at 0x{off:x}")
    return struct.unpack_from("<f", data, off)[0]


def _resolve_string(
    data: bytes,
    relative_base: int,
    relative: int,
) -> dict[str, Any]:
    absolute = relative_base + relative
    text = None
    if relative and 0 <= absolute < len(data):
        end = data.find(b"\0", absolute)
        if end >= 0:
            text = data[absolute:end].decode("utf-8", "replace")
    return {
        "relative_offset": relative,
        "relative_base": relative_base,
        "absolute_offset": absolute if text is not None else None,
        "text": text,
    }


def _tag(raw: bytes) -> str:
    return raw[::-1].decode("ascii", "replace")


def _parse_wrapper_records(
    data: bytes,
    start: int,
    end: int,
    count: int,
    *,
    strict: bool,
    wrapper_kind: str,
) -> list[dict[str, Any]]:
    """Decode the shared variable-stride NODE/SUMM record grammar."""
    from sgb_object_runtime import (
        SGBObjectDecodeError,
        parse_sgb_object_payload,
    )

    rows: list[dict[str, Any]] = []
    cursor = start + 12
    for index in range(count):
        if cursor + 32 > end:
            raise SGBRuntimeDecodeError(
                f"{wrapper_kind} record {index} header exceeds chunk"
            )
        stride = _u32(data, cursor)
        if stride < 32 or cursor + stride > end:
            raise SGBRuntimeDecodeError(
                f"invalid {wrapper_kind} stride {stride} at record {index}"
            )
        record_end = cursor + stride
        words = [_u32(data, cursor + 4 * i) for i in range(8)]
        flags = data[cursor + 24]
        variation = struct.unpack_from("<h", data, cursor + 26)[0]

        object_base = cursor + 0x1C
        try:
            object_report = parse_sgb_object_payload(
                data,
                base_offset=object_base,
                end_offset=record_end,
                reference_base_offset=0,
                strict=strict,
            )
        except SGBObjectDecodeError as exc:
            if strict:
                raise SGBRuntimeDecodeError(
                    f"{wrapper_kind} object {index}: {exc}"
                ) from exc
            object_report = {
                "format": "SHIFT.SGBObjectRuntime/1",
                "decoded": False,
                "status": "blocked",
                "blockers": [f"object:{exc}"],
            }

        row = {
            "index": index,
            "offset": cursor,
            "stride": stride,
            "record_end": record_end,
            "raw_u32_header": words,
            "unknown_word_1": words[1],
            "name": _resolve_string(
                data, 0, len(data), _i32(data, cursor + 8)
            ),
            "resource": _resolve_string(
                data, 0, len(data), _i32(data, cursor + 12)
            ),
            "variation_palette_file": _resolve_string(
                data, 0, len(data), _i32(data, cursor + 16)
            ),
            "instances": words[5],
            "flags": {
                "raw": flags,
                "bit0": bool(flags & 1),
                "bit1": bool(flags & 2),
                "bit2": bool(flags & 4),
            },
            "variation_index": variation,
            "object_payload": {
                "inline_offset_in_record": 0x1C,
                "absolute_offset": object_base,
                "record_end": record_end,
                "reference_base_offset": 0,
                "decoder": "FUN_0069bc50",
                "decoded": bool(object_report.get("decoded")),
                "report": object_report,
            },
        }

        if wrapper_kind == "NODE":
            row["runtime_wrapper"] = {
                "vtable": NODE_RUNTIME_VTABLE,
                "payload_field_offset": 0x08,
                "resource_field_offset": 0x18,
                "variation_palette_field_offset": 0x1C,
                "variation_index_field_offset": 0x20,
                "instances_field_offset": 0x24,
                "flag_byte_offsets": {
                    "bit0": 0x15,
                    "bit1": 0x16,
                    "bit2": 0x17,
                },
                "name_hash_field_offset": 0x28,
                "name_hash_field_size": 0x08,
                "source_mapping": {
                    "object_payload": (
                        "record +0x1c inline -> FUN_0069bc50"
                    ),
                    "resource": "record +0x0c + SGB base -> wrapper +0x18",
                    "variation_palette": (
                        "record +0x10 + SGB base -> wrapper +0x1c"
                    ),
                    "variation_index": "record +0x1a -> wrapper +0x20",
                    "instances": "record +0x14 -> wrapper +0x24",
                    "flags": "record +0x18 -> wrapper +0x15/+0x16/+0x17",
                    "name_hash": (
                        "record +0x08 + SGB base -> wrapper "
                        "+0x28/+0x2c via FUN_0064eba0"
                    ),
                },
            }
        else:
            row["runtime_wrapper"] = {
                **SUMM_RUNTIME_WRAPPER,
                "kind": "SUMM",
                "object_payload_inline_offset": 0x1C,
                "record_stride_source": "record +0x00",
            }

        rows.append(row)
        cursor = record_end

    if cursor != end:
        raise SGBRuntimeDecodeError(
            f"{wrapper_kind} records stop at 0x{cursor:x}, "
            f"expected chunk end 0x{end:x}"
        )
    return rows


def _parse_node(
    data: bytes,
    start: int,
    end: int,
    count: int,
    *,
    strict: bool,
) -> list[dict[str, Any]]:
    return _parse_wrapper_records(
        data,
        start,
        end,
        count,
        strict=strict,
        wrapper_kind="NODE",
    )


def _parse_part(def _parse_part(data: bytes, start: int, end: int, count: int) -> list[dict[str, Any]]:
    rows = []
    cursor = start + 12
    for index in range(count):
        # FUN_006a4d10 reads the fixed source header through piVar4[0xb],
        # so the minimum record is 0x30 bytes before the variable object list.
        if cursor + 48 > end:
            raise SGBRuntimeDecodeError(f"PART record {index} header exceeds chunk")

        partition_id = _i32(data, cursor)
        bbox_min = [
            _f32(data, cursor + 4),
            _f32(data, cursor + 8),
            _f32(data, cursor + 12),
        ]
        bbox_max = [
            _f32(data, cursor + 16),
            _f32(data, cursor + 20),
            _f32(data, cursor + 24),
        ]
        child_partition_ids = [
            _i32(data, cursor + 28 + 4 * i)
            for i in range(4)
        ]
        child_partition_table_present = child_partition_ids[0] != 0

        child_count = _u32(data, cursor + 44)
        child_base = cursor + 48
        if child_base + child_count * 4 > end:
            raise SGBRuntimeDecodeError(
                f"PART child table exceeds chunk at record {index}"
            )
        child_ids = [
            _i32(data, child_base + 4 * i)
            for i in range(child_count)
        ]
        child_lookup_indices_u32 = [
            (value - 1) & 0xFFFFFFFF for value in child_ids
        ]

        next_cursor = child_base + child_count * 4
        runtime_slots = [
            {
                "slot": slot,
                "source_partition_id": value,
                "runtime_field_offset": 0x1C + 4 * slot,
                "initial_state": (
                    "unresolved-partition-id"
                    if child_partition_table_present
                    else "empty"
                ),
                "mask_bit": slot,
                "insert_consumer": "FUN_00689a30",
                "resolved_state": "runtime-partition-node-pointer",
            }
            for slot, value in enumerate(child_partition_ids)
        ]

        rows.append({
            "index": index,
            "offset": cursor,
            "record_bytes_minimum": 48,
            "record_end": next_cursor,
            "partition_id": partition_id,
            "aabbox_min": bbox_min,
            "aabbox_max": bbox_max,
            "child_partition_ids": child_partition_ids,
            "child_partition_table_present": child_partition_table_present,
            "child_object_count": child_count,
            "child_object_indices": child_ids,
            "child_object_lookup_indices_u32": child_lookup_indices_u32,
            "child_object_lookup_transform": "(source_id - 1) & 0xffffffff",
            "runtime_partition_tree": {
                **PART_RUNTIME_TREE,
                "root_record": index == 0,
                "root_creation": (
                    "FUN_0068a360 -> FUN_00688ef0"
                    if index == 0
                    else None
                ),
                "subsequent_insertion": (
                    None
                    if index == 0
                    else "FUN_0068a360 -> FUN_00689a30"
                ),
                "aabbox_copy": {
                    "min": {
                        "source_offset": 0x04,
                        "runtime_offset": 0x04,
                        "value": bbox_min,
                    },
                    "max": {
                        "source_offset": 0x10,
                        "runtime_offset": 0x10,
                        "value": bbox_max,
                    },
                },
                "child_partition_slots": runtime_slots,
                "child_partition_mask_initial": (
                    0x0F if child_partition_table_present else 0
                ),
                "child_partition_resolution": (
                    "FUN_00689a30 matches partition_id against a masked "
                    "slot, replaces the source id with a child-node pointer, "
                    "then clears that slot's mask bit"
                ),
                "child_object_resolution": {
                    "reference_transform": "source_id - 1",
                    "lookup_argument_type": "uint32",
                    "lookup": "FUN_006885b0(scene_wrapper_list, id - 1)",
                    "resolved_wrapper_partition_bounds_write_offset": 0x30,
                    "partition_bounds_target": (
                        "runtime partition node +0x04"
                    ),
                    "virtual_kind_dispatch": {
                        "vfunc_offset": 0x04,
                        "observed_raw_codes": [1, 3, 4],
                        "code_1_root_behavior": (
                            "release payload through its vtable"
                        ),
                        "code_3_behavior": (
                            "append wrapper to manager +0x58"
                        ),
                        "code_4_behavior": (
                            "append wrapper to partition node +0x34"
                        ),
                    },
                },
            },
        })
        cursor = next_cursor
    return rows


def _parse_summ(
    data: bytes,
    start: int,
    end: int,
    count: int,
    *,
    strict: bool,
) -> list[dict[str, Any]]:
    return _parse_wrapper_records(
        data,
        start,
        end,
        count,
        strict=strict,
        wrapper_kind="SUMM",
    )


def _parse_occl(def _parse_occl(
    data: bytes,
    start: int,
    end: int,
    count: int,
    *,
    batched: bool,
) -> list[dict[str, Any]]:
    rows = []
    cursor = start + 12
    names = ("position_tl", "position_tr", "position_bl", "position_br")
    for index in range(count):
        if cursor + 56 > end:
            raise SGBRuntimeDecodeError(f"OCCL record {index} exceeds chunk")

        name_rel = _i32(data, cursor)
        resource_rel = _i32(data, cursor + 4)
        vectors = {
            name: [
                _f32(data, cursor + 8 + 12 * n),
                _f32(data, cursor + 12 + 12 * n),
                _f32(data, cursor + 16 + 12 * n),
            ]
            for n, name in enumerate(names)
        }
        runtime_vectors = {
            name: [*value, 1.0]
            for name, value in vectors.items()
        }

        rows.append({
            "index": index,
            "offset": cursor,
            "record_bytes": 56,
            "raw_u32": [_u32(data, cursor + 4 * i) for i in range(14)],
            "name": _resolve_string(data, 0, name_rel),
            "resource": _resolve_string(data, 0, resource_rel),
            **vectors,
            "runtime_object": {
                **OCCL_RUNTIME_OBJECT,
                "vector_copy": runtime_vectors,
                "name_source": "record +0x00 -> object +0x60 via FUN_00631740/FUN_008244e0",
                "resource_source": "record +0x04 -> object +0x60 via FUN_008246a0",
                "secondary_matrix_source": "DAT_00b88a40 -> object +0xd0 via FUN_00401d10/FUN_006b43d0",
            },
            "runtime_admission": {
                "header_flag_bit1": batched,
                "mode": (
                    "batched-object-registration"
                    if batched
                    else "per-record-wrapper"
                ),
                "wrapper": (
                    None
                    if batched
                    else dict(OCCL_RUNTIME_WRAPPER)
                ),
                "batch_sink": (
                    "FUN_004f5e60 -> FUN_0068b5a0"
                    if batched
                    else None
                ),
            },
        })
        cursor += 56
    return rows



def parse_sgb_runtime(data: bytes, *, strict: bool = True) -> dict[str, Any]:
    if len(data) < 16 or data[:4] != MAGIC:
        raise SGBRuntimeDecodeError("not a SHIFT SGB resource")

    flags = _u32(data, 8)
    header = {
        "magic": MAGIC.decode("latin-1"),
        "magic_hex": data[:4].hex(),
        "word_1": _u32(data, 4),
        "flags_word": flags,
        "word_3": _u32(data, 12),
        "flag_bits": {
            "bit0": bool(flags & 1),
            "bit1": bool(flags & 2),
            "bit2": bool(flags & 4),
        },
        "runtime_source": "FUN_006a5270",
    }

    chunks = []
    blockers = []
    cursor = 16
    while cursor + 8 <= len(data):
        tag = _tag(data[cursor:cursor + 4])
        size = _u32(data, cursor + 4)
        if size < 8:
            blockers.append(f"chunk-size-invalid:{tag}:{size}")
            break
        chunk_end = cursor + size
        if chunk_end > len(data):
            blockers.append(f"chunk-truncated:{tag}:0x{cursor:x}")
            break

        row = {
            "tag": tag,
            "offset": cursor,
            "size": size,
            "payload_size": size - 8,
            "header_hex": data[cursor:cursor + 8].hex(),
            "payload_sha256": hashlib.sha256(data[cursor + 8:chunk_end]).hexdigest(),
            "recognized_by_runtime": tag in KNOWN_TAGS,
            "decode_status": "decoded",
        }
        try:
            if tag in {"NODE", "PART", "SUMM", "OCCL"}:
                if size < 12:
                    raise SGBRuntimeDecodeError(f"{tag} has no record-count word")
                count = _u32(data, cursor + 8)
                row["record_count"] = count
            if tag == "NODE":
                row["records"] = _parse_node(
                    data,
                    cursor,
                    chunk_end,
                    count,
                    relative_base=0,
                    strict=strict,
                )
                row["decoder"] = "FUN_006a4b40 -> FUN_0069bc50"
                row["object_payload_layout"] = (
                    "inline at NODE record +0x1c; internal offsets "
                    "are relative to SGB base"
                )
            elif tag == "PART":
                row["records"] = _parse_part(data, cursor, chunk_end, count)
                row["decoder"] = "FUN_006a4d10"
            elif tag == "SUMM":
                row["records"] = _parse_summ(
                    data,
                    cursor,
                    chunk_end,
                    count,
                    strict=strict,
                )
                row["decoder"] = "FUN_006a4900 -> FUN_0069bc50"
            elif tag == "OCCL":
                row["records"] = _parse_occl(
                    data,
                    cursor,
                    chunk_end,
                    count,
                    batched=bool(flags & 2),
                )
                row["decoder"] = "FUN_006a4f10"
            elif tag == "FLAT":
                body = data[cursor + 12:chunk_end] if size >= 12 else b""
                row["record_count_word"] = _u32(data, cursor + 8) if size >= 12 else None
                row["raw_body_sha256"] = hashlib.sha256(body).hexdigest()
                row["raw_body_hex_prefix"] = body[:96].hex()
                row["decoder"] = "FUN_006a48d0 -> FUN_0068a8b0"
                from flat_runtime import parse_flat_runtime
                normalize_signed_terminal_spans = not bool(flags & 4)
                flat = parse_flat_runtime(
                    body,
                    strict=strict,
                    normalize_signed_terminal_spans=(
                        normalize_signed_terminal_spans
                    ),
                )
                row["flat_span_normalization"] = {
                    "header_flag_bit2": bool(flags & 4),
                    "normalize_signed_terminal_spans": (
                        normalize_signed_terminal_spans
                    ),
                    "source": (
                        "FUN_006a5270 bit2 -> FUN_006a48d0 param_3 -> "
                        "FUN_006afd30/FUN_006af6c0"
                    ),
                }
                row["flat_runtime"] = flat
                row["decoded"] = flat["ready"]
            elif tag == "END ":
                row["decoder"] = "FUN_006a5270"
        except SGBRuntimeDecodeError as exc:
            row["decode_status"] = "blocked"
            row["decode_error"] = str(exc)
            blockers.append(f"{tag}:decode:{exc}")
            if strict:
                raise

        chunks.append(row)
        cursor = chunk_end
        if tag == "END ":
            break

    # Retail SGB resources keep referenced strings and NODE subobject data
    # after the END chunk. FUN_006a5270 stops chunk dispatch at END but all
    # relative offsets continue to use the complete SGB base.
    post_end_reference = data[cursor:]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": not blockers,
        "status": "decoded" if not blockers else "decoded-with-blockers",
        "header": header,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "container_end": cursor,
        "chunk_stream_end": cursor,
        "trailing_bytes": 0,
        "trailing_hex_prefix": "",
        "post_end_reference_bytes": len(post_end_reference),
        "post_end_reference_sha256": (
            hashlib.sha256(post_end_reference).hexdigest()
            if post_end_reference else None
        ),
        "blockers": blockers,
        "evidence": {
            "entry": "FUN_006a5270",
            "NODE": "FUN_006a4b40",
            "FLAT": "FUN_006a48d0",
            "PART": "FUN_006a4d10",
            "SUMM": "FUN_006a4900",
            "OCCL": "FUN_006a4f10",
        },
        "limitations": [
            "NODE object payload is inline at record +0x1c and decoded against the complete SGB-relative reference arena; byte +0x21 and DAMAGE-specific payload fields remain unresolved.",
            "FLAT signed terminal spans are normalized exactly when SGB header bit2 is clear, matching FUN_006a5270 -> FUN_006a48d0 -> FUN_006af6c0.",
            "SUMM vectors remain positional; their semantic names are not proven by FUN_006a4900.",
            "OCCL Name/Resource and PositionTL/TR/BL/BR semantics are source-backed by the matching XML constructor FUN_006a3c40 and binary loader FUN_006a4f10.",
            "PART AABB, child-partition IDs and one-based child-object references are source-backed through FUN_006a4d10, FUN_0068a360 and FUN_00689a30; child virtual kind codes remain numeric rather than class-named.",
            "SUMM runtime wrapper field copies are source-backed; the 64-bit name hash is retained as provenance-only until FUN_0040b831 is normalized.",
        ],
    }
