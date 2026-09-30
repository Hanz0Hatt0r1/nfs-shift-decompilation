"""Neutral geometry adapter for source-backed SHIFT binary MeshInst (.imb).

Phase 560 consumes the Phase 557-559 IMB decoder output and materializes a
renderer-neutral geometry contract without claiming MEB container equivalence.

The serialized Type/Usage/Channel triples are preserved exactly. Streams whose
triple is already proven by the MEB/D3D9 ABI are decoded into the established
neutral mesh fields; other source-backed streams remain explicit raw/deferred
records.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any

from imb_format import parse_imb_binary_mesh

FORMAT = "SHIFT.IMBNeutralGeometry/1"
NEUTRAL_MESH_FORMAT = "SHIFT.NeutralMesh/1"

# These IDs use the repository's proven [Type, Usage, Channel] concatenation.
# They intentionally match the existing MEB neutral fields without asserting
# that IMB and MEB are the same serialized container.
_FIELD_BY_PROPERTY = {
    "200": ("vertices", "f32x3", 3, False),
    "220": ("normals", "f32x3", 3, False),
    "240": ("tangents", "f32x3", 3, False),
    "250": ("tangents2", "f32x3", 3, False),
    "310": ("bone_weights", "f32x4", 4, False),
    "460": ("colors", "u8x4", 4, True),
    "461": ("colors2", "u8x4", 4, True),
    "580": ("bone_indices", "u8x4", 4, False),
}
for _channel in range(5):
    _FIELD_BY_PROPERTY[f"13{_channel}"] = (
        f"uv:{130 + _channel}",
        "f32x2",
        2,
        False,
    )
    _FIELD_BY_PROPERTY[f"23{_channel}"] = (
        f"uv:{230 + _channel}",
        "f32x3",
        3,
        False,
    )


def _decode_payload(payload: bytes, storage: str) -> list[list[int | float]]:
    if storage == "f32x2":
        return [list(row) for row in struct.iter_unpack("<2f", payload)]
    if storage == "f32x3":
        return [list(row) for row in struct.iter_unpack("<3f", payload)]
    if storage == "f32x4":
        return [list(row) for row in struct.iter_unpack("<4f", payload)]
    if storage == "u8x4":
        if len(payload) % 4:
            raise ValueError("IMB u8x4 stream payload is not 4-byte aligned")
        return [list(payload[offset:offset + 4]) for offset in range(0, len(payload), 4)]
    raise ValueError(f"unsupported neutral IMB storage {storage!r}")


def _property_id(stream: dict[str, Any]) -> str:
    return (
        f"{int(stream['type_ordinal'])}"
        f"{int(stream['usage_ordinal'])}"
        f"{int(stream['channel'])}"
    )


def build_imb_neutral_geometry(data: bytes) -> dict[str, Any]:
    """Decode a v0.4 IMB into a neutral mesh plus per-primitive draw ranges."""
    source = parse_imb_binary_mesh(data, decode_primitives=True)
    vertex_count = int(source["header"]["vertex_count"])

    mesh: dict[str, Any] = {
        "format": NEUTRAL_MESH_FORMAT,
        "source_format": source["format"],
        "source_resource_name": (source.get("prefix") or {}).get("resource_name"),
        "vertex_count": vertex_count,
        "indices": [],
        "vertices": [],
        "normals": [],
        "tangents": [],
        "tangents2": [],
        "uv_layers": {},
        "colors": [],
        "colors2": [],
        "bone_weights": [],
        "bone_indices": [],
        "vertex_layout": {
            "source_layout": "descriptor-then-vertices-per-stream",
            "runtime_interleaved_stride": int(
                source["streams"]["runtime_vertex_stride"]
            ),
            "attributes": [],
        },
        "bones": source.get("bones"),
        "bounding_sphere": source["header"]["bounding_sphere"],
        "aabb": source["header"]["aabb"],
    }

    deferred_streams: list[dict[str, Any]] = []
    decoded_properties: list[str] = []
    seen_properties: set[str] = set()

    for raw_stream in source["streams"]["records"]:
        stream = dict(raw_stream)
        prop = _property_id(stream)
        if prop in seen_properties:
            raise ValueError(f"duplicate IMB Type/Usage/Channel property {prop}")
        seen_properties.add(prop)

        payload = bytes.fromhex(str(stream["vertex_payload_hex"]))
        mapping = _FIELD_BY_PROPERTY.get(prop)
        attribute = {
            "property_id": prop,
            "type_ordinal": int(stream["type_ordinal"]),
            "usage_ordinal": int(stream["usage_ordinal"]),
            "channel": int(stream["channel"]),
            "source_offset": int(stream["source_offset"]),
            "payload_offset": int(stream["vertex_payload_offset"]),
            "payload_size": int(stream["vertex_payload_size"]),
            "element_size": int(stream["element_size_bytes"]),
            "runtime_element_offset": int(stream["runtime_element_offset"]),
            "status": "deferred-unmapped",
        }

        if mapping is None:
            deferred_streams.append({
                **attribute,
                "raw_hex": payload.hex(),
            })
            mesh["vertex_layout"]["attributes"].append(attribute)
            continue

        field, storage, components, normalized = mapping
        rows = _decode_payload(payload, storage)
        if len(rows) != vertex_count:
            raise ValueError(
                f"IMB property {prop} decoded {len(rows)} rows; "
                f"expected {vertex_count}"
            )

        if field.startswith("uv:"):
            mesh["uv_layers"][field.split(":", 1)[1]] = rows
        else:
            mesh[field] = rows

        decoded_properties.append(prop)
        attribute.update({
            "storage": storage,
            "components": components,
            "normalized": normalized,
            "status": "decoded",
        })
        mesh["vertex_layout"]["attributes"].append(attribute)

    primitives: list[dict[str, Any]] = []
    combined_indices: list[int] = []
    for primitive in source["primitives"].get("records") or []:
        first_index = len(combined_indices)
        indices = [int(value) for value in primitive["indices_u16"]]
        combined_indices.extend(indices)
        primitives.append({
            "index": int(primitive["index"]),
            "material": str(primitive["material_name"]),
            "material_opaque_word": int(primitive["material_opaque_word"]),
            "primitive_type": int(primitive["primitive_type"]),
            "triangle_count": int(primitive["triangle_count"]),
            "first_index": first_index,
            "index_count": len(indices),
            "vertex_range_u16": list(primitive["vertex_range_u16"]),
            "bone_palette_u16": list(primitive["bone_palette_u16"]),
            "bounding_sphere": primitive["bounding_sphere"],
            "aabb": primitive["aabb"],
            "source_offset": int(primitive["source_offset"]),
            "source_size": int(primitive["source_size"]),
        })
    mesh["indices"] = combined_indices

    blockers: list[str] = []
    if not mesh["vertices"] and vertex_count:
        blockers.append("position-stream-200-missing")
    if int(source["header"]["primitive_count"]) and not combined_indices:
        blockers.append("primitive-index-payload-missing")

    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "source": {
            "format": source["format"],
            "prefix_format": (source.get("prefix") or {}).get("format"),
            "packed_version": (source.get("prefix") or {}).get("packed_version"),
            "version_text": (source.get("prefix") or {}).get("version_text"),
            "resource_name": (source.get("prefix") or {}).get("resource_name"),
            "source_end_offset": source["primitives"].get("source_end_offset"),
            "trailing_bytes": source["primitives"].get("trailing_bytes"),
        },
        "mesh": mesh,
        "primitive_count": len(primitives),
        "primitives": primitives,
        "decoded_properties": decoded_properties,
        "deferred_stream_count": len(deferred_streams),
        "deferred_streams": deferred_streams,
        "boundary": {
            "imb_prefix_header_streams": "source-backed",
            "imb_v0_4_primitives": "source-backed",
            "neutral_field_mapping": "proven Type/Usage/Channel triples only",
            "unknown_stream_policy": "preserve-raw-and-defer",
            "bone_palette_policy": (
                "preserved per primitive; no invented palette remap"
            ),
            "meb_container_equivalence": False,
            "render_command_generation": "not-performed",
            "material_resolution": "not-performed",
        },
    }


def build_imb_neutral_geometry_file(
    input_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    report = build_imb_neutral_geometry(Path(input_path).read_bytes())
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decode a source-backed .imb into neutral geometry"
    )
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = build_imb_neutral_geometry_file(args.input, args.output)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "primitive_count": report["primitive_count"],
        "decoded_properties": report["decoded_properties"],
        "deferred_stream_count": report["deferred_stream_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
