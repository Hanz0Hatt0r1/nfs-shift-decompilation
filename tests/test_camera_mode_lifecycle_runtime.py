from camera_mode_lifecycle_runtime import (
    INACTIVE_MODE,
    describe_mode_command,
    enter_camera_mode,
    leave_camera_mode,
)


def test_mode_commands_preserve_raw_ids():
    assert describe_mode_command(1)["function"] == "FUN_008182f0"
    assert describe_mode_command(5)["function"] == "FUN_008186a0"
    assert describe_mode_command(0)["inactive_function"] == "FUN_00818400"


def test_enter_mode_requires_collection():
    result = enter_camera_mode(
        mode=2,
        collection_present=False,
        reverse=True,
    )
    assert result["status"] == "ignored"


def test_enter_mode_sets_common_state_and_reverse_dispatch():
    result = enter_camera_mode(
        mode=4,
        collection_present=True,
        reverse=True,
    )
    assert result["state"]["+0x244"] == 4
    assert any(
        a["action"] == "FUN_00817440" and a["args"] == [0, 1]
        for a in result["actions"]
    )


def test_enter_mode_contains_output_matrix_and_valid_flag_writes():
    result = enter_camera_mode(
        mode=5,
        collection_present=True,
        reverse=False,
    )
    assert any(a["action"] == "clear output matrix" for a in result["actions"])
    assert any(a["action"] == "set output-valid" for a in result["actions"])


def test_leave_mode_restores_inactive_mode():
    result = leave_camera_mode(
        mode=3,
        collection_present=True,
        clear_output=True,
        reset_collection=True,
        reset_selector=True,
        reset_helper=3,
    )
    assert any(a.get("value") == INACTIVE_MODE for a in result["actions"])
    assert any(a["action"] == "FUN_00818000" for a in result["actions"])
