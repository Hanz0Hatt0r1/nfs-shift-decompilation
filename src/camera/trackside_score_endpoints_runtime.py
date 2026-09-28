"""Trackside score, event, copy and spline-endpoint helpers.

Recovered from FUN_008154d0, FUN_00815590, FUN_008155f0, FUN_00815620,
FUN_008156b0, FUN_008160f0 and FUN_00816120.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.TracksideCameraScoreRuntime/1"
FLT_MAX = 3.4028235e38


def select_trackside_score(
    *,
    candidate_scores: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_008154d0's minimum-score and negative early-exit loop."""
    best = FLT_MAX
    selected = -1
    trace: list[dict[str, Any]] = []
    for index, raw_score in enumerate(candidate_scores):
        score = float(raw_score)
        if score < best:
            best = score
            selected = index
        trace.append({
            "index": index,
            "score": score,
            "best_after": best,
        })
        if best < 0.0:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "trackside-score",
                "status": "negative-early-exit",
                "score": best,
                "selected": selected,
                "trace": trace,
                "evidence": {
                    "function": "FUN_008154d0",
                    "initial_best": FLT_MAX,
                },
            }
    if not candidate_scores:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "trackside-score",
            "status": "empty",
            "score": FLT_MAX,
            "selected": -1,
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "trackside-score",
        "status": "complete",
        "score": best,
        "selected": selected,
        "trace": trace,
        "evidence": {
            "function": "FUN_008154d0",
            "initial_best": FLT_MAX,
        },
    }


def describe_camera_script_event(
    *,
    event_name: str,
    resolved_event: Any | None,
    source_event: Any,
) -> dict[str, Any]:
    """Trace FUN_00815590's script-event lookup/dispatch."""
    actions = [
        {
            "action": "read event string",
            "source": "param_1 + 0x04",
            "fallback": "DAT_00aa9b60",
            "value": event_name,
        },
        {
            "action": "FUN_0069d8f0",
            "frame_stack": "+0x140",
            "name": event_name,
        },
    ]
    if resolved_event is not None:
        actions.append({
            "action": "FUN_00671100",
            "event_object": resolved_event,
            "source_event": source_event,
        })
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "script-event",
            "status": "dispatched",
            "actions": actions,
            "evidence": {"function": "FUN_00815590"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "script-event",
        "status": "not-found",
        "actions": actions,
        "evidence": {"function": "FUN_00815590"},
    }


def resolve_shake_target_metadata(
    *,
    active_target_data: Any,
    attached_target_id: int,
    fallback_metadata: Sequence[float],
    direct_metadata: Sequence[float] | None,
) -> dict[str, Any]:
    """Trace FUN_008155f0's attached-target vs camera-manager fallback."""
    if active_target_data not in (None, 0) and int(attached_target_id) != -1:
        metadata = list(map(float, direct_metadata)) if direct_metadata is not None else [0.0] * 3
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "shake-target-metadata",
            "status": "attached-target",
            "result": metadata,
            "action": {
                "action": "FUN_00812de0",
                "target_id": int(attached_target_id),
            },
        }
    if len(fallback_metadata) != 3:
        raise ValueError("fallback_metadata requires three values")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "shake-target-metadata",
        "status": "camera-manager-fallback",
        "result": list(map(float, fallback_metadata)),
        "action": {
            "action": "FUN_008142c0",
        },
    }


def copy_static_camera_payload(
    source: Mapping[int, Any],
) -> dict[str, Any]:
    """Reproduce FUN_00815620's exact copied field groups."""
    scalar_offsets = [
        0x00, 0x04, 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c,
        0x24, 0x28, 0x2c, 0x30, 0x34,
    ]
    byte_offsets = [0x20, 0x21, 0x38]
    missing = [x for x in [*scalar_offsets, *byte_offsets] if x not in source]
    if missing:
        raise ValueError(f"missing static-camera source offsets: {missing}")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-copy",
        "scalar_copy": {f"+0x{x:02x}": source[x] for x in scalar_offsets},
        "byte_copy": {f"+0x{x:02x}": source[x] for x in byte_offsets},
        "nested_blocks": [
            {"destination": "+0x3c", "source": "+0x3c", "helper": "FUN_00814340"},
            {"destination": "+0x90", "source": "+0x90", "helper": "FUN_00814340"},
        ],
        "evidence": {"function": "FUN_00815620"},
    }


def static_camera_property_registration() -> dict[str, Any]:
    """Reproduce FUN_008156b0's reflected property registration.

    Duplicate property offsets/names are intentionally retained because the
    executable registers them in that order.
    """
    props = [
        {"name_symbol": "DAT_00aaf9fc", "type_id": 0, "offset": 0x60, "flags": 3},
        {"name_symbol": "DAT_00afc8b8", "type_id": 0x10, "offset": 0x20, "flags": 3},
        {"name": "QuatOri", "type_id": 0x19, "offset": 0x10, "flags": 3},
        {"name_symbol": "DAT_00b15fa0", "type_id": 10, "offset": 0x64, "flags": 3},
        {"name_symbol": "DAT_00aaf9c8", "type_id": 3, "offset": 0x68, "flags": 3},
        {"name": "NearZ", "type_id": 10, "offset": 0x6c, "flags": 3},
        {"name_symbol": "DAT_00b15f90", "type_id": 10, "offset": 0x70, "flags": 3},
        {"name": "Target", "type_id": 0x0D, "offset": 0x78, "flags": 3},
        {"name": "TargetOffset", "type_id": 0x10, "offset": 0x84, "flags": 3},
        {"name": "LookAt", "type_id": 0x0D, "offset": 0x80, "flags": 3},
        {"name": "LookAtOffset", "type_id": 0x10, "offset": 0x90, "flags": 3},
        {"name": "ProximityShakeFrequency", "type_id": 10, "offset": 0x9c, "flags": 3},
        {"name": "ProximityShakeMagnitude", "type_id": 10, "offset": 0xa0, "flags": 3},
        {"name": "ProximityShakeMinDistance", "type_id": 10, "offset": 0xa4, "flags": 3},
        {"name": "ProximityShakeMaxDistance", "type_id": 10, "offset": 0xa8, "flags": 3},
        {"name": "ProximityShakeMinSpeed", "type_id": 10, "offset": 0xac, "flags": 3},
        {"name": "ProximityShakeMaxSpeed", "type_id": 10, "offset": 0xb0, "flags": 3},
        {"name": "ShakeMagnitude", "type_id": 10, "offset": 0xc0, "flags": 3},
        {"name": "ShakeMagnitudeMin", "type_id": 10, "offset": 0xbc, "flags": 3},
        {"name": "ShakeFrequency", "type_id": 10, "offset": 0xb8, "flags": 3},
        {"name": "ShakeFrequencyMin", "type_id": 10, "offset": 0xb4, "flags": 3},
        {"name": "ShakeScreenVelocity", "type_id": 10, "offset": 0xb8, "flags": 3},
        {"name": "ShakeScreenVelocityMin", "type_id": 10, "offset": 0xb4, "flags": 3},
        {"name": "SoundEffect", "type_id": 0, "offset": 0xcc, "flags": 3},
        {"name": "LODDistanceMultiplier", "type_id": 10, "offset": 0xd0, "flags": 3},
        {"name": "OverridedBy", "type_id": 0, "offset": 0xd4, "flags": 3},
        {"name": "UserDataName", "type_id": 0, "offset": 0xdc, "flags": 3},
        {"name": "UserDataValue", "type_id": 10, "offset": 0xe0, "flags": 3},
        {"name": "ActiveAreas", "type_id": 6, "offset": 0x2c, "flags": 3},
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-property-registration",
        "registration_object": "DAT_00b8ded8",
        "properties": props,
        "evidence": {
            "function": "FUN_008156b0",
            "registration_helper": "FUN_0063a280",
            "active_areas_callbacks": {
                "save": "FUN_008144f0",
                "load": "FUN_008145c0",
            },
        },
    }


def endpoint_readiness(*, start_gate: int, end_gate: int) -> dict[str, Any]:
    """Reproduce FUN_008160f0: return 1 if either spline-end gate succeeds."""
    if int(start_gate) != 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "endpoint-readiness",
            "result": 1,
            "source": "FUN_00821870",
        }
    if int(end_gate) != 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "endpoint-readiness",
            "result": 1,
            "source": "FUN_00821890",
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "endpoint-readiness",
        "result": 0,
    }


def build_forward_endpoint_record(
    *,
    record_position: Sequence[float],
    record_scalar_1c: float,
    record_scalar_20: float,
    current_index: int,
    default_scalar_20: float,
) -> dict[str, Any]:
    """Reproduce FUN_00816120's 9-value output record."""
    if len(record_position) != 3:
        raise ValueError("record_position requires three values")
    value = float(record_scalar_20)
    if value == 0.0:
        value = float(default_scalar_20)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "forward-endpoint-record",
        "output": {
            "+0x00": float(record_position[0]),
            "+0x04": float(record_position[1]),
            "+0x08": float(record_position[2]),
            "+0x0c": 1.0,
            "+0x10": int(current_index) - 2,
            "+0x14": int(current_index),
            "+0x18": 1.0,
            "+0x1c": 0.0,
            "+0x20": value,
        },
        "evidence": {
            "function": "FUN_00816120",
            "record_stride": 0x24,
            "source_scalar_1c": "+0x1c",
            "source_scalar_20": "+0x20",
        },
    }
