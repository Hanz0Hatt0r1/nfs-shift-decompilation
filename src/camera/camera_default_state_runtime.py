"""Evidence-backed default state for SHIFT camera data templates.

FUN_00813180 initializes the global CStaticCamData template used by FUN_00813300.
FUN_0081f8c0 derives a CTrackingCamData template by copying that static template and
adding the tracking/spline fields. This module exports only fields whose offsets and
names are independently present in FUN_008156b0/FUN_0081ebc0.

Raw IEEE-754 bit patterns are retained alongside decoded float values so defaults
remain attributable to the executable initializer rather than to a hand-written
unit conversion.
"""

from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.CameraDefaultStateRuntime/1"


def _f32_bits(bits: int) -> dict[str, Any]:
    value = struct.unpack("<f", struct.pack("<I", bits))[0]
    return {"bits_hex": f"0x{bits:08x}", "value": value}


STATIC_CAMERA_DEFAULTS = {
    "Name": "",
    "Pos": [0.0, 0.0, 0.0],
    "QuatOri": [0.0, 0.0, 0.0, 0.0],
    "FOV": _f32_bits(0x3F490FDB),
    "Type": 1,
    "NearZ": _f32_bits(0x3F800000),
    "FarZ": _f32_bits(0x443B8000),
    "Target": 6,
    "LookAt": 6,
    "TargetOffset": [0.0, 0.0, 0.0],
    "LookAtOffset": [0.0, 0.0, 0.0],
    "ProximityShakeFrequency": _f32_bits(0x41400000),
    "ProximityShakeMagnitude": _f32_bits(0x00000000),
    "ProximityShakeMinDistance": _f32_bits(0x40800000),
    "ProximityShakeMaxDistance": _f32_bits(0x41A00000),
    "ProximityShakeMinSpeed": _f32_bits(0x41A00000),
    "ProximityShakeMaxSpeed": _f32_bits(0x42200000),
    "ShakeFrequencyMin": _f32_bits(0x00000000),
    "ShakeFrequency": _f32_bits(0x41400000),
    "ShakeMagnitudeMin": _f32_bits(0x00000000),
    "ShakeMagnitude": _f32_bits(0x00000000),
    "ShakeScreenVelocityMin": _f32_bits(0x00000000),
    "ShakeScreenVelocity": _f32_bits(0x41400000),
    "SoundEffect": "",
    "LODDistanceMultiplier": _f32_bits(0x3F800000),
    "OverridedBy": "",
    "UserDataName": "",
    "UserDataValue": _f32_bits(0x00000000),
    "ActiveAreas": [],
}

TRACKING_CAMERA_DEFAULTS = {
    **STATIC_CAMERA_DEFAULTS,
    "MovementRate": _f32_bits(0x00000000),
    "TrackingRate": _f32_bits(0x00000000),
    "SplineID": -1,
    "TargetSplineID": -1,
    "bAutoZoom": False,
    "bStaticDirection": False,
    "SplineChaseDir": _f32_bits(0x00000000),
    "TargetSplineChaseDir": _f32_bits(0x00000000),
    "TrackingLag": _f32_bits(0x00000000),
    "TrackingLagSmoothening": _f32_bits(0x3F4CCCCD),
    "TrackingErrorFrequency": _f32_bits(0x40000000),
    "TrackingErrorCorrectionSpeed": _f32_bits(0x3F800000),
    "TrackingErrorMagnitude": _f32_bits(0x00000000),
    "SplinesRatio": _f32_bits(0x3F800000),
    "bSyncSplines": False,
    "OnSplineEndReached": "",
    "OnTargetSplineEndReached": "",
}

STATIC_FIELD_OFFSETS = {
    "Name": 0x60, "Pos": 0x20, "QuatOri": 0x10, "FOV": 0x64, "Type": 0x68,
    "NearZ": 0x6C, "FarZ": 0x70, "Target": 0x78, "LookAt": 0x80,
    "TargetOffset": 0x84, "LookAtOffset": 0x90,
    "ProximityShakeFrequency": 0x9C, "ProximityShakeMagnitude": 0xA0,
    "ProximityShakeMinDistance": 0xA4, "ProximityShakeMaxDistance": 0xA8,
    "ProximityShakeMinSpeed": 0xAC, "ProximityShakeMaxSpeed": 0xB0,
    "ShakeFrequencyMin": 0xB4, "ShakeFrequency": 0xB8,
    "ShakeMagnitudeMin": 0xBC, "ShakeMagnitude": 0xC0,
    "ShakeScreenVelocityMin": 0xB4, "ShakeScreenVelocity": 0xB8,
    "SoundEffect": 0xCC, "LODDistanceMultiplier": 0xD0,
    "OverridedBy": 0xD4, "UserDataName": 0xDC, "UserDataValue": 0xE0,
    "ActiveAreas": 0x2C,
}

TRACKING_FIELD_OFFSETS = {
    "MovementRate": 0xF0, "TrackingRate": 0xF4, "SplineID": 0xF8,
    "TargetSplineID": 0xFC, "bAutoZoom": 0x100, "bStaticDirection": 0x101,
    "SplineChaseDir": 0x104, "TargetSplineChaseDir": 0x108,
    "TrackingLag": 0x128, "TrackingLagSmoothening": 0x12C,
    "TrackingErrorFrequency": 0x130, "TrackingErrorCorrectionSpeed": 0x134,
    "TrackingErrorMagnitude": 0x138, "SplinesRatio": 0x13C,
    "bSyncSplines": 0x140, "OnSplineEndReached": 0x144,
    "OnTargetSplineEndReached": 0x148,
}

def camera_default_state(kind: str = "static") -> dict[str, Any]:
    """Return one evidence-backed camera-data initializer contract."""
    if kind not in {"static", "tracking"}:
        raise ValueError("kind must be static or tracking")
    values = STATIC_CAMERA_DEFAULTS if kind == "static" else TRACKING_CAMERA_DEFAULTS
    return {
        "format": FORMAT,
        "version": 1,
        "kind": kind,
        "fields": values.copy(),
        "offsets": dict(STATIC_FIELD_OFFSETS if kind == "static" else {**STATIC_FIELD_OFFSETS, **TRACKING_FIELD_OFFSETS}),
        "evidence": {
            "static_template": "FUN_00813180",
            "static_copy_constructor": "FUN_00813300",
            "tracking_template": "FUN_0081f8c0" if kind == "tracking" else None,
            "tracking_copy_constructor": "FUN_0081f990" if kind == "tracking" else None,
            "static_property_registration": "FUN_008156b0",
            "tracking_property_registration": "FUN_0081ebc0" if kind == "tracking" else None,
        },
        "limitations": [
            "float units are not synthesized when the initializer only supplies a raw scalar",
            "unregistered template fields are intentionally omitted",
            "QuatOri is preserved exactly as the zeroed initializer value; no normalization is applied",
        ],
    }
