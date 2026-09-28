"""Evidence-backed collision-query contract around FUN_007b0710.

This phase intentionally stops at the query/cache boundary. The retail source
proves that FUN_007b0710 consumes a world-space query record, optionally reuses
an existing cached surface record, and returns a pointer to a 0x58-byte record
while writing a surface normal and a contact height. PhysX class names and
physical units remain unresolved.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Optional, Sequence

FORMAT = "SHIFT.CollisionQueryRuntime/1"
FUNCTION = "FUN_007b0710"
CALLER = "FUN_00765c40"
FALLBACK_QUERY = "FUN_0074f560"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 811231
CALLER_SOURCE_LINE = 759173

QUERY_POSITION_OFFSET = 0x00
QUERY_Y_TOLERANCE_OFFSET = 0x18
QUERY_MAX_AUX_OFFSET = 0x20
QUERY_OUTPUT_HEIGHT_OFFSET = 0x28
QUERY_CACHE_HANDLE_OFFSET = 0x30
QUERY_RECORD_DOUBLES = 7

QUERY_Y_BIAS = 0.15
QUERY_Y_TOLERANCE = 200.35
QUERY_MAX_AUX = 9.999999933815813e36
QUERY_CACHE_FLAG = 1

CACHE_RECORD_SIZE = 0x58
CACHE_VTABLE_OFFSET = 0x00
CACHE_QUERY_POINT_OFFSET = 0x04
CACHE_NORMAL_OFFSET = 0x10
CACHE_CONTACT_HEIGHT_OFFSET = 0x1C
CACHE_TRIANGLE_A_OFFSET = 0x20
CACHE_TRIANGLE_B_OFFSET = 0x2C
CACHE_TRIANGLE_C_OFFSET = 0x38
CACHE_VALID_OFFSET = 0x44
CACHE_AUX_OFFSET = 0x48
CACHE_HIT_COUNT_OFFSET = 0x50


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (self.x, self.y, self.z)):
            raise ValueError("Vec3 values must be finite")

    def as_tuple(self) -> tuple[float, float, float]:
        return (float(self.x), float(self.y), float(self.z))


@dataclass(frozen=True)
class CollisionQueryRecord:
    query_position: Vec3
    y_tolerance: float = QUERY_Y_TOLERANCE
    max_aux: float = QUERY_MAX_AUX
    cache_handle: Optional[int] = None
    cache_enabled: bool = True

    def __post_init__(self) -> None:
        if not isfinite(float(self.y_tolerance)):
            raise ValueError("y_tolerance must be finite")
        if not isfinite(float(self.max_aux)):
            raise ValueError("max_aux must be finite")
        if self.cache_handle is not None and self.cache_handle < 0:
            raise ValueError("cache_handle must be a non-negative address token")

    @property
    def param3(self) -> int:
        return QUERY_CACHE_FLAG if self.cache_enabled else 0


@dataclass(frozen=True)
class CollisionSurfaceRecord:
    address_token: int
    query_point: Vec3
    normal: Vec3
    contact_height: float
    triangle_a: Vec3
    triangle_b: Vec3
    triangle_c: Vec3
    valid: int = 1
    hit_count: Optional[int] = None

    def __post_init__(self) -> None:
        if self.address_token < 0:
            raise ValueError("address_token must be non-negative")
        if self.valid not in (0, 1):
            raise ValueError("valid must be 0 or 1")
        if not isfinite(float(self.contact_height)):
            raise ValueError("contact_height must be finite")
        if self.hit_count is not None and self.hit_count < 0:
            raise ValueError("hit_count must be non-negative")


@dataclass(frozen=True)
class CollisionQueryOutput:
    surface: Optional[CollisionSurfaceRecord]
    normal: Vec3
    contact_height: Optional[float]
    reused_cache: bool

    @property
    def hit(self) -> bool:
        return self.surface is not None


def build_wheel_query_record(
    world_position: Sequence[float],
    *,
    cached_handle: Optional[int] = None,
) -> CollisionQueryRecord:
    """Build the exact FUN_00765c40 query payload before FUN_007b0710."""
    if len(world_position) != 3:
        raise ValueError("world_position must contain exactly three values")
    x, y, z = (float(v) for v in world_position)
    return CollisionQueryRecord(
        query_position=Vec3(x, y + QUERY_Y_BIAS, z),
        y_tolerance=QUERY_Y_TOLERANCE,
        max_aux=QUERY_MAX_AUX,
        cache_handle=cached_handle,
        cache_enabled=True,
    )


def emit_query_vector(surface_normal: Optional[Vec3]) -> Vec3:
    """Mirror the miss fallback written to param_2 by FUN_007b0710."""
    return surface_normal if surface_normal is not None else Vec3(0.0, 1.0, 0.0)


def apply_query_result(
    query: CollisionQueryRecord,
    *,
    surface: Optional[CollisionSurfaceRecord],
) -> CollisionQueryOutput:
    """Model only the caller-visible writes from FUN_007b0710."""
    if surface is None:
        return CollisionQueryOutput(
            surface=None,
            normal=Vec3(0.0, 1.0, 0.0),
            contact_height=None,
            reused_cache=False,
        )
    reused = query.cache_handle is not None and query.cache_handle == surface.address_token
    return CollisionQueryOutput(
        surface=surface,
        normal=surface.normal,
        contact_height=surface.contact_height,
        reused_cache=reused,
    )


def caller_depth_or_fallback(
    *,
    original_world_y: float,
    query_output: CollisionQueryOutput,
    fallback_value: float,
) -> float:
    """Mirror FUN_00765c40's post-query +0x38e0 write."""
    original_y = float(original_world_y)
    fallback = float(fallback_value)
    if not isfinite(original_y) or not isfinite(fallback):
        raise ValueError("original_world_y and fallback_value must be finite")
    if query_output.surface is None:
        return fallback
    assert query_output.contact_height is not None
    return original_y - query_output.contact_height


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "caller": CALLER,
        "fallback_query": FALLBACK_QUERY,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "caller_source_line": CALLER_SOURCE_LINE,
        "query_record": {
            "position_offset": QUERY_POSITION_OFFSET,
            "y_tolerance_offset": QUERY_Y_TOLERANCE_OFFSET,
            "max_aux_offset": QUERY_MAX_AUX_OFFSET,
            "output_height_offset": QUERY_OUTPUT_HEIGHT_OFFSET,
            "cache_handle_offset": QUERY_CACHE_HANDLE_OFFSET,
            "record_doubles": QUERY_RECORD_DOUBLES,
            "param3_cache_flag": QUERY_CACHE_FLAG,
            "position_bias": [0.0, QUERY_Y_BIAS, 0.0],
            "y_tolerance": QUERY_Y_TOLERANCE,
            "max_aux": QUERY_MAX_AUX,
        },
        "returned_cache_record": {
            "size": CACHE_RECORD_SIZE,
            "query_point_offset": CACHE_QUERY_POINT_OFFSET,
            "normal_offset": CACHE_NORMAL_OFFSET,
            "contact_height_offset": CACHE_CONTACT_HEIGHT_OFFSET,
            "triangle_a_offset": CACHE_TRIANGLE_A_OFFSET,
            "triangle_b_offset": CACHE_TRIANGLE_B_OFFSET,
            "triangle_c_offset": CACHE_TRIANGLE_C_OFFSET,
            "valid_offset": CACHE_VALID_OFFSET,
            "aux_offset": CACHE_AUX_OFFSET,
            "hit_count_offset": CACHE_HIT_COUNT_OFFSET,
        },
        "observable_output": {
            "param2_on_hit": "returned surface normal",
            "param2_on_miss": [0.0, 1.0, 0.0],
            "param1_plus_0x28_on_hit": "returned contact height",
            "return_on_hit": "pointer to cached surface record",
            "return_on_miss": None,
        },
        "caller_post_query": {
            "state_0x38dc": "returned query handle",
            "state_0x38e0_on_hit": "original_world_y - returned contact height",
            "state_0x38e0_on_miss": "state +0x38e8 fallback",
        },
        "status": "caller-visible collision-query/cache contract only; PhysX class and physical units remain unresolved",
    }


__all__ = [
    "FORMAT", "FUNCTION", "CALLER", "FALLBACK_QUERY",
    "SOURCE_LINE", "CALLER_SOURCE_LINE",
    "QUERY_POSITION_OFFSET", "QUERY_Y_TOLERANCE_OFFSET",
    "QUERY_MAX_AUX_OFFSET", "QUERY_OUTPUT_HEIGHT_OFFSET",
    "QUERY_CACHE_HANDLE_OFFSET", "QUERY_RECORD_DOUBLES",
    "QUERY_Y_BIAS", "QUERY_Y_TOLERANCE", "QUERY_MAX_AUX",
    "QUERY_CACHE_FLAG", "CACHE_RECORD_SIZE", "CACHE_VTABLE_OFFSET",
    "CACHE_QUERY_POINT_OFFSET", "CACHE_NORMAL_OFFSET",
    "CACHE_CONTACT_HEIGHT_OFFSET", "CACHE_TRIANGLE_A_OFFSET",
    "CACHE_TRIANGLE_B_OFFSET", "CACHE_TRIANGLE_C_OFFSET",
    "CACHE_VALID_OFFSET", "CACHE_AUX_OFFSET", "CACHE_HIT_COUNT_OFFSET",
    "Vec3", "CollisionQueryRecord", "CollisionSurfaceRecord",
    "CollisionQueryOutput", "build_wheel_query_record",
    "emit_query_vector", "apply_query_result", "caller_depth_or_fallback",
    "build_contract",
]
