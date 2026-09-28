"""Evidence-backed three-node wheel thermal integrator from retail SHIFT.exe.c.

FUN_00755a60 is called once per wheel from FUN_00770e80 with the wheel runtime
object, wheel index and timestep. This module reconstructs the observable scalar
state updates while keeping all coefficient names tied to their recovered
offsets. It does not assign physical units or claim a higher-level tyre model.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt

FORMAT = "SHIFT.WheelThermalIntegratorRuntime/1"
FUNCTION = "FUN_00755a60"
CALLER = "FUN_00770e80"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 750869

KELVIN_BIAS = 273.16
RESERVOIR_CLAMP_LOW = 273.16
RESERVOIR_CLAMP_HIGH = 546.32
WEAR_FLOOR = 0.6875


@dataclass(frozen=True)
class ThermalIntegratorInputs:
    dt: float
    ambient_a: float
    ambient_b: float
    spin_measure: float
    spin_activity_scale: float
    activity: float
    factor_control: float
    heat_shape: float
    heat_gain: float
    steering_a_product: float
    steering_b_product: float
    steering_b_base: float
    steering_b_reference: float
    steering_b_gain: float
    sqrt_input_base: float
    global_constant_c12c24: float
    ambient_coupling_a: float
    ambient_coupling_b: float
    reservoir_temperature: float
    temperature_0: float
    temperature_1: float
    temperature_2: float
    reservoir_scale: float
    reservoir_exchange: float
    temp_reference: float
    temp_gain_negative: float
    temp_gain_positive: float
    temp_alert_threshold: float
    abrasion_scale: float
    abrasion_accumulator: float
    wear_event_enabled: bool
    grip_state: float
    derived_reservoir_scale: float
    derived_aux_scale: float
    derived_aux_bias: float
    output_limit_reference: float
    wear_enabled: bool
    global_wear_scale: float
    # The recovered abrasion path references this scalar; absent legacy inputs use unity.
    average_temperature_scale: float = 1.0


@dataclass(frozen=True)
class ThermalIntegratorStep:
    source_heat: float
    shape_factor: float
    secondary_source: float
    steering_a: float
    steering_b: float
    fractions: tuple[float, float, float]
    temperatures_after: tuple[float, float, float]
    reservoir_before: float
    reservoir_after: float
    average_temperature: float
    abrasion_term: float
    abrasion_after: float
    normalized_temperature_delta: float
    limited_temperature_factor: float
    grip_output: float
    derived_reservoir_field: float
    derived_auxiliary_field: float
    wear_floor_crossed: bool
    overtemperature_condition: bool


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def clamp(value: float, low: float, high: float) -> float:
    value = _finite("value", value)
    return min(high, max(low, value))


def compute_source_heat(
    *,
    spin_measure: float,
    spin_activity_scale: float,
    activity: float,
) -> float:
    activity = _finite("activity", activity)
    if activity <= 0.0:
        return 0.0
    return abs(_finite("spin_measure", spin_measure)) * _finite(
        "spin_activity_scale", spin_activity_scale
    ) * activity


def compute_shape_factor(*, factor_control: float) -> float:
    """Reproduce the sqrt branch used before the three temperature fractions."""
    x = _finite("factor_control", factor_control)
    factor = 1.0
    if x <= 1.0:
        factor = sqrt(x)
        if factor < 0.5:
            factor = factor * factor + 0.25
    return 1.0 - factor


def compute_temperature_fractions(
    *,
    steering_a: float,
    steering_b: float,
    dt: float,
) -> tuple[float, float, float]:
    dt = _finite("dt", dt)
    a = _finite("steering_a", steering_a)
    b = _finite("steering_b", steering_b)
    return (
        ((b * 0.5 - a + 1.5) / 3.0) * dt,
        ((1.5 - b) / 3.0) * dt,
        ((a + b * 0.5 + 1.5) / 3.0) * dt,
    )


def update_three_node_temperatures(
    *,
    temperatures: tuple[float, float, float],
    reservoir: float,
    fractions: tuple[float, float, float],
    activity: float,
    source_heat: float,
    secondary_source: float,
    ambient_a: float,
    ambient_b: float,
    ambient_exchange: float,
    reservoir_exchange: float,
) -> tuple[tuple[float, float, float], float]:
    temps = [_finite(f"temperature_{i}", value) for i, value in enumerate(temperatures)]
    reservoir = _finite("reservoir", reservoir)
    ambient_a = _finite("ambient_a", ambient_a)
    ambient_b = _finite("ambient_b", ambient_b)
    ambient_exchange = _finite("ambient_exchange", ambient_exchange)
    reservoir_exchange = _finite("reservoir_exchange", reservoir_exchange)

    updated: list[float] = []
    for index, fraction in enumerate(fractions):
        fraction = _finite(f"fraction_{index}", fraction)
        original = temps[index]
        value = original + fraction * source_heat + fraction * secondary_source
        if activity > 0.0:
            value += fraction * ambient_exchange * (ambient_a - original)
        transfer = (reservoir - original) * reservoir_exchange
        value += (ambient_b - original) * ambient_exchange
        value += transfer
        reservoir -= transfer
        updated.append(value)
    return (tuple(updated), reservoir)


def compute_grip_output(
    *,
    average_temperature: float,
    reservoir_temperature: float,
    temp_reference: float,
    temp_gain_negative: float,
    temp_gain_positive: float,
    output_limit_reference: float,
    normalization_reference: float,
    grip_state: float,
) -> tuple[float, float, float]:
    delta = average_temperature - temp_reference
    slope = temp_gain_positive if delta >= 0.0 else temp_gain_negative
    normalization = _finite("normalization_reference", normalization_reference)
    scale = _finite("output_limit_reference", output_limit_reference)
    if normalization == 0.0:
        raise ValueError("normalization_reference must be non-zero")
    temperature_factor = (
        delta * slope
        + abs(reservoir_temperature - normalization) * scale / normalization
    )
    if temperature_factor != temperature_factor:
        limited = temperature_factor
    else:
        limited = max(1.0, temperature_factor)
    output = (1.0 - 0.5 * limited * limited) * grip_state
    return temperature_factor, limited, output


def integrate_wheel_thermal_state(
    inputs: ThermalIntegratorInputs,
) -> ThermalIntegratorStep:
    """Execute the recovered scalar temperature/wear update."""
    dt = _finite("dt", inputs.dt)
    ambient_a = _finite("ambient_a", inputs.ambient_a) + KELVIN_BIAS
    ambient_b = _finite("ambient_b", inputs.ambient_b) + KELVIN_BIAS

    source_heat = compute_source_heat(
        spin_measure=inputs.spin_measure,
        spin_activity_scale=inputs.spin_activity_scale,
        activity=inputs.activity,
    )
    shape_factor = compute_shape_factor(factor_control=inputs.factor_control)
    heat_shape = _finite("heat_shape", inputs.heat_shape)
    secondary_source = (
        shape_factor * _finite("activity", inputs.activity) * heat_shape * heat_shape
        * _finite("heat_gain", inputs.heat_gain)
    )

    steering_a = clamp(inputs.steering_a_product, -1.0, 1.0)
    local_steering_b = (
        _finite("steering_b_product", inputs.steering_b_product)
        + _finite("steering_b_base", inputs.steering_b_base)
    )
    steering_b = clamp(
        (local_steering_b - _finite("steering_b_reference", inputs.steering_b_reference))
        * _finite("steering_b_gain", inputs.steering_b_gain),
        -1.0,
        1.0,
    )

    fractions = compute_temperature_fractions(
        steering_a=steering_a,
        steering_b=steering_b,
        dt=dt,
    )

    sqrt_argument = (
        _finite("sqrt_input_base", inputs.sqrt_input_base)
        + 1.0
        + _finite("global_constant_c12c24", inputs.global_constant_c12c24)
    )
    sqrt_value = sqrt(sqrt_argument)
    ambient_exchange = (
        sqrt_value * _finite("ambient_coupling_a", inputs.ambient_coupling_a)
        + _finite("ambient_coupling_b", inputs.ambient_coupling_b)
    ) * sqrt_value * dt
    reservoir_exchange = _finite("reservoir_exchange", inputs.reservoir_exchange) * dt

    temperatures_after, reservoir_after = update_three_node_temperatures(
        temperatures=(inputs.temperature_0, inputs.temperature_1, inputs.temperature_2),
        reservoir=inputs.reservoir_temperature,
        fractions=fractions,
        activity=inputs.activity,
        source_heat=source_heat,
        secondary_source=secondary_source,
        ambient_a=ambient_a,
        ambient_b=ambient_b,
        ambient_exchange=ambient_exchange,
        reservoir_exchange=reservoir_exchange,
    )
    reservoir_after = clamp(
        reservoir_after,
        RESERVOIR_CLAMP_LOW,
        RESERVOIR_CLAMP_HIGH,
    )

    average = sum(temperatures_after) / 3.0
    d7d8 = reservoir_after * _finite("derived_reservoir_scale", inputs.derived_reservoir_scale)
    abrasion_temp = average * _finite("average_temperature_scale", inputs.average_temperature_scale)
    angular = (
        (abs(steering_b) + abs(steering_a) + 4.0) / 6.0
        * dt
        * abrasion_temp * abrasion_temp
        * shape_factor
        * _finite("abrasion_scale", inputs.abrasion_scale)
        + _finite("abrasion_accumulator", inputs.abrasion_accumulator)
    )
    wear_before = _finite("grip_state", inputs.grip_state)
    abrasion_after = wear_before
    wear_floor_crossed = False
    if inputs.wear_enabled and wear_before > WEAR_FLOOR:
        abrasion_after = wear_before - _finite("global_wear_scale", inputs.global_wear_scale) * angular
        if abrasion_after < WEAR_FLOOR:
            abrasion_after = WEAR_FLOOR
            wear_floor_crossed = True

    temperature_factor, limited, output = compute_grip_output(
        average_temperature=average,
        reservoir_temperature=d7d8,
        temp_reference=inputs.temp_reference,
        temp_gain_negative=inputs.temp_gain_negative,
        temp_gain_positive=inputs.temp_gain_positive,
        output_limit_reference=_finite("output_limit_reference", inputs.output_limit_reference),
        normalization_reference=local_steering_b,
        grip_state=abrasion_after,
    )

    derived_auxiliary = d7d8 * _finite("derived_aux_scale", inputs.derived_aux_scale) + _finite("derived_aux_bias", inputs.derived_aux_bias)
    overtemperature_condition = average > _finite("temp_alert_threshold", inputs.temp_alert_threshold)

    return ThermalIntegratorStep(
        source_heat=source_heat,
        shape_factor=shape_factor,
        secondary_source=secondary_source,
        steering_a=steering_a,
        steering_b=steering_b,
        fractions=fractions,
        temperatures_after=temperatures_after,
        reservoir_before=_finite("reservoir_temperature", inputs.reservoir_temperature),
        reservoir_after=reservoir_after,
        average_temperature=average,
        abrasion_term=angular,
        abrasion_after=abrasion_after,
        normalized_temperature_delta=temperature_factor,
        limited_temperature_factor=limited,
        grip_output=output,
        derived_reservoir_field=d7d8,
        derived_auxiliary_field=derived_auxiliary,
        wear_floor_crossed=wear_floor_crossed,
        overtemperature_condition=overtemperature_condition,
    )


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "caller": CALLER,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "ambient_bias": KELVIN_BIAS,
        "state_offsets": {
            "temperature_0": "0x7b0",
            "temperature_1": "0x7b8",
            "temperature_2": "0x7c0",
            "reservoir_temperature": "0x7c8",
            "derived_reservoir_temperature": "0x7d8",
            "abrasion_state": "0x7f8",
            "grip_output": "0x800",
            "accumulator": "0x850",
        },
        "wheel_object": {
            "base": "this+0x400",
            "stride": "0x150",
            "caller_expression": "((double*)this+0x740)-0x68"
        },
        "inputs": {
            "activity": "0x740",
            "spin_measure": "0x350",
            "spin_activity_scale": "0x818",
            "factor_control": "0x3e0",
            "heat_shape": "0x668",
            "heat_gain": "0x820",
            "steering_a_product": "0x808*0x730",
            "steering_b_base": "0x780",
            "steering_b_product": "0x788*0x738",
            "steering_b_reference": "0x7d8",
            "steering_b_gain": "0x810",
            "sqrt_argument_base": "0x670 + 1 + 0xc12c24",
            "ambient_coupling_a": "0x838",
            "ambient_coupling_b": "0x830",
            "reservoir_exchange": "0x840",
            "average_temperature_scale": "0x760",
            "temp_reference": "0x758",
            "temp_gain_negative": "0x768",
            "temp_gain_positive": "0x770",
            "temp_alert_threshold": "0x778",
            "abrasion_scale": "0x848",
            "abrasion_accumulator": "0x850",
            "wear_enabled_flag": "0x798",
            "global_wear_scale": "FUN_00749340(0xc12c80) * 0xc12f38",
            "wear_state": "0x7f8",
            "derived_reservoir_scale": "0x7d0",
            "derived_aux_scale": "0x7f0",
            "derived_aux_bias": "0x7e8",
            "output_limit_reference": "0x790",
        "normalization_reference": "0x780 + 0x788*0x738",
        },
        "call_order": [
            "compute ambient Kelvin values",
            "compute source_heat and secondary_source",
            "clamp steering terms",
            "derive three temperature fractions",
            "update temperature_0/1/2 with ambient and reservoir transfers",
            "clamp reservoir_temperature to [273.16, 546.32]",
            "recompute derived reservoir field and average temperature",
            "accumulate abrasion term and update wear state when enabled",
            "derive final bounded temperature factor and output at +0x800",
        ],
        "explicit_unknowns": [
            "physical units of all scalar coefficients",
            "semantic names for the three temperature nodes",
            "exact runtime event side effects from FUN_0070e2c0",
            "decompiler-aliased parameter-stack behavior around param_3 in the tail",
        ],
        "status": "source/disassembly-backed three-node thermal arithmetic boundary with conservative unknowns",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "CALLER",
    "SOURCE_LINE",
    "KELVIN_BIAS",
    "RESERVOIR_CLAMP_LOW",
    "RESERVOIR_CLAMP_HIGH",
    "WEAR_FLOOR",
    "ThermalIntegratorInputs",
    "ThermalIntegratorStep",
    "compute_source_heat",
    "compute_shape_factor",
    "compute_temperature_fractions",
    "update_three_node_temperatures",
    "compute_grip_output",
    "integrate_wheel_thermal_state",
    "build_contract",
]
