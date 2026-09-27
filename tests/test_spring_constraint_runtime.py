import pytest

from spring_constraint_runtime import (
    BODY_OFFSET,
    COLLISION_LENGTH_OFFSET,
    ELEMENT_ARRAY_OFFSET,
    ELEMENT_COUNT_OFFSET,
    ELEMENT_STRIDE,
    FORMAT,
    HEAD_OFFSET,
    SPRING_PARAM_A_OFFSET,
    SPRING_PARAM_B_OFFSET,
    TYPE_OFFSET,
    Vec3,
    SpringElementInput,
    build_spring_constraint_contract,
    collision_window_allows,
    compute_projection,
    compute_spring_force,
    compute_type01_response,
    direction_for_type,
    sign_crossing_blocks,
)


def test_contract_freezes_element_storage_and_property_offsets():
    c = build_spring_constraint_contract()
    assert c["format"] == FORMAT == "SHIFT.SpringConstraintRuntime/1"
    assert c["function"] == "FUN_0075489c"
    assert c["element_storage"] == {
        "array_offset": 0x100,
        "stride": 0x90,
        "count_offset": 0xA8,
        "object_size": 0x90,
    }
    assert c["property_offsets"]["SpringType"] == TYPE_OFFSET == 0x10
    assert c["property_offsets"]["SpringHead"] == HEAD_OFFSET == 0x30
    assert c["property_offsets"]["SpringBody"] == BODY_OFFSET == 0x48
    assert c["property_offsets"]["CollisionLength"] == COLLISION_LENGTH_OFFSET == 0x60
    assert c["property_offsets"]["SpringParamsA"] == SPRING_PARAM_A_OFFSET == 0x68
    assert c["property_offsets"]["SpringParamsB"] == SPRING_PARAM_B_OFFSET == 0x70


def test_direction_normalization_and_projection_are_explicit():
    assert direction_for_type(1, (0.0, 3.0, 4.0)) == Vec3(0.0, 0.6, 0.8)
    assert compute_projection((0.0, 3.0, 4.0), (0.0, 3.0, 4.0), spring_type=1) == pytest.approx(5.0)


def test_collision_length_window_matches_source_gate():
    assert collision_window_allows(collision_length=0.0, projection=0.0) is True
    assert collision_window_allows(collision_length=5.0, projection=4.9) is False
    assert collision_window_allows(collision_length=5.0, projection=-5.0) is True


def test_type01_response_is_directional_and_sign_suppression_is_separate():
    response, body_projection = compute_type01_response(
        projection=2.0,
        body_relative_vector=(0.0, 1.0, 0.0),
        direction=(0.0, 1.0, 0.0),
        spring_type=1,
        spring_param_a=3.0,
        spring_param_b=4.0,
    )
    assert body_projection == 1.0
    assert response == 10.0
    assert sign_crossing_blocks(
        collision_length=5.0, projection=2.0, response_scalar=-1.0
    ) is True


def test_type0_and_type1_share_the_same_force_construction():
    for spring_type in (0, 1):
        result = compute_spring_force(
            SpringElementInput(
                spring_type=spring_type,
                direction=Vec3(2.0, 0.0, 0.0),
                body_relative_vector=Vec3(3.0, 0.0, 0.0),
                collision_length=0.0,
                spring_param_a=3.0,
                spring_param_b=4.0,
            )
        )
        assert result.applied is True
        if spring_type == 0:
            assert result.projection == 6.0
            assert result.force == Vec3(84.0, 0.0, 0.0)
            assert result.response_scalar == 42.0
        else:
            assert result.projection == 3.0
            assert result.force == Vec3(21.0, 0.0, 0.0)
            assert result.response_scalar == 21.0


def test_type2_adds_body_relative_vector_and_directional_component():
    result = compute_spring_force(
        SpringElementInput(
            spring_type=2,
            direction=Vec3(1.0, 0.0, 0.0),
            body_relative_vector=Vec3(0.0, 2.0, 0.0),
            collision_length=0.0,
            spring_param_a=3.0,
            spring_param_b=4.0,
        )
    )
    assert result.force == Vec3(0.0, 8.0, 0.0)


def test_unsupported_type_is_explicitly_blocked():
    result = compute_spring_force(
        SpringElementInput(
            spring_type=7,
            direction=Vec3(1.0, 0.0, 0.0),
            body_relative_vector=Vec3(0.0, 1.0, 0.0),
            collision_length=0.0,
            spring_param_a=1.0,
            spring_param_b=1.0,
        )
    )
    assert result.applied is False
    assert result.reason == "unsupported spring type"


def test_zero_direction_is_rejected():
    with pytest.raises(ValueError):
        direction_for_type(1, (0.0, 0.0, 0.0))
