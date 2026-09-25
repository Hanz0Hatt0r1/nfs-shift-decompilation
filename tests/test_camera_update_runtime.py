from camera_update_runtime import (
    CameraUpdateState,
    elapsed_u32,
    resolve_camera_timestamp,
    step_camera_update_timing,
)


def test_timestamp_uses_base_value_without_high_resolution_flag():
    assert resolve_camera_timestamp(100) == 100


def test_timestamp_adds_high_resolution_delta_when_bit_is_enabled():
    assert resolve_camera_timestamp(
        100,
        high_resolution_enabled=True,
        high_resolution_delta=7,
    ) == 107


def test_first_update_is_not_suppressed_and_advances_cursor_before_dispatch():
    state, result = step_camera_update_timing(
        CameraUpdateState(time_cursor=90, time_initialized=False),
        current_timestamp=100,
        active_channel=1,
        events=[{"type_word": 99, "channel": 1}],
    )
    assert result["status"] == "updated"
    assert result["previous_timestamp"] == 90
    assert result["elapsed_u32"] == 10
    assert result["event_dispatch"]["accepted_count"] == 1
    assert state.time_cursor == 100
    assert state.time_initialized is True


def test_repeated_update_inside_twenty_tick_hex_window_is_suppressed():
    state = CameraUpdateState(time_cursor=100, time_initialized=True)
    new_state, result = step_camera_update_timing(
        state,
        current_timestamp=119,
        events=[{"type_word": 5, "channel": 0, "payload": [0, 1, 0, 0, 7, 3]}],
        active_channel=0,
    )
    assert result["status"] == "suppressed"
    assert result["elapsed_u32"] == 19
    assert result["event_dispatch"] is None
    assert new_state == state


def test_update_at_exact_window_boundary_is_processed():
    state, result = step_camera_update_timing(
        CameraUpdateState(time_cursor=100, time_initialized=True),
        current_timestamp=120,
        events=[],
    )
    assert result["status"] == "updated"
    assert result["elapsed_u32"] == 20
    assert state.time_cursor == 120


def test_negative_signed_difference_becomes_large_uint32_elapsed_for_controller():
    assert elapsed_u32(10, 20) == 0xFFFFFFF6
