"""Four-wheel tyre thermal runtime orchestration.

Phase 363 keeps the recovered per-wheel thermal arithmetic authoritative and
reconstructs only the observed call topology: FUN_00760b50 is invoked once for
each wheel after the main physics passes. No new tyre-force semantics are introduced.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from tire_thermal_runtime import ThermalStep, compute_thermal_step

FORMAT = "SHIFT.TireThermalBatchRuntime/1"
FUNCTION = "FUN_00770e80"
WHEEL_ORDER = ("FRONTLEFT", "FRONTRIGHT", "REARLEFT", "REARRIGHT")
WHEEL_STRIDE = 0xA80

@dataclass(frozen=True)
class WheelThermalStep:
    wheel: str
    step: ThermalStep

@dataclass(frozen=True)
class ThermalBatch:
    wheels: tuple[WheelThermalStep, ...]
    @property
    def temperatures_after(self) -> dict[str, float]:
        return {row.wheel: row.step.temperature_after for row in self.wheels}
    @property
    def reserves_after(self) -> dict[str, float]:
        return {row.wheel: row.step.thermal_reserve_after for row in self.wheels}

def compute_four_wheel_thermal_step(
    wheel_inputs: Mapping[str, Mapping[str, Any]],
) -> ThermalBatch:
    """Run the recovered thermal function once per wheel in retail order."""
    missing = [wheel for wheel in WHEEL_ORDER if wheel not in wheel_inputs]
    extra = sorted(set(wheel_inputs) - set(WHEEL_ORDER))
    if missing:
        raise ValueError(f"missing wheel thermal state: {', '.join(missing)}")
    if extra:
        raise ValueError(f"unknown wheel thermal state: {', '.join(extra)}")
    rows = tuple(
        WheelThermalStep(wheel, compute_thermal_step(**dict(wheel_inputs[wheel])))
        for wheel in WHEEL_ORDER
    )
    return ThermalBatch(rows)

def build_thermal_batch_contract() -> dict[str, Any]:
    return {
        "format": FORMAT, "version": 1, "caller": FUNCTION,
        "callee": "FUN_00760b50", "wheel_stride": WHEEL_STRIDE,
        "wheel_order": list(WHEEL_ORDER),
        "ordering": {
            "position": "after main FUN_00770e80 physics passes",
            "invocations": 4, "per_wheel_state_is_independent": True,
        },
        "arithmetic_source": "SHIFT.TireThermalRuntime/1",
        "scope": "call topology only; tyre traction/contact law remains separate",
        "status": "evidence-backed orchestration",
    }

__all__ = [
    "FORMAT", "FUNCTION", "WHEEL_ORDER", "WHEEL_STRIDE",
    "ThermalBatch", "WheelThermalStep",
    "build_thermal_batch_contract", "compute_four_wheel_thermal_step",
]
