import pytest
from tire_thermal_batch_runtime import (
    WHEEL_ORDER, WHEEL_STRIDE, build_thermal_batch_contract,
    compute_four_wheel_thermal_step,
)

def _state(temperature: float, reserve: float) -> dict:
    return {
        "dt": 0.01, "spin_measure": 1.0, "spin_heat_scale": 1.0,
        "accumulated_heat_scale": 1.0, "speed_transfer_base": 0.0,
        "speed_transfer_rate": 0.0, "longitudinal_velocity": 0.0,
        "ambient_temperature_a": 20.0, "ambient_temperature_b": 20.0,
        "temperature_state": temperature, "reference_temperature": temperature,
        "thermal_reserve": reserve, "reserve_depletion_capacity": 1.0,
        "reserve_floor": 10.0, "thermal_tolerance": 2.0,
        "failure_gain_base": 8.0, "overheat_scale": 0.5,
        "failure_rng": lambda: 1.0,
    }

def test_contract_records_four_wheel_call_topology():
    c = build_thermal_batch_contract()
    assert c["caller"] == "FUN_00770e80"
    assert c["callee"] == "FUN_00760b50"
    assert c["wheel_stride"] == WHEEL_STRIDE == 0xA80
    assert c["wheel_order"] == list(WHEEL_ORDER)
    assert c["ordering"]["invocations"] == 4

def test_batch_preserves_retail_wheel_order_and_independence():
    states = {w: _state(300.0 + i, 100.0) for i, w in enumerate(WHEEL_ORDER)}
    result = compute_four_wheel_thermal_step(states)
    assert tuple(row.wheel for row in result.wheels) == WHEEL_ORDER
    assert result.temperatures_after["FRONTLEFT"] != result.temperatures_after["FRONTRIGHT"]
    assert all(0.0 < value < 100.0 for value in result.reserves_after.values())

def test_batch_rejects_missing_or_unknown_wheels():
    states = {w: _state(300.0, 100.0) for w in WHEEL_ORDER}
    states.pop("REARLEFT")
    with pytest.raises(ValueError):
        compute_four_wheel_thermal_step(states)
    states = {w: _state(300.0, 100.0) for w in WHEEL_ORDER}
    states["SPARE"] = _state(300.0, 100.0)
    with pytest.raises(ValueError):
        compute_four_wheel_thermal_step(states)
