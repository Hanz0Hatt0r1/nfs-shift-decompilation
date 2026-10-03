import pytest

from fun_0076d100_anchor_sequence_runtime import (
    CONTACT_FACTOR,
    CONTACT_OUTER,
    CONTACT_RESPONSE,
    FORMAT,
    MOTION_READ_GATE,
    TAIL,
    WHEEL_UPDATE,
    contract,
    execute_required_anchor_sequence,
)


def test_contract_preserves_only_proven_relative_anchor_orders():
    payload = contract()
    assert payload["format"] == FORMAT
    assert payload["required_pass_order"] == [
        CONTACT_FACTOR,
        WHEEL_UPDATE,
        CONTACT_RESPONSE,
        TAIL,
    ]
    assert payload["required_tail_order"] == [CONTACT_OUTER, MOTION_READ_GATE]
    assert payload["complete_fun_0076d100_semantics"] is False
    assert payload["complete_fun_00769ef0_semantics"] is False
    assert payload["intervening_local_work_modeled"] is False
    assert payload["callback_bodies_external"] is True


def test_leaf_anchor_callbacks_run_in_proven_nested_order():
    observed = []
    result = execute_required_anchor_sequence(
        lambda: observed.append(CONTACT_FACTOR),
        lambda: observed.append(WHEEL_UPDATE),
        lambda: observed.append(CONTACT_RESPONSE),
        lambda: observed.append(CONTACT_OUTER),
        lambda: observed.append(MOTION_READ_GATE),
    )
    expected = [
        CONTACT_FACTOR,
        WHEEL_UPDATE,
        CONTACT_RESPONSE,
        CONTACT_OUTER,
        MOTION_READ_GATE,
    ]
    assert observed == expected
    assert list(result.events) == expected
    assert result.tail_invocation_count == 1


@pytest.mark.parametrize("missing_index", range(5))
def test_missing_anchor_callback_fails_closed(missing_index):
    callbacks = [lambda: None for _ in range(5)]
    callbacks[missing_index] = None
    with pytest.raises(ValueError, match="all callback boundaries"):
        execute_required_anchor_sequence(*callbacks)
