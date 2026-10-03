import math

import pytest

from fun_00770e80_two_half_step_schedule_runtime import (
    FORMAT,
    HALF_STEP,
    PHYSICS_PASS,
    POST_HALF_STEP,
    contract,
    execute_two_half_step_schedule,
)


def test_contract_preserves_only_proven_anchor_schedule():
    payload = contract()
    assert payload["format"] == FORMAT
    assert payload["pass_count"] == 2
    assert payload["per_pass_order"] == [PHYSICS_PASS, HALF_STEP, POST_HALF_STEP]
    assert payload["complete_fun_00770e80_semantics"] is False
    assert payload["rendered_frame_cadence_proven"] is False
    assert payload["callback_bodies_external"] is True


def test_exact_two_pass_order_and_half_timestep():
    observed = []

    def physics_pass(index):
        observed.append((PHYSICS_PASS, index, None))

    def half_step(index, timestep):
        observed.append((HALF_STEP, index, timestep))

    def post_half_step(index):
        observed.append((POST_HALF_STEP, index, None))

    result = execute_two_half_step_schedule(0.5, physics_pass, half_step, post_half_step)
    assert result.outer_timestep == 0.5
    assert result.half_timestep == 0.25
    assert observed == [
        (PHYSICS_PASS, 0, None),
        (HALF_STEP, 0, 0.25),
        (POST_HALF_STEP, 0, None),
        (PHYSICS_PASS, 1, None),
        (HALF_STEP, 1, 0.25),
        (POST_HALF_STEP, 1, None),
    ]
    assert [(event.function, event.pass_index, event.timestep) for event in result.events] == observed


def test_negative_zero_timestep_is_preserved():
    observed = []
    result = execute_two_half_step_schedule(
        -0.0,
        lambda index: None,
        lambda index, timestep: observed.append(timestep),
        lambda index: None,
    )
    assert math.copysign(1.0, result.half_timestep) == -1.0
    assert len(observed) == 2
    assert all(math.copysign(1.0, value) == -1.0 for value in observed)


def test_missing_callbacks_and_nonfinite_timestep_fail_closed():
    noop_pass = lambda index: None
    noop_half = lambda index, timestep: None
    noop_post = lambda index: None

    with pytest.raises(ValueError, match="outer timestep"):
        execute_two_half_step_schedule(float("nan"), noop_pass, noop_half, noop_post)
    with pytest.raises(ValueError, match="callback boundaries"):
        execute_two_half_step_schedule(1.0, None, noop_half, noop_post)
    with pytest.raises(ValueError, match="callback boundaries"):
        execute_two_half_step_schedule(1.0, noop_pass, None, noop_post)
    with pytest.raises(ValueError, match="callback boundaries"):
        execute_two_half_step_schedule(1.0, noop_pass, noop_half, None)
