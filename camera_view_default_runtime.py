"""Evidence-backed CCameraView projection defaults from SHIFT.exe.

FUN_0081aeb0 explicitly initializes the four projection scalars used by the camera
view object. FUN_0081ac70 independently registers the same storage offsets as
FOV, AspectRatio, NearZ and FarZ.
"""

from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.CameraViewDefaultRuntime/1"


def _f32(bits: int) -> dict[str, Any]:
    return {
        "bits_hex": f"0x{bits:08x}",
        "value": struct.unpack("<f", struct.pack("<I", bits))[0],
    }


FIELDS = {
    "FOV": {"offset": 0x34, "default": _f32(0x3F490FDB)},
    "AspectRatio": {"offset": 0x38, "default": _f32(0x3FAAAAAB)},
    "NearZ": {"offset": 0x3C, "default": _f32(0x3DCCCCCD)},
    "FarZ": {"offset": 0x40, "default": _f32(0x443B8000)},
}


def camera_view_default_state() -> dict[str, Any]:
    """Return the four projection defaults explicitly written by FUN_0081aeb0."""
    return {
        "format": FORMAT,
        "version": 1,
        "fields": {name: dict(row) for name, row in FIELDS.items()},
        "evidence": {
            "initializer": "FUN_0081aeb0",
            "property_registration": "FUN_0081ac70",
        },
        "limitations": [
            "only explicitly initialized projection scalars are exposed",
            "no projection-matrix convention or angle-unit conversion is inferred",
        ],
    }
