"""Exact three-record force aggregate used by FUN_00759c90."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Sequence

FORMAT = "SHIFT.WheelForceAggregateRuntime/1"
FUNCTION = "FUN_00759c90"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 753792
RECORD_BASE_OFFSET = 0x7F0
RECORD_STRIDE = 0x150
RECORD_COUNT = 3
VECTOR_A_OFFSET = 0xB0
VECTOR_B_OFFSET = 0x98
POINT_OFFSET = 0xF8

@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float
    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (self.x,self.y,self.z)):
            raise ValueError("vector components must be finite")
    def as_tuple(self): return (self.x,self.y,self.z)

@dataclass(frozen=True)
class AggregateRecord:
    scalar_at_base: float
    vector_a: Vec3
    scalar_at_minus_8: float
    vector_b: Vec3
    point: Vec3

def _add(a,b): return Vec3(a.x+b.x,a.y+b.y,a.z+b.z)
def _scale(v,s): return Vec3(v.x*s,v.y*s,v.z*s)
def _sub(a,b): return Vec3(a.x-b.x,a.y-b.y,a.z-b.z)
def _cross(a,b): return Vec3(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x)

def aggregate(records: Sequence[AggregateRecord], body_matrix: Sequence[float], body_mass: float):
    if len(records) != RECORD_COUNT:
        raise ValueError("FUN_00759c90 processes exactly three records")
    if len(body_matrix) != 9:
        raise ValueError("body_matrix must contain nine coefficients")
    total = Vec3(0.0,0.0,0.0)
    torque = Vec3(0.0,0.0,0.0)
    for record in records:
        a = _scale(record.vector_a, record.scalar_at_base)
        b = _scale(record.vector_b, record.scalar_at_minus_8)
        summed = _add(a,b)
        relative_point = _sub(record.point, Vec3(0.0,0.0,0.0))
        total = _add(total, summed)
        torque = _add(torque, _cross(relative_point, summed))
    m = tuple(float(x) for x in body_matrix)
    transformed = Vec3(
        m[6]*total.z + m[0]*total.x + m[3]*total.y,
        m[7]*total.z + m[4]*total.y + m[1]*total.x,
        m[8]*total.z + m[5]*total.y + m[2]*total.x,
    )
    if body_mass == 0.0:
        raise ValueError("body_mass must be non-zero")
    return total, torque, transformed.x / body_mass

def build_contract():
    return {
        "format": FORMAT, "version": 1, "function": FUNCTION,
        "source": {"file": SOURCE_FILE, "line": SOURCE_LINE},
        "record_count": 3, "record_stride": "0x150", "base": "this + 0x7f0",
        "per_record": [
            "vector at +0xb0 * scalar at +0x00",
            "vector at +0x98 * scalar at -0x08",
            "sum the two vectors",
            "point at +0xf8 minus body_position",
            "cross(relative_point, summed_vector)",
        ],
        "outputs": [
            "sum of the three summed vectors",
            "sum of the three cross vectors",
            "body-matrix transformed X / body field at +0x120",
        ],
        "status": "instruction-stream exact aggregate; source fields retain unnamed physical semantics",
    }

__all__ = ["FORMAT","FUNCTION","SOURCE_FILE","SOURCE_LINE","RECORD_BASE_OFFSET","RECORD_STRIDE",
           "RECORD_COUNT","VECTOR_A_OFFSET","VECTOR_B_OFFSET","POINT_OFFSET","Vec3",
           "AggregateRecord","aggregate","build_contract"]
