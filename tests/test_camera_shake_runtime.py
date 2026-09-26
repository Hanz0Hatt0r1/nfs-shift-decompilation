from camera_shake_runtime import (
    ShakeState,
    advance_shake_state,
    describe_shake_step,
    interpolate_block,
    random_unit_vector_from_rng,
    set_first_target,
    set_second_target,
    set_shake_rate,
    smoothstep_cubic,
    zero_shake_state,
)


def test_smoothstep_matches_exact_cubic():
    assert smoothstep_cubic(0.0) == 0.0
    assert smoothstep_cubic(0.5) == 0.5
    assert smoothstep_cubic(1.0) == 1.0


def test_rng_conversion_maps_unit_samples_to_minus_one_one_in_reversed_order():
    assert random_unit_vector_from_rng([0.0, 0.5, 1.0]) == (1.0, 0.0, -1.0)


def test_zero_state_matches_exact_storage_shape():
    result = zero_shake_state()
    assert len(result["writes"]["+0x00..+0x20"]) == 9
    assert result["writes"]["+0x48"] == 0.0
    assert result["writes"]["+0x50"] == 0.0


def test_setters_write_rate_and_target_blocks():
    state = set_shake_rate(ShakeState(), 2.0)
    state = set_first_target(state, [1, 2, 3])
    state = set_second_target(state, [4, 5, 6])
    assert state.rate == 2.0
    assert state.first == (1.0, 2.0, 3.0)
    assert state.second == (4.0, 5.0, 6.0)


def test_advance_decreases_time_until_zero():
    state = ShakeState(time=1.0, rate=2.0)
    advanced = advance_shake_state(
        state,
        delta=0.2,
        rng_first=[0.5, 0.5, 0.5],
        rng_second=[0.5, 0.5, 0.5],
    )
    assert advanced.time == 0.6


def test_advance_reseeds_and_resets_time_when_countdown_expires():
    state = ShakeState(
        first_target=(1, 0, 0),
        second_target=(0, 1, 0),
        time=0.1,
        rate=2.0,
    )
    advanced = advance_shake_state(
        state,
        delta=0.1,
        rng_first=[1, 0, 0],
        rng_second=[0, 1, 0],
    )
    assert advanced.time == 1.0
    assert advanced.first_current == (1, 0, 0)


def test_negative_delta_is_ignored():
    state = ShakeState(time=1.0, rate=2.0)
    assert advance_shake_state(state, delta=-1.0) == state


def test_interpolation_uses_smoothstep_and_amplitude():
    result = interpolate_block(
        current=[0, 0, 0],
        target=[2, 4, 6],
        amplitude=0.5,
        time=0.5,
    )
    assert result == [0.5, 1.0, 1.5]


def test_describe_step_exposes_both_output_read_helpers():
    result = describe_shake_step(
        ShakeState(
            first_current=(0, 0, 0),
            first_target=(1, 0, 0),
            second_current=(0, 0, 0),
            second_target=(0, 1, 0),
            amplitude=2,
            rate=1,
            time=0.5,
        ),
        delta=0,
    )
    assert result["actions"][1]["action"] == "FUN_00823cb0"
    assert result["actions"][2]["action"] == "FUN_00823cd0"
