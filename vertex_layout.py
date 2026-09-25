from __future__ import annotations
from typing import Iterable

from meb_format import PROP_NAMES


# MEB properties are stored as separate contiguous payloads. These descriptors
# preserve the physical source ABI while also defining a deterministic target
# interleaved layout for Android/OpenGL.
ABI_STATUS = {
    "exact": "proven",
    "derived-from-stride": "inferred",
    "ambiguous-declaration-and-channel-order": "ambiguous",
    "verified": "proven",
    "unknown": "unknown",
}

EVIDENCE_BASIS = {
    "200": "12-byte MEB payload decoded as FLOAT32x3; POSITION0 semantic confirmed by shader declaration corpus",
    "220": "12-byte MEB payload decoded as FLOAT32x3; NORMAL0 semantic confirmed by shader declaration corpus",
    "240": "12-byte MEB payload decoded as FLOAT32x3; TANGENT0 semantic confirmed by shader declaration corpus",
    "250": "12-byte MEB payload decoded as FLOAT32x3; BINORMAL0 semantic confirmed by shader declaration corpus",
    "130": "8-byte MEB payload decoded as FLOAT32x2; TEXCOORD0 semantic",
    "131": "8-byte MEB payload decoded as FLOAT32x2; TEXCOORD1 semantic",
    "132": "8-byte MEB payload decoded as FLOAT32x2; TEXCOORD2 semantic",
    "133": "8-byte MEB payload decoded as FLOAT32x2; TEXCOORD3 semantic",
    "134": "8-byte MEB payload decoded as FLOAT32x2; TEXCOORD4 semantic",
    "230": "12-byte MEB payload decoded as FLOAT32x3; TEXCOORD0-4 family retained as established importer mapping",
    "231": "12-byte MEB payload decoded as FLOAT32x3; TEXCOORD0-4 family retained as established importer mapping",
    "232": "12-byte MEB payload decoded as FLOAT32x3; TEXCOORD0-4 family retained as established importer mapping",
    "233": "12-byte MEB payload decoded as FLOAT32x3; TEXCOORD0-4 family retained as established importer mapping",
    "234": "12-byte MEB payload decoded as FLOAT32x3; TEXCOORD0-4 family retained as established importer mapping",
    "310": "16-byte MEB payload decoded as four FLOAT32 values; BLENDWEIGHT0 semantic and four-influence contract confirmed",
    "580": "4-byte MEB payload decoded as four U8 values; BLENDINDICES0 semantic and four-influence contract confirmed",
    "460": "4-byte MEB payload; COLOR0 semantic confirmed, but D3D9 D3DCOLOR vs UBYTE4N and RGBA/BGRA byte order remain unresolved",
    "461": "4-byte MEB payload; COLOR1 semantic confirmed, but D3D9 D3DCOLOR vs UBYTE4N and RGBA/BGRA byte order remain unresolved",
    "033": "4-byte MEB payload preserved as opaque RAW4; semantic/type not proven",
}

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
    "460": {"d3d9_candidates": ["D3DCOLOR", "UBYTE4N"], "android": "UINT8x4", "android_candidates": ["UINT8x4_RGBA", "UINT8x4_BGRA"], "components": 4, "normalized": True, "element_size": 4, "confidence": "ambiguous-declaration-and-channel-order", "channel_order_candidates": ["RGBA", "BGRA"], "source_evidence": {"kind": "shift-exe-c", "function": "FUN_008310c0", "address": "0x008310C0", "observed_behavior": "float4 RGBA is rounded to 8-bit channels and packed as 0xAARRGGBB", "little_endian_memory_order": "BGRA", "status": "supporting-packed-color-evidence-not-MEB-declaration-proof"}},
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


def build_vertex_layout(
    properties: Iterable[str | dict],
    *,
    repack_interleaved: bool = True,
    color_abi_evidence: dict | None = None,
) -> dict:
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
                "abi_status": "unknown",
                "evidence_basis": "property id is not decoded by the current MEB ABI table",
            }
            rows.append(row)
            continue

        usage, index = SEMANTICS.get(pid, ("UNKNOWN", 0))
        effective_info = dict(info)
        if pid in {"460", "461"} and isinstance(color_abi_evidence, dict):
            bridge_props = color_abi_evidence.get("properties") or {}
            bridge_row = bridge_props.get(pid) if isinstance(bridge_props, dict) else None
            mapping = bridge_row.get("property_to_type") if isinstance(bridge_row, dict) else None
            selected = mapping.get("selected") if isinstance(mapping, dict) else None
            if (
                color_abi_evidence.get("format") == "SHIFT.MEBD3D9ColorBridgeEvidence/1"
                and color_abi_evidence.get("verified_abi") is True
                and isinstance(mapping, dict)
                and mapping.get("status") == "observed"
                and isinstance(selected, dict)
                and int(selected.get("code", -1)) == 4
            ):
                effective_info.update({
                    "d3d9": "D3DCOLOR",
                    "confidence": "verified",
                    "channel_order_candidates": [str(selected.get("memory_order") or "BGRA")],
                    "android_candidates": ["UINT8x4_BGRA"],
                    "source_evidence": {
                        "kind": "SHIFT.MEBD3D9ColorBridgeEvidence/1",
                        "status": "verified",
                        "d3d9_type_code": 4,
                        "d3d9_type": "D3DCOLOR",
                        "memory_order": str(selected.get("memory_order") or "BGRA"),
                        "shader_order": str(selected.get("shader_order") or "RGBA"),
                    },
                })
        abi_status = ABI_STATUS.get(effective_info.get("confidence", "unknown"), "unknown")
        row = {
            "property_id": pid,
            "name": PROP_NAMES.get(pid, "unknown"),
            "usage": usage,
            "usage_index": index,
            "location": location,
            "abi_status": abi_status,
            "evidence_basis": EVIDENCE_BASIS.get(pid, "no evidence recorded"),
            **effective_info,
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

    semantic_map: dict[tuple[str, int], list[str]] = {}
    for row in rows:
        if "usage" in row:
            semantic_map.setdefault((row["usage"], int(row["usage_index"])), []).append(row["property_id"])
    semantic_collisions = [
        {"usage": usage, "usage_index": index, "property_ids": ids}
        for (usage, index), ids in semantic_map.items()
        if len(ids) > 1
    ]
    result = {
        "format": "SHIFT.VertexLayout/1",
        "source": "MEB",
        "buffer_mode": "interleaved-repack" if repack_interleaved else "split-arrays",
        "attributes": rows,
        "semantic_collisions": semantic_collisions,
        "evidence": {
            "ambiguous_properties": [x["property_id"] for x in rows if x.get("abi_status") == "ambiguous"],
            "unknown_properties": [x["property_id"] for x in rows if x.get("abi_status") == "unknown"],
            "inferred_properties": [x["property_id"] for x in rows if x.get("abi_status") == "inferred"],
            "proven_properties": [x["property_id"] for x in rows if x.get("abi_status") == "proven"],
        },
    }
    if repack_interleaved:
        result["buffer_stride"] = offset
    return result


def build_layout_from_summary(
    summary: dict,
    *,
    color_abi_evidence: dict | None = None,
) -> dict:
    layouts = summary.get("property_layouts") or summary.get("vertex_properties") or []
    return build_vertex_layout(layouts, color_abi_evidence=color_abi_evidence)


def property_abi(property_id: str) -> dict:
    """Return the preserved ABI descriptor for a single MEB property."""
    pid = str(property_id)
    info = D3DDECLTYPES.get(pid)
    if not info:
        return {
            "property_id": pid,
            "name": PROP_NAMES.get(pid, "unknown"),
            "status": "unknown",
            "abi_status": "unknown",
            "evidence_basis": "property id is not decoded by the current MEB ABI table",
        }
    usage, index = SEMANTICS.get(pid, ("UNKNOWN", 0))
    return {
        "property_id": pid,
        "name": PROP_NAMES.get(pid, "unknown"),
        "usage": usage,
        "usage_index": index,
        "abi_status": ABI_STATUS.get(info.get("confidence", "unknown"), "unknown"),
        "evidence_basis": EVIDENCE_BASIS.get(pid, "no evidence recorded"),
        **info,
    }
