from __future__ import annotations
from typing import Iterable

from meb_format import PROP_NAMES


# MEB properties are stored as separate contiguous payloads. These descriptors
# preserve the physical source ABI while also defining a deterministic target
# interleaved layout for Android/OpenGL.
D3DDECLTYPES = {
    "200": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "220": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "240": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "250": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "130": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False, "element_size": 8, "confidence": "derived-from-stride"},
    "131": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False, "element_size": 8, "confidence": "derived-from-stride"},
    "132": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False, "element_size": 8, "confidence": "derived-from-stride"},
    "133": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False, "element_size": 8, "confidence": "derived-from-stride"},
    "134": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False, "element_size": 8, "confidence": "derived-from-stride"},
    "230": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "231": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "232": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "233": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "234": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False, "element_size": 12, "confidence": "derived-from-stride"},
    "310": {"d3d9": "FLOAT4", "android": "FLOAT32x4", "components": 4, "normalized": False, "element_size": 16, "confidence": "exact"},
    "580": {"d3d9": "UBYTE4", "android": "UINT8x4", "components": 4, "normalized": False, "element_size": 4, "confidence": "exact"},
    "460": {"d3d9_candidates": ["D3DCOLOR", "UBYTE4N"], "android": "UINT8x4", "android_candidates": ["UINT8x4_RGBA", "UINT8x4_BGRA"], "components": 4, "normalized": True, "element_size": 4, "confidence": "ambiguous-channel-order", "channel_order_candidates": ["RGBA", "BGRA"]},
    "461": {"d3d9_candidates": ["D3DCOLOR", "UBYTE4N"], "android": "UINT8x4", "android_candidates": ["UINT8x4_RGBA", "UINT8x4_BGRA"], "components": 4, "normalized": True, "element_size": 4, "confidence": "ambiguous-channel-order", "channel_order_candidates": ["RGBA", "BGRA"]},
    "033": {"d3d9_candidates": ["UNKNOWN4"], "android": "RAW4", "components": 4, "normalized": False, "element_size": 4, "confidence": "unknown"},
}

SEMANTICS = {
    "200": ("POSITION", 0), "460": ("COLOR", 0), "461": ("COLOR", 1),
    "220": ("NORMAL", 0), "240": ("TANGENT", 0), "250": ("BINORMAL", 0),
    "310": ("BLENDWEIGHT", 0), "580": ("BLENDINDICES", 0),
}
for i, pid in enumerate(("130", "131", "132", "133", "134", "230", "231", "232", "233", "234")):
    SEMANTICS[pid] = ("TEXCOORD", i % 5)


def build_vertex_layout(properties: Iterable[str | dict], *, repack_interleaved: bool = True) -> dict:
    rows = []
    offset = 0
    for location, value in enumerate(properties):
        pid = str(value.get("id")) if isinstance(value, dict) else str(value)
        info = D3DDECLTYPES.get(pid)
        if not info:
            row = {
                "property_id": pid,
                "name": PROP_NAMES.get(pid, "unknown"),
                "location": location,
                "status": "unknown",
            }
            rows.append(row)
            continue

        usage, index = SEMANTICS.get(pid, ("UNKNOWN", 0))
        row = {
            "property_id": pid,
            "name": PROP_NAMES.get(pid, "unknown"),
            "usage": usage,
            "usage_index": index,
            "location": location,
            **info,
        }
        if isinstance(value, dict):
            for k in ("payload_offset", "stride", "bytes"):
                if k in value:
                    row[k] = value[k]
        if "stride" not in row:
            row["stride"] = info.get("element_size")
        row["source_storage_bytes"] = row["stride"]
        if repack_interleaved:
            row["buffer_index"] = 0
            row["offset"] = offset
            offset += int(row["element_size"])
        rows.append(row)

    result = {
        "format": "SHIFT.VertexLayout/1",
        "source": "MEB",
        "buffer_mode": "interleaved-repack" if repack_interleaved else "split-arrays",
        "attributes": rows,
    }
    if repack_interleaved:
        result["buffer_stride"] = offset
    return result


def build_layout_from_summary(summary: dict) -> dict:
    layouts = summary.get("property_layouts") or summary.get("vertex_properties") or []
    return build_vertex_layout(layouts)


def property_abi(property_id: str) -> dict:
    """Return the preserved ABI descriptor for a single MEB property."""
    pid = str(property_id)
    info = D3DDECLTYPES.get(pid)
    if not info:
        return {
            "property_id": pid,
            "name": PROP_NAMES.get(pid, "unknown"),
            "status": "unknown",
        }
    usage, index = SEMANTICS.get(pid, ("UNKNOWN", 0))
    return {
        "property_id": pid,
        "name": PROP_NAMES.get(pid, "unknown"),
        "usage": usage,
        "usage_index": index,
        **info,
    }
