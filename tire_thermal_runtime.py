"""Evidence-backed tire thermal-state update extracted from SHIFT.exe.c."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

FORMAT = "SHIFT.TireThermalRuntime/1"
FUNCTION = "FUN_00760b50"
SOURCE_FILE = "./Source/Vehicle/hdvehicle.cpp"
SOURCE_LINE = 756009

@dataclass(frozen=True)
class ThermalFieldEvidence:
    name: str
    offset: int
    evidence: str

THERMAL_FIELDS = (
    ThermalFieldEvidence("spin_measure_source", 0x350, "absolute value is used as primary heat input"),
    ThermalFieldEvidence("spin_heat_scale", 0x858, "multiplies the primary heat input"),
    ThermalFieldEvidence("accumulated_heat_scale", 0x898, "multiplies the first heat source"),
    ThermalFieldEvidence("speed_transfer_base", 0x8A0, "affine coefficient for transformed longitudinal speed"),
    ThermalFieldEvidence("speed_transfer_rate", 0x8A8, "multiplies transformed longitudinal speed"),
    ThermalFieldEvidence("temperature_state", 0x888, "updated by thermal rate times dt"),
    ThermalFieldEvidence("reference_temperature", 0x890, "reference for tolerance branch"),
    ThermalFieldEvidence("thermal_tolerance", 0x878, "absolute temperature difference threshold"),
    ThermalFieldEvidence("failure_gain_state", 0x868, "updated on successful thermal-reserve branch"),
    ThermalFieldEvidence("failure_gain_base", 0x870, "base value for +0x868"),
    ThermalFieldEvidence("thermal_reserve", 0x8B0, "depleted above reserve floor"),
    ThermalFieldEvidence("reserve_gain_for_later_state", 0x8B8, "consumed after thermal update"),
    ThermalFieldEvidence("reserve_depletion_capacity", 0x8C0, "multiplies source heat and temperature cubed"),
    ThermalFieldEvidence("reserve_floor", 0x8C8, "normalizes thermal rate and guards reserve exhaustion"),
)

@dataclass(frozen=True)
class ThermalStep:
    source_heat: float
    ambient_kelvin: float
    convective_term: float
    net_heat: float
    rate: float
    temperature_before: float
    temperature_after: float
    thermal_reserve_before: float
    thermal_reserve_after: float
    failure_gain_after: float

def compute_thermal_step(
    *,
    dt: float,
    spin_measure: float,
    spin_heat_scale: float,
    accumulated_heat_scale: float,
    speed_transfer_base: float,
    speed_transfer_rate: float,
    longitudinal_velocity: float,
    ambient_temperature_a: float,
    ambient_temperature_b: float,
    temperature_state: float,
    reference_temperature: float,
    thermal_reserve: float,
    reserve_depletion_capacity: float,
    reserve_floor: float,
    thermal_tolerance: float,
    failure_gain_base: float,
    overheat_scale: float,
    failure_rng: Callable[[], float] = lambda: 0.0,
) -> ThermalStep:
    source_heat = abs(spin_measure) * spin_heat_scale
    source_heat *= accumulated_heat_scale

    abs_longitudinal = -longitudinal_velocity if longitudinal_velocity < 0.0 else 0.0
    ambient_kelvin = (
        ambient_temperature_a + 273.16
        + ambient_temperature_b + 273.16
    ) * 0.5
    convective_term = (
        speed_transfer_rate * abs_longitudinal + speed_transfer_base
    ) * (ambient_kelvin - temperature_state)
    net_heat = convective_term + source_heat

    reserve_after = thermal_reserve
    failure_gain_after = failure_gain_base

    if thermal_reserve <= reserve_floor:
        rate = net_heat / reserve_floor
    else:
        cubic_loss = (
            reserve_depletion_capacity
            * source_heat
            * temperature_state
            * temperature_state
            * temperature_state
        )
        reserve_after = (
            thermal_reserve
            - overheat_scale * cubic_loss * dt
        )
        if reserve_after >= reserve_floor:
            rate = net_heat / reserve_after
            if abs(temperature_state - reference_temperature) <= thermal_tolerance:
                failure_gain_after = (
                    failure_rng() * 0.25 + 0.75
                ) * failure_gain_base
            else:
                failure_gain_after = failure_gain_base * 0.5
        else:
            reserve_after = 0.0
            failure_gain_after = 0.0
            rate = 0.0

    temperature_after = temperature_state + rate * dt
    return ThermalStep(
        source_heat=source_heat,
        ambient_kelvin=ambient_kelvin,
        convective_term=convective_term,
        net_heat=net_heat,
        rate=rate,
        temperature_before=temperature_state,
        temperature_after=temperature_after,
        thermal_reserve_before=thermal_reserve,
        thermal_reserve_after=reserve_after,
        failure_gain_after=failure_gain_after,
    )

def build_thermal_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "wheel_stride": 0xA80,
        "fields": [
            {
                "name": field.name,
                "offset": field.offset,
                "offset_hex": hex(field.offset),
                "evidence": field.evidence,
            }
            for field in THERMAL_FIELDS
        ],
        "ordered_update": [
            "source_heat = abs(+0x350) * +0x858 * +0x898",
            "abs_longitudinal = max(0, -transformed_longitudinal_component)",
            "ambient_kelvin = ((ambient_A + 273.16) + (ambient_B + 273.16)) * 0.5",
            "convective = (+0x8A8 * abs_longitudinal + +0x8A0) * (ambient_kelvin - +0x888)",
            "net_heat = source_heat + convective",
            "if +0x8B0 <= +0x8C8: rate = net_heat / +0x8C8",
            "else: reserve -= global_overheat_scale * +0x8C0 * source_heat * (+0x888)^3 * dt",
            "if reserve >= floor: rate = net_heat / reserve and update +0x868",
            "else: zero +0x8B0 and +0x868 and force rate=0",
            "+0x888 += rate * dt",
        ],
        "external_constants": {
            "kelvin_bias": 273.16,
            "failure_random_weight": 0.25,
            "failure_random_base": 0.75,
            "overheat_scale_source": "FUN_00749340(&DAT_00c12c90) * DAT_00c12f38",
        },
        "status": "exact arithmetic boundary; physical units and semantic labels remain conservative",
    }

__all__ = [
    "FORMAT",
    "FUNCTION",
    "SOURCE_LINE",
    "THERMAL_FIELDS",
    "ThermalFieldEvidence",
    "ThermalStep",
    "build_thermal_contract",
    "compute_thermal_step",
]
