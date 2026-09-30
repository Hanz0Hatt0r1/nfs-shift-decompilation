"""Source-backed WayPointBase horizontal perpendicular helper.

This reconstructs retail FUN_007ade70: cross world-up with the record vector
at +0x13c, normalize when its length is above 0.01, otherwise return (1,0,0).
"""
from __future__ import annotations

import math
import struct
from typing import Any

from waypoint_base_runtime import SIZE

FORMAT = "SHIFT.WayPointHorizontalPerpendicularRuntime/1"

FUNCTION = "FUN_007ade70"
FUNCTION_ADDRESS = 0x007ADE70
CROSS_PRODUCT_FUNCTION = "FUN_0047bdb0"
SOURCE_VECTOR_OFFSET = 0x13C
WORLD_UP = (0.0, 1.0, 0.0)
DEGENERATE_FALLBACK = (1.0, 0.0, 0.0)
NORMALIZE_THRESHOLD_BITS = 0x3C23D70A
NORMALIZE_THRESHOLD = struct.unpack(
    "<f", struct.pack("<I", NORMALIZE_THRESHOLD_BITS)
)[0]
KNOWN_CALLERS = ("FUN_00759210", "FUN_007adf30")


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def cross_product(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Reproduce the direct three-float FUN_0047bdb0 helper."""
    ax, ay, az = (_f32(value) for value in a)
    bx, by, bz = (_f32(value) for value in b)
    return (
        _f32(float(ay) * float(bz) - float(az) * float(by)),
        _f32(float(az) * float(bx) - float(ax) * float(bz)),
        _f32(float(ax) * float(by) - float(ay) * float(bx)),
    )


def horizontal_perpendicular(
    direction: tuple[float, float, float],
) -> dict[str, Any]:
    """Reproduce FUN_007ade70 over one source direction vector."""
    source = tuple(_f32(value) for value in direction)
    crossed = cross_product(WORLD_UP, source)

    # Retail stores the squared-length sum and sqrt result through float locals
    # before the >0.01 comparison.
    length_sq = _f32(
        float(crossed[0]) * float(crossed[0])
        + float(crossed[1]) * float(crossed[1])
        + float(crossed[2]) * float(crossed[2])
    )
    length = _f32(math.sqrt(float(length_sq)))

    if NORMALIZE_THRESHOLD < length:
        inverse = _f32(1.0 / float(length))
        result = tuple(
            _f32(float(component) * float(inverse))
            for component in crossed
        )
        mode = "normalized-cross"
    else:
        inverse = None
        result = DEGENERATE_FALLBACK
        mode = "fallback"

    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "source_direction": source,
        "cross": crossed,
        "length_sq": length_sq,
        "length": length,
        "threshold": NORMALIZE_THRESHOLD,
        "inverse_length": inverse,
        "mode": mode,
        "result": result,
    }


def derive_waypoint_horizontal_perpendicular(
    record: bytes | bytearray | memoryview,
) -> dict[str, Any]:
    """Read WayPointBase +0x13c and apply FUN_007ade70."""
    view = memoryview(record)
    if len(view) < SIZE:
        raise ValueError(f"WayPointBase record requires 0x{SIZE:x} bytes")
    source = struct.unpack_from("<fff", view, SOURCE_VECTOR_OFFSET)
    return horizontal_perpendicular(source)


def describe_waypoint_horizontal_perpendicular_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "function_address": FUNCTION_ADDRESS,
        "known_callers": list(KNOWN_CALLERS),
        "source_vector_offset": SOURCE_VECTOR_OFFSET,
        "world_up": WORLD_UP,
        "cross_product_helper": CROSS_PRODUCT_FUNCTION,
        "length_expression": "sqrt(cross.x^2 + cross.y^2 + cross.z^2)",
        "normalization": {
            "condition": "length > 0.01",
            "threshold_bits": NORMALIZE_THRESHOLD_BITS,
            "threshold": NORMALIZE_THRESHOLD,
            "fallback": DEGENERATE_FALLBACK,
        },
        "simplified_cross": "(source.z, 0, -source.x)",
        "evidence_boundary": (
            "The exact vector operation and threshold behavior are recovered. "
            "The +0x13c source field remains named structurally here; its "
            "producer/normalization belongs to the larger FUN_007ada70 pass."
        ),
    }
