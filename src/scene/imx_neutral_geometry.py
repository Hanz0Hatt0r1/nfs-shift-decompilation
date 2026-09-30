"""Neutral geometry adapter for source-backed SHIFT XML MeshInst (.imx)."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.IMXNeutralGeometry/1"
SOURCE_FORMAT = "SHIFT.IMXXMLMesh/1"
NEUTRAL_MESH_FORMAT = "SHIFT.NeutralMesh/1"

# Exact retail XML name tables recovered from SHIFT.exe:
# PTR_DAT_00b901d0 (17 Type names) and PTR_s_Position_00b901a8 (9 Usage names).
TYPE_NAMES = (
    "F32",
    "F32Vec2",
    "F32Vec3",
    "F32Vec4",
    "RGBA32",
    "U8Vec4",
    "S16Vec2",
    "S16Vec4",
    "U8Vec4N",
    "S16Vec2N",
    "S16Vec4N",
    "U16Vec2N",
    "U16Vec4N",
    "U10Vec3",
    "U10Vec3N",
    "F16Vec2",
    "F16Vec4",
)
TYPE_SIZES = (4, 8, 12, 16, 4, 4, 4, 8, 4, 4, 8, 4, 8, 4, 4, 4, 8)
TYPE_CODES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 15)

USAGE_NAMES = (
    "Position",
    "BlendWeights",
    "Normal",
    "TexCoord",
    "Tangent",
    "Binormal",
    "Colour",
    "Depth",
    "BlendIndices",
)
USAGE_CODES = (0, 1, 3, 5, 6, 7, 10, 12, 2)
USAGE_VALUE_FIELDS = (
    "Pos",
    "Weights",
    "Normal",
    "UV",
    "Tangent",
    "Binormal",
    "Colour",
    "Depth",
    "Indices",
)

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

_TYPE_ORDINAL = {name: index for index, name in enumerate(TYPE_NAMES)}
_USAGE_ORDINAL = {name: index for index, name in enumerate(USAGE_NAMES)}


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _tag(child) == name]


def _first(element: ET.Element, name: str) -> ET.Element | None:
    for child in list(element):
        if _tag(child) == name:
            return child
    return None


def _required_attr(element: ET.Element, name: str) -> str:
    value = element.get(name)
    if value is None:
        raise ValueError(f"{_tag(element)} missing required {name} attribute")
    return value


def _nonnegative_int(element: ET.Element, name: str) -> int:
    raw = _required_attr(element, name)
    try:
        value = int(raw, 0)
    except ValueError as exc:
        raise ValueError(f"{_tag(element)} {name} is not an integer") from exc
    if value < 0:
        raise ValueError(f"{_tag(element)} {name} must be non-negative")
    return value


def _float_list(raw: str, count: int, *, label: str) -> list[float]:
    values = raw.replace(",", " ").split()
    if len(values) != count:
        raise ValueError(f"{label} requires {count} scalars; got {len(values)}")
    try:
        return [float(value) for value in values]
    except ValueError as exc:
        raise ValueError(f"{label} contains a non-float scalar") from exc


def _u8_list(raw: str, count: int, *, label: str) -> list[int]:
    values = raw.replace(",", " ").split()
    if len(values) != count:
        raise ValueError(f"{label} requires {count} integer scalars; got {len(values)}")
    rows: list[int] = []
    for value in values:
        try:
            parsed = int(value, 10)
        except ValueError as exc:
            raise ValueError(f"{label} contains a non-integer scalar") from exc
        if not 0 <= parsed <= 0xFF:
            raise ValueError(f"{label} scalar is outside U8 range")
        rows.append(parsed)
    return rows


def _u16_list(raw: str, count: int | None, *, label: str) -> list[int]:
    values = raw.replace(",", " ").split()
    if count is not None and len(values) != count:
        raise ValueError(f"{label} requires {count} integer scalars; got {len(values)}")
    rows: list[int] = []
    for value in values:
        try:
            parsed = int(value, 10)
        except ValueError as exc:
            raise ValueError(f"{label} contains a non-integer scalar") from exc
        if not 0 <= parsed <= 0xFFFF:
            raise ValueError(f"{label} scalar is outside U16 range")
        rows.append(parsed)
    return rows


def _decode_stream_value(type_ordinal: int, raw: str, *, label: str) -> list[int | float]:
    # FUN_008587e0 has explicit XML ITEM conversion cases only for ordinals 0..5.
    if type_ordinal == 0:
        return _float_list(raw, 1, label=label)
    if type_ordinal == 1:
        return _float_list(raw, 2, label=label)
    if type_ordinal == 2:
        return _float_list(raw, 3, label=label)
    if type_ordinal == 3:
        return _float_list(raw, 4, label=label)
    if type_ordinal == 4:
        try:
            packed = int(raw.strip(), 0)
        except ValueError as exc:
            raise ValueError(f"{label} is not an RGBA32 integer") from exc
        if not 0 <= packed <= 0xFFFFFFFF:
            raise ValueError(f"{label} is outside RGBA32 range")
        # The retail declaration code is D3DCOLOR (type code 4). Preserve the
        # exact little-endian four bytes consumed by the D3D9 vertex stream.
        return list(packed.to_bytes(4, "little"))
    if type_ordinal == 5:
        return _u8_list(raw, 4, label=label)
    raise ValueError(
        f"IMX XML loader has no recovered ITEM conversion for Type ordinal {type_ordinal}"
    )


def _property_id(type_ordinal: int, usage_ordinal: int, channel: int) -> str:
    return f"{type_ordinal}{usage_ordinal}{channel}"


def _parse_bones(mesh_node: ET.Element) -> dict[str, Any] | None:
    bones_node = _first(mesh_node, "BONES")
    if bones_node is None:
        return None
    count = _nonnegative_int(bones_node, "NumBones")
    nodes = _children(bones_node, "NODE")
    if len(nodes) != count:
        raise ValueError(
            f"BONES NumBones={count} but XML contains {len(nodes)} NODE elements"
        )
    records: list[dict[str, Any]] = []
    for index, node in enumerate(nodes):
        name = _required_attr(node, "Name")
        values = _float_list(
            _required_attr(node, "Transform"),
            12,
            label=f"BONES/NODE[{index}] Transform",
        )
        matrix = [
            values[0], values[1], values[2], 0.0,
            values[3], values[4], values[5], 0.0,
            values[6], values[7], values[8], 0.0,
            values[9], values[10], values[11], 1.0,
        ]
        records.append({"index": index, "name": name, "matrix": matrix})
    return {
        "count": count,
        "records": records,
        "source_matrix_shape": "12 floats expanded to row-major 4x4",
    }


def build_imx_neutral_geometry(data: bytes | str) -> dict[str, Any]:
    """Decode the source-backed FUN_008587e0 XML mesh grammar."""
    raw = data.decode("utf-8-sig") if isinstance(data, bytes) else str(data)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"invalid IMX XML: {exc}") from exc

    mesh_node = root if _tag(root) == "MESH" else next(
        (node for node in root.iter() if _tag(node) == "MESH"),
        None,
    )
    if mesh_node is None:
        raise ValueError("IMX document does not contain MESH")

    vertex_count = _nonnegative_int(mesh_node, "Vertices")
    declared_stream_count = _nonnegative_int(mesh_node, "Streams")
    declared_buffer_count = _nonnegative_int(mesh_node, "Buffers")
    env_text = mesh_node.get("EnvMapType")
    env_map_type = (
        1
        if env_text is None
        else 2
        if env_text == "EDEMT_INSIDE"
        else 1
        if env_text == "EDEMT_OUTSIDE"
        else 0
    )

    sphere_node = _first(mesh_node, "BOUNDSPHERE")
    box_node = _first(mesh_node, "AABBOX")
    if sphere_node is None:
        raise ValueError("IMX MESH missing BOUNDSPHERE")
    if box_node is None:
        raise ValueError("IMX MESH missing AABBOX")
    centre = _float_list(
        _required_attr(sphere_node, "Centre"),
        3,
        label="BOUNDSPHERE Centre",
    )
    radius = float(_required_attr(sphere_node, "Radius"))
    aabb_min = _float_list(
        _required_attr(box_node, "Min"),
        3,
        label="AABBOX Min",
    )
    aabb_max = _float_list(
        _required_attr(box_node, "Max"),
        3,
        label="AABBOX Max",
    )

    stream_nodes = _children(mesh_node, "STREAM")
    if len(stream_nodes) != declared_stream_count:
        raise ValueError(
            f"MESH Streams={declared_stream_count} but XML contains "
            f"{len(stream_nodes)} STREAM elements"
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
            "source_layout": "xml-stream-items",
            "runtime_interleaved_stride": 0,
            "attributes": [],
        },
        "bones": _parse_bones(mesh_node),
        "bounding_sphere": [*centre, radius],
        "aabb": {"min": aabb_min, "max": aabb_max},
        "environment_map_type": {
            "source": env_text,
            "runtime_value": env_map_type,
        },
    }

    decoded_properties: list[str] = []
    deferred_streams: list[dict[str, Any]] = []
    seen_properties: set[str] = set()
    runtime_offset = 0

    for stream_index, stream in enumerate(stream_nodes):
        type_name = _required_attr(stream, "Type")
        usage_name = _required_attr(stream, "Usage")
        if type_name not in _TYPE_ORDINAL:
            raise ValueError(f"STREAM[{stream_index}] unknown Type {type_name!r}")
        if usage_name not in _USAGE_ORDINAL:
            raise ValueError(f"STREAM[{stream_index}] unknown Usage {usage_name!r}")
        type_ordinal = _TYPE_ORDINAL[type_name]
        usage_ordinal = _USAGE_ORDINAL[usage_name]
        channel = _nonnegative_int(stream, "Channel")
        property_id = _property_id(type_ordinal, usage_ordinal, channel)
        if property_id in seen_properties:
            raise ValueError(
                f"duplicate IMX Type/Usage/Channel property {property_id}"
            )
        seen_properties.add(property_id)

        if type_ordinal > 5:
            raise ValueError(
                f"STREAM[{stream_index}] Type {type_name} has no recovered "
                "FUN_008587e0 XML ITEM conversion"
            )

        items = _children(stream, "ITEM")
        if len(items) != vertex_count:
            raise ValueError(
                f"STREAM[{stream_index}] contains {len(items)} ITEM rows; "
                f"expected {vertex_count}"
            )
        value_field = USAGE_VALUE_FIELDS[usage_ordinal]
        rows = [
            _decode_stream_value(
                type_ordinal,
                _required_attr(item, value_field),
                label=f"STREAM[{stream_index}]/ITEM[{item_index}] {value_field}",
            )
            for item_index, item in enumerate(items)
        ]

        element_size = TYPE_SIZES[type_ordinal]
        attribute = {
            "property_id": property_id,
            "type_name": type_name,
            "type_ordinal": type_ordinal,
            "d3d9_type_code": TYPE_CODES[type_ordinal],
            "usage_name": usage_name,
            "usage_ordinal": usage_ordinal,
            "d3d9_usage_code": USAGE_CODES[usage_ordinal],
            "channel": channel,
            "source_value_field": value_field,
            "element_size": element_size,
            "runtime_element_offset": runtime_offset,
            "status": "deferred-unmapped",
        }
        runtime_offset += element_size

        mapping = _FIELD_BY_PROPERTY.get(property_id)
        if mapping is None:
            deferred_streams.append({
                **attribute,
                "values": rows,
            })
            mesh["vertex_layout"]["attributes"].append(attribute)
            continue

        field, storage, components, normalized = mapping
        if field.startswith("uv:"):
            mesh["uv_layers"][field.split(":", 1)[1]] = rows
        else:
            mesh[field] = rows

        decoded_properties.append(property_id)
        attribute.update({
            "storage": storage,
            "components": components,
            "normalized": normalized,
            "status": "decoded",
        })
        mesh["property_layouts"].append({
            "id": property_id,
            "name": field,
            "stride": element_size,
            "bytes": element_size * vertex_count,
            "storage": storage,
            "components": components,
            "normalized": normalized,
        })
        mesh["vertex_layout"]["attributes"].append(attribute)

    mesh["vertex_layout"]["runtime_interleaved_stride"] = runtime_offset

    buffer_nodes = _children(mesh_node, "INDEXBUFFER")
    if len(buffer_nodes) != declared_buffer_count:
        raise ValueError(
            f"MESH Buffers={declared_buffer_count} but XML contains "
            f"{len(buffer_nodes)} INDEXBUFFER elements"
        )

    primitives: list[dict[str, Any]] = []
    combined_indices: list[int] = []
    for buffer_index, buffer_node in enumerate(buffer_nodes):
        entries = _nonnegative_int(buffer_node, "Entries")
        triangles = _children(buffer_node, "TRIANGLE")
        if len(triangles) != entries:
            raise ValueError(
                f"INDEXBUFFER[{buffer_index}] Entries={entries} but XML contains "
                f"{len(triangles)} TRIANGLE elements"
            )
        indices: list[int] = []
        for triangle_index, triangle in enumerate(triangles):
            row = _u16_list(
                _required_attr(triangle, "Indices"),
                3,
                label=(
                    f"INDEXBUFFER[{buffer_index}]/TRIANGLE[{triangle_index}] "
                    "Indices"
                ),
            )
            if vertex_count and any(index >= vertex_count for index in row):
                raise ValueError(
                    f"INDEXBUFFER[{buffer_index}] triangle index exceeds vertex count"
                )
            indices.extend(row)

        num_bones = int(buffer_node.get("NumBones", "0"), 0)
        if num_bones < 0:
            raise ValueError(f"INDEXBUFFER[{buffer_index}] NumBones must be non-negative")
        palette_raw = buffer_node.get("BoneIndices")
        if num_bones:
            if palette_raw is None:
                raise ValueError(
                    f"INDEXBUFFER[{buffer_index}] NumBones requires BoneIndices"
                )
            palette = _u16_list(
                palette_raw,
                num_bones,
                label=f"INDEXBUFFER[{buffer_index}] BoneIndices",
            )
        else:
            palette = []

        first_index = len(combined_indices)
        combined_indices.extend(indices)
        primitives.append({
            "index": buffer_index,
            "material": str(buffer_node.get("Material") or ""),
            "source_type": buffer_node.get("Type"),
            "primitive_type": 4,
            "triangle_count": entries,
            "first_index": first_index,
            "index_count": len(indices),
            "vertex_range_u16": (
                [min(indices), max(indices)] if indices else [0, 0]
            ),
            "bone_palette_u16": palette,
            "bounding_sphere": None,
            "aabb": None,
        })

    mesh["indices"] = combined_indices
    mesh["triangle_count"] = len(combined_indices) // 3
    mesh["vertex_properties"] = list(decoded_properties)
    mesh["primitives"] = [dict(row) for row in primitives]

    blockers: list[str] = []
    if vertex_count and not mesh["vertices"]:
        blockers.append("position-stream-200-missing")
    if declared_buffer_count and not combined_indices:
        blockers.append("primitive-index-payload-missing")

    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "source": {
            "format": SOURCE_FORMAT,
            "root": "MESH",
            "vertex_count": vertex_count,
            "stream_count": declared_stream_count,
            "buffer_count": declared_buffer_count,
            "environment_map_type": env_text,
        },
        "mesh": mesh,
        "primitive_count": len(primitives),
        "primitives": primitives,
        "decoded_properties": decoded_properties,
        "deferred_stream_count": len(deferred_streams),
        "deferred_streams": deferred_streams,
        "boundary": {
            "xml_loader_function": "FUN_008587e0",
            "type_name_table": "PTR_DAT_00b901d0",
            "usage_name_table": "PTR_s_Position_00b901a8",
            "xml_item_type_conversion_ordinals": [0, 1, 2, 3, 4, 5],
            "primitive_type": "source-constant-4-triangle-list",
            "index_count_rule": "Entries*3 via FUN_00853c80(type=4)",
            "neutral_field_mapping": "proven Type/Usage/Channel triples only",
            "unknown_stream_policy": "preserve-decoded-values-and-defer",
            "meb_container_equivalence": False,
            "imb_container_equivalence": False,
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
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decode a source-backed .imx XML MeshInst into neutral geometry"
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
