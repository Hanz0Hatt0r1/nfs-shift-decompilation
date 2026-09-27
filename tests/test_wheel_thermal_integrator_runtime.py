import pytest

from wheel_thermal_integrator_runtime import (
    KELVIN_BIAS,
    RESERVOIR_CLAMP_HIGH,
    RESERVOIR_CLAMP_LOW,
    ThermalIntegratorInputs,
    build_contract,
    compute_grip_output,
    compute_shape_factor,
    compute_source_heat,
    compute_temperature_fractions,
    integrate_wheel_thermal_state,
)


def _inputs(**overrides):
    values = dict(
        dt=0.1,
        ambient_a=20.0,
        ambient_b=30.0,
        spin_measure=10.0,
        spin_activity_scale=2.0,
        activity=0.0,
        factor_control=0.0,
        heat_shape=2.0,
        heat_gain=1.0,
        steering_a_product=0.0,
        steering_b_product=0.0,
        steering_b_base=300.0,
        steering_b_reference=300.0,
        steering_b_gain=1.0,
        sqrt_input_base=0.0,
        global_constant_c12c24=0.0,
        ambient_coupling_a=0.0,
        ambient_coupling_b=0.0,
        reservoir_temperature=300.0,
        temperature_0=300.0,
        temperature_1=300.0,
        temperature_2=300.0,
        reservoir_scale=1.0,
        reservoir_exchange=0.0,
        temp_reference=300.0,
        temp_gain_negative=0.1,
        temp_gain_positive=0.1,
        temp_alert_threshold=350.0,
        abrasion_scale=0.0,
        abrasion_accumulator=0.0,
        wear_event_enabled=True,
        grip_state=1.0,
        derived_reservoir_scale=1.0,
        derived_aux_scale=1.0,
        derived_aux_bias=0.0,
        output_limit_reference=1.0,
        wear_enabled=True,
        global_wear_scale=1.0,
    )
    values.update(overrides)
    return ThermalIntegratorInputs(**values)


def test_contract_freezes_function_and_wheel_substructure():
    c = build_contract()
    assert c["function"] == "FUN_00755a60"
    assert c["caller"] == "FUN_00770e80"
    assert c["wheel_object"]["base"] == "this+0x400"
    assert c["wheel_object"]["stride"] == "0x150"
    assert c["state_offsets"]["temperature_0"] == "0x7b0"
    assert c["state_offsets"]["temperature_1"] == "0x7b8"
    assert c["state_offsets"]["temperature_2"] == "0x7c0"
    assert c["state_offsets"]["reservoir_temperature"] == "0x7c8"


def test_source_heat_zero_and_positive_paths():
    assert compute_source_heat(
        spin_measure=10.0, spin_activity_scale=2.0, activity=0.0
    ) == 0.0
    assert compute_source_heat(
        spin_measure=-10.0, spin_activity_scale=2.0, activity=1.5
    ) == 30.0


def test_shape_factor_matches_sqrt_then_quarter_floor_adjustment():
    assert compute_shape_factor(factor_control=0.0) == 0.75
    assert compute_shape_factor(factor_control=0.25) == 0.25
    assert compute_shape_factor(factor_control=4.0) == 0.0


def test_temperature_fraction_partition_matches_source_expression():
    fractions = compute_temperature_fractions(
        steering_a=0.0, steering_b=0.0, dt=0.1
    )
    assert fractions == pytest.approx((0.05, 0.05, 0.05))


def test_reservoir_exchange_is_applied_sequentially_across_three_nodes():
    result = integrate_wheel_thermal_state(
        _inputs(
            reservoir_temperature=310.0,
            reservoir_exchange=1.0,
        )
    )
    assert result.temperatures_after == pytest.approx(
        (301.0, 300.9, 300.81)
    )
    assert result.reservoir_after == pytest.approx(307.29)


def test_positive_activity_adds_source_heat_and_secondary_source():
    result = integrate_wheel_thermal_state(
        _inputs(activity=1.0)
    )
    assert result.source_heat == pytest.approx(20.0)
    assert result.shape_factor == pytest.approx(0.75)
    assert result.secondary_source == pytest.approx(3.0)
    assert result.temperatures_after == pytest.approx(
        (301.15, 301.15, 301.15)
    )


def test_reservoir_clamp_and_derived_fields_are_preserved():
    result = integrate_wheel_thermal_state(
        _inputs(
            reservoir_temperature=1000.0,
            reservoir_exchange=0.0,
            derived_reservoir_scale=2.0,
            derived_aux_scale=3.0,
            derived_aux_bias=4.0,
        )
    )
    assert result.reservoir_after == RESERVOIR_CLAMP_HIGH
    assert result.derived_reservoir_field == pytest.approx(
        2.0 * RESERVOIR_CLAMP_HIGH
    )
    assert result.derived_auxiliary_field == pytest.approx(
        3.0 * 2.0 * RESERVOIR_CLAMP_HIGH + 4.0
    )


def test_wear_floor_is_enforced_when_abrasion_exceeds_remaining_state():
    result = integrate_wheel_thermal_state(
        _inputs(
            dt=1.0,
            abrasion_scale=1.0,
            global_wear_scale=1.0,
            grip_state=1.0,
        )
    )
    assert result.abrasion_term > 0.0
    assert result.abrasion_after == 0.6875
    assert result.wear_floor_crossed is True


def test_final_output_uses_max_one_temperature_factor():
    factor, limited, output = compute_grip_output(
        average_temperature=300.0,
        reservoir_temperature=300.0,
        temp_reference=300.0,
        temp_gain_negative=0.1,
        temp_gain_positive=0.1,
        output_limit_reference=1.0,
        normalization_reference=300.0,
        grip_state=1.0,
    )
    assert factor == pytest.approx(0.0)
    assert limited == 1.0
    assert output == pytest.approx(0.5)


def test_kelvin_constants_match_retail_values():
    assert KELVIN_BIAS == 273.16
    assert RESERVOIR_CLAMP_LOW == 273.16
    assert RESERVOIR_CLAMP_HIGH == 546.32
