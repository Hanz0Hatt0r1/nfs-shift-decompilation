import pytest

from collision_query_runtime import (
    CACHE_CONTACT_HEIGHT_OFFSET,
    CACHE_NORMAL_OFFSET,
    CACHE_RECORD_SIZE,
    CACHE_TRIANGLE_A_OFFSET,
    CACHE_TRIANGLE_B_OFFSET,
    CACHE_TRIANGLE_C_OFFSET,
    QUERY_MAX_AUX,
    QUERY_Y_BIAS,
    QUERY_Y_TOLERANCE,
    Vec3,
    CollisionSurfaceRecord,
    apply_query_result,
    build_contract,
    build_wheel_query_record,
    caller_depth_or_fallback,
    emit_query_vector,
)

def test_contract_freezes_query_offsets_and_constants():
    contract = build_contract()
    assert contract["function"] == "FUN_007b0710"
    assert contract["caller"] == "FUN_00765c40"
    assert contract["query_record"]["cache_handle_offset"] == 0x30
    assert contract["query_record"]["param3_cache_flag"] == 1
    assert QUERY_Y_BIAS == pytest.approx(0.15)
    assert QUERY_Y_TOLERANCE == pytest.approx(200.35)
    assert QUERY_MAX_AUX == pytest.approx(9.999999933815813e36)
    assert CACHE_RECORD_SIZE == 0x58
    assert CACHE_NORMAL_OFFSET == 0x10
    assert CACHE_CONTACT_HEIGHT_OFFSET == 0x1C
    assert CACHE_TRIANGLE_A_OFFSET == 0x20
    assert CACHE_TRIANGLE_B_OFFSET == 0x2C
    assert CACHE_TRIANGLE_C_OFFSET == 0x38

def test_wheel_query_applies_only_proven_y_bias():
    record = build_wheel_query_record((10.0, 20.0, 30.0), cached_handle=1234)
    assert record.query_position.as_tuple() == pytest.approx((10.0, 20.15, 30.0))
    assert record.y_tolerance == pytest.approx(200.35)
    assert record.max_aux == pytest.approx(9.999999933815813e36)
    assert record.cache_handle == 1234
    assert record.param3 == 1

def test_hit_writes_normal_and_contact_height_and_reuses_matching_cache():
    surface = CollisionSurfaceRecord(
        address_token=1234,
        query_point=Vec3(10.0, 20.15, 30.0),
        normal=Vec3(0.0, 1.0, 0.0),
        contact_height=19.75,
        triangle_a=Vec3(9.0, 19.0, 29.0),
        triangle_b=Vec3(11.0, 19.0, 29.0),
        triangle_c=Vec3(10.0, 19.0, 31.0),
        hit_count=4,
    )
    query = build_wheel_query_record((10.0, 20.0, 30.0), cached_handle=1234)
    out = apply_query_result(query, surface=surface)
    assert out.hit
    assert out.normal.as_tuple() == (0.0, 1.0, 0.0)
    assert out.contact_height == pytest.approx(19.75)
    assert out.reused_cache
    assert CACHE_RECORD_SIZE >= CACHE_TRIANGLE_C_OFFSET + 12

def test_miss_uses_identity_up_normal():
    query = build_wheel_query_record((0.0, 1.0, 2.0))
    out = apply_query_result(query, surface=None)
    assert not out.hit
    assert emit_query_vector(None).as_tuple() == (0.0, 1.0, 0.0)
    assert out.contact_height is None

def test_caller_hit_scalar_is_original_y_minus_contact_height():
    surface = CollisionSurfaceRecord(
        address_token=1,
        query_point=Vec3(0.0, 1.15, 0.0),
        normal=Vec3(0.0, 1.0, 0.0),
        contact_height=0.8,
        triangle_a=Vec3(0.0, 0.0, 0.0),
        triangle_b=Vec3(1.0, 0.0, 0.0),
        triangle_c=Vec3(0.0, 0.0, 1.0),
    )
    out = apply_query_result(build_wheel_query_record((0.0, 1.0, 0.0)), surface=surface)
    assert caller_depth_or_fallback(original_world_y=1.0, query_output=out, fallback_value=7.0) == pytest.approx(0.2)

def test_caller_miss_scalar_uses_fallback():
    out = apply_query_result(build_wheel_query_record((0.0, 1.0, 0.0)), surface=None)
    assert caller_depth_or_fallback(original_world_y=1.0, query_output=out, fallback_value=7.0) == pytest.approx(7.0)

def test_invalid_world_position_rejected():
    with pytest.raises(ValueError):
        build_wheel_query_record((1.0, 2.0))
