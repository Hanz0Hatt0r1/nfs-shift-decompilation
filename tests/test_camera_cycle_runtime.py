from camera_cycle_runtime import (
    cycle_camera_id,
    describe_cycle_update,
)


def test_next_input_increments_camera_id():
    result = cycle_camera_id(
        current_id=1,
        camera_count=5,
        next_input_active=True,
        previous_input_active=False,
    )
    assert result["selected_id"] == 2
    assert result["direction"] == "increment"
    assert result["changed"] is True


def test_next_input_wraps_at_camera_count():
    result = cycle_camera_id(
        current_id=4,
        camera_count=5,
        next_input_active=True,
        previous_input_active=False,
    )
    assert result["selected_id"] == 0


def test_previous_input_decrements_when_next_is_inactive():
    result = cycle_camera_id(
        current_id=3,
        camera_count=5,
        next_input_active=False,
        previous_input_active=True,
    )
    assert result["selected_id"] == 2
    assert result["direction"] == "decrement"


def test_previous_input_wraps_below_zero():
    result = cycle_camera_id(
        current_id=0,
        camera_count=5,
        next_input_active=False,
        previous_input_active=True,
    )
    assert result["selected_id"] == 4


def test_next_input_has_priority_when_both_probes_are_active():
    result = cycle_camera_id(
        current_id=1,
        camera_count=5,
        next_input_active=True,
        previous_input_active=True,
    )
    assert result["selected_id"] == 2
    assert result["direction"] == "increment"


def test_no_input_is_noop():
    result = cycle_camera_id(
        current_id=2,
        camera_count=5,
        next_input_active=False,
        previous_input_active=False,
    )
    assert result["changed"] is False
    assert result["actions"] == []


def test_changed_cycle_sets_dirty_and_activates_current_group():
    result = describe_cycle_update(
        manager_active_camera_id=1,
        camera_count=5,
        active_group=7,
        next_input_active=True,
        previous_input_active=False,
    )
    assert result["actions"][0] == {"action": "write +0xb4", "value": 1}
    assert result["actions"][1]["arguments"] == {
        "group": 7,
        "group_repeat": 7,
        "camera_id": 2,
    }


def test_camera_count_must_be_positive():
    try:
        cycle_camera_id(
            current_id=0,
            camera_count=0,
            next_input_active=True,
            previous_input_active=False,
        )
    except ValueError:
        return
    raise AssertionError("expected positive camera_count validation")
