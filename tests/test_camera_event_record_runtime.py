import pytest

from camera_event_record_runtime import build_camera_command_event, build_type3_camera_event


def test_type5_camera_command_record_has_exact_six_dword_payload():
    result = build_camera_command_event([0, 1, 0, 0, 7, 3], channel=0x102)
    assert result["header"]["type"] == 5
    assert result["header"]["channel"] == 2
    assert result["header"]["payload_offset"] == 0x0C
    assert result["header"]["payload_dword_count"] == 6
    assert result["payload_words"] == [0, 1, 0, 0, 7, 3]


def test_type5_payload_preserves_raw_unsigned_bits():
    result = build_camera_command_event([-1, -2, 0, 0, 7, 3], channel=1)
    assert result["payload_words"][:2] == [0xFFFFFFFF, 0xFFFFFFFE]


def test_type5_requires_exact_six_words():
    with pytest.raises(ValueError):
        build_camera_command_event([0, 1, 2], channel=1)


def test_type3_builder_matches_two_payload_words():
    result = build_type3_camera_event(
        0xFFFFFFFF,
        7,
        channel=0x101,
        byte_parameter=255,
    )
    assert result["header"]["type"] == 3
    assert result["header"]["channel"] == 1
    assert result["payload_words"] == [0xFFFFFFFF, 7]
    assert result["byte_parameter"] == 255


def test_type3_byte_parameter_is_one_byte():
    with pytest.raises(ValueError):
        build_type3_camera_event(1, 2, channel=1, byte_parameter=256)
