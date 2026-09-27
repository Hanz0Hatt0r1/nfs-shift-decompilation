import pytest
from vehicle_rate_response_runtime import rate_geometry, response_595d0, apply_682c0, build_contract

def test_rate_geometry_matches_source_equations():
    g=rate_geometry(3.0,4.0,2.0,1.0)
    assert g.valid
    assert g.speed==pytest.approx(5.0)
    assert g.direction.as_tuple()==pytest.approx((0.6,0.0,0.8))
    assert g.lateral_direction.as_tuple()==pytest.approx((-0.8,0.0,0.6))
    assert g.radius_like==pytest.approx(-25.0)

def test_rate_geometry_low_speed_is_inactive():
    g=rate_geometry(1.0,2.0,2.0,3.0)
    assert not g.valid and g.radius_like==0.0 and g.reciprocal_like==0.0

def test_response_zero_below_angle_limit():
    assert response_595d0(0,0,0.7,0.8,1,0.5235988,1,0,2,3)==0.0

def test_apply_speed_gate_and_accumulator_path():
    assert apply_682c0(4.9,1.0,2.0,3.0,0,5,0,4,1,1,2,100,2)==0.0
    assert isinstance(apply_682c0(10.0,1.0,2.0,3.0,0,5,0,4,1,1,2,100,2),float)

def test_contract():
    c=build_contract()
    assert c["geometry"]["minimum_speed"]==4.0
    assert c["apply"]["accumulator_offsets"]==["body +0x48 += 0","body +0x50 += result","body +0x58 += 0"]
