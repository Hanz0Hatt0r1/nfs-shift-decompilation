"""Evidence-backed CameraManager config snapshot/runtime parser.

Recovered from FUN_00823640, FUN_00823700, FUN_00823760, and FUN_00823960.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Sequence

FORMAT = "SHIFT.CameraConfigSnapshotRuntime/1"


@dataclass(frozen=True)
class ConfigSnapshot:
    vec_a: tuple[float, float, float] = (0.0, 0.0, 0.0)  # +0x18
    vec_b: tuple[float, float, float] = (0.0, 0.0, 0.0)  # +0x24
    type_a: int = 0  # +0x08
    type_b: int = 0  # +0x0c
    object_a: Any = None  # +0x00
    object_b: Any = None  # +0x04
    parameter: int = 0  # +0x10
    has_vec_b: bool = False  # +0x14
    source_selector: int = -1  # +0xfc


def parse_semicolon_vec3(text_value: str) -> tuple[float, float, float]:
    """Reproduce FUN_00823640's semicolon-delimited atof parser."""
    raw = "" if text_value is None else str(text_value)
    parts = raw.split(";")
    values = [float(parts[0]) if parts[0] else 0.0]
    if len(parts) > 1:
        values.append(float(parts[1]) if parts[1] else 0.0)
    if len(parts) > 2:
        values.append(float(parts[2]) if parts[2] else 0.0)
    while len(values) < 3:
        values.append(0.0)
    return tuple(values[:3])


def describe_string_property_parse(
    *,
    target: str,
    text_value: str,
    helper_811390_result: int,
) -> dict[str, Any]:
    """Trace FUN_00823640 including the opaque FUN_00811390 gate."""
    vector = parse_semicolon_vec3(text_value)
    gate = int(helper_811390_result)
    callback = (
        "FUN_00823560"
        if gate != 15
        else ("FUN_00823590" if target == "vec_a" else "FUN_008235b0")
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "string-property-parse",
        "target": target,
        "input": text_value,
        "helper_811390_result": gate,
        "vector": vector,
        "callback": callback,
        "evidence": {
            "function": "FUN_00823640",
            "length_gate": 15,
            "delimiter": ";",
        },
    }


def update_config_snapshot(
    snapshot: ConfigSnapshot,
    *,
    first_text: str,
    second_text: str | None,
    parameter: int,
) -> ConfigSnapshot:
    """Reproduce FUN_00823700 state writes."""
    first = parse_semicolon_vec3(first_text)
    if second_text is not None and len(second_text) > 0:
        second = parse_semicolon_vec3(second_text)
        return replace(
            snapshot,
            vec_a=first,
            vec_b=second,
            parameter=int(parameter),
            has_vec_b=True,
        )
    return replace(
        snapshot,
        vec_a=first,
        parameter=int(parameter),
        has_vec_b=False,
    )


def camera_config_snapshot_defaults() -> dict[str, Any]:
    """Reproduce FUN_00823760 raw defaults relevant to the camera config snapshot."""
    writes = {
        "+0x10": 0x43B40000,  # 360.0
        "+0x14": 0x43B40000,
        "+0x18": 0x43B40000,
        "+0x1c": 0,
        "+0x20": 0,
        "+0x24": "0;0;0",
        "+0x28": "",
        "+0x2c": 0,
        "+0x30": 0,
        "+0x34": 0,
        "+0x38": 0,
        "+0x3c": 0,
        "+0x40": 0,
        "+0x44": 1,
        "+0x48": 1,
        "+0x4c": 1,
        "+0x50": 0,
        "+0x54": 0x3F99999A,
        "+0x58": 0x3F99999A,
        "+0x5c": 0x42B40000,
        "+0x60": 0x3FAAAAAB,
        "+0x64": 0x3DCCCCCD,
        "+0x68": 0x43FA0000,
        "+0x6c": 0,
        "+0x70": 0,
        "+0x74": 0,
        "+0x78": 0,
        "+0x7c": 0,
        "+0x80": 0,
        "+0x84": 0,
        "+0x88": 0,
        "+0x8c": 0,
        "+0x90": 0,
        "+0x94": 0,
        "+0x98": 0,
        "+0x9c": 0,
        "+0xa0": 0,
        "+0xa4": 0,
        "+0xa8": 0x3F800000,
        "+0xac": 0,
        "+0xb0": 0,
        "+0xb4": 1,
        "+0xb8": 0,
        "+0xbc": 1,
        "+0xc0": 2,
        "+0xc4": 0,
        "+0xc8": 0x3F800000,
        "+0xcc": 1,
        "+0xd0": 0x3F800000,
        "+0xd4": 1,
        "+0xd8": 0x3F800000,
        "+0xdc": 1,
        "+0xe0": 6,
        "+0xe4": 0,
        "+0xe8": 0x3F800000,
        "+0xec": 0,
        "+0xf0": 0,
        "+0xfc": 0xFFFFFFFF,
    }
    byte_writes = {
        "+0xad": 0,
        "+0xae": 0,
        "+0xaf": 1,
        "+0xc5": 0,
        "+0x100": 0,
    }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-config-snapshot-defaults",
        "writes": writes,
        "byte_writes": byte_writes,
        "evidence": {
            "function": "FUN_00823760",
            "final_vtable": "PTR_FUN_00b16bf8",
        },
    }


def refresh_cached_config(
    *,
    current_selector: int,
    requested_selector: int,
    snapshot: ConfigSnapshot,
    first_text: str,
    second_text: str | None,
    parameter: int,
) -> dict[str, Any]:
    """Reproduce FUN_00823960's conditional refresh call."""
    if int(current_selector) == int(requested_selector):
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "cached-config-query",
            "status": "cache-hit",
            "returned_object": "+0xec",
            "snapshot": snapshot,
        }
    updated = replace(
        update_config_snapshot(
            snapshot,
            first_text=first_text,
            second_text=second_text,
            parameter=parameter,
        ),
        source_selector=int(requested_selector),
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "cached-config-query",
        "status": "refreshed",
        "returned_object": "+0xec",
        "snapshot": updated,
        "new_selector": int(requested_selector),
        "action": {
            "function": "FUN_00823700",
            "destination": "+0xec",
        },
        "evidence": {
            "function": "FUN_00823960",
            "selector_field": "+0xfc",
        },
    }
