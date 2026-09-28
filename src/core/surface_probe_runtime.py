"""Exact source contract for FUN_00759210's recursive surface probe."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Optional, Sequence

FORMAT = "SHIFT.SurfaceProbeRuntime/1"
FUNCTION = "FUN_00759210"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 753361

NODE_POINT_OFFSET = 0x8C
NODE_NORMAL_OFFSET = 0x13C
NODE_DISTANCE_OFFSET = 0xFC
NODE_RADIUS_OFFSET = 0x158
NODE_PARENT_OFFSET = 0x17C
NODE_CHILD_OFFSET = 0x180

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
class SurfaceNode:
    point: Vec3
    normal: Vec3
    distance: float
    radius: float
    parent: Optional["SurfaceNode"] = None
    child: Optional["SurfaceNode"] = None
    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (self.distance, self.radius)):
            raise ValueError("surface node scalars must be finite")

@dataclass(frozen=True)
class SurfaceProbeResult:
    point: Vec3
    scalar: float
    used_parent: bool = False

def _cross(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x)

def _dot(a: Vec3, b: Vec3) -> float:
    return a.x*b.x + a.y*b.y + a.z*b.z

def _sub(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(a.x-b.x, a.y-b.y, a.z-b.z)

def _add(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(a.x+b.x, a.y+b.y, a.z+b.z)

def _scale(v: Vec3, s: float) -> Vec3:
    return Vec3(v.x*s, v.y*s, v.z*s)

def _normalize(v: Vec3, threshold: float = 0.01) -> Vec3:
    length = sqrt(_dot(v, v))
    if length <= threshold:
        return Vec3(1.0, 0.0, 0.0)
    return _scale(v, 1.0/length)

def node_direction(node: SurfaceNode) -> Vec3:
    return _normalize(_cross(Vec3(0.0, 1.0, 0.0), node.normal))

def _sign(value: float) -> int:
    if value > 0.0: return 1
    if value < 0.0: return -1
    return 0

def probe(point: Sequence[float], node: SurfaceNode) -> SurfaceProbeResult:
    """Mirror FUN_00759210 without assigning undocumented physical names."""
    p = Vec3(*(float(v) for v in point))
    rel = _sub(p, node.point)
    projection = _dot(rel, node.normal)
    if projection < 0.0 and node.parent is not None:
        result = probe(p.as_tuple(), node.parent)
        return SurfaceProbeResult(result.point, result.scalar, True)

    direction = node_direction(node)
    candidate = _add(node.point, _scale(direction, node.radius))
    point_delta = _sub(p, candidate)
    denom = abs(_dot(rel, point_delta))
    if denom == 0.0 or node.radius == 0.0 or node.distance == 0.0:
        raise ValueError("FUN_00759210 denominator/radius path is non-finite at zero")

    blend = (projection / denom) / (node.distance / abs(node.radius))
    blend = min(1.0, max(0.0, blend))

    child = node.child
    if child is not None and _sign(child.radius) == _sign(node.radius):
        child_direction = node_direction(child)
        child_candidate = _add(child.point, _scale(child_direction, child.radius))
        out_point = _add(_scale(candidate, 1.0-blend), _scale(child_candidate, blend))
        out_scalar = abs(node.radius*(1.0-blend) + child.radius*blend)
        return SurfaceProbeResult(out_point, out_scalar, False)

    return SurfaceProbeResult(candidate, abs(node.radius), False)

def build_contract() -> dict:
    return {
        "format": FORMAT, "version": 1, "function": FUNCTION,
        "source": {"file": SOURCE_FILE, "line": SOURCE_LINE},
        "node_fields": {
            "point": ["+0x8c", "+0x90", "+0x94"],
            "normal": ["+0x13c", "+0x140", "+0x144"],
            "distance": "+0xfc", "radius": "+0x158",
            "parent": "+0x17c", "child": "+0x180",
        },
        "projection": "dot(point - node.point, node.normal)",
        "negative_projection": "recurse to parent when projection < 0 and parent != null",
        "direction": "normalize((0,1,0) x node.normal), fallback (1,0,0) when length <= 0.01",
        "candidate": "node.point + direction * radius",
        "blend_factor": "clamp((projection / abs(dot(point-node.point, point-candidate))) / (distance / abs(radius)), 0, 1)",
        "child_blend": "same radius sign => linear point blend and absolute weighted radius",
        "status": "instruction-stream exact contract; node fields remain semantically unnamed",
    }

__all__ = [
    "FORMAT","FUNCTION","SOURCE_FILE","SOURCE_LINE",
    "NODE_POINT_OFFSET","NODE_NORMAL_OFFSET","NODE_DISTANCE_OFFSET",
    "NODE_RADIUS_OFFSET","NODE_PARENT_OFFSET","NODE_CHILD_OFFSET",
    "Vec3","SurfaceNode","SurfaceProbeResult","node_direction","probe","build_contract",
]
