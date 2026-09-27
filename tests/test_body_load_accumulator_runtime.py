import pytest

from body_load_accumulator_runtime import (
    LINEAR_X_OFFSET,
    LINEAR_Y_OFFSET,
    LINEAR_Z_OFFSET,
    MOMENT_X_OFFSET,
    MOMENT_Y_OFFSET,
    MOMENT_Z_OFFSET,
    Vec3,
    apply_load,
    build_contract,
    point_cross_vector,
    zero_accumulator,
)


def test_cross_product_matches_fun_007baa70():
    result = point_cross_vector(Vec3(1.0, 2.0, 3.0), Vec3(4.0, 5.0, 6.0))
    assert result.as_tuple() == pytest.approx((-3.0, 6.0, -3.0))


def test_apply_load_updates_vector_and_cross_accumulators():
    updated = apply_load(zero_accumulator(), (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    assert updated.point_cross_vector.as_tuple() == pytest.approx((-3.0, 6.0, -3.0))
    assert updated.vector_sum.as_tuple() == pytest.approx((4.0, 5.0, 6.0))


def test_multiple_calls_accumulate_linearly():
    state = zero_accumulator()
    state = apply_load(state, (1.0, 0.0, 0.0), (0.0, 2.0, 0.0))
    state = apply_load(state, (0.0, 1.0, 0.0), (0.0, 0.0, 3.0))
    assert state.point_cross_vector.as_tuple() == pytest.approx((3.0, 0.0, 2.0))
    assert state.vector_sum.as_tuple() == pytest.approx((0.0, 2.0, 3.0))


def test_contract_freezes_storage_offsets_and_no_origin_adjustment():
    contract = build_contract()
    assert contract["function"] == "FUN_007baa70"
    assert contract["storage"]["point_cross_vector"] == [
        "+0x48", "+0x50", "+0x58"
    ]
    assert contract["storage"]["vector_sum"] == [
        "+0x60", "+0x68", "+0x70"
    ]
    assert contract["arithmetic"]["origin_adjustment"] == "none inside FUN_007baa70"
    assert MOMENT_X_OFFSET == 0x48
    assert MOMENT_Y_OFFSET == 0x50
    assert MOMENT_Z_OFFSET == 0x58
    assert LINEAR_X_OFFSET == 0x60
    assert LINEAR_Y_OFFSET == 0x68
    assert LINEAR_Z_OFFSET == 0x70


def test_invalid_vector_cardinality_rejected():
    with pytest.raises(ValueError):
        apply_load(zero_accumulator(), (1.0, 2.0), (3.0, 4.0, 5.0))
