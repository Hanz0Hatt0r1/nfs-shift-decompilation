"""Evidence-backed reconstruction of FUN_007555b0.

The recovered C decompilation loses the x87 return value because FUN_007555b0
is emitted with a void prototype even though callers consume ST0 immediately
after the call. Phase 365 reconstructs the finite-value arithmetic directly
from the retail SHIFT.exe instruction stream.

All coefficient names stay address-based. No physical units are inferred.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

FORMAT = "SHIFT.SpringHelperRuntime/1"
FUNCTION = "FUN_007555b0"
CALLER = "FUN_00755950"
SOURCE_FILE = "./Source/Vehicle/hdvehicle.cpp"
SOURCE_LINE = 750726
BINARY_VA = 0x7555B0

HARD_STOP_VALUE = -80000.0


@dataclass(frozen=True)
class SpringHelperCoefficients:
    """Derived coefficient slots written by FUN_00755450."""

    c_1d0: float
    c_1d8: float
    c_1e0: float
    c_1e8: float
    c_1f0: float
    c_1f8: float
    c_200: float
    c_208: float
    c_210: float
    c_218: float
    c_220: float
    c_228: float
    c_230: float
    c_238: float
    c_240: float


@dataclass(frozen=True)
class SpringHelperStep:
    displacement: float
    velocity_projection: float
    previous_gap: float
    gap: float
    damping_term: float
    base_response: float
    stop_polynomial: float | None
    hard_stop_applied: bool
    response: float
    crossing_triggered: bool
    trigger_value: float | None


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def compute_gap(*, displacement: float, c_238: float, c_240: float) -> float:
    """Exact finite-value gap selection: +0x240 - p when p <= +0x240, else p - +0x238."""
    displacement = _finite("displacement", displacement)
    c_238 = _finite("c_238", c_238)
    c_240 = _finite("c_240", c_240)
    if displacement <= c_240:
        return c_240 - displacement
    return displacement - c_238


def compute_damping_term_exact(
    *,
    velocity_projection: float,
    c_1e0: float,
    c_1e8: float,
    c_1f8: float,
    c_200: float,
    c_208: float,
    c_210: float,
) -> float:
    velocity_projection = _finite("velocity_projection", velocity_projection)
    c_1e8 = _finite("c_1e8", c_1e8)
    if velocity_projection > 0.0 and velocity_projection <= c_1e8:
        return c_1e0 * velocity_projection
    if velocity_projection >= c_208:
        return c_200 * velocity_projection
    return c_1f8 * velocity_projection + c_210


def compute_stop_polynomial(
    *,
    gap: float,
    velocity_projection: float,
    c_218: float,
    c_220: float,
    c_228: float,
    c_230: float,
) -> float:
    """Exact polynomial tested before the -80000 branch."""
    gap = _finite("gap", gap)
    velocity_projection = _finite("velocity_projection", velocity_projection)
    return (
        (c_220 * gap + c_218) * gap
        + (c_230 * gap + c_228) * velocity_projection
    )


def compute_spring_helper_step(
    *,
    displacement: float,
    velocity_projection: float,
    previous_gap: float,
    coefficients: SpringHelperCoefficients,
) -> SpringHelperStep:
    """Evaluate FUN_007555b0 for finite inputs and preserve its state transition."""
    displacement = _finite("displacement", displacement)
    velocity_projection = _finite("velocity_projection", velocity_projection)
    previous_gap = _finite("previous_gap", previous_gap)

    gap = compute_gap(
        displacement=displacement,
        c_238=coefficients.c_238,
        c_240=coefficients.c_240,
    )

    damping = compute_damping_term_exact(
        velocity_projection=velocity_projection,
        c_1e0=coefficients.c_1e0,
        c_1e8=coefficients.c_1e8,
        c_1f8=coefficients.c_1f8,
        c_200=coefficients.c_200,
        c_208=coefficients.c_208,
        c_210=coefficients.c_210,
    )
    base = coefficients.c_1d0 * displacement + damping

    stop_polynomial: float | None = None
    hard_stop = False
    response = base
    if gap > 0.0:
        stop_polynomial = compute_stop_polynomial(
            gap=gap,
            velocity_projection=velocity_projection,
            c_218=coefficients.c_218,
            c_220=coefficients.c_220,
            c_228=coefficients.c_228,
            c_230=coefficients.c_230,
        )
        if stop_polynomial > 0.0:
            hard_stop = True
            response += HARD_STOP_VALUE

    crossing = gap >= 0.0 and previous_gap < 0.0
    trigger = velocity_projection if crossing else None
    return SpringHelperStep(
        displacement=displacement,
        velocity_projection=velocity_projection,
        previous_gap=previous_gap,
        gap=gap,
        damping_term=damping,
        base_response=base,
        stop_polynomial=stop_polynomial,
        hard_stop_applied=hard_stop,
        response=response,
        crossing_triggered=crossing,
        trigger_value=trigger,
    )


def build_spring_helper_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "caller": CALLER,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "binary_virtual_address": "0x7555b0",
        "return_abi": {
            "register": "x87 ST0",
            "evidence": "FUN_00755950 executes FSTP QWORD PTR [runtime+0x548] immediately after CALL 0x7555b0",
            "decompiler_issue": "recovered C prototype was emitted as void despite the live x87 result consumed by the caller",
        },
        "state": {
            "previous_gap_offset": 0x250,
            "current_gap_offset": 0x248,
            "crossing_flag_offset": 0x260,
            "trigger_value_offset": 0x258,
            "coefficients": {
                "c_1d0": 0x1D0,
                "c_1d8": 0x1D8,
                "c_1e0": 0x1E0,
                "c_1e8": 0x1E8,
                "c_1f0": 0x1F0,
                "c_1f8": 0x1F8,
                "c_200": 0x200,
                "c_208": 0x208,
                "c_210": 0x210,
                "c_218": 0x218,
                "c_220": 0x220,
                "c_228": 0x228,
                "c_230": 0x230,
                "c_238": 0x238,
                "c_240": 0x240,
            },
        },
        "arithmetic": {
            "gap": "if displacement <= +0x240: +0x240 - displacement; else displacement - +0x238",
            "damping": (
                "if velocity > 0 and velocity <= +0x1e8: +0x1e0*velocity; "
                "else if velocity >= +0x208: +0x200*velocity; "
                "else: +0x1f8*velocity + +0x210"
            ),
            "base_response": "+0x1d0*displacement + damping",
            "stop_polynomial": "(+0x220*gap + +0x218)*gap + (+0x230*gap + +0x228)*velocity",
            "response": "base_response; if gap > 0 and stop_polynomial > 0 then response += -80000",
            "crossing": "after storing current gap, if current gap >= 0 and previous gap < 0 set +0x260 and store velocity at +0x258",
        },
        "constants": {
            "hard_stop_value": -80000.0,
            "hard_stop_source_va": "0xb09048",
        },
        "scope": "exact finite-value x87 arithmetic/state boundary; semantic names and physical units remain unresolved",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "CALLER",
    "SOURCE_LINE",
    "HARD_STOP_VALUE",
    "SpringHelperCoefficients",
    "SpringHelperStep",
    "compute_gap",
    "compute_damping_term_exact",
    "compute_stop_polynomial",
    "compute_spring_helper_step",
    "build_spring_helper_contract",
]
