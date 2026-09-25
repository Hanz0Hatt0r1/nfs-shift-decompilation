"""Evidence-backed reconstruction of the SHIFT BAB animation runtime payload.

The parser follows recovered routines in SHIFT.exe.c:
FUN_00680690, FUN_00683b10/FUN_00683e20/FUN_00684180, FUN_00684320,
and the channel samplers/interpolators used by them.

Only semantics established by those routines are exposed. Unknown higher-level
pose composition remains explicit rather than guessed.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import Any

FORMAT = "SHIFT.BABAnimationRuntime/1"

class BABAnimationDecodeError(ValueError):
    pass

@dataclass
class _Cursor:
    data: bytes
    offset: int = 0

    def need(self, size: int) -> None:
        if size < 0 or self.offset + size > len(self.data):
            raise BABAnimationDecodeError(
                f"animation payload truncated at 0x{self.offset:x}, need {size} bytes"
            )

    def u8(self) -> int:
        self.need(1)
        value = self.data[self.offset]
        self.offset += 1
        return value

    def u32(self) -> int:
        self.need(4)
        value = struct.unpack_from("<I", self.data, self.offset)[0]
        self.offset += 4
        return value

    def f32(self) -> float:
        self.need(4)
        value = struct.unpack_from("<f", self.data, self.offset)[0]
        self.offset += 4
        return value

    def f32x3(self) -> tuple[float, float, float]:
        return self.f32(), self.f32(), self.f32()

    def f32x4(self) -> tuple[float, float, float, float]:
        return self.f32(), self.f32(), self.f32(), self.f32()

    def string(self) -> dict[str, Any]:
        start = self.offset
        length = self.u32()
        self.need(length)
        raw = self.data[self.offset:self.offset + length]
        self.offset += length
        aligned = (length + 3) & ~3
        self.need(aligned - length)
        self.offset += aligned - length
        return {
            "offset": start,
            "length": length,
            "text": raw.decode("utf-8", "replace"),
            "raw_hex": raw.hex(),
            "aligned_size": aligned,
        }

def _word_float(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value))[0]

def _hex(value: int) -> str:
    return f"0x{value:08x}"

CHANNEL_SPECS: dict[int, dict[str, Any]] = {
    0: {"name": "uniform_vec3", "storage": "frame_sequence", "interpolation": "linear", "element": "vec3"},
    1: {"name": "uniform_quaternion", "storage": "frame_sequence", "interpolation": "quaternion_slerp", "element": "quat_xyzw"},
    2: {"name": "timed_vec3", "storage": "keyframes", "interpolation": "linear", "element": "vec3"},
    3: {"name": "timed_vec4", "storage": "keyframes", "interpolation": "linear", "element": "vec4"},
    4: {"name": "constant_vec3", "storage": "constant", "interpolation": "constant", "element": "vec3"},
    5: {"name": "constant_vec4", "storage": "constant", "interpolation": "constant", "element": "vec4"},
    6: {
        "name": "constant_euler3",
        "storage": "constant",
        "interpolation": "euler_to_quaternion",
        "element": "euler3",
        "semantic_status": "conversion formula reconstructed; axis/order convention unresolved",
    },
    7: {"name": "uniform_scalar", "storage": "frame_sequence", "interpolation": "linear", "element": "scalar"},
    8: {"name": "timed_scalar", "storage": "keyframes", "interpolation": "linear", "element": "scalar"},
    9: {"name": "constant_u32", "storage": "constant", "interpolation": "constant", "element": "u32"},
}

def _read_base_record(cur: _Cursor) -> dict[str, Any]:
    start = cur.offset
    field0 = cur.u32()
    name = cur.string()
    vec4 = tuple(cur.u32() for _ in range(4))
    field7 = cur.u32()
    vec3 = tuple(cur.u32() for _ in range(3))
    return {
        "offset": start,
        "field0": field0,
        "name": name,
        "vec4_raw_u32": list(vec4),
        "field7": field7,
        "vec3_raw_u32": list(vec3),
        "bytes": cur.offset - start,
    }

def _read_common_bank(cur: _Cursor, mode: int) -> dict[str, Any]:
    start = cur.offset
    flags = cur.u32()
    record_count = cur.u32()
    resource_or_bank_id = cur.u32()
    base_record_count = cur.u32()
    base_records = [_read_base_record(cur) for _ in range(base_record_count)]
    vector3 = tuple(cur.u32() for _ in range(3))
    field30 = cur.u32()
    name = cur.string()
    return {
        "offset": start,
        "mode": mode,
        "flags": flags,
        "flags_hex": _hex(flags),
        "record_count": record_count,
        "resource_or_bank_id": resource_or_bank_id,
        "base_record_count": base_record_count,
        "base_records": base_records,
        "vector3_raw_u32": list(vector3),
        "field30": field30,
        "name": name,
        "bytes": cur.offset - start,
    }

def _channel_metadata(cur: _Cursor, kind: int, count: int) -> dict[str, Any]:
    start = cur.offset
    subtype_or_flags = cur.u32()
    name = cur.string()
    metadata_u32 = cur.u32()
    return {
        "offset": start,
        "subtype_or_flags": subtype_or_flags,
        "subtype_or_flags_hex": _hex(subtype_or_flags),
        "name": name,
        "metadata_u32": metadata_u32,
        "count": count,
        "kind": kind,
        "bytes": cur.offset - start,
    }

def _channel_payload(cur: _Cursor, kind: int, count: int) -> dict[str, Any]:
    if kind == 0:
        return {"values": [list(cur.f32x3()) for _ in range(count)], "serialization_bytes_per_item": 12}
    if kind == 1:
        return {"values": [list(cur.f32x4()) for _ in range(count)], "serialization_bytes_per_item": 16}
    if kind == 2:
        keys = []
        for _ in range(count):
            raw = cur.u32()
            keys.append({"time": _word_float(raw), "time_raw_u32": raw, "value": list(cur.f32x3())})
        return {"keys": keys, "serialization_bytes_per_item": 16}
    if kind == 3:
        keys = []
        for _ in range(count):
            raw = cur.u32()
            keys.append({
                "time": _word_float(raw),
                "time_raw_u32": raw,
                "value": list(cur.f32x4()),
                "runtime_padding_u32": 0,
            })
        return {"keys": keys, "serialization_bytes_per_item": 20, "runtime_storage_bytes_per_item": 24}
    if kind == 4:
        return {"value": list(cur.f32x3()), "serialization_bytes_per_item": 12}
    if kind == 5:
        return {"value": list(cur.f32x4()), "serialization_bytes_per_item": 16}
    if kind == 6:
        return {
            "value": list(cur.f32x3()),
            "serialization_bytes_per_item": 12,
            "runtime_conversion": "FUN_004d8c10",
            "conversion": "euler3_to_quaternion",
            "conversion_status": "formula-reconstructed-axis-order-unresolved",
        }
    if kind == 7:
        return {"values": [cur.f32() for _ in range(count)], "serialization_bytes_per_item": 4}
    if kind == 8:
        keys = []
        for _ in range(count):
            time_raw = cur.u32()
            value_raw = cur.u32()
            keys.append({
                "time": _word_float(time_raw),
                "time_raw_u32": time_raw,
                "value": _word_float(value_raw),
                "value_raw_u32": value_raw,
            })
        return {"keys": keys, "serialization_bytes_per_item": 8}
    if kind == 9:
        return {"value_raw_u32": cur.u32(), "serialization_bytes_per_item": 4}
    raise BABAnimationDecodeError(f"unsupported BAB animation channel type {kind}")

def parse_animation_channel(cur: _Cursor) -> dict[str, Any]:
    start = cur.offset
    kind = cur.u32()
    count = cur.u32()
    metadata = _channel_metadata(cur, kind, count)
    payload_offset = cur.offset
    payload = _channel_payload(cur, kind, count)
    return {
        "format": "SHIFT.BABAnimationChannel/1",
        "offset": start,
        "kind": kind,
        "count": count,
        "spec": dict(CHANNEL_SPECS.get(kind, {"name": "unknown"})),
        "metadata": metadata,
        "payload": payload,
        "payload_offset": payload_offset,
        "bytes": cur.offset - start,
    }

def _optional_channel(cur: _Cursor) -> dict[str, Any] | None:
    present = cur.u8()
    if present == 0:
        return None
    if present != 1:
        raise BABAnimationDecodeError(f"invalid animation channel presence byte {present}")
    return parse_animation_channel(cur)

def _parse_mode0(cur: _Cursor, bone_count: int) -> dict[str, Any]:
    return {
        "mode": 0,
        "arrays": [
            {"name": name, "channels": [_optional_channel(cur) for _ in range(bone_count)]}
            for name in ("translation", "rotation", "scale")
        ],
    }

def _parse_mode1(cur: _Cursor, bone_count: int) -> dict[str, Any]:
    raw = cur.u32()
    return {
        "mode": 1,
        "frame_quantum": _word_float(raw),
        "frame_quantum_raw_u32": raw,
        "frame_count": cur.u32(),
        "root_or_primary": _optional_channel(cur),
        "per_bone": [_optional_channel(cur) for _ in range(bone_count)],
    }

def _parse_mode2(cur: _Cursor, bone_count: int) -> dict[str, Any]:
    return {"mode": 2, "channels": [_optional_channel(cur) for _ in range(bone_count)]}

def parse_bab_animation_payload(data: bytes, *, mode: int, strict: bool = True) -> dict[str, Any]:
    """Decode a BAB animation-bank payload from its animation payload boundary."""
    if mode not in (0, 1, 2):
        raise ValueError("BAB animation runtime mode must be 0, 1 or 2")
    cur = _Cursor(data)
    try:
        common = _read_common_bank(cur, mode)
        bone_count = common["record_count"]
        body = {0: _parse_mode0, 1: _parse_mode1, 2: _parse_mode2}[mode](cur, bone_count)
        trailing = data[cur.offset:]
        status = "decoded" if not trailing else "decoded-with-trailing-bytes"
        blockers = [] if not trailing else ["bab-animation:unconsumed-tail"]
        return {
            "format": FORMAT,
            "version": 1,
            "mode": mode,
            "ready": True,
            "status": status,
            "common": common,
            "body": body,
            "consumed_bytes": cur.offset,
            "trailing_bytes": len(trailing),
            "trailing_hex_prefix": trailing[:64].hex(),
            "blockers": blockers,
            "evidence": {
                "runtime_functions": [
                    "FUN_00680690", "FUN_00683b10", "FUN_00683e20",
                    "FUN_00684180", "FUN_00684320", "FUN_00684a60",
                    "FUN_00684c50", "FUN_00684660", "FUN_00684860",
                    "FUN_00446150",
                ],
                "source_rule": "derived from decompiled SHIFT.exe.c; unknown higher-level semantics remain explicit",
            },
        }
    except BABAnimationDecodeError as exc:
        if strict:
            raise
        return {
            "format": FORMAT,
            "version": 1,
            "mode": mode,
            "ready": False,
            "status": "blocked",
            "consumed_bytes": cur.offset,
            "trailing_bytes": len(data) - cur.offset,
            "blockers": [f"bab-animation:decode:{exc}"],
            "evidence": {"runtime_functions": ["FUN_00680690", "FUN_00684320"]},
        }

def channel_sample_policy(kind: int) -> dict[str, Any]:
    try:
        spec = CHANNEL_SPECS[kind]
    except KeyError as exc:
        raise ValueError(f"unknown BAB animation channel type {kind}") from exc
    return {
        "format": "SHIFT.BABAnimationSamplePolicy/1",
        "kind": kind,
        "name": spec["name"],
        "storage": spec["storage"],
        "interpolation": spec["interpolation"],
        "semantic_status": spec.get("semantic_status", "proven-at-sampler-level"),
    }
