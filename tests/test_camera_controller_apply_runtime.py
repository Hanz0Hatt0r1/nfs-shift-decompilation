from camera_controller_apply_runtime import (
    CameraControllerApplyState,
    CameraControllerRollback,
    CameraSourceState,
    apply_camera_controller,
    restore_camera_controller,
)


def test_null_camera_source_keeps_controller_state_unchanged():
    state = CameraControllerApplyState(
        enabled=True, camera_source="old", mode=2, refresh_requested=True
    )
    new_state, result = apply_camera_controller(
        state,
        camera_source_present=False,
        camera_source=None,
        mode=1,
        buffer_sub_index=4,
        buffer_sub_flag=1,
        source_state_after_callback=None,
    )
    assert result["status"] == "no-camera-source"
    assert new_state == state


def test_apply_sets_source_mode_and_clears_refresh_flag():
    state, result = apply_camera_controller(
        CameraControllerApplyState(),
        camera_source_present=True,
        camera_source="camera-A",
        mode=2,
        buffer_sub_index=7,
        buffer_sub_flag=1,
        source_state_after_callback=CameraSourceState(
            mode=3, buffer_sub_index=9
        ),
    )
    assert state.enabled is True
    assert state.camera_source == "camera-A"
    assert state.mode == 2
    assert state.refresh_requested is False
    assert result["status"] == "applied"


def test_mode_one_with_sub_index_calls_both_buffer_helpers():
    _, result = apply_camera_controller(
        CameraControllerApplyState(),
        camera_source_present=True,
        camera_source="camera-A",
        mode=1,
        buffer_sub_index=7,
        buffer_sub_flag=0xFF,
        source_state_after_callback=CameraSourceState(mode=1, buffer_sub_index=7),
    )
    actions = result["actions"]
    assert actions[6]["action"].startswith("FUN_0081c920")
    assert actions[7]["action"].startswith("FUN_0081cb60")
    assert actions[7]["sub_flag_signed_i8"] == -1


def test_mode_one_with_minus_one_sub_index_skips_buffer_selection():
    _, result = apply_camera_controller(
        CameraControllerApplyState(),
        camera_source_present=True,
        camera_source="camera-A",
        mode=1,
        buffer_sub_index=-1,
        buffer_sub_flag=0,
        source_state_after_callback=CameraSourceState(mode=1, buffer_sub_index=2),
    )
    assert result["actions"][6]["action"] == "no mode-1 buffer apply"


def test_non_mode_one_skips_buffer_selection_even_with_sub_index():
    _, result = apply_camera_controller(
        CameraControllerApplyState(),
        camera_source_present=True,
        camera_source="camera-A",
        mode=3,
        buffer_sub_index=4,
        buffer_sub_flag=1,
        source_state_after_callback=CameraSourceState(mode=3, buffer_sub_index=4),
    )
    assert result["actions"][6]["action"] == "no mode-1 buffer apply"


def test_post_apply_state_copies_three_values():
    _, result = apply_camera_controller(
        CameraControllerApplyState(),
        camera_source_present=True,
        camera_source="camera-A",
        mode=1,
        buffer_sub_index=3,
        buffer_sub_flag=1,
        source_state_after_callback=CameraSourceState(mode=2, buffer_sub_index=8),
    )
    assert result["post_apply_state"] == {
        "word0_plus_0x2a14": "manager +0x26b0",
        "word1_plus_0x2a18": 2,
        "word2_plus_0x2a1c": 8,
    }


def test_restore_replays_gate_then_apply_in_source_order():
    result = restore_camera_controller(
        CameraControllerRollback(
            previous_mode=1,
            previous_camera_source="camera-old",
            previous_buffer_sub_index=6,
            previous_buffer_sub_flag=0xFF,
            previous_camera_id=10,
        ),
        gate_state={"status": "transition-required"},
    )
    assert result["state_write"]["mode"] == 1
    assert result["gate"]["action"] == "FUN_0080d3d0"
    assert result["gate"]["arguments"]["sub_flag_signed_i8"] == -1
    assert result["reapply"]["action"] == "FUN_0080d300"
    assert result["reapply"]["arguments"]["camera_source"] == "camera-old"
