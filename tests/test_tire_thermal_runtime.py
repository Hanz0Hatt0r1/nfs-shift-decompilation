from tire_model_runtime import build_curve_contract
from tire_thermal_runtime import THERMAL_FIELDS, build_thermal_contract, compute_thermal_step

def test_contract_offsets():
    c = build_thermal_contract()
    assert c["function"] == "FUN_00760b50"
    fields = {x["name"]: x for x in c["fields"]}
    assert fields["temperature_state"]["offset"] == 0x888
    assert fields["thermal_reserve"]["offset"] == 0x8B0
    assert fields["reserve_floor"]["offset"] == 0x8C8
    assert len(THERMAL_FIELDS) == 14

def test_low_reserve_uses_floor_normalization():
    r = compute_thermal_step(
        dt=0.1, spin_measure=10.0, spin_heat_scale=2.0,
        accumulated_heat_scale=3.0, speed_transfer_base=1.0,
        speed_transfer_rate=0.5, longitudinal_velocity=-4.0,
        ambient_temperature_a=20.0, ambient_temperature_b=30.0,
        temperature_state=290.0, reference_temperature=300.0,
        thermal_reserve=5.0, reserve_depletion_capacity=2.0,
        reserve_floor=10.0, thermal_tolerance=2.0,
        failure_gain_base=4.0, overheat_scale=1.0)
    assert r.source_heat == 60.0
    assert r.thermal_reserve_after == 5.0
    assert r.rate == r.net_heat / 10.0
    assert r.temperature_after == 290.0 + r.rate * 0.1

def test_over_reserve_cubic_depletion_and_failure_gain():
    r = compute_thermal_step(
        dt=0.01, spin_measure=1.0, spin_heat_scale=1.0,
        accumulated_heat_scale=1.0, speed_transfer_base=0.0,
        speed_transfer_rate=0.0, longitudinal_velocity=0.0,
        ambient_temperature_a=20.0, ambient_temperature_b=20.0,
        temperature_state=1.0, reference_temperature=1.0,
        thermal_reserve=100.0, reserve_depletion_capacity=1.0,
        reserve_floor=10.0, thermal_tolerance=2.0,
        failure_gain_base=8.0, overheat_scale=0.5,
        failure_rng=lambda: 1.0)
    assert r.thermal_reserve_after == 99.995
    assert r.failure_gain_after == 8.0
    assert r.temperature_after != 1.0

def test_exhausted_reserve_zeroes_rate_and_failure_gain():
    r = compute_thermal_step(
        dt=1.0, spin_measure=100.0, spin_heat_scale=100.0,
        accumulated_heat_scale=100.0, speed_transfer_base=0.0,
        speed_transfer_rate=0.0, longitudinal_velocity=0.0,
        ambient_temperature_a=20.0, ambient_temperature_b=20.0,
        temperature_state=300.0, reference_temperature=250.0,
        thermal_reserve=11.0, reserve_depletion_capacity=100.0,
        reserve_floor=10.0, thermal_tolerance=2.0,
        failure_gain_base=8.0, overheat_scale=1.0)
    assert r.thermal_reserve_after == 0.0
    assert r.failure_gain_after == 0.0
    assert r.rate == 0.0
    assert r.temperature_after == 300.0

def test_phase_361_loader_boundary_is_corrected():
    assert build_curve_contract()["functions"]["load_tbc"] == "FUN_007a32a0"
