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


def _resolve_string(data: bytes, chunk_start: int, chunk_end: int, relative: int) -> dict[str, Any]:
    absolute = chunk_start + relative
    text = None
    if relative and chunk_start <= absolute < chunk_end:
        end = data.find(b"\0", absolute, chunk_end)
        if end >= 0:
            text = data[absolute:end].decode("utf-8", "replace")
    return {
        "relative_offset": relative,
        "absolute_offset": absolute if text is not None else None,
        "text": text,
    }


def _tag(raw: bytes) -> str:
    return raw[::-1].decode("ascii", "replace")


def _parse_node(data: bytes, start: int, end: int, count: int) -> list[dict[str, Any]]:
    rows = []
    cursor = start + 12
    for index in range(count):
        if cursor + 32 > end:
            raise SGBRuntimeDecodeError(f"NODE record {index} header exceeds chunk")
        words = [_u32(data, cursor + 4 * i) for i in range(8)]
        flags = data[cursor + 24]
        variation = struct.unpack_from("<h", data, cursor + 26)[0]
        object_rel = _i32(data, cursor + 28)
        rows.append({
            "index": index,
            "offset": cursor,
            "stride": words[0],
            "raw_u32_header": words,
            "unknown_word_1": words[1],
            "name": _resolve_string(data, start, end, _i32(data, cursor + 8)),
            "resource": _resolve_string(data, start, end, _i32(data, cursor + 12)),
            "variation_palette_file": _resolve_string(data, start, end, _i32(data, cursor + 16)),
            "instances": words[5],
            "flags": {
                "raw": flags,
                "present": bool(flags & 1),
                "animated": bool(flags & 2),
                "dynamic": bool(flags & 4),
            },
            "variation_index": variation,
            "object_payload": {
                "relative_offset": object_rel,
                "absolute_offset": start + object_rel if object_rel else None,
                "decoder": "FUN_0069bc50",
                "decoded": False,
            },
        })
        stride = words[0]
        if stride < 32 or cursor + stride > end or cursor + stride <= cursor:
            if index + 1 < count:
                raise SGBRuntimeDecodeError(f"invalid NODE stride {stride} at record {index}")
        cursor += stride
    return rows


def _parse_part(data: bytes, start: int, end: int, count: int) -> list[dict[str, Any]]:
    rows = []
    cursor = start + 12
    for index in range(count):
        if cursor + 48 > end:
            raise SGBRuntimeDecodeError(f"PART record {index} header exceeds chunk")
        partition_id = _i32(data, cursor)
        bbox_min = [_f32(data, cursor + 4), _f32(data, cursor + 8), _f32(data, cursor + 12)]
        bbox_max = [_f32(data, cursor + 16), _f32(data, cursor + 20), _f32(data, cursor + 24)]
        fixed_flag = _u32(data, cursor + 28)
        fixed_quad = [_i32(data, cursor + 28 + 4 * i) for i in range(4)]
        child_count = _u32(data, cursor + 44)
        child_base = cursor + 48
        if child_base + child_count * 4 > end:
            raise SGBRuntimeDecodeError(f"PART child table exceeds chunk at record {index}")
        child_ids = [_i32(data, child_base + 4 * i) for i in range(child_count)]
        next_cursor = child_base + child_count * 4
        rows.append({
            "index": index,
            "offset": cursor,
            "partition_id": partition_id,
            "aabbox_min": bbox_min,
            "aabbox_max": bbox_max,
            "fixed_quad": fixed_quad,
            "fixed_quad_first_word": fixed_flag,
            "child_object_count": child_count,
            "child_object_indices": child_ids,
            "record_end": next_cursor,
        })
        cursor = next_cursor
    return rows


def _parse_fixed14(data: bytes, start: int, end: int, count: int, kind: str) -> list[dict[str, Any]]:
    rows = []
    cursor = start + 12
    for index in range(count):
        if cursor + 56 > end:
            raise SGBRuntimeDecodeError(f"{kind} record {index} exceeds chunk")
        a = _i32(data, cursor)
        b = _i32(data, cursor + 4)
        vectors = [
            [_f32(data, cursor + 8 + 12 * n), _f32(data, cursor + 12 + 12 * n), _f32(data, cursor + 16 + 12 * n)]
            for n in range(4)
        ]
        rows.append({
            "index": index,
            "offset": cursor,
            "raw_u32": [_u32(data, cursor + 4 * i) for i in range(14)],
            "string_a": _resolve_string(data, start, end, a),
            "string_b": _resolve_string(data, start, end, b),
            "vectors": vectors,
            "record_bytes": 56,
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
                row["records"] = _parse_node(data, cursor, chunk_end, count)
                row["decoder"] = "FUN_006a4b40"
            elif tag == "PART":
                row["records"] = _parse_part(data, cursor, chunk_end, count)
                row["decoder"] = "FUN_006a4d10"
            elif tag in {"SUMM", "OCCL"}:
                row["records"] = _parse_fixed14(data, cursor, chunk_end, count, tag)
                row["decoder"] = "FUN_006a4900" if tag == "SUMM" else "FUN_006a4f10"
            elif tag == "FLAT":
                body = data[cursor + 12:chunk_end] if size >= 12 else b""
                row["record_count_word"] = _u32(data, cursor + 8) if size >= 12 else None
                row["raw_body_sha256"] = hashlib.sha256(body).hexdigest()
                row["raw_body_hex_prefix"] = body[:96].hex()
                row["decoder"] = "FUN_006a48d0 -> FUN_0068a8b0"
                row["decoded"] = False
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

    trailing = data[cursor:]
    if trailing:
        blockers.append("sgb:trailing-bytes")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": not blockers,
        "status": "decoded" if not blockers else "decoded-with-blockers",
        "header": header,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "container_end": cursor,
        "trailing_bytes": len(trailing),
        "trailing_hex_prefix": trailing[:96].hex(),
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
            "NODE object payload is preserved because FUN_0069bc50/FUN_0069a6c0 has not yet been normalized into this IR.",
            "FLAT body is preserved because it is forwarded to FUN_0068a8b0.",
            "SUMM/OCCL vectors remain positional; their semantic names are not proven by these handlers.",
        ],
    }
