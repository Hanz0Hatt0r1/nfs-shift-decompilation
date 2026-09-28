"""Evidence-backed spring gap/state helper from retail SHIFT.exe.c.

Phase 365 intentionally models only semantics that are stable across the
recovered source and the retail instruction stream. The recovered C prototype
declares FUN_007555b0 as void; FUN_00755950 nevertheless executes an x87
FSTP immediately after the call. That caller-side ABI anomaly remains
explicitly unresolved rather than being turned into an invented force law.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

FORMAT = "SHIFT.SpringGapRuntime/1"
FUNCTION = "FUN_007555b0"
CALLER = "FUN_00755950"
SOURCE_FILE = "./Source/Vehicle/hdvehicle.cpp"
SOURCE_LINE = 750726
BINARY_VA = 0x7555B0


@dataclass(frozen=True)
class SpringGapStep:
    spring_type: int
    displacement: float
    previous_gap: float
    current_gap: float
    transition_triggered: bool
    trigger_value: float | None


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def compute_spring_gap(
    *,
    displacement: float,
    lower_boundary: float,
    upper_boundary: float,
) -> float:
    """Recover the exact two-sided gap expression in FUN_007555b0."""
    displacement = _finite("displacement", displacement)
    lower = _finite("lower_boundary", lower_boundary)
    upper = _finite("upper_boundary", upper_boundary)
    if displacement <= upper:
        return upper - displacement
    return displacement - lower


def update_spring_gap_state(
    *,
    spring_type: int,
    displacement: float,
    lower_boundary: float,
    upper_boundary: float,
    previous_gap: float,
    trigger_value: float,
) -> SpringGapStep:
    """Reproduce the source-visible +0x248/+0x250/+0x258/+0x260 state transition."""
    if int(spring_type) < 0:
        raise ValueError("spring_type must be non-negative")
    previous = _finite("previous_gap", previous_gap)
    trigger = _finite("trigger_value", trigger_value)
    current = compute_spring_gap(
        displacement=displacement,
        lower_boundary=lower_boundary,
        upper_boundary=upper_boundary,
    )
    transition = current > 0.0 and previous < 0.0
    return SpringGapStep(
        spring_type=int(spring_type),
        displacement=float(displacement),
        previous_gap=previous,
        current_gap=current,
        transition_triggered=transition,
        trigger_value=trigger if transition else None,
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
        "state_offsets": {
            "previous_gap": 0x250,
            "current_gap": 0x248,
            "crossing_flag": 0x260,
            "trigger_value": 0x258,
        },
        "boundary_offsets": {
            "lower_boundary": 0x238,
            "upper_boundary": 0x240,
        },
        "arithmetic": {
            "if_displacement_le_upper": "+0x240 - displacement",
            "else": "displacement - +0x238",
            "transition": "current_gap > 0 and previous_gap < 0",
        },
        "caller_abi_anomaly": {
            "caller_consumes_x87_after_call": True,
            "instruction": "FUN_00755950 executes FSTP QWORD PTR [runtime+0x548]",
            "callee_recovered_prototype": "void",
            "return_semantics": "unresolved",
        },
        "scope": "exact spring gap/state transition; force response and caller x87 value remain separate unresolved boundaries",
        "status": "evidence-backed",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "CALLER",
    "SOURCE_LINE",
    "BINARY_VA",
    "SpringGapStep",
    "compute_spring_gap",
    "update_spring_gap_state",
    "build_spring_helper_contract",
]
