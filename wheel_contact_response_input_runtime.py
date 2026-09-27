"""Source contract for the explicit response-input vector in FUN_00766510.

The retail source directly shows:
FUN_007af0a0(body + 0xd4, body + 0x18, local_200)
followed by FUN_007551e0(..., local_200, ...).

This phase records that producer boundary only. FUN_007af0a0 transform
semantics and the physical meaning of body field +0x18 remain external.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

FORMAT = "SHIFT.WheelContactResponseInputRuntime/1"
FUNCTION = "FUN_00766510"
TRANSFORM = "FUN_007af0a0"
CONSUMER = "FUN_007551e0"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 759553

BODY_BASE_OFFSET = 0x33A0
BODY_TRANSFORM_OFFSET = 0xD4
BODY_INPUT_VECTOR_OFFSET = 0x18
RESPONSE_INPUT_COMPONENTS = 3


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (self.x, self.y, self.z)):
            raise ValueError("vector values must be finite")

    def as_tuple(self) -> tuple[float, float, float]:
        return (float(self.x), float(self.y), float(self.z))


@dataclass(frozen=True)
class ResponseInputSource:
    body_base: int
    transform_context: int
    source_vector_offset: int
    output_local_name: str = "local_200"


@dataclass(frozen=True)
class ResponseInputEvidence:
    source: Vec3
    transformed: Vec3


def source_contract() -> ResponseInputSource:
    return ResponseInputSource(
        body_base=BODY_BASE_OFFSET,
        transform_context=BODY_BASE_OFFSET + BODY_TRANSFORM_OFFSET,
        source_vector_offset=BODY_BASE_OFFSET + BODY_INPUT_VECTOR_OFFSET,
    )


def capture_transform_result(
    source_vector: Sequence[float],
    transformed_vector: Sequence[float],
) -> ResponseInputEvidence:
    """Keep source and transform output distinct at the producer boundary."""
    if len(source_vector) != RESPONSE_INPUT_COMPONENTS:
        raise ValueError("source_vector must contain exactly three values")
    if len(transformed_vector) != RESPONSE_INPUT_COMPONENTS:
        raise ValueError("transformed_vector must contain exactly three values")
    source = Vec3(*(float(v) for v in source_vector))
    transformed = Vec3(*(float(v) for v in transformed_vector))
    return ResponseInputEvidence(source=source, transformed=transformed)


def build_contract() -> dict:
    src = source_contract()
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "transform": TRANSFORM,
        "consumer": CONSUMER,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "body": {
            "base_offset": "+0x33a0",
            "transform_context": "+0xd4",
            "input_vector": "+0x18",
        },
        "producer_call": {
            "this_transform": "body + 0xd4",
            "source_vector": "body + 0x18",
            "destination": "local_200",
            "component_count": RESPONSE_INPUT_COMPONENTS,
        },
        "consumer_call": {
            "function": CONSUMER,
            "input": "local_200",
        },
        "topology": {
            "body_object_field_source": "+0x18",
            "transform_context_offset": "+0xd4",
            "response_kernel_input": "local_200",
        },
        "addressed_offsets": {
            "body_base": src.body_base,
            "body_transform": src.transform_context,
            "body_input_vector": src.source_vector_offset,
        },
        "unresolved": [
            "FUN_007af0a0 transform semantics",
            "physical meaning and units of body field +0x18",
            "whether body field +0x18 is a velocity, state vector, or another engine quantity",
        ],
        "status": "direct caller-side producer/consumer boundary; no physical semantic inference",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "TRANSFORM",
    "CONSUMER",
    "SOURCE_FILE",
    "SOURCE_LINE",
    "BODY_BASE_OFFSET",
    "BODY_TRANSFORM_OFFSET",
    "BODY_INPUT_VECTOR_OFFSET",
    "RESPONSE_INPUT_COMPONENTS",
    "Vec3",
    "ResponseInputSource",
    "ResponseInputEvidence",
    "source_contract",
    "capture_transform_result",
    "build_contract",
]
