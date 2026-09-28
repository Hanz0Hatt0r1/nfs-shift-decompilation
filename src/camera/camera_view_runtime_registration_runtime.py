"""Exact CCameraView runtime registration and angle-wrap helpers.

Recovered from FUN_0081b610 and FUN_0081b740.
"""

from __future__ import annotations

import math
from typing import Any

FORMAT = "SHIFT.CameraViewRuntimeRegistrationRuntime/1"
PI_F32 = 3.1415927


def wrap_angle_from_runtime(
    angle: float,
    runtime_seed: float,
) -> dict[str, Any]:
    """Reproduce FUN_0081b610 using the opaque FUN_0090328a result."""
    value = float(angle)
    seed = float(runtime_seed)
    if not math.isnan(value) and value > 0.0:
        result = seed - PI_F32
        branch = "positive"
    else:
        result = -(seed - PI_F32)
        branch = "non-positive-or-nan"
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "angle-wrap",
        "input": value,
        "runtime_seed": seed,
        "result": result,
        "branch": branch,
        "evidence": {
            "function": "FUN_0081b610",
            "seed_source": "FUN_0090328a(this)",
            "constant": PI_F32,
        },
    }


def camera_view_property_registration() -> dict[str, Any]:
    """Reproduce FUN_0081b740's three registration calls."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "property-registration",
        "registration_object": "DAT_00b8e00c",
        "properties": [
            {
                "name": "FreeLookOri",
                "property_type_id": 0x10,
                "storage_offset": 0x84,
                "registration_flags": 2,
                "default_value": "DAT_00aa9b60",
            },
            {
                "name": "PosOri",
                "property_type_id": 0x10,
                "storage_offset": 0x90,
                "registration_flags": 2,
                "default_value": "DAT_00aa9b60",
            },
            {
                "name": "AttachedVehicleIndex",
                "property_type_id": 3,
                "storage_offset": 0xC0,
                "registration_flags": 2,
                "default_value": "DAT_00aa9b60",
            },
        ],
        "evidence": {
            "function": "FUN_0081b740",
            "registration_helper": "FUN_0063a280",
            "string_builder": "FUN_00631740",
        },
    }
