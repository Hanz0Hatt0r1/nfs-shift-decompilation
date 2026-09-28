"""Evidence-backed spring-constraint force boundary from retail SHIFT.exe.c.

FUN_0075489c iterates registered spring elements and decides when to construct
and apply a force vector. The transform helpers that produce the world-space
anchor/reference vectors remain external inputs here; their own semantics are
not inferred by this phase.

Spring object registration from FUN_00754cc0 establishes:
    +0x10 Spring Type
    +0x18 Spring Direction
    +0x30 Spring Head
    +0x48 Spring Body
    +0x60 Collision Length
    +0x68/+0x70 Spring Params

The element array is at +0x100, stride 0x90, with count at +0xA8.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from math import sqrt
from typing import Sequence

FORMAT = "SHIFT.SpringConstraintRuntime/1"
FUNCTION = "FUN_0075489c"
SOURCE_FILE = "unresolved-from-recovered-source"
SOURCE_LINE = 750161

ELEMENT_ARRAY_OFFSET = 0x100
ELEMENT_STRIDE = 0x90
ELEMENT_COUNT_OFFSET = 0xA8
SPRING_OBJECT_SIZE = 0x90

TYPE_OFFSET = 0x10
DIRECTION_OFFSET = 0x18
HEAD_OFFSET = 0x30
BODY_OFFSET = 0x48
COLLISION_LENGTH_OFFSET = 0x60
SPRING_PARAM_A_OFFSET = 0x68
SPRING_PARAM_B_OFFSET = 0x70

VECTOR_EPSILON = 0.0


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def scaled(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def add(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def norm(self) -> float:
        return sqrt(self.dot(self))

    def normalized(self) -> "Vec3":
        length = self.norm()
        if length <= VECTOR_EPSILON:
            raise ValueError("spring direction must be non-zero")
        inv = 1.0 / length
        return self.scaled(inv)


@dataclass(frozen=True)
class SpringElementInput:
    spring_type: int
    relative_vector: Vec3
    spring_direction: Vec3
    body_relative_vector: Vec3
    collision_length: float
    spring_param_a: float
    spring_param_b: float


@dataclass(frozen=True)
class SpringForceResult:
    spring_type: int
    eligible: bool
    applied: bool
    projection: float
    body_projection: float
    response_scalar: float | None
    force: Vec3 | None
    reason: str


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _vec(values: Sequence[float] | Vec3) -> Vec3:
    if isinstance(values, Vec3):
        return Vec3(
            _finite("vector[0]", values.x),
            _finite("vector[1]", values.y),
            _finite("vector[2]", values.z),
        )
    if len(values) != 3:
        raise ValueError("vector requires exactly 3 components")
    return Vec3(*(_finite(f"vector[{i}]", value) for i, value in enumerate(values)))


def direction_for_type(
    spring_type: int,
    relative_vector: Sequence[float],
    spring_direction: Sequence[float],
) -> Vec3:
    if spring_type == 0:
        return _vec(spring_direction)
    return _vec(relative_vector).normalized()


def compute_projection(
    relative_vector: Sequence[float],
    spring_direction: Sequence[float],
    *,
    spring_type: int = 1,
) -> float:
    direction = direction_for_type(
        spring_type, relative_vector, spring_direction
    )
    return direction.dot(_vec(relative_vector))


def collision_window_allows(*, collision_length: float, projection: float) -> bool:
    length = _finite("collision_length", collision_length)
    projection = _finite("projection", projection)
    return length <= 0.0 or length <= abs(projection)


def compute_type01_response(
    *,
    projection: float,
    body_relative_vector: Sequence[float],
    direction: Sequence[float],
    spring_type: int,
    spring_param_a: float,
    spring_param_b: float,
) -> tuple[float, float]:
    """Return (response_scalar, direction dot body_relative_vector) for types 0/1."""
    projection = _finite("projection", projection)
    a = _finite("spring_param_a", spring_param_a)
    b = _finite("spring_param_b", spring_param_b)
    direction_vec = direction_for_type(spring_type, direction, direction)
    body = _vec(body_relative_vector)
    body_projection = direction_vec.dot(body)
    response = a * projection + body_projection * b
    return response, body_projection


def sign_crossing_blocks(
    *,
    collision_length: float,
    projection: float,
    response_scalar: float,
) -> bool:
    """Exact type-0/1 suppression branch when a finite collision window is active."""
    length = _finite("collision_length", collision_length)
    projection = _finite("projection", projection)
    response_scalar = _finite("response_scalar", response_scalar)
    if length <= 0.0:
        return False
    return (projection > 0.0 and response_scalar < 0.0) or (
        projection < 0.0 and response_scalar > 0.0
    )


def compute_spring_force(
    spring: SpringElementInput,
) -> SpringForceResult:
    """Evaluate the source force construction after upstream transforms."""
    collision_length = _finite("collision_length", spring.collision_length)
    body = _vec(spring.body_relative_vector)
    relative = _vec(spring.relative_vector)
    configured_direction = _vec(spring.spring_direction)
    direction = direction_for_type(
        spring.spring_type, relative, configured_direction
    )
    projection = direction.dot(relative)

    if not collision_window_allows(
        collision_length=collision_length,
        projection=projection,
    ):
        return SpringForceResult(
            spring_type=spring.spring_type,
            eligible=False,
            applied=False,
            projection=projection,
            body_projection=direction.dot(body),
            response_scalar=None,
            force=None,
            reason="collision-length window rejects projection",
        )

    if spring.spring_type == 2:
        response = spring.spring_param_a * projection
        force = body.scaled(spring.spring_param_b).add(direction.scaled(response))
        return SpringForceResult(
            spring_type=2,
            eligible=True,
            applied=True,
            projection=projection,
            body_projection=direction.dot(body),
            response_scalar=None,
            force=force,
            reason="type-2 vector response",
        )

    if spring.spring_type not in {0, 1}:
        return SpringForceResult(
            spring_type=spring.spring_type,
            eligible=True,
            applied=False,
            projection=projection,
            body_projection=direction.dot(body),
            response_scalar=None,
            force=None,
            reason="unsupported spring type",
        )

    response, body_projection = compute_type01_response(
        projection=projection,
        body_relative_vector=body,
        direction=direction,
        spring_type=spring.spring_type,
        spring_param_a=spring.spring_param_a,
        spring_param_b=spring.spring_param_b,
    )
    if sign_crossing_blocks(
        collision_length=collision_length,
        projection=projection,
        response_scalar=response,
    ):
        return SpringForceResult(
            spring_type=spring.spring_type,
            eligible=True,
            applied=False,
            projection=projection,
            body_projection=body_projection,
            response_scalar=response,
            force=None,
            reason="type-0/1 sign-crossing suppression",
        )

    force = direction.scaled(response)
    return SpringForceResult(
        spring_type=spring.spring_type,
        eligible=True,
        applied=True,
        projection=projection,
        body_projection=body_projection,
        response_scalar=response,
        force=force,
        reason="type-0/1 directional response",
    )


def build_spring_constraint_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "element_storage": {
            "array_offset": ELEMENT_ARRAY_OFFSET,
            "stride": ELEMENT_STRIDE,
            "count_offset": ELEMENT_COUNT_OFFSET,
            "object_size": SPRING_OBJECT_SIZE,
        },
        "property_offsets": {
            "SpringType": TYPE_OFFSET,
            "SpringDirection": DIRECTION_OFFSET,
            "SpringHead": HEAD_OFFSET,
            "SpringBody": BODY_OFFSET,
            "CollisionLength": COLLISION_LENGTH_OFFSET,
            "SpringParamsA": SPRING_PARAM_A_OFFSET,
            "SpringParamsB": SPRING_PARAM_B_OFFSET,
        },
        "dispatch": {
            "type_0": "configured Spring Direction is used raw",
            "type_1": "computed relative vector is normalized and used as direction",
            "type_2": "computed relative vector is normalized and used as direction",
        },
        "activation_gate": "collision_length <= 0 OR collision_length <= abs(projection)",
        "type_01": {
            "direction": "type 0 keeps transformed configured Spring Direction raw; type 1 uses normalized computed relative vector",
            "body_projection": "dot(direction_used, body_relative_vector)",
            "response_scalar": "spring_param_a*projection + body_projection*spring_param_b",
            "force": "direction_used*response_scalar",
            "suppression": (
                "when collision_length > 0: "
                "(projection > 0 and response < 0) OR "
                "(projection < 0 and response > 0)"
            ),
        },
        "type_2": {
            "relative_vector": "normalized computed relative vector supplies the direction",
            "force": (
                "body_relative_vector*spring_param_b + "
                "normalized_relative_vector*(spring_param_a*projection)"
            ),
        },
        "application": {
            "helper": "FUN_007baa70",
            "anchor_input": "world-space SpringHead result prepared upstream",
            "force_input": "constructed force vector",
        },
        "explicit_unknowns": [
            "world-space transform semantics of FUN_007aefb0",
            "semantic names/units of SpringParamsA/B",
            "semantic meaning of Spring Type 0/1/2 beyond observed dispatch",
        ],
        "status": "evidence-backed force-construction boundary; transform ownership remains external",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "SOURCE_LINE",
    "ELEMENT_ARRAY_OFFSET",
    "ELEMENT_STRIDE",
    "ELEMENT_COUNT_OFFSET",
    "SPRING_OBJECT_SIZE",
    "TYPE_OFFSET",
    "DIRECTION_OFFSET",
    "HEAD_OFFSET",
    "BODY_OFFSET",
    "COLLISION_LENGTH_OFFSET",
    "SPRING_PARAM_A_OFFSET",
    "SPRING_PARAM_B_OFFSET",
    "Vec3",
    "SpringElementInput",
    "SpringForceResult",
    "direction_for_type",
    "compute_projection",
    "collision_window_allows",
    "compute_type01_response",
    "sign_crossing_blocks",
    "compute_spring_force",
    "build_spring_constraint_contract",
]
