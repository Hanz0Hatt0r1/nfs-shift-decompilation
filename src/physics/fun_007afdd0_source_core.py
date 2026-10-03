"""Source-shaped FUN_007afdd0 basis-rotation core.

Recovered SHIFT.exe.c proves the finite/non-zero algebra and in-place 3x3 f32
write order, but the exact x87/CRT production of sqrt/sin/cos remains gated by
the Phase 680 machine/p-code freeze.  This module therefore accepts those
scalar boundaries explicitly and never substitutes host math functions.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Sequence

FORMAT = "SHIFT.Fun007afdd0SourceCore/1"
SOURCE_FUNCTION = "FUN_007afdd0"
SOURCE_LINE = 810824
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SINE_HELPER = "FUN_00900c40"
COSINE_HELPER = "FUN_00900b10"
BASIS_FLOAT_COUNT = 9
ROTATION_INCREMENT_DOUBLE_COUNT = 3
MACHINE_PRECISION_GATE_REQUIRED = True


def f32(value: float) -> float:
    """Round a Python float to IEEE-754 binary32."""
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _finite(values: Sequence[float], label: str) -> None:
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError(f"{label} contains non-finite value")


@dataclass(frozen=True)
class Fun007afdd0ScalarBoundary:
    """Externally supplied scalar results at the unresolved x87/CRT boundary.

    squared_magnitude_test is the f32 value used by the retail zero test.
    sqrt_magnitude is the f32 cast of the __CIsqrt result.  sine/cosine are the
    f32 casts of FUN_00900c40 / FUN_00900b10 respectively.
    """

    squared_magnitude_test: float
    sqrt_magnitude: float = 0.0
    sine: float = 0.0
    cosine: float = 1.0


@dataclass(frozen=True)
class Fun007afdd0SourceCoreResult:
    applied: bool
    normalized_axis: tuple[float, float, float]
    rotation_coefficients: tuple[float, ...]
    basis: tuple[float, ...]


def _rotation_coefficients(
    x: float,
    y: float,
    z: float,
    sine: float,
    cosine: float,
) -> tuple[float, ...]:
    """Evaluate the recovered fVar assignment graph using binary32 stores.

    Each named source temporary is rounded when assigned.  Phase 680 remains
    responsible for proving any x87 excess-precision retained *inside* a source
    expression, so this is a structural/source oracle rather than a machine-
    parity claim.
    """

    x = f32(x)
    y = f32(y)
    z = f32(z)
    sine = f32(sine)
    cosine = f32(cosine)

    one_minus_c = f32(1.0 - cosine)       # recovered fVar8, first assignment
    xy = f32(one_minus_c * y * x)         # recovered fVar9
    xz = f32(z * x * one_minus_c)         # recovered fVar10
    yz = f32(one_minus_c * y * z)         # recovered fVar8, reused

    r00 = f32((1.0 - x * x) * cosine + x * x)  # fVar7
    r01 = f32(xy - z * sine)                    # fVar11
    r02 = f32(y * sine + xz)                    # fVar12
    r10 = f32(xy + z * sine)                    # fVar9, reused
    r11 = f32((1.0 - y * y) * cosine + y * y)  # fVar6
    r12 = f32(yz - sine * x)                    # fVar13
    r20 = f32(xz - y * sine)                    # fVar10, reused
    r21 = f32(sine * x + yz)                    # fVar8, reused
    r22 = f32(z * z + (1.0 - z * z) * cosine)  # fVar4, reused

    return (r00, r01, r02, r10, r11, r12, r20, r21, r22)


def _apply_rotation_in_source_write_order(
    basis: Sequence[float],
    rotation: Sequence[float],
) -> tuple[float, ...]:
    if len(basis) != BASIS_FLOAT_COUNT:
        raise ValueError("FUN_007afdd0 basis must contain exactly 9 f32 values")
    if len(rotation) != BASIS_FLOAT_COUNT:
        raise ValueError("FUN_007afdd0 rotation must contain exactly 9 f32 values")
    _finite(basis, "FUN_007afdd0 basis")
    _finite(rotation, "FUN_007afdd0 rotation")

    r00, r01, r02, r10, r11, r12, r20, r21, r22 = map(f32, rotation)
    result = [f32(value) for value in basis]

    # Exact recovered in-place stripe order.  All three old values in a stripe
    # are snapshotted before the corresponding writes can alias them.
    for i0, i1, i2 in ((0, 3, 6), (1, 4, 7), (2, 5, 8)):
        old0 = result[i0]
        old1 = result[i1]
        old2 = result[i2]
        result[i0] = f32(r02 * old2 + old1 * r01 + old0 * r00)
        result[i1] = f32(r12 * old2 + r10 * old0 + r11 * old1)
        result[i2] = f32(r22 * old2 + r21 * old1 + r20 * old0)

    return tuple(result)


def execute_fun_007afdd0_source_core(
    basis: Sequence[float],
    rotation_increment: Sequence[float],
    scalars: Fun007afdd0ScalarBoundary,
) -> Fun007afdd0SourceCoreResult:
    """Execute only the source-proven finite/non-zero arithmetic core.

    Host sqrt/sin/cos are deliberately absent.  The caller must provide the
    values observed at the source's explicit f32 boundaries.  A zero f32
    magnitude-test value takes the retail no-op branch and does not consume the
    other scalar fields.
    """

    if len(basis) != BASIS_FLOAT_COUNT:
        raise ValueError("FUN_007afdd0 basis must contain exactly 9 f32 values")
    if len(rotation_increment) != ROTATION_INCREMENT_DOUBLE_COUNT:
        raise ValueError("FUN_007afdd0 rotation increment must contain exactly 3 f64 values")
    _finite(basis, "FUN_007afdd0 basis")
    _finite(rotation_increment, "FUN_007afdd0 rotation increment")
    if not math.isfinite(float(scalars.squared_magnitude_test)):
        raise ValueError("FUN_007afdd0 f32 magnitude test must be finite")

    original = tuple(f32(value) for value in basis)
    magnitude_test = f32(scalars.squared_magnitude_test)
    if magnitude_test == 0.0:
        return Fun007afdd0SourceCoreResult(
            applied=False,
            normalized_axis=(0.0, 0.0, 0.0),
            rotation_coefficients=(
                1.0, 0.0, 0.0,
                0.0, 1.0, 0.0,
                0.0, 0.0, 1.0,
            ),
            basis=original,
        )

    _finite(
        (scalars.sqrt_magnitude, scalars.sine, scalars.cosine),
        "FUN_007afdd0 external scalar boundary",
    )
    sqrt_magnitude = f32(scalars.sqrt_magnitude)
    if sqrt_magnitude == 0.0:
        raise ValueError("FUN_007afdd0 non-zero path requires non-zero f32 sqrt magnitude")

    inverse_magnitude = f32(1.0 / sqrt_magnitude)
    x = f32(inverse_magnitude * f32(rotation_increment[0]))
    y = f32(f32(rotation_increment[1]) * inverse_magnitude)
    z = f32(inverse_magnitude * f32(rotation_increment[2]))
    axis = (x, y, z)

    rotation = _rotation_coefficients(
        x,
        y,
        z,
        f32(scalars.sine),
        f32(scalars.cosine),
    )
    updated = _apply_rotation_in_source_write_order(original, rotation)
    return Fun007afdd0SourceCoreResult(
        applied=True,
        normalized_axis=axis,
        rotation_coefficients=rotation,
        basis=updated,
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "source_function": SOURCE_FUNCTION,
        "source_line": SOURCE_LINE,
        "source_sha256": SOURCE_SHA256,
        "basis_storage": {"type": "f32", "count": 9, "bytes": 36},
        "rotation_increment": {"type": "f64", "count": 3},
        "external_scalar_boundary": {
            "squared_magnitude_test": "f32 cast after x87/extended squared-magnitude expression",
            "sqrt_magnitude": "f32 cast of __CIsqrt result",
            "sine": f"f32 cast of {SINE_HELPER} result",
            "cosine": f"f32 cast of {COSINE_HELPER} result",
        },
        "normalized_axis_storage": "f32",
        "coefficient_storage": "f32 source temporaries",
        "in_place_write_stripes": [[0, 3, 6], [1, 4, 7], [2, 5, 8]],
        "zero_test_noop_proven": True,
        "sine_helper_role_source_backed": True,
        "cosine_helper_role_source_backed": True,
        "host_math_used": False,
        "machine_precision_gate_required": MACHINE_PRECISION_GATE_REQUIRED,
        "native_callback_replacement_ready": False,
        "scope_note": (
            "The recovered C body proves algebra, f32 storage boundaries and in-place write order. "
            "Exact x87 stack lifetime, CRT argument/result precision and expression excess precision "
            "remain gated by SHIFT.Fun007afdd0BasisRotationStatic/1."
        ),
    }
