import pytest

from camera_event_stream_runtime import dispatch_camera_event_stream


def test_channel_filter_uses_byte_event_channel():
    result = dispatch_camera_event_stream(
        [
            {"type_word": 5, "channel": 2, "payload": [0, 1, 0, 0, 7, 3]},
            {"type_word": 5, "channel": 1, "payload": [0, 1, 0, 0, 7, 3]},
        ],
        active_channel=1,
    )
    assert result["accepted_count"] == 1
    assert result["filtered_count"] == 1
    assert result["accepted"][0]["type"] == 5
    assert result["accepted"][0]["target_function"] == "FUN_0080e650"


def test_type_five_forwards_payload_to_camera_command_dispatcher():
    result = dispatch_camera_event_stream(
        [{"type_word": 5, "channel": 1, "payload": [10, 4]}],
        active_channel=1,
    )
    command = result["accepted"][0]["camera_command"]
    assert command["operation"] == "external-view-source"
    assert command["arguments"] == {"source": 10, "enabled": 1}


def test_type_five_without_payload_is_blocked():
    result = dispatch_camera_event_stream(
        [{"type_word": 5, "channel": 1}],
        active_channel=1,
    )
    assert result["accepted"][0]["status"] == "blocked-missing-camera-command-payload"


@pytest.mark.parametrize(
    ("event_type", "target"),
    [
        (0, "FUN_0080b910"),
        (1, "FUN_0080bf30"),
        (2, "FUN_0080c230"),
        (3, "FUN_0080c2e0"),
    ],
)
def test_other_known_event_types_keep_source_target_only(event_type, target):
    result = dispatch_camera_event_stream(
        [{"type_word": event_type, "channel": 0, "payload": [1, 2]}],
        active_channel=0,
    )
    row = result["accepted"][0]
    assert row["status"] == "accepted"
    assert row["target_function"] == target
    assert "camera_command" not in row


def test_unknown_event_type_is_explicitly_unsupported():
    result = dispatch_camera_event_stream(
        [{"type_word": 99, "channel": 0}],
        active_channel=0,
    )
    assert result["accepted"][0]["status"] == "unsupported-event-type"


def test_channel_compare_uses_low_byte():
    result = dispatch_camera_event_stream(
        [{"type_word": 5, "channel": 0x101, "payload": [0, 4]}],
        active_channel=1,
    )
    assert result["accepted_count"] == 1
