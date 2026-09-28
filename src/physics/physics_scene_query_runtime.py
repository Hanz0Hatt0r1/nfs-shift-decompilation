"""Evidence-backed reconstruction of the SHIFT PhysX scene query wrapper."""
from __future__ import annotations

from math import isfinite
from typing import Any

FORMAT = "SHIFT.PhysicsSceneQueryRuntime/1"
FLT_MAX = 3.4028235e38

QUERY_MODES = {
    0: {"scene_query_type": 1, "mask": 0x7FFFFFFF},
    1: {"scene_query_type": 2, "mask": 0x7FFFFFFF},
    2: {"scene_query_type": 1, "mask": 0x80000000},
    3: {"scene_query_type": 3, "mask": 0x7FFFFFFF},
}


def query_mode_contract(mode: int) -> dict[str, Any]:
    try:
        value = QUERY_MODES[mode]
    except KeyError as exc:
        raise ValueError(f"unsupported physics scene query mode {mode}") from exc
    return {
        "format": FORMAT,
        "mode": mode,
        "scene_query_type": value["scene_query_type"],
        "mask_u32": value["mask"],
        "default_filter": 0xFFFFFFFF,
        "evidence": "FUN_0074ef30 vtable +0x1c0",
    }


def validate_query_inputs(scene_present: bool, mode: int, distance: float) -> dict[str, Any]:
    valid = scene_present and mode in QUERY_MODES and isfinite(distance) and distance >= 0.0
    return {
        "format": "SHIFT.PhysicsSceneQueryInputValidation/1",
        "ready": valid,
        "scene_present": scene_present,
        "mode": mode,
        "distance": distance,
        "failure_result": FLT_MAX,
        "blockers": [] if valid else ["physics-query:invalid-scene-mode-or-distance"],
    }


def build_scene_query_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "source": ".\\Source\\System\\PhysicsSystem.cpp",
        "function": "FUN_0074ef30",
        "scene_vtable_offset": 0x1C0,
        "modes": {mode: query_mode_contract(mode) for mode in QUERY_MODES},
        "failure": {
            "no_scene": FLT_MAX,
            "negative_distance": FLT_MAX,
            "nan_distance": FLT_MAX,
            "no_hit": FLT_MAX,
        },
        "outputs": {
            "param_5": "hit position vec3",
            "param_6": "hit normal vec3",
            "param_7": "shape/material-index output depending on query result",
            "param_8": "raw u16 mapping/index output when available",
        },
        "shape_lookup": {
            "mode_2": "writes piVar1[0xf] to param_7",
            "shape_kind_1": "mapping may pass through FUN_0077cbf0 and +0x134",
            "unresolved": "exact shape table semantics",
        },
        "status": "query-dispatch-reconstructed",
    }
