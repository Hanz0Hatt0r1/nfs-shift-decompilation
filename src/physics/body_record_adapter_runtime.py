"""Reference codec for the source-backed 0x170-byte retail BODY record.

This module freezes only the byte layout consumed/written by the proven
FUN_007bab70 integration primitive.  It does not implement FUN_007afdd0 and does
not claim whole-frame scheduler parity.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Sequence

FORMAT = "SHIFT.NativeBodyRecordAdapter/1"
BODY_RECORD_SIZE = 0x170

ORIGIN = (0x00, 0x08, 0x10)
CROSS_VECTOR = (0x18, 0x20, 0x28)
PREPARED_VECTOR = (0x30, 0x38, 0x40)
ACCUMULATOR_A = (0x48, 0x50, 0x58)
ACCUMULATOR_B = (0x60, 0x68, 0x70)
MOTION_TRIPLET = (0x78, 0x80, 0x88)
SCALAR_0X90 = 0x90
SYMMETRIC_TENSOR = (
    0xB0, 0xB4, 0xB8,
    0xBC, 0xC0, 0xC4,
    0xC8, 0xCC, 0xD0,
)
BASIS = (
    0xD4, 0xD8, 0xDC,
    0xE0, 0xE4, 0xE8,
    0xEC, 0xF0, 0xF4,
)
RECIPROCAL_COEFFICIENTS = (0x138, 0x140, 0x148)


@dataclass(frozen=True)
class BodyRecordInputs:
    origin: tuple[float, float, float]
    cross_vector: tuple[float, float, float]
    prepared_vector: tuple[float, float, float]
    accumulator_a: tuple[float, float, float]
    accumulator_b: tuple[float, float, float]
    motion_triplet: tuple[float, float, float]
    scalar_0x90: float
    basis: tuple[float, ...]
    reciprocal_coefficients: tuple[float, float, float]


@dataclass(frozen=True)
class BodyRecordWriterPayload:
    origin: tuple[float, float, float]
    cross_vector: tuple[float, float, float]
    prepared_vector: tuple[float, float, float]
    motion_triplet: tuple[float, float, float]
    symmetric_tensor: tuple[float, ...]
    basis: tuple[float, ...]


def _require_record(record: bytes | bytearray) -> None:
    if len(record) != BODY_RECORD_SIZE:
        raise ValueError(
            f"BODY record must be exactly {BODY_RECORD_SIZE} bytes, got {len(record)}"
        )


def _finite(values: Sequence[float], label: str, expected: int) -> tuple[float, ...]:
    if len(values) != expected:
        raise ValueError(f"{label} must contain exactly {expected} values")
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{label} contains non-finite value")
    return result


def _read_f64s(record: bytes | bytearray, offsets: Sequence[int]) -> tuple[float, ...]:
    return tuple(struct.unpack_from("<d", record, offset)[0] for offset in offsets)


def _read_f32s(record: bytes | bytearray, offsets: Sequence[int]) -> tuple[float, ...]:
    return tuple(struct.unpack_from("<f", record, offset)[0] for offset in offsets)


def decode_fun_007bab70_body_record(record: bytes | bytearray) -> BodyRecordInputs:
    _require_record(record)
    result = BodyRecordInputs(
        origin=_read_f64s(record, ORIGIN),
        cross_vector=_read_f64s(record, CROSS_VECTOR),
        prepared_vector=_read_f64s(record, PREPARED_VECTOR),
        accumulator_a=_read_f64s(record, ACCUMULATOR_A),
        accumulator_b=_read_f64s(record, ACCUMULATOR_B),
        motion_triplet=_read_f64s(record, MOTION_TRIPLET),
        scalar_0x90=struct.unpack_from("<d", record, SCALAR_0X90)[0],
        basis=_read_f32s(record, BASIS),
        reciprocal_coefficients=_read_f64s(record, RECIPROCAL_COEFFICIENTS),
    )
    for label, values in (
        ("origin", result.origin),
        ("cross_vector", result.cross_vector),
        ("prepared_vector", result.prepared_vector),
        ("accumulator_a", result.accumulator_a),
        ("accumulator_b", result.accumulator_b),
        ("motion_triplet", result.motion_triplet),
        ("basis", result.basis),
        ("reciprocal_coefficients", result.reciprocal_coefficients),
    ):
        _finite(values, label, len(values))
    _finite((result.scalar_0x90,), "scalar_0x90", 1)
    return result


def apply_fun_007bab70_writer_payload(
    original: bytes | bytearray,
    payload: BodyRecordWriterPayload,
) -> bytes:
    _require_record(original)
    origin = _finite(payload.origin, "origin", 3)
    cross = _finite(payload.cross_vector, "cross_vector", 3)
    prepared = _finite(payload.prepared_vector, "prepared_vector", 3)
    motion = _finite(payload.motion_triplet, "motion_triplet", 3)
    tensor = _finite(payload.symmetric_tensor, "symmetric_tensor", 9)
    basis = _finite(payload.basis, "basis", 9)

    record = bytearray(original)
    for offsets, values in (
        (ORIGIN, origin),
        (CROSS_VECTOR, cross),
        (PREPARED_VECTOR, prepared),
        (MOTION_TRIPLET, motion),
    ):
        for offset, value in zip(offsets, values):
            struct.pack_into("<d", record, offset, value)
    for offsets, values in ((SYMMETRIC_TENSOR, tensor), (BASIS, basis)):
        for offset, value in zip(offsets, values):
            struct.pack_into("<f", record, offset, value)
    return bytes(record)


def apply_fun_007b2270_body_buffer_payloads(
    body_bytes: bytes | bytearray,
    payloads: Sequence[BodyRecordWriterPayload],
) -> bytes:
    expected = len(payloads) * BODY_RECORD_SIZE
    if len(body_bytes) != expected:
        raise ValueError(
            f"BODY buffer size/count mismatch: expected {expected}, got {len(body_bytes)}"
        )
    output = bytearray(body_bytes)
    for index, payload in enumerate(payloads):
        base = index * BODY_RECORD_SIZE
        output[base : base + BODY_RECORD_SIZE] = apply_fun_007bab70_writer_payload(
            output[base : base + BODY_RECORD_SIZE], payload
        )
    return bytes(output)


def writer_byte_indices() -> frozenset[int]:
    indices: set[int] = set()
    for offsets, width in (
        (ORIGIN, 8),
        (CROSS_VECTOR, 8),
        (PREPARED_VECTOR, 8),
        (MOTION_TRIPLET, 8),
        (SYMMETRIC_TENSOR, 4),
        (BASIS, 4),
    ):
        for offset in offsets:
            indices.update(range(offset, offset + width))
    return frozenset(indices)


def build_body_record_adapter_contract() -> dict:
    return {
        "format": FORMAT,
        "body_record_size": BODY_RECORD_SIZE,
        "body_array_function": "FUN_007b2270",
        "body_integrator_function": "FUN_007bab70",
        "f64_input_offsets": {
            "origin": ORIGIN,
            "cross_vector": CROSS_VECTOR,
            "prepared_vector": PREPARED_VECTOR,
            "accumulator_a": ACCUMULATOR_A,
            "accumulator_b": ACCUMULATOR_B,
            "motion_triplet": MOTION_TRIPLET,
            "scalar_0x90": (SCALAR_0X90,),
            "reciprocal_coefficients": RECIPROCAL_COEFFICIENTS,
        },
        "f32_input_offsets": {"basis": BASIS},
        "f32_writer_offsets": {
            "symmetric_tensor": SYMMETRIC_TENSOR,
            "basis": BASIS,
        },
        "unrelated_bytes_preserved": True,
        "basis_rotation_arithmetic_external": True,
        "render_frame_scheduler_proven": False,
    }
