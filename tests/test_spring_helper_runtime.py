import pytest

from spring_helper_runtime import (
    build_spring_helper_contract,
    compute_spring_gap,
    update_spring_gap_state,
)


def test_contract_preserves_source_gap_offsets_and_abi_anomaly():
    c = build_spring_helper_contract()
    assert c["state_offsets"]["current_gap"] == 0x248
    assert c["state_offsets"]["previous_gap"] == 0x250
    assert c["state_offsets"]["crossing_flag"] == 0x260
    assert c["state_offsets"]["trigger_value"] == 0x258
    assert c["boundary_offsets"]["lower_boundary"] == 0x238
    assert c["boundary_offsets"]["upper_boundary"] == 0x240
    assert c["caller_abi_anomaly"]["caller_consumes_x87_after_call"] is True
    assert c["caller_abi_anomaly"]["return_semantics"] == "unresolved"


def test_gap_uses_upper_boundary_until_displacement_exceeds_it():
    assert compute_spring_gap(
        displacement=5.0, lower_boundary=2.0, upper_boundary=5.0
    ) == 0.0
    assert compute_spring_gap(
        displacement=4.0, lower_boundary=2.0, upper_boundary=5.0
    ) == 1.0
    assert compute_spring_gap(
        displacement=7.0, lower_boundary=2.0, upper_boundary=5.0
    ) == 5.0


def test_transition_copies_previous_gap_and_latches_trigger_value():
    step = update_spring_gap_state(
        spring_type=0,
        displacement=4.0,
        lower_boundary=2.0,
        upper_boundary=5.0,
        previous_gap=-0.25,
        trigger_value=-3.5,
    )
    assert step.previous_gap == -0.25
    assert step.current_gap == 1.0
    assert step.transition_triggered is True
    assert step.trigger_value == -3.5


def test_non_crossing_state_does_not_latch_trigger():
    step = update_spring_gap_state(
        spring_type=2,
        displacement=6.0,
        lower_boundary=2.0,
        upper_boundary=5.0,
        previous_gap=1.0,
        trigger_value=4.0,
    )
    assert step.current_gap == 4.0
    assert step.transition_triggered is False
    assert step.trigger_value is None


def test_invalid_nonfinite_or_negative_type_is_rejected():
    with pytest.raises(ValueError):
        compute_spring_gap(
            displacement=float("nan"),
            lower_boundary=1.0,
            upper_boundary=2.0,
        )
    with pytest.raises(ValueError):
        update_spring_gap_state(
            spring_type=-1,
            displacement=1.0,
            lower_boundary=0.0,
            upper_boundary=2.0,
            previous_gap=0.0,
            trigger_value=0.0,
        )
