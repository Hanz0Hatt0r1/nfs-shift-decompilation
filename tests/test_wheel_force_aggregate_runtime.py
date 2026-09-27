import pytest
from wheel_force_aggregate_runtime import Vec3, AggregateRecord, aggregate, build_contract

def test_three_record_aggregate_and_matrix_x():
    r=AggregateRecord(2.0,Vec3(0,1,0),3.0,Vec3(1,0,0),Vec3(0,0,2))
    body=Vec3(0,0,1)
    total, torque, value=aggregate([r,r,r],body,[1,0,0,0,1,0,0,0,1],3.0)
    assert total.as_tuple()==pytest.approx((9.0,6.0,0.0))
    assert torque.as_tuple()==pytest.approx((-6.0,18.0,0.0))
    assert value==pytest.approx(3.0)

def test_contract_freezes_record_shape():
    c=build_contract()
    assert c["record_count"]==3
    assert c["record_stride"]=="0x150"
    assert c["per_record"][0]=="vector at +0xb0 * scalar at +0x00"
    assert "body position" in c["per_record"][3]
