import struct
import pytest

from bab_animation_runtime import (
    BABAnimationDecodeError,
    _Cursor,
    channel_sample_policy,
    parse_animation_channel,
    parse_bab_animation_payload,
)


def _channel_prefix(kind: int, count: int, *, name: bytes = b"") -> bytes:
    encoded = struct.pack("<I", len(name)) + name
    encoded += b"\0" * ((-len(name)) & 3)
    return struct.pack("<II", kind, count) + struct.pack("<I", kind) + encoded + struct.pack("<I", 0)


def test_type8_is_time_value_float_pair():
    data = _channel_prefix(8, 2)
    data += struct.pack("<ff", 0.0, 10.0)
    data += struct.pack("<ff", 1.0, 20.0)
    channel = parse_animation_channel(_Cursor(data))
    assert channel["spec"]["name"] == "timed_scalar"
    assert channel["payload"]["keys"][0]["time"] == 0.0
    assert channel["payload"]["keys"][0]["value"] == 10.0
    assert channel["payload"]["keys"][1]["time"] == 1.0
    assert channel["payload"]["keys"][1]["value"] == 20.0


def test_type1_is_quaternion_slerp_channel():
    assert channel_sample_policy(1)["interpolation"] == "quaternion_slerp"


def test_type6_is_explicitly_unresolved_axis_order():
    policy = channel_sample_policy(6)
    assert "axis/order" in policy["semantic_status"]


def test_mode2_payload_with_zero_bones_decodes():
    payload = struct.pack("<IIII", 0, 0, 0, 0)
    payload += struct.pack("<III", 0, 0, 0) + struct.pack("<I", 0) + struct.pack("<I", 0)
    result = parse_bab_animation_payload(payload, mode=2)
    assert result["ready"] is True
    assert result["status"] == "decoded"
    assert result["consumed_bytes"] == len(payload)


def test_mode0_presence_bytes_select_channels():
    payload = struct.pack("<IIII", 0, 1, 0, 0)
    payload += struct.pack("<III", 0, 0, 0) + struct.pack("<I", 0) + struct.pack("<I", 0)
    for kind in (0, 1, 7):
        payload += b"\1" + _channel_prefix(kind, 1)
        if kind == 0:
            payload += struct.pack("<fff", 1.0, 2.0, 3.0)
        elif kind == 1:
            payload += struct.pack("<ffff", 0.0, 0.0, 0.0, 1.0)
        else:
            payload += struct.pack("<f", 2.0)
    result = parse_bab_animation_payload(payload, mode=0)
    assert result["body"]["arrays"][0]["channels"][0]["spec"]["name"] == "uniform_vec3"
    assert result["body"]["arrays"][1]["channels"][0]["spec"]["name"] == "uniform_quaternion"
    assert result["body"]["arrays"][2]["channels"][0]["spec"]["name"] == "uniform_scalar"


def test_truncated_payload_is_blocked_in_non_strict_mode():
    result = parse_bab_animation_payload(b"\0" * 8, mode=2, strict=False)
    assert result["ready"] is False
    assert "bab-animation:decode:" in result["blockers"][0]


def test_truncated_payload_raises_in_strict_mode():
    with pytest.raises(BABAnimationDecodeError):
        parse_bab_animation_payload(b"\0" * 8, mode=2)
