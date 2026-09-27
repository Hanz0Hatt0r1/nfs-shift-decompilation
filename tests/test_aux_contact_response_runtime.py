import pytest

from aux_contact_response_runtime import (
    ACTIVE_FLAG_OFFSET,
    BODY_BASE_OFFSET,
    BODY_TRANSFORM_OFFSET,
    RECORD_DIRECTIONAL_CURVE_OFFSET,
    RECORD_GAIN_OFFSET,
    RECORD_POINT_OFFSET,
    RECORD_SCALE_OFFSET,
    Vec3,
    build_contract,
    build_local_response,
)


def test_negative_relative_z_builds_exact_squared_response():
    out = build_local_response(
        record_active=True,
        transformed_record_point=(5.0, 4.0, 1.0),
        reference_point=(2.0, 3.0, 5.0),
        directional_multiplier=0.5,
        gain=4.0,
        scale=2.0,
    )
    assert out.relative_point == Vec3(3.0, 1.0, -4.0)
    assert out.square_negative_z == pytest.approx(16.0)
    assert out.local_response.as_tuple() == pytest.approx((0.0, 32.0, 32.0))


def test_nonnegative_relative_z_is_zero_response():
    out = build_local_response(
        record_active=True,
        transformed_record_point=(0.0, 0.0, 3.0),
        reference_point=(0.0, 0.0, 2.0),
        directional_multiplier=7.0,
        gain=8.0,
        scale=9.0,
    )
    assert out.relative_point.z == pytest.approx(1.0)
    assert out.local_response.as_tuple() == (0.0, 0.0, 0.0)


def test_inactive_record_is_zero_response():
    out = build_local_response(
        record_active=False,
        transformed_record_point=(0.0, 0.0, -4.0),
        reference_point=(0.0, 0.0, 0.0),
        directional_multiplier=2.0,
        gain=3.0,
        scale=4.0,
    )
    assert out.local_response.as_tuple() == (0.0, 0.0, 0.0)


def test_contract_freezes_record_offsets_and_caller_instances():
    c = build_contract()
    assert c["record"]["active_flag_offset"] == "+0x00"
    assert c["record"]["point_offset"] == "+0x68"
    assert c["record"]["directional_curve_offset"] == "+0x48"
    assert c["record"]["gain_offset"] == "+0x38"
    assert c["record"]["scale_offset"] == "+0x40"
    assert c["caller_instances"]["first"] == "this + 0x37d8"
    assert c["caller_instances"]["second"] == "this + 0x3858"
    assert c["caller_instances"]["stride"] == "0x80"
    assert ACTIVE_FLAG_OFFSET == 0
    assert RECORD_POINT_OFFSET == 0x68
    assert RECORD_DIRECTIONAL_CURVE_OFFSET == 0x48
    assert RECORD_GAIN_OFFSET == 0x38
    assert RECORD_SCALE_OFFSET == 0x40
    assert BODY_BASE_OFFSET == 0x33A0
    assert BODY_TRANSFORM_OFFSET == 0xD4


def test_invalid_point_cardinality_rejected():
    with pytest.raises(ValueError):
        build_local_response(
            record_active=True,
            transformed_record_point=(1.0, 2.0),
            reference_point=(3.0, 4.0, 5.0),
            directional_multiplier=1.0,
            gain=1.0,
            scale=1.0,
        )
