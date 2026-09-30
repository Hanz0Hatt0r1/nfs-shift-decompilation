"""Source-backed neutral geometry adapter for SHIFT MeshInst XML (.imx).

The grammar is reconstructed from retail SHIFT.exe FUN_008587e0
CMeshPrimitiveType::LoadXMLMeshFromResource.  XML Type/Usage enum remaps are
kept as provenance; neutral property IDs are assigned only for semantics already
proven by the repository's renderer ABI.
"""
from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.IMXNeutralGeometry/1"
SOURCE_FORMAT = "SHIFT.IMXXMLMesh/1"
NEUTRAL_MESH_FORMAT = "SHIFT.NeutralMesh/1"

# Exact source string order, runtime mapper result and element width recovered
# from PTR_DAT_00b901d0, DAT_00b90088 and DAT_00b8eef0.
_XML_TYPES: dict[str, dict[str, int]] = {
    "F32": {"source_index": 0, "runtime_type": 0, "size": 4},
    "F32Vec2": {"source_index": 1, "runtime_type": 1, "size": 8},
    "F32Vec3": {"source_index": 2, "runtime_type": 2, "size": 12},
    "F32Vec4": {"source_index": 3, "runtime_type": 3, "size": 16},
    "RGBA32": {"source_index": 4, "runtime_type": 4, "size": 4},
    "U8Vec4": {"source_index": 5, "runtime_type": 5, "size": 4},
    "S16Vec2": {"source_index": 6, "runtime_type": 6, "size": 4},
    "S16Vec4": {"source_index": 7, "runtime_type": 7, "size": 8},
    "U8Vec4N": {"source_index": 8, "runtime_type": 8, "size": 4},
    "S16Vec2N": {"source_index": 9, "runtime_type": 9, "size": 4},
    "S16Vec4N": {"source_index": 10, "runtime_type": 10, "size": 8},
    "U16Vec2N": {"source_index": 11, "runtime_type": 11, "size": 4},
    "U16Vec4N": {"source_index": 12, "runtime_type": 12, "size": 8},
    "U10Vec3": {"source_index": 13, "runtime_type": 13, "size": 4},
    "U10Vec3N": {"source_index": 14, "runtime_type": 14, "size": 4},
    "F16Vec2": {"source_index": 15, "runtime_type": 15, "size": 4},
    # The retail mapper table aliases the final source enum to runtime value 15.
    "F16Vec4": {"source_index": 16, "runtime_type": 15, "size": 8},
}

# Exact source string order and D3D9 runtime usage values from
# PTR_s_Position_00b901a8 and DAT_00b9011c.
_XML_USAGES: dict[str, dict[str, Any]] = {
    "Position": {
        "source_index": 0,
        "runtime_usage": 0,
        "item_attribute": "Pos",
    },
    "BlendWeights": {
        "source_index": 1,
        "runtime_usage": 1,
        "item_attribute": "Weights",
    },
    "Normal": {
        "source_index": 2,
        "runtime_usage": 3,
        "item_attribute": "Normal",
    },
    "TexCoord": {
        "source_index": 3,
        "runtime_usage": 5,
        "item_attribute": "UV",
    },
    "Tangent": {
        "source_index": 4,
        "runtime_usage": 6,
        "item_attribute": "Tangent",
    },
    "Binormal": {
        "source_index": 5,
        "runtime_usage": 7,
        "item_attribute": "Binormal",
    },
    "Colour": {
        "source_index": 6,
        "runtime_usage": 10,
        "item_attribute": "Colour",
    },
    "Depth": {
        "source_index": 7,
        "runtime_usage": 12,
        "item_attribute": "Depth",
    },
    "BlendIndices": {
        "source_index": 8,
        "runtime_usage": 2,
        "item_attribute": "Indices",
    },
}

# FUN_008587e0 has explicit XML value decoding cases only for source type
# indices 0..5.  Later type strings are recognized by the declaration table but
# are not promoted to decoded neutral values here.
_XML_VALUE_DECODERS = {
    "F32",
    "F32Vec2",
    "F32Vec3",
    "F32Vec4",
    "RGBA32",
    "U8Vec4",
}

# XML usage runtime values are D3DDECLUSAGE values, not the binary IMB property
# ordinals.  Map by proven semantic/type identity rather than concatenating the
# XML runtime enum values.
_NEUTRAL_BY_XML: dict[tuple[str, str], tuple[str, str, int, bool]] = {
    ("F32Vec3", "Position"): ("200", "vertices", 3, False),
    ("F32Vec3", "Normal"): ("220", "normals", 3, False),
    ("F32Vec3", "Tangent"): ("240", "tangents", 3, False),
    ("F32Vec3", "Binormal"): ("250", "tangents2", 3, False),
    ("F32Vec4", "BlendWeights"): ("310", "bone_weights", 4, False),
    ("U8Vec4", "BlendIndices"): ("580", "bone_indices", 4, False),
}


def _local_tag(node: ET.Element) -> str:
    return str(node.tag).rsplit("}", 1)[-1]


def _children(node: ET.Element, tag: str) -> list[ET.Element]:
    return [child for child in list(node) if _local_tag(child) == tag]


def _first_child(node: ET.Element, tag: str) -> ET.Element | None:
    for child in list(node):
        if _local_tag(child) == tag:
            return child
    return None


def _required_attr(node: ET.Element, name: str) -> str:
    value = node.get(name)
    if value is None:
        raise ValueError(
            f"IMX {_local_tag(node)} is missing required {name!r} attribute"
        )
    return value.strip()


def _int_attr(
    node: ET.Element,
    name: str,
    *,
    default: int | None = None,
) -> int:
    value = node.get(name)
    if value is None:
        if default is None:
            raise ValueError(
                f"IMX {_local_tag(node)} is missing required {name!r} attribute"
            )
        return default
    try:
        parsed = int(value.strip(), 10)
    except ValueError as exc:
        raise ValueError(
            f"IMX {_local_tag(node)} attribute {name!r} is not an integer"
        ) from exc
    if parsed < 0:
        raise ValueError(
            f"IMX {_local_tag(node)} attribute {name!r} must be non-negative"
        )
    return parsed


def _float_attr(node: ET.Element, name: str) -> float:
    raw = _required_attr(node, name)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"IMX {_local_tag(node)} attribute {name!r} is not a float"
        ) from exc
    if not math.isfinite(value):
        raise ValueError(
            f"IMX {_local_tag(node)} attribute {name!r} is non-finite"
        )
    return value


def _float_values(raw: str, count: int, label: str) -> list[float]:
    parts = raw.split()
    if len(parts) != count:
        raise ValueError(
            f"IMX {label} expects {count} floats, got {len(parts)}"
        )
    try:
        values = [float(part) for part in parts]
    except ValueError as exc:
        raise ValueError(f"IMX {label} contains a non-float value") from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"IMX {label} contains a non-finite value")
    return values


def _uint_c_base0(raw: str, label: str) -> int:
    text = raw.strip()
    try:
        lower = text.lower()
        if lower.startswith("0x"):
            value = int(text, 16)
        elif len(text) > 1 and text.startswith("0"):
            value = int(text, 8)
        else:
            value = int(text, 10)
    except ValueError as exc:
        raise ValueError(f"IMX {label} is not an unsigned integer") from exc
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"IMX {label} exceeds uint32 range")
    return value


def _decode_item_value(
    type_name: str,
    raw: str,
    label: str,
) -> list[int | float]:
    if type_name == "F32":
        return _float_values(raw, 1, label)
    if type_name == "F32Vec2":
        return _float_values(raw, 2, label)
    if type_name == "F32Vec3":
        return _float_values(raw, 3, label)
    if type_name == "F32Vec4":
        return _float_values(raw, 4, label)
    if type_name == "RGBA32":
        value = _uint_c_base0(raw, label)
        return list(value.to_bytes(4, "little"))
    if type_name == "U8Vec4":
        parts = raw.split()
        if len(parts) != 4:
            raise ValueError(
                f"IMX {label} expects 4 decimal bytes, got {len(parts)}"
            )
        try:
            values = [int(part, 10) for part in parts]
        except ValueError as exc:
            raise ValueError(
                f"IMX {label} contains a non-integer byte"
            ) from exc
        if any(value < 0 or value > 255 for value in values):
            raise ValueError(f"IMX {label} byte is outside uint8 range")
        return values
    raise ValueError(
        f"IMX XML value decoding is not source-backed for Type {type_name}"
    )


def _neutral_mapping(
    type_name: str,
    usage_name: str,
    channel: int,
) -> tuple[str, str, int, bool] | None:
    if usage_name == "TexCoord":
        if not 0 <= channel <= 4:
            return None
        if type_name == "F32Vec2":
            return (
                str(130 + channel),
                f"uv:{130 + channel}",
                2,
                False,
            )
        if type_name == "F32Vec3":
            return (
                str(230 + channel),
                f"uv:{230 + channel}",
                3,
                False,
            )
        return None
    if usage_name == "Colour":
        if type_name != "RGBA32" or channel not in {0, 1}:
            return None
        return (
            str(460 + channel),
            "colors" if channel == 0 else "colors2",
            4,
            True,
        )
    base = _NEUTRAL_BY_XML.get((type_name, usage_name))
    if base is None or channel != 0:
        return None
    return base


def _expand_source_matrix(values: list[float]) -> list[float]:
    if len(values) != 12:
        raise ValueError("IMX bone transform requires 12 floats")
    return [
        values[0], values[1], values[2], 0.0,
        values[3], values[4], values[5], 0.0,
        values[6], values[7], values[8], 0.0,
        values[9], values[10], values[11], 1.0,
    ]


def _parse_root(data: bytes) -> ET.Element:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"invalid IMX XML: {exc}") from exc
    if _local_tag(root) == "MESH":
        return root
    for node in root.iter():
        if _local_tag(node) == "MESH":
            return node
    raise ValueError("IMX XML does not contain a MESH root")


def build_imx_neutral_geometry(data: bytes) -> dict[str, Any]:
    """Decode FUN_008587e0's XML mesh grammar into SHIFT.NeutralMesh/1."""
    root = _parse_root(data)
    vertex_count = _int_attr(root, "Vertices")
    declared_stream_count = _int_attr(root, "Streams")
    declared_buffer_count = _int_attr(root, "Buffers")

    env_raw = root.get("EnvMapType")
    if env_raw is None:
        env_runtime = 1
    elif env_raw == "EDEMT_INSIDE":
        env_runtime = 2
    elif env_raw == "EDEMT_OUTSIDE":
        env_runtime = 1
    else:
        env_runtime = 0

    sphere_node = _first_child(root, "BOUNDSPHERE")
    if sphere_node is None:
        raise ValueError("IMX MESH is missing BOUNDSPHERE")
    sphere = {
        "center_xyz": _float_values(
            _required_attr(sphere_node, "Centre"),
            3,
            "BOUNDSPHERE.Centre",
        ),
        "radius": _float_attr(sphere_node, "Radius"),
    }

    aabb_node = _first_child(root, "AABBOX")
    if aabb_node is None:
        raise ValueError("IMX MESH is missing AABBOX")
    aabb = {
        "min_xyz": _float_values(
            _required_attr(aabb_node, "Min"),
            3,
            "AABBOX.Min",
        ),
        "max_xyz": _float_values(
            _required_attr(aabb_node, "Max"),
            3,
            "AABBOX.Max",
        ),
    }

    bones_node = _first_child(root, "BONES")
    if bones_node is None:
        bones: dict[str, Any] = {
            "present": False,
            "count": 0,
            "names": [],
            "matrices": [],
        }
    else:
        bone_count = _int_attr(bones_node, "NumBones")
        bone_nodes = _children(bones_node, "NODE")
        if len(bone_nodes) != bone_count:
            raise ValueError(
                "IMX BONES NumBones does not match NODE child count"
            )
        names: list[str] = []
        matrices: list[dict[str, Any]] = []
        for index, node in enumerate(bone_nodes):
            name = _required_attr(node, "Name")
            values = _float_values(
                _required_attr(node, "Transform"),
                12,
                f"BONES.NODE[{index}].Transform",
            )
            names.append(name)
            matrices.append({
                "index": index,
                "name": name,
                "source_storage": "12xf32 / four rows of xyz",
                "source_values": values,
                "runtime_matrix_4x4": _expand_source_matrix(values),
                "runtime_stride": 0x40,
                "inverse_generated_by": "FUN_006308b0",
            })
        bones = {
            "present": True,
            "count": bone_count,
            "names": names,
            "matrices": matrices,
            "runtime_name_array_offset": 0x64,
            "runtime_matrix_array_offset": 0x68,
            "runtime_inverse_matrix_array_offset": 0x6C,
        }

    stream_nodes = _children(root, "STREAM")
    if len(stream_nodes) != declared_stream_count:
        raise ValueError(
            "IMX Streams attribute does not match STREAM child count"
        )

    mesh: dict[str, Any] = {
        "format": NEUTRAL_MESH_FORMAT,
        "source_format": SOURCE_FORMAT,
        "source_resource_name": None,
        "vertex_count": vertex_count,
        "triangle_count": 0,
        "vertex_properties": [],
        "property_layouts": [],
        "primitives": [],
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
            "source_layout": "xml-stream-arrays-then-runtime-interleave",
            "runtime_interleaved_stride": 0,
            "attributes": [],
        },
        "bones": bones,
        "bounding_sphere": sphere,
        "aabb": aabb,
        "environment_map_type": {
            "source": env_raw,
            "runtime_value": env_runtime,
        },
    }

    blockers: list[str] = []
    deferred_streams: list[dict[str, Any]] = []
    decoded_properties: list[str] = []
    seen_properties: set[str] = set()
    runtime_offset = 0

    for stream_index, node in enumerate(stream_nodes):
        type_name = _required_attr(node, "Type")
        usage_name = _required_attr(node, "Usage")
        channel = _int_attr(node, "Channel", default=0)
        type_info = _XML_TYPES.get(type_name)
        usage_info = _XML_USAGES.get(usage_name)
        if type_info is None:
            raise ValueError(f"unknown IMX STREAM Type {type_name!r}")
        if usage_info is None:
            raise ValueError(f"unknown IMX STREAM Usage {usage_name!r}")

        items = _children(node, "ITEM")
        if len(items) != vertex_count:
            raise ValueError(
                f"IMX STREAM {stream_index} ITEM count {len(items)} "
                f"does not match Vertices={vertex_count}"
            )

        raw_values = [
            _required_attr(item, str(usage_info["item_attribute"]))
            for item in items
        ]
        mapping = _neutral_mapping(type_name, usage_name, channel)
        attribute: dict[str, Any] = {
            "stream_index": stream_index,
            "source_type": type_name,
            "source_type_index": int(type_info["source_index"]),
            "runtime_type_ordinal": int(type_info["runtime_type"]),
            "source_usage": usage_name,
            "source_usage_index": int(usage_info["source_index"]),
            "runtime_usage_ordinal": int(usage_info["runtime_usage"]),
            "channel": channel,
            "item_attribute": str(usage_info["item_attribute"]),
            "element_size": int(type_info["size"]),
            "runtime_element_offset": runtime_offset,
            "status": "blocked-unmapped",
        }
        runtime_offset += int(type_info["size"])

        if type_name not in _XML_VALUE_DECODERS:
            reason = (
                f"stream-{stream_index}:xml-value-decoder-unproven:{type_name}"
            )
            blockers.append(reason)
            deferred_streams.append({
                **attribute,
                "reason": reason,
                "raw_values": raw_values,
            })
            mesh["vertex_layout"]["attributes"].append(attribute)
            continue

        if mapping is None:
            reason = (
                f"stream-{stream_index}:neutral-semantic-unmapped:"
                f"{type_name}/{usage_name}/{channel}"
            )
            blockers.append(reason)
            deferred_streams.append({
                **attribute,
                "reason": reason,
                "raw_values": raw_values,
            })
            mesh["vertex_layout"]["attributes"].append(attribute)
            continue

        property_id, field, components, normalized = mapping
        if property_id in seen_properties:
            raise ValueError(
                f"duplicate IMX neutral property {property_id}"
            )
        seen_properties.add(property_id)
        rows = [
            _decode_item_value(
                type_name,
                raw,
                f"STREAM[{stream_index}].ITEM[{item_index}]",
            )
            for item_index, raw in enumerate(raw_values)
        ]

        if field.startswith("uv:"):
            mesh["uv_layers"][field.split(":", 1)[1]] = rows
        else:
            mesh[field] = rows

        storage = {
            "F32": "f32x1",
            "F32Vec2": "f32x2",
            "F32Vec3": "f32x3",
            "F32Vec4": "f32x4",
            "RGBA32": "u8x4",
            "U8Vec4": "u8x4",
        }[type_name]
        decoded_properties.append(property_id)
        attribute.update({
            "property_id": property_id,
            "storage": storage,
            "components": components,
            "normalized": normalized,
            "status": "decoded",
        })
        mesh["property_layouts"].append({
            "id": property_id,
            "name": field,
            "stride": int(type_info["size"]),
            "bytes": vertex_count * int(type_info["size"]),
            "storage": storage,
            "components": components,
            "normalized": normalized,
            "source_stream_index": stream_index,
        })
        mesh["vertex_layout"]["attributes"].append(attribute)

    mesh["vertex_layout"]["runtime_interleaved_stride"] = runtime_offset

    index_nodes = _children(root, "INDEXBUFFER")
    if len(index_nodes) != declared_buffer_count:
        raise ValueError(
            "IMX Buffers attribute does not match INDEXBUFFER child count"
        )

    primitives: list[dict[str, Any]] = []
    combined_indices: list[int] = []
    for primitive_index, node in enumerate(index_nodes):
        material = (node.get("Material") or "").strip()
        if not material:
            blockers.append(
                f"primitive-{primitive_index}:material-reference-missing"
            )
        triangle_count = _int_attr(node, "Entries")
        triangle_nodes = _children(node, "TRIANGLE")
        if len(triangle_nodes) < triangle_count:
            raise ValueError(
                f"IMX INDEXBUFFER {primitive_index} has fewer TRIANGLE nodes "
                f"than Entries={triangle_count}"
            )

        indices: list[int] = []
        for triangle_index, triangle in enumerate(
            triangle_nodes[:triangle_count]
        ):
            parts = _required_attr(triangle, "Indices").split()
            if len(parts) != 3:
                raise ValueError(
                    f"IMX TRIANGLE {primitive_index}:{triangle_index} "
                    "must contain three indices"
                )
            try:
                values = [int(part, 10) for part in parts]
            except ValueError as exc:
                raise ValueError(
                    f"IMX TRIANGLE {primitive_index}:{triangle_index} "
                    "contains a non-integer index"
                ) from exc
            if any(value < 0 or value > 0xFFFF for value in values):
                raise ValueError("IMX TRIANGLE index exceeds uint16 range")
            if any(value >= vertex_count for value in values):
                raise ValueError("IMX TRIANGLE index exceeds vertex count")
            indices.extend(values)

        palette_count = _int_attr(node, "NumBones", default=0)
        palette: list[int] = []
        palette_raw = node.get("BoneIndices")
        if palette_count:
            if palette_raw is None:
                raise ValueError(
                    f"IMX INDEXBUFFER {primitive_index} NumBones requires "
                    "BoneIndices"
                )
            try:
                palette = [
                    int(part, 10)
                    for part in palette_raw.split()
                ]
            except ValueError as exc:
                raise ValueError(
                    f"IMX INDEXBUFFER {primitive_index} has invalid "
                    "BoneIndices"
                ) from exc
            if len(palette) != palette_count:
                raise ValueError(
                    f"IMX INDEXBUFFER {primitive_index} BoneIndices count "
                    "does not match NumBones"
                )
            if any(value < 0 or value > 0xFFFF for value in palette):
                raise ValueError("IMX bone palette index exceeds uint16 range")

        first_index = len(combined_indices)
        combined_indices.extend(indices)
        vertex_range = (
            [min(indices), max(indices)] if indices else [0, 0]
        )
        primitives.append({
            "index": primitive_index,
            "material": material,
            "material_opaque_word": None,
            "primitive_type": 4,
            "triangle_count": triangle_count,
            "first_index": first_index,
            "index_count": len(indices),
            "vertex_range_u16": vertex_range,
            "vertex_range_source": "derived-from-XML-triangle-indices",
            "bone_palette_u16": palette,
            "bounding_sphere": None,
            "aabb": None,
            "source_triangle_node_count": len(triangle_nodes),
            "ignored_extra_triangle_count": (
                len(triangle_nodes) - triangle_count
            ),
        })

    mesh["indices"] = combined_indices
    mesh["triangle_count"] = len(combined_indices) // 3
    mesh["vertex_properties"] = list(decoded_properties)
    mesh["primitives"] = [dict(row) for row in primitives]

    if vertex_count and not mesh["vertices"]:
        blockers.append("position-stream-200-missing")
    if declared_buffer_count and not combined_indices:
        blockers.append("primitive-index-payload-missing")

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "source": {
            "format": SOURCE_FORMAT,
            "loader": "FUN_008587e0",
            "retail_name": (
                "MWL::Renderer::WinRenderer::"
                "CMeshPrimitiveType::LoadXMLMeshFromResource"
            ),
            "source_file": ".\\Source\\Platforms\\Win\\CPrimitiveType.cpp",
            "root": "MESH",
            "declared_vertex_count": vertex_count,
            "declared_stream_count": declared_stream_count,
            "declared_buffer_count": declared_buffer_count,
        },
        "mesh": mesh,
        "primitive_count": len(primitives),
        "primitives": primitives,
        "decoded_properties": decoded_properties,
        "deferred_stream_count": len(deferred_streams),
        "deferred_streams": deferred_streams,
        "boundary": {
            "xml_mesh_grammar": "source-backed-FUN_008587e0",
            "type_table": "PTR_DAT_00b901d0/DAT_00b90088/DAT_00b8eef0",
            "usage_table": "PTR_s_Position_00b901a8/DAT_00b9011c",
            "runtime_usage_values_are_d3ddeclusage": True,
            "neutral_property_mapping": (
                "semantic/type mapping; never concatenates XML D3D usage codes"
            ),
            "unsupported_xml_stream_policy": "preserve-raw-and-block",
            "primitive_type": "source-backed constant 4 / triangle-list",
            "primitive_vertex_range": "derived from TRIANGLE Indices",
            "primitive_bounds": "not serialized by recovered XML loader",
            "imb_container_equivalence": False,
            "meb_container_equivalence": False,
            "render_command_generation": "not-performed",
            "material_resolution": "not-performed",
        },
    }


def build_imx_neutral_geometry_file(
    input_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    report = build_imx_neutral_geometry(Path(input_path).read_bytes())
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decode a source-backed .imx XML mesh into neutral geometry"
    )
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = build_imx_neutral_geometry_file(args.input, args.output)
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
