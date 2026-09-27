import pytest

from body_point_transform_runtime import (
    ANGULAR_X_OFFSET,
    ANGULAR_Y_OFFSET,
    ANGULAR_Z_OFFSET,
    BODY_POSITION_X_OFFSET,
    BODY_POSITION_Y_OFFSET,
    BODY_POSITION_Z_OFFSET,
    BODY_TRANSLATION_X_OFFSET,
    BODY_TRANSLATION_Y_OFFSET,
    BODY_TRANSLATION_Z_OFFSET,
    BodyTransform,
    Vec3,
    build_contract,
    transform_point,
    transform_point_relative,
)


def test_fun_007537b0_matches_cross_product_plus_translation():
    body = BodyTransform(
        angular=Vec3(1.0, 2.0, 3.0),
        body_position=Vec3(10.0, 20.0, 30.0),
        translation=Vec3(100.0, 200.0, 300.0),
    )
    result = transform_point(body, (4.0, 5.0, 6.0))
    assert result.as_tuple() == pytest.approx((97.0, 206.0, 297.0))


def test_fun_00753810_subtracts_body_position_first():
    body = BodyTransform(
        angular=Vec3(1.0, 2.0, 3.0),
        body_position=Vec3(1.0, 1.0, 1.0),
        translation=Vec3(0.0, 0.0, 0.0),
    )
    result = transform_point_relative(body, (4.0, 5.0, 6.0))
    assert result.as_tuple() == pytest.approx((-2.0, 4.0, -2.0))


def test_zero_angular_vector_returns_translation():
    body = BodyTransform(
        angular=Vec3(0.0, 0.0, 0.0),
        body_position=Vec3(2.0, 3.0, 4.0),
        translation=Vec3(10.0, 20.0, 30.0),
    )
    assert transform_point(body, (100.0, 200.0, 300.0)).as_tuple() == (10.0, 20.0, 30.0)


def test_contract_freezes_body_offsets():
    c = build_contract()
    assert c["body_fields"]["angular"] == ["+0x18", "+0x20", "+0x28"]
    assert c["body_fields"]["body_position"] == ["+0x00", "+0x08", "+0x10"]
    assert c["body_fields"]["translation"] == ["+0x78", "+0x80", "+0x88"]
    assert ANGULAR_X_OFFSET == 0x18
    assert ANGULAR_Y_OFFSET == 0x20
    assert ANGULAR_Z_OFFSET == 0x28
    assert BODY_POSITION_X_OFFSET == 0
    assert BODY_POSITION_Y_OFFSET == 0x08
    assert BODY_POSITION_Z_OFFSET == 0x10
    assert BODY_TRANSLATION_X_OFFSET == 0x78
    assert BODY_TRANSLATION_Y_OFFSET == 0x80
    assert BODY_TRANSLATION_Z_OFFSET == 0x88
