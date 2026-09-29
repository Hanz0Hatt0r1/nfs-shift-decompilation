"""Evidence-backed BMT cull-state translation for D3D9/Vulkan."""
from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.MaterialCullState/1"

_ROWS = {
    "EBFCT_NONE": {
        "engine_enum_index": 0,
        "d3d9_value": 1,
        "d3d9_name": "D3DCULL_NONE",
        "vulkan_cull_mode": "VK_CULL_MODE_NONE",
    },
    "EBFCT_CLOCKWISE": {
        "engine_enum_index": 1,
        "d3d9_value": 2,
        "d3d9_name": "D3DCULL_CW",
        # Vulkan frontFace is CCW in both native executors, therefore
        # clockwise triangles are back-facing and are culled with BACK_BIT.
        "vulkan_cull_mode": "VK_CULL_MODE_BACK_BIT",
    },
    "EBFCT_ANTICLOCKWISE": {
        "engine_enum_index": 2,
        "d3d9_value": 3,
        "d3d9_name": "D3DCULL_CCW",
        "vulkan_cull_mode": "VK_CULL_MODE_FRONT_BIT",
    },
}

_INDEX_TO_NAME = {
    row["engine_enum_index"]: name
    for name, row in _ROWS.items()
}


def translate_bmt_cull(value: Any) -> dict[str, Any]:
    """Translate the retail material cull enum without guessing unknown values."""
    if value is None or value == "":
        return {
            "format": FORMAT,
            "status": "not-supplied",
            "ready": True,
            "blocking_reasons": [],
            "source_value": value,
            "front_face": "VK_FRONT_FACE_COUNTER_CLOCKWISE",
            "vulkan_cull_mode": "VK_CULL_MODE_NONE",
            "evidence_status": "not-supplied",
        }

    name: str | None = None
    if isinstance(value, bool):
        name = None
    elif isinstance(value, int):
        name = _INDEX_TO_NAME.get(value)
    else:
        text = str(value).strip().upper()
        if text in _ROWS:
            name = text
        elif text.isdigit():
            name = _INDEX_TO_NAME.get(int(text))

    if name is None:
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": [
                f"material-cull:unsupported:{value}"
            ],
            "source_value": value,
            "front_face": "VK_FRONT_FACE_COUNTER_CLOCKWISE",
            "evidence_status": "unsupported",
        }

    row = dict(_ROWS[name])
    return {
        "format": FORMAT,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "source_value": value,
        "engine_name": name,
        **row,
        "front_face": "VK_FRONT_FACE_COUNTER_CLOCKWISE",
        "evidence_status": "retail-static",
        "evidence": {
            "enum_string_table_va": "0x00b173e0",
            "d3d9_lookup_table_va": "0x00b8ecd8",
            "lookup_function": "FUN_0083f610",
        },
    }


__all__ = ["FORMAT", "translate_bmt_cull"]
