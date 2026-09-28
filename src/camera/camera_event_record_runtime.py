"""Evidence-backed serialization of CameraManager event records.

FUN_0080b9b0 builds the type-5 camera-command record consumed by FUN_0080c710:
event byte +4 is 5, byte +5 is copied from the camera event channel at
queue-object +0x244, and six dword payload values are copied at +0xc..+0x20.

FUN_0080ccb0 builds a type-3 record with two payload dwords and an explicit
channel byte taken from the manager +0x7e4 field.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraEventRecordRuntime/1"


def _u32(value: Any) -> int:
    value = int(value)
    if value < -(1 << 31) or value > 0xFFFFFFFF:
        raise ValueError(f"value outside 32-bit range: {value}")
    return value & 0xFFFFFFFF


def build_camera_command_event(
    command: Sequence[Any],
    *,
    channel: int,
) -> dict[str, Any]:
    """Reproduce FUN_0080b9b0's type-5 record layout."""
    if len(command) != 6:
        raise ValueError(f"camera command event requires six dwords, got {len(command)}")
    payload = [_u32(value) for value in command]
    return {
        "format": FORMAT,
        "version": 1,
        "header": {
            "type": 5,
            "channel": int(channel) & 0xFF,
            "payload_offset": 0x0C,
            "payload_dword_count": 6,
        },
        "payload_words": payload,
        "source_layout": {
            "type_byte_offset": 0x04,
            "channel_byte_offset": 0x05,
            "payload_range": [0x0C, 0x20],
            "builder": "FUN_0080b9b0",
            "queue_channel_source": "queue object +0x244",
        },
    }


def build_type3_camera_event(
    first: Any,
    second: Any,
    *,
    channel: int,
    byte_parameter: int,
) -> dict[str, Any]:
    """Reproduce the field writes in FUN_0080ccb0 for event type 3."""
    byte_parameter = int(byte_parameter)
    if not 0 <= byte_parameter <= 0xFF:
        raise ValueError("byte_parameter must fit one byte")
    return {
        "format": FORMAT,
        "version": 1,
        "header": {
            "type": 3,
            "channel": int(channel) & 0xFF,
            "payload_offset": 0x0C,
            "payload_dword_count": 2,
        },
        "payload_words": [_u32(first), _u32(second)],
        "byte_parameter": byte_parameter,
        "source_layout": {
            "type_byte_offset": 0x04,
            "channel_byte_offset": 0x05,
            "first_payload_word_offset": 0x0C,
            "second_payload_word_offset": 0x10,
            "builder": "FUN_0080ccb0",
            "channel_source": "manager +0x7e4",
        },
        "limitations": [
            "the semantic meaning of the two type-3 payload words is unresolved",
        ],
    }
