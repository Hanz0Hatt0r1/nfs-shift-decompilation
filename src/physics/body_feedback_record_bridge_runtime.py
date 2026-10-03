"""Reference codec for BODY accumulator feedback in raw 0x170-byte records.

This freezes only the source-backed accumulator A/B storage boundary used by the
native solver/post-solve feedback chain. It deliberately does not schedule the
BODY pose integrator or claim whole-frame scheduler parity.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Sequence

FORMAT = "SHIFT.NativeBodyFeedbackRecordBridge/1"
BODY_RECORD_SIZE = 0x170
ACCUMULATOR_A = (0x48, 0x50, 0x58)
ACCUMULATOR_B = (0x60, 0x68, 0x70)


@dataclass(frozen=True)
class BodyAccumulatorRecordState:
    angular: tuple[float, float, float]
    linear: tuple[float, float, float]


def _finite3(values: Sequence[float], label: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{label} must contain exactly 3 values")
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{label} contains non-finite value")
    return result  # type: ignore[return-value]


def _require_shape(body_bytes: bytes | bytearray, body_count: int) -> None:
    if isinstance(body_count, bool) or not isinstance(body_count, int) or body_count < 0:
        raise ValueError("BODY count must be a non-negative integer")
    expected = body_count * BODY_RECORD_SIZE
    if len(body_bytes) != expected:
        raise ValueError(
            f"BODY feedback buffer size/count mismatch: expected {expected}, got {len(body_bytes)}"
        )


def decode_body_accumulators_from_buffer(
    body_bytes: bytes | bytearray,
    body_count: int,
) -> tuple[BodyAccumulatorRecordState, ...]:
    _require_shape(body_bytes, body_count)
    result: list[BodyAccumulatorRecordState] = []
    for index in range(body_count):
        base = index * BODY_RECORD_SIZE
        angular = tuple(
            struct.unpack_from("<d", body_bytes, base + offset)[0]
            for offset in ACCUMULATOR_A
        )
        linear = tuple(
            struct.unpack_from("<d", body_bytes, base + offset)[0]
            for offset in ACCUMULATOR_B
        )
        result.append(
            BodyAccumulatorRecordState(
                angular=_finite3(angular, f"BODY[{index}] accumulator A"),
                linear=_finite3(linear, f"BODY[{index}] accumulator B"),
            )
        )
    return tuple(result)


def apply_body_accumulators_to_buffer(
    body_bytes: bytes | bytearray,
    bodies: Sequence[BodyAccumulatorRecordState],
) -> bytes:
    _require_shape(body_bytes, len(bodies))
    output = bytearray(body_bytes)
    for index, body in enumerate(bodies):
        angular = _finite3(body.angular, f"BODY[{index}] accumulator A")
        linear = _finite3(body.linear, f"BODY[{index}] accumulator B")
        base = index * BODY_RECORD_SIZE
        for offset, value in zip(ACCUMULATOR_A, angular):
            struct.pack_into("<d", output, base + offset, value)
        for offset, value in zip(ACCUMULATOR_B, linear):
            struct.pack_into("<d", output, base + offset, value)
    return bytes(output)


def accumulator_writer_byte_indices() -> frozenset[int]:
    result: set[int] = set()
    for offset in (*ACCUMULATOR_A, *ACCUMULATOR_B):
        result.update(range(offset, offset + 8))
    return frozenset(result)


def build_body_feedback_record_bridge_contract() -> dict:
    return {
        "format": FORMAT,
        "body_record_size": BODY_RECORD_SIZE,
        "body_feedback_function": "FUN_007b4110",
        "body_array_function": "FUN_007b2270",
        "accumulator_a_offsets": ACCUMULATOR_A,
        "accumulator_b_offsets": ACCUMULATOR_B,
        "accumulator_writer_bytes": len(accumulator_writer_byte_indices()),
        "raw_feedback_seed_proven": True,
        "post_solve_accumulator_write_proven": True,
        "unrelated_bytes_preserved": True,
        "body_integration_scheduled": False,
        "runtime_scheduling_proven": False,
    }
