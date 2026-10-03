import math

import pytest

from wheel_spring_gap_batch_runtime import (
    FORMAT,
    WheelSpringGapBatchSlotInput,
    build_wheel_spring_gap_batch_contract,
    execute_wheel_spring_gap_batch,
)


def _slot(
    *,
    skip=False,
    relative=(1.0, 0.0, 0.0),
    reference=1.0,
    projection=0.0,
    spring_type=0,
    lower=0.0,
    upper=1.0,
    previous=0.0,
):
    return WheelSpringGapBatchSlotInput(
        skip_flag_nonzero=skip,
        relative_vector=relative,
        reference_length=reference,
        projection_input=projection,
        spring_type=spring_type,
        lower_boundary=lower,
        upper_boundary=upper,
        current_gap_before=previous,
    )


def test_contract_freezes_retail_four_wheel_order_and_scope():
    contract = build_wheel_spring_gap_batch_contract()
    assert contract["format"] == FORMAT == "SHIFT.WheelSpringGapBatchRuntime/1"
    assert contract["function"] == "FUN_00758b50"
    assert contract["pre_helper"] == "FUN_00755950"
    assert contract["spring_helper"] == "FUN_007555b0"
    assert contract["wheel_count"] == 4
    assert contract["iteration_order"] == [0, 1, 2, 3]
    assert contract["caller_x87_runtime_0x548"] == "unresolved_external"
    assert contract["runtime_scheduling"] == "unproven"


def test_batch_matches_exact_three_active_slot_fixture():
    result = execute_wheel_spring_gap_batch(
        (
            _slot(
                relative=(3.0, 4.0, 0.0),
                reference=7.0,
                projection=-1.5,
                lower=0.0,
                upper=3.0,
                previous=-0.25,
            ),
            _slot(skip=True, relative=(0.0, 0.0, 0.0)),
            _slot(
                relative=(0.0, 0.0, 2.0),
                reference=1.0,
                projection=0.25,
                lower=-2.0,
                upper=0.5,
                previous=0.5,
            ),
            _slot(
                relative=(1.0, 2.0, 2.0),
                reference=10.0,
                projection=-4.0,
                lower=1.0,
                upper=6.0,
                previous=-2.0,
            ),
        )
    )

    assert result.processed == (True, False, True, True)
    assert result.processed_order == (0, 2, 3)
    assert result.processed_count == 3
    assert result.slots[1] is None

    first = result.slots[0]
    assert first is not None
    assert first.kinematic.relative_length == 5.0
    assert first.kinematic.distance_error == 2.0
    assert first.kinematic.stored_projection_value == 1.5
    assert first.spring_state.previous_gap == -0.25
    assert first.spring_state.current_gap == 1.0
    assert first.spring_state.transition_triggered is True
    assert first.spring_state.trigger_value == 1.5

    third = result.slots[2]
    assert third is not None
    assert third.kinematic.relative_length == 2.0
    assert third.spring_state.displacement == -1.0
    assert third.spring_state.current_gap == 1.5
    assert third.spring_state.transition_triggered is False
    assert third.spring_state.trigger_value is None

    fourth = result.slots[3]
    assert fourth is not None
    assert fourth.kinematic.relative_length == 3.0
    assert fourth.spring_state.displacement == 7.0
    assert fourth.spring_state.current_gap == 6.0
    assert fourth.spring_state.transition_triggered is True
    assert fourth.spring_state.trigger_value == 4.0


def test_skip_gate_precedes_zero_vector_consumption():
    slots = [_slot(skip=True, relative=(0.0, 0.0, 0.0)) for _ in range(4)]
    result = execute_wheel_spring_gap_batch(slots)
    assert result.processed_count == 0
    assert result.processed == (False, False, False, False)


def test_invalid_size_and_active_nonfinite_fail_closed():
    with pytest.raises(ValueError):
        execute_wheel_spring_gap_batch((_slot(),) * 3)

    slots = [_slot(skip=True) for _ in range(4)]
    slots[2] = _slot(relative=(math.inf, 0.0, 0.0))
    with pytest.raises(ValueError):
        execute_wheel_spring_gap_batch(slots)


def test_active_invalid_spring_type_and_zero_vector_fail_closed():
    slots = [_slot(skip=True) for _ in range(4)]
    slots[0] = _slot(spring_type=-1)
    with pytest.raises(ValueError):
        execute_wheel_spring_gap_batch(slots)

    slots[0] = _slot(relative=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError):
        execute_wheel_spring_gap_batch(slots)
