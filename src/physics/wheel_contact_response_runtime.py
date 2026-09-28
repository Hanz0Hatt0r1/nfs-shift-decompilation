"""Evidence-backed first wheel contact-response kernel.

This module freezes the arithmetic immediately after FUN_00765c40's collision
query. It models the exact query-scalar clamp, FUN_00752f10 curve packing,
FUN_00755340 directional multiplier, and FUN_007551e0 quadratic response-vector
builder. It does not assign undocumented physical names to the resulting
vectors or coefficients.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, isfinite, pi
from typing import Sequence

FORMAT = "SHIFT.WheelContactResponseRuntime/1"
CONSUMER = "FUN_00766510"
QUERY_CALLER = "FUN_00765c40"
CURVE_PACKER = "FUN_00752f10"
DIRECTIONAL_FACTOR = "FUN_00755340"
RESPONSE_BUILDER = "FUN_007551e0"
SOURCE_FILE = "SHIFT.exe.c"
CONSUMER_SOURCE_LINE = 759370
CURVE_PACKER_SOURCE_LINE = 748873
RESPONSE_BUILDER_SOURCE_LINE = 750568
DIRECTIONAL_FACTOR_SOURCE_LINE = 750619

DEPTH_STATE_OFFSET = 0x38E0
DEPTH_LIMIT_OFFSET = 0x38E8
DEPTH_SLOPE_OFFSET = 0x3910
BASE_OFFSET = 0x3908
DIRECTIONAL_CURVE_OFFSET = 0x3918
RESPONSE_TABLE_OFFSET = 0x3950
RESPONSE_OUTPUT_OFFSET = 0x39D0

RESPONSE_VECTOR_COUNT = 6
RESPONSE_VECTOR_STRIDE = 0x18
RESPONSE_SCALAR_BASE = 0x90
RESPONSE_SCALAR_STRIDE = 0x08
NEGATIVE_OR_ZERO_VECTOR_OFFSETS = (0x00, 0x48, 0x78)
POSITIVE_VECTOR_OFFSETS = (0x18, 0x30, 0x60)


@dataclass(frozen=True)
class CurveParameters:
    """Four doubles stored by FUN_00752f10 at offsets 0x00..0x18."""

    amplitude: float
    double_width: float
    inverse_width_pi: float
    half_offset: float

    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (
            self.amplitude, self.double_width,
            self.inverse_width_pi, self.half_offset,
        )):
            raise ValueError("curve parameters must be finite")


@dataclass(frozen=True)
class ResponseTable:
    """Six 3-vectors followed by three scalar coefficients."""

    negative_or_zero: tuple[tuple[float, float, float], ...]
    positive: tuple[tuple[float, float, float], ...]
    component_scales: tuple[float, float, float]

    def __post_init__(self) -> None:
        if len(self.negative_or_zero) != 3 or len(self.positive) != 3:
            raise ValueError("exactly three vectors are required per sign branch")
        if len(self.component_scales) != 3:
            raise ValueError("exactly three component scales are required")
        for group in (self.negative_or_zero, self.positive):
            for vector in group:
                if len(vector) != 3 or not all(isfinite(float(v)) for v in vector):
                    raise ValueError("response vectors must contain three finite values")
        if not all(isfinite(float(v)) for v in self.component_scales):
            raise ValueError("component scales must be finite")


@dataclass(frozen=True)
class ContactResponse:
    query_scalar_input: float
    clamped_query_scalar: float
    directional_factor: float
    response_gain: float
    response_vector: tuple[float, float, float]
    auxiliary_response: tuple[float, float, float]


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def pack_curve_parameters(first: float, width: float, target: float) -> CurveParameters:
    """Exact FUN_00752f10 storage transform."""
    first = _finite(first, "first")
    width = _finite(width, "width")
    target = _finite(target, "target")
    inverse = pi / width if width > 0.0 else 0.0
    return CurveParameters(
        amplitude=first,
        double_width=width + width,
        inverse_width_pi=inverse,
        half_offset=(target - 1.0) * 0.5,
    )


def clamp_query_scalar(value: float, upper: float) -> float:
    """Mirror FUN_00766510's [0, +0x38e8] clamp exactly."""
    value = _finite(value, "value")
    upper = _finite(upper, "upper")
    if value < 0.0:
        return 0.0
    if value > upper:
        return upper
    return value


def directional_factor(curve: CurveParameters, tangent_x: float, tangent_z: float) -> float:
    """Exact FUN_00755340 arithmetic, including its angle branch."""
    x = _finite(tangent_x, "tangent_x")
    z = _finite(tangent_z, "tangent_z")
    angular = 1.0
    if curve.half_offset != 0.0:
        angle = atan2(x, -z)
        if curve.double_width > abs(angle):
            angular = 1.0 + (1.0 - cos(angle * curve.inverse_width_pi)) * curve.half_offset
    z2 = z * z
    denom = x * x + z2
    if denom <= 0.0:
        return angular
    ratio = z2 / denom
    ratio4 = ratio * ratio
    ratio4 = ratio4 * ratio4
    return angular * (1.0 - (1.0 - ratio4) * curve.amplitude)


def build_quadratic_response(
    table: ResponseTable,
    response_input: Sequence[float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Exact FUN_007551e0 response-vector and auxiliary-vector arithmetic."""
    if len(response_input) != 3:
        raise ValueError("response_input must contain exactly three values")
    v = tuple(_finite(x, f"response_input[{i}]") for i, x in enumerate(response_input))
    vector = [0.0, 0.0, 0.0]
    auxiliary = []
    for component, value in enumerate(v):
        coefficients = table.negative_or_zero if value <= 0.0 else table.positive
        selected = coefficients[component]
        square = value * value
        for axis in range(3):
            vector[axis] += selected[axis] * square
        aux = square * table.component_scales[component]
        if value > 0.0:
            aux = -aux
        auxiliary.append(aux)
    return tuple(vector), tuple(auxiliary)


def evaluate_contact_response(
    *,
    query_scalar: float,
    query_limit: float,
    depth_slope: float,
    base_offset: float,
    directional_curve: CurveParameters,
    response_table: ResponseTable,
    tangent_x: float,
    tangent_z: float,
    response_input: Sequence[float],
) -> ContactResponse:
    """Compose the first response stage in FUN_00766510."""
    clamped = clamp_query_scalar(query_scalar, query_limit)
    factor = directional_factor(directional_curve, tangent_x, tangent_z)
    gain = (
        _finite(depth_slope, "depth_slope") * clamped
        + _finite(base_offset, "base_offset")
    ) * factor
    response_vector, auxiliary = build_quadratic_response(response_table, response_input)
    return ContactResponse(
        query_scalar_input=float(query_scalar),
        clamped_query_scalar=clamped,
        directional_factor=factor,
        response_gain=gain,
        response_vector=response_vector,
        auxiliary_response=auxiliary,
    )


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "consumer": CONSUMER,
        "query_caller": QUERY_CALLER,
        "source_file": SOURCE_FILE,
        "source_lines": {
            "consumer": CONSUMER_SOURCE_LINE,
            "curve_packer": CURVE_PACKER_SOURCE_LINE,
            "directional_factor": DIRECTIONAL_FACTOR_SOURCE_LINE,
            "response_builder": RESPONSE_BUILDER_SOURCE_LINE,
        },
        "state": {
            "query_scalar": f"+0x{DEPTH_STATE_OFFSET:x}",
            "query_limit": f"+0x{DEPTH_LIMIT_OFFSET:x}",
            "depth_slope": f"+0x{DEPTH_SLOPE_OFFSET:x}",
            "base_offset": f"+0x{BASE_OFFSET:x}",
            "directional_curve": f"+0x{DIRECTIONAL_CURVE_OFFSET:x}",
            "response_table": f"+0x{RESPONSE_TABLE_OFFSET:x}",
            "response_output": f"+0x{RESPONSE_OUTPUT_OFFSET:x}",
        },
        "query_scalar": {
            "clamp": "0 <= value <= +0x38e8",
            "negative_result": 0.0,
            "above_limit_result": "+0x38e8",
        },
        "curve_packer": {
            "stored": [
                "first",
                "width * 2",
                "pi / width when width > 0 else 0",
                "(target - 1) * 0.5",
            ],
            "function": CURVE_PACKER,
        },
        "directional_factor": {
            "angle": "atan2(tangent_x, -tangent_z)",
            "angle_gate": "abs(angle) < stored_double_width",
            "angular": "1 + (1 - cos(angle * stored_inverse_width_pi)) * stored_half_offset",
            "planar_ratio": "(tangent_z^2 / (tangent_x^2 + tangent_z^2))^4",
            "factor": "angular * (1 - (1 - planar_ratio) * amplitude)",
            "zero_denominator": "angular",
        },
        "response_builder": {
            "negative_or_zero_vector_offsets_by_component": ["0x00", "0x48", "0x78"],
            "positive_vector_offsets_by_component": ["0x18", "0x30", "0x60"],
            "per_component_multiplier": "response_input_component^2",
            "auxiliary_scales": "0x90, 0x98, 0xa0",
            "auxiliary_sign": "negative for response_input > 0, unchanged for response_input <= 0",
        },
        "composition": {
            "gain": "(depth_slope * clamped_query_scalar + base_offset) * directional_factor",
            "response_input": "FUN_00766510 passes local_200 to FUN_007551e0; its producer is not proven in this boundary",
            "application_boundary": "FUN_007baa70 after body-local/world transform",
        },
        "unresolved": [
            "physical names and units of +0x38e0/+0x38e8",
            "physical meaning of the six response vectors and three auxiliary scales",
            "exact semantics of FUN_007baa70",
        ],
    }
