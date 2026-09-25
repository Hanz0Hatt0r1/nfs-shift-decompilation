"""Evidence-backed CCameraView construction defaults from FUN_0081cba0.

The constructor first delegates projection defaults to FUN_0081aeb0, initializes
its nested camera-state object with FUN_0081c3b0, frame stack/runtime data, then
chooses the initial camera profile through the observed capability-name checks.
The chosen profile id is copied into +0xc4/+0xc8/+0xcc, with -1 normalized to 0.
"""

from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.CameraViewConstructorRuntime/1"

DEFAULT_SELECTIONS = (
    ("Cam_Bumper", "BumperCam"),
    ("Cam_Bonnet", "BonnetCam"),
    ("Cam_Cockpit", "CockpitCam"),
)


def choose_initial_camera_profile(
    capabilities: Mapping[str, bool],
) -> dict[str, Any]:
    """Reproduce FUN_0081cba0's capability/name decision tree."""
    checks = {str(key): bool(value) for key, value in capabilities.items()}

    for capability, profile_name in DEFAULT_SELECTIONS:
        if checks.get(capability, False):
            return {
                "format": FORMAT,
                "version": 1,
                "status": "selected",
                "capability": capability,
                "profile_name": profile_name,
                "evidence": {"function": "FUN_0081cba0"},
            }

    if checks.get("Cam_Chase", False):
        return {
            "format": FORMAT,
            "version": 1,
            "status": "selected",
            "capability": "Cam_Chase",
            "profile_name": "ChaseCam",
            "evidence": {"function": "FUN_0081cba0"},
        }

    if checks.get("Cam_Shotgun", False):
        return {
            "format": FORMAT,
            "version": 1,
            "status": "selected",
            "capability": "Cam_Shotgun",
            "profile_name": "ShotgunCam",
            "evidence": {"function": "FUN_0081cba0"},
        }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "fallback",
        "capability": None,
        "profile_name": "ChaseCam",
        "evidence": {"function": "FUN_0081cba0"},
    }


def normalize_initial_profile_id(profile_id: int) -> int:
    """Reproduce the constructor's -1 -> 0 normalization."""
    value = int(profile_id)
    return 0 if value == -1 else value


def describe_view_constructor(
    *,
    selected_profile_id: int,
    projection_defaults: bool = True,
) -> dict[str, Any]:
    """Expose the exact constructor write footprint relevant to profile history."""
    normalized = normalize_initial_profile_id(selected_profile_id)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "constructed",
        "delegates": [
            {
                "action": "FUN_0081aeb0",
                "purpose": "projection/base initialization",
                "enabled": bool(projection_defaults),
            },
            {
                "action": "FUN_0081c3b0",
                "target": "nested camera data at +0x20",
            },
            {
                "action": "FUN_00675c60",
                "target": "+0x60",
            },
            {
                "action": "FUN_0042dd30",
                "target": "+0xb4",
            },
        ],
        "writes": {
            "+0xc4": normalized,
            "+0xc8": normalized,
            "+0xcc": normalized,
            "+0x2a0": 0,
            "+0x2a4": 0,
            "+0x2a8": 0,
            "+0x2ac": 0,
            "+0x2b0": 0,
            "+0x2b4": 0,
            "+0x2b8": 0,
            "+0x2bc": 0,
            "+0x2c0": 0,
        },
        "raw_selected_profile_id": int(selected_profile_id),
        "normalized_profile_id": normalized,
        "evidence": {
            "constructor": "FUN_0081cba0",
            "selection_id": "+0xc4",
            "service_history_id": "+0xc8",
            "fallback_history_id": "+0xcc",
        },
        "limitations": [
            "FUN_00646af0 capability checks are preserved as boolean inputs",
            "FUN_00811570 profile-name lookup is opaque",
        ],
    }
