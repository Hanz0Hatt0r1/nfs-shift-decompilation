from static_camera_collision_runtime import (
    describe_static_camera_constructor,
    interpolate_static_camera_sample,
    trace_forward_collision_sampling,
    trace_reverse_collision_sampling,
)


def test_static_camera_constructor_preserves_two_shake_rates():
    result = describe_static_camera_constructor()
    assert result["shake"]["+0x84"]["rate_bits"] == 0x40C00000
    assert result["shake"]["+0xD8"]["rate_bits"] == 0x41800000
    assert result["shake"]["+0x84"]["target_bits"] == [
        0x3C23D70A, 0x3C23D70A, 0x3BA3D70A
    ]


def test_interpolated_sample_forwards_to_135b0():
    result = interpolate_static_camera_sample(
        static_camera="camera",
        alpha=0.25,
    )
    assert result["actions"][0]["action"] == "FUN_00814670"
    assert result["actions"][1]["action"] == "FUN_008135b0"


def test_forward_collision_sampling_uses_negative_point_zero_five_steps():
    result = trace_forward_collision_sampling(
        initial_alpha=1.0,
        max_steps=3,
        initial_query_result=-1.0,
        sampled_query_results=[-1.0, 1.0],
    )
    assert result["status"] == "hit"
    assert result["alpha"] == 0.9
    assert result["action"] == "FUN_00813750"


def test_forward_collision_sampling_calls_14690_when_exhausted():
    result = trace_forward_collision_sampling(
        initial_alpha=0.1,
        max_steps=5,
        initial_query_result=-1.0,
        sampled_query_results=[-1.0, -1.0],
    )
    assert result["action"] == "FUN_00814690"


def test_reverse_collision_sampling_uses_positive_point_zero_five_steps():
    result = trace_reverse_collision_sampling(
        initial_alpha=0.0,
        max_steps=3,
        initial_query_result=-1.0,
        sampled_query_results=[-1.0, 1.0],
    )
    assert result["status"] == "hit"
    assert result["alpha"] == 0.1
    assert result["action"] == "FUN_00813750"


def test_reverse_collision_sampling_calls_146e0_when_exhausted():
    result = trace_reverse_collision_sampling(
        initial_alpha=0.9,
        max_steps=5,
        initial_query_result=-1.0,
        sampled_query_results=[-1.0, -1.0],
    )
    assert result["action"] == "FUN_008146e0"
