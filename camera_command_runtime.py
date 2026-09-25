"""Evidence-backed camera command dispatch from FUN_0080e650.

The runtime command record is consumed by its positional fields. Only the dispatch
shape is reconstructed here; numeric command meanings beyond the observed cases
remain contextual.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraCommandRuntime/1"


def dispatch_camera_command(command: Sequence[Any]) -> dict[str, Any]:
    """Reproduce the switch in FUN_0080e650 over command[1]."""
    if len(command) < 2:
        raise ValueError("camera command requires at least two fields")

    kind = int(command[1])
    if kind == 1:
        if len(command) < 5:
            raise ValueError("command kind 1 requires fields 0..4")
        return {
            "format": FORMAT,
            "version": 1,
            "kind": 1,
            "operation": "static-view",
            "arguments": {
                "group": command[4],
                "secondary": command[2],
            },
            "target_functions": ["FUN_0080de00"],
        }

    if kind in (2, 3):
        if len(command) < 6:
            raise ValueError("command kind 2/3 requires fields 0..5")
        return {
            "format": FORMAT,
            "version": 1,
            "kind": kind,
            "operation": "camera-activation",
            "arguments": {
                "param_3": command[3],
                "param_1": command[4],
                "param_2": command[5],
            },
            "target_functions": ["FUN_0080e1b0"],
        }

    if kind == 4:
        return {
            "format": FORMAT,
            "version": 1,
            "kind": 4,
            "operation": "external-view-source",
            "arguments": {
                "source": command[0],
                "enabled": 1,
            },
            "target_functions": ["FUN_0080d520"],
        }

    return {
        "format": FORMAT,
        "version": 1,
        "kind": kind,
        "operation": "unsupported",
        "arguments": {},
        "target_functions": [],
        "limitations": ["FUN_0080e650 has no action for this command kind"],
    }
