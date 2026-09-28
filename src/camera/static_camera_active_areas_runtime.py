"""StaticCamera ActiveAreas container and runtime initializer.

Recovered from FUN_008143d0, FUN_00814460, FUN_008144f0 and FUN_008145c0.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.StaticCameraActiveAreasRuntime/1"
UINT16_MASK = 0xFFFF


def append_active_area(stored_indices: Sequence[int], index: int) -> dict[str, Any]:
    """Reproduce FUN_008143d0's uint16 append boundary."""
    values = list(map(int, stored_indices))
    masked = int(index) & UINT16_MASK
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "append-area",
        "input_index": int(index),
        "stored_value": masked,
        "stored_indices": values + [masked],
        "evidence": {
            "function": "FUN_008143d0",
            "storage_width": 16,
            "mask": "0xffff",
        },
    }


def initialize_static_camera_runtime() -> dict[str, Any]:
    """Reproduce FUN_00814460's raw initializer and nested shake reset."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "static-camera-runtime-init",
        "writes": {
            "+0x00..+0x18": [0] * 7,
            "+0x24": 0,
            "+0x28": 0,
            "+0x2c": 0,
            "+0x30": 0,
            "+0x34": 0,
            "+0x38": 0,
            "+0x3c": 0,
            "+0x40": 0,
            "+0x44": 0,
            "+0x48": 6,
            "+0x4c": 6,
            "+0x50": 0,
            "+0x54": 0,
        },
        "byte_writes": {
            "+0x20": 0,
            "+0x21": 0,
            "+0x38": 0,
        },
        "shake_resets": [
            {"action": "FUN_00823bc0", "target": "+0x3c"},
            {"action": "FUN_00823bc0", "target": "+0x90"},
        ],
        "evidence": {"function": "FUN_00814460"},
    }


def serialize_active_areas(
    *,
    indices: Sequence[int],
) -> dict[str, Any]:
    """Trace FUN_008144f0's save callback."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "active-areas-save",
        "count": len(indices),
        "elements": [
            {
                "name": f"areaIndex{i}",
                "value": int(index) & UINT16_MASK,
                "source_index": i,
            }
            for i, index in enumerate(indices)
        ],
        "actions": [
            {"action": "FUN_0063e9b0", "path": "elements"},
            {"action": "allocate funcpropdata", "bytes": 0x50},
            {"action": "FUN_0063c0d0"},
        ],
        "evidence": {
            "function": "FUN_008144f0",
            "property_name_format": "areaIndex%d",
            "count_source": "+0x50",
            "array_source": "+0x2c",
        },
    }


def deserialize_active_areas(
    *,
    values: Sequence[int],
) -> dict[str, Any]:
    """Trace FUN_008145c0's load callback."""
    stored = [int(value) & UINT16_MASK for value in values]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "active-areas-load",
        "count": len(stored),
        "elements": [
            {
                "name": f"areaIndex{i + 1}",
                "input_value": int(value),
                "stored_value": int(value) & UINT16_MASK,
            }
            for i, value in enumerate(values)
        ],
        "stored_indices": stored,
        "actions": [
            {"action": "FUN_0063d390", "path": "elements"},
            {"action": "parse property name", "format": "areaIndex%d"},
            {"action": "FUN_0063d390", "value_type": "long"},
            {"action": "FUN_008143d0", "mask": "0xffff"},
        ],
        "evidence": {
            "function": "FUN_008145c0",
            "property_name_format": "areaIndex%d",
            "storage_width": 16,
        },
    }
