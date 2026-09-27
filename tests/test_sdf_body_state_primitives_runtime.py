import pytest

import sdf_body_state_primitives_runtime as runtime


def test_body_coefficient_initialization_matches_retail_reciprocals():
    result = runtime.initialize_body_coefficients((2.0, 4.0, 8.0))
    assert result["ready"] is True
    assert result["input_float32"] == [2.0, 4.0, 8.0]
    assert result["reciprocal"] == [0.5, 0.25, 0.125]
    assert result["storage"]["input"] == ["+0x128", "+0x12c", "+0x130"]
    assert result["storage"]["reciprocal"] == ["+0x138", "+0x140", "+0x148"]
    assert result["next_stage"] == "FUN_007ba7e0"


def test_body_coefficient_initialization_rejects_zero_values():
    with pytest.raises(ValueError, match="non-zero"):
        runtime.initialize_body_coefficients((1.0, 0.0, 2.0))


def test_point_accumulator_delta_uses_world_point_relative_to_body_origin():
    result = runtime.point_accumulator_delta(
        (5.0, 7.0, 9.0),
        (1.0, 2.0, 3.0),
        (2.0, 4.0, 8.0),
        sign=1,
    )
    assert result["lever_arm"] == [4.0, 5.0, 6.0]
    assert result["linear_delta"] == [2.0, 4.0, 8.0]
    assert result["angular_delta"] == [16.0, -20.0, 6.0]
    assert result["source_function"] == "FUN_007ba9e0"


def test_point_accumulator_delta_negative_mirrors_source_update():
    result = runtime.point_accumulator_delta(
        (5.0, 7.0, 9.0),
        (1.0, 2.0, 3.0),
        (2.0, 4.0, 8.0),
        sign=-1,
    )
    assert result["linear_delta"] == [-2.0, -4.0, -8.0]
    assert result["angular_delta"] == [-16.0, 20.0, -6.0]


def test_body_state_primitives_contract_keeps_source_boundaries():
    result = runtime.describe_sdf_body_state_primitives()
    assert result["coefficient_init"]["function"] == "FUN_007ba860"
    assert result["point_accumulator"]["function"] == "FUN_007ba9e0"
    assert result["point_accumulator"]["relative_point_rule"] == "point - body_origin"
