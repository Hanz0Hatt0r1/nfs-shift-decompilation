from __future__ import annotations
from typing import Iterable

from meb_format import PROP_NAMES

D3DDECLTYPES = {
    "200": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "220": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "240": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "250": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "130": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False},
    "131": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False},
    "132": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False},
    "133": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False},
    "134": {"d3d9": "FLOAT2", "android": "FLOAT32x2", "components": 2, "normalized": False},
    "230": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "231": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "232": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "233": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "234": {"d3d9": "FLOAT3", "android": "FLOAT32x3", "components": 3, "normalized": False},
    "310": {"d3d9": "FLOAT4", "android": "FLOAT32x4", "components": 4, "normalized": False},
    "580": {"d3d9": "UBYTE4", "android": "UINT8x4", "components": 4, "normalized": False},
    # MEB stores colors as four raw bytes. Whether the original D3D9 declaration
    # used D3DCOLOR (BGRA) or UBYTE4N is not yet proven, so preserve both candidates.
    "460": {"d3d9_candidates": ["D3DCOLOR", "UBYTE4N"], "android": "UINT8x4", "android_candidates": ["UINT8x4_RGBA", "UINT8x4_BGRA"], "components": 4, "normalized": True, "channel_order_candidates": ["RGBA", "BGRA"]},
    "461": {"d3d9_candidates": ["D3DCOLOR", "UBYTE4N"], "android": "UINT8x4", "android_candidates": ["UINT8x4_RGBA", "UINT8x4_BGRA"], "components": 4, "normalized": True, "channel_order_candidates": ["RGBA", "BGRA"]},
    "033": {"d3d9_candidates": ["UNKNOWN4"], "android": "RAW4", "components": 4, "normalized": False},
}

SEMANTICS = {
    "200": ("POSITION", 0), "460": ("COLOR", 0), "461": ("COLOR", 1),
    "220": ("NORMAL", 0), "240": ("TANGENT", 0), "250": ("BINORMAL", 0),
    "310": ("BLENDWEIGHT", 0), "580": ("BLENDINDICES", 0),
}
for i, pid in enumerate(("130","131","132","133","134","230","231","232","233","234")):
    SEMANTICS[pid] = ("TEXCOORD", i % 5)


def build_vertex_layout(properties: Iterable[str | dict], *, repack_interleaved: bool = True) -> dict:
    rows = []
    for value in properties:
        pid = str(value.get("id")) if isinstance(value, dict) else str(value)
        info = D3DDECLTYPES.get(pid)
        if not info:
            rows.append({"property_id": pid, "name": PROP_NAMES.get(pid, "unknown"), "status": "unknown"})
            continue
        usage, index = SEMANTICS.get(pid, ("UNKNOWN", 0))
        row = {"property_id": pid, "name": PROP_NAMES.get(pid, "unknown"), "usage": usage, "usage_index": index, **info}
        if isinstance(value, dict):
            for k in ("payload_offset","stride","bytes"):
                if k in value: row[k] = value[k]
        rows.append(row)
    return {"format":"SHIFT.VertexLayout/1","source":"MEB","buffer_mode":"interleaved-repack" if repack_interleaved else "split-arrays","attributes":rows}


def build_layout_from_summary(summary: dict) -> dict:
    layouts = summary.get("property_layouts") or summary.get("vertex_properties") or []
    return build_vertex_layout(layouts)
