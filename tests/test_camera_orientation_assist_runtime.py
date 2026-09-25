from camera_orientation_assist_runtime import (
    OrientationAssistInputs,
    cross3,
    describe_orientation_assist,
    normalize3,
)


def test_cross_product_matches_source_component_order():
    assert cross3([1, 0, 0], [0, 1, 0]) == (0.0, 0.0, 1.0)


def test_normalize3_reports_length_and_unit_vector():
    unit, length = normalize3([3, 0, 4])
    assert length == 5.0
    assert unit == (0.6, 0.0, 0.8)


def test_orientation_assist_guard_requires_profile_rate_and_delta():
    result = describe_orientation_assist(
        OrientationAssistInputs(
            profile_enabled=True,
            profile_rate=0.0,
            delta=2.0,
            vehicle_direction=[1, 0, 0],
            negative_velocity=[0, 1, 0],
        )
    )
    assert result["status"] == "guarded-off"


def test_orientation_assist_builds_first_cross_from_normalized_direction():
    result = describe_orientation_assist(
        OrientationAssistInputs(
            profile_enabled=True,
            profile_rate=1.0,
            delta=2.0,
            vehicle_direction=[1, 0, 0],
            negative_velocity=[0, 1, 0],
            angle_sample=0.2,
        ),
        helper_900c40=0.5,
        helper_900b10=0.25,
    )
    assert result["vectors"]["vehicle_direction_normalized"] == (1.0, 0.0, 0.0)
    assert result["vectors"]["first_cross"] == (0.0, 0.0, 1.0)
    assert result["first_norm_clamp"] == 1.0


def test_orientation_assist_uses_second_axis_norm_epsilon():
    result = describe_orientation_assist(
        OrientationAssistInputs(
            profile_enabled=True,
            profile_rate=1.0,
            delta=2.0,
            vehicle_direction=[1, 0, 0],
            negative_velocity=[0, 0, 0],
        )
    )
    assert result["vectors"]["second_cross_norm"] == 0.0
    assert any(x["action"] == "FUN_007840a0" for x in result["actions"])


def test_orientation_assist_keeps_final_output_helpers_opaque():
    result = describe_orientation_assist(
        OrientationAssistInputs(
            profile_enabled=True,
            profile_rate=1.0,
            delta=2.0,
            vehicle_direction=[1, 0, 0],
            negative_velocity=[0, 1, 0],
        ),
        quaternion_output=[1, 0, 0, 0],
        helper_7bdb0_output=[1, 2, 3, 4],
    )
    assert any(x["action"] == "FUN_004f8040" for x in result["actions"])
    assert any(x["action"] == "FUN_00449930" for x in result["actions"])
