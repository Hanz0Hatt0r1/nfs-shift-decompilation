import pytest

from wheel_longitudinal_velocity_runtime import (
    WHEEL_BASE,
    WHEEL_COUNT,
    WHEEL_STRIDE,
    Vec3,
    apply_longitudinal_subtraction,
    batch_from_precomputed_wheels,
    build_contract,
    extract_wheel_longitudinal,
)


def _obs(index: int, x: float) -> object:
    return extract_wheel_longitudinal(
        wheel_index=index,
        shared_velocity=Vec3(10.0, 20.0, 30.0),
        local_velocity=Vec3(x, x + 1.0, x + 2.0),
        reconstructed_world_velocity=Vec3(1.0, 2.0, 3.0),
    )


def test_contract_freezes_wheel_stride_and_transform_chain():
    c = build_contract()
    assert c["function"] == "FUN_00755f80"
    assert c["caller"] == "FUN_00763570"
    assert c["wheel_layout"] == {"base": WHEEL_BASE, "stride": WHEEL_STRIDE, "count": WHEEL_COUNT}
    assert c["transform_chain"]["extract"] == "longitudinal_component = local_vec3.x"
    assert c["shared_physics"]["velocity_offset"] == 0x48
    assert c["shared_physics"]["pose_offset"] == 0xD4


def test_extracts_first_local_component_and_subtracts_reconstructed_vector():
    obs = _obs(2, 7.5)
    assert obs.wheel_object_offset == 0x400 + 2 * 0xA80
    assert obs.longitudinal_component == 7.5
    assert obs.shared_velocity_after == Vec3(9.0, 18.0, 27.0)


def test_subtraction_helper_matches_source_vector_update():
    assert apply_longitudinal_subtraction(
        shared_velocity=(10.0, 20.0, 30.0),
        reconstructed_world_velocity=(1.0, 2.0, 3.0),
    ) == Vec3(9.0, 18.0, 27.0)


def test_four_wheel_batch_preserves_order():
    batch = batch_from_precomputed_wheels([_obs(i, float(i + 1)) for i in range(4)])
    assert batch.reported_components == (1.0, 2.0, 3.0, 4.0)


def test_rear_pair_average_matches_caller_branch():
    batch = batch_from_precomputed_wheels(
        [_obs(0, 1.0), _obs(1, 2.0), _obs(2, 10.0), _obs(3, 6.0)],
        rear_pair_average_enabled=True,
        mode=0,
        global_config_byte=True,
    )
    assert batch.reported_components == pytest.approx((1.0, 2.0, 8.0, 8.0))


def test_rear_pair_average_is_guarded():
    batch = batch_from_precomputed_wheels(
        [_obs(0, 1.0), _obs(1, 2.0), _obs(2, 10.0), _obs(3, 6.0)],
        rear_pair_average_enabled=True,
        mode=1,
        global_config_byte=True,
    )
    assert batch.reported_components == (1.0, 2.0, 10.0, 6.0)


def test_invalid_batch_and_wheel_index_are_rejected():
    with pytest.raises(ValueError):
        _obs(4, 1.0)
    with pytest.raises(ValueError):
        batch_from_precomputed_wheels([_obs(i, float(i)) for i in range(3)])
