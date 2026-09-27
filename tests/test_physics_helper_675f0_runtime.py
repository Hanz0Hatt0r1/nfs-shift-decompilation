import pytest
from physics_helper_675f0_runtime import Vec3, contact_force_scalar, contact_gate, gap_factor, normalize_planar, planar_length_xz, speed_factor, submission_scales, update_distance_state, build_contract

def test_planar_and_normalized_vector():
    v=Vec3(3.0,7.0,4.0)
    assert planar_length_xz(v)==pytest.approx(5.0)
    assert normalize_planar(v).as_tuple()==pytest.approx((0.6,0.0,0.8))

def test_distance_state_uses_exact_lowpass_and_cap():
    assert update_distance_state(10.0,20.0,100.0)==pytest.approx(10.0+10.0*(0.5/100.5))
    assert update_distance_state(10.0,250.0,100.0)==pytest.approx(200.0)

def test_speed_factor_thresholds():
    speed,factor=speed_factor(13.888889,0.0)
    assert speed==pytest.approx(13.888889) and factor==pytest.approx(0.0)
    assert speed_factor(13.888889+5.5555553,0.0)[1]==pytest.approx(1.0)
    assert speed_factor(40.0,0.0)[1]==pytest.approx(1.0)

def test_contact_gate_is_strict():
    assert contact_gate(10.0,2.0)
    assert not contact_gate(5.0,2.0)
    assert not contact_gate(10.0,1.0)
    assert not contact_gate(200.0,2.0)

def test_force_shape_and_submission_scales():
    shape=gap_factor(7.0,5.0)
    assert shape==pytest.approx(1.0)
    force=contact_force_scalar(10.0,2.0,0.5,3.0,0.25)
    assert force==pytest.approx((15.0-2.0)*1.5*0.5*3.0*0.25)
    assert submission_scales(force,2.0)==pytest.approx((force*2.0,force*2.0*-0.05))

def test_contract_freezes_boundaries():
    c=build_contract()
    assert c["gate"]=="distance < 200 && distance > 5 && speed > 1"
    assert c["submission"]["consumer"]=="FUN_007ba9e0"
