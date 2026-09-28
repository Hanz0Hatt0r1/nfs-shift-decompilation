"""Evidence-backed camera event-stream boundary from FUN_0080c710.

The runtime iterates an event collection, filters records by the current channel
(byte at event +5 compared with manager +0x580), then dispatches the low byte of
event +4. Event type 5 forwards the record payload beginning at +0xc into
FUN_0080e650.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.CameraEventStreamRuntime/1"

EVENT_TARGETS = {
    0: "FUN_0080b910",
    1: "FUN_0080bf30",
    2: "FUN_0080c230",
    3: "FUN_0080c2e0",
    5: "FUN_0080e650",
}


def dispatch_camera_event_stream(
    events: Iterable[Mapping[str, Any]],
    *,
    active_channel: int,
) -> dict[str, Any]:
    """Reproduce the channel filter and event-type switch in FUN_0080c710."""
    channel = int(active_channel)
    accepted: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []

    for ordinal, event in enumerate(events):
        event_type_word = int(event.get("type_word", event.get("type", -1)))
        event_type = event_type_word & 0xFF
        event_channel = int(event.get("channel", -1)) & 0xFF
        row = {
            "ordinal": ordinal,
            "type_word": event_type_word,
            "type": event_type,
            "channel": event_channel,
        }
        if event_channel != channel:
            row["status"] = "channel-filtered"
            ignored.append(row)
            continue

        row["status"] = "accepted"
        row["target_function"] = EVENT_TARGETS.get(event_type)
        if event_type == 5:
            command = event.get("payload", event.get("command"))
            if command is None:
                row["status"] = "blocked-missing-camera-command-payload"
                row["camera_command"] = None
            else:
                from camera_command_runtime import dispatch_camera_command

                row["camera_command"] = dispatch_camera_command(command)
        elif event_type not in EVENT_TARGETS:
            row["status"] = "unsupported-event-type"
        accepted.append(row)

    return {
        "format": FORMAT,
        "version": 1,
        "active_channel": channel,
        "accepted_count": len(accepted),
        "filtered_count": len(ignored),
        "accepted": accepted,
        "filtered": ignored,
        "evidence": {
            "dispatcher": "FUN_0080c710",
            "event_type_field": "event +0x4 low byte",
            "channel_field": "event +0x5",
            "camera_command_payload": "event +0xc",
            "camera_command_dispatcher": "FUN_0080e650",
        },
        "limitations": [
            "event type 0/1/2/3 target functions are named but their payload semantics are not decoded here",
            "event source/queue ownership is not inferred",
        ],
    }
