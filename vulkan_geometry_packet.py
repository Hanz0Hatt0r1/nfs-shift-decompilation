"""Export a validated SHIFT.RenderCommand/1 mesh into a Vulkan-neutral binary packet.

The native Vulkan backend deliberately does not parse BFF/MEB/RenderCommand JSON. This
module is the bridge from the neutral Python submission contract to a small, versioned
binary geometry packet. Phase 208 supports POSITION0 only; other RenderCommand
attributes are reported as deferred rather than guessed.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VulkanGeometryPacket/1"
MAGIC = b"SVGP"
VERSION = 2
HEADER = struct.Struct("<4sIIIIII4f")
ATTRIBUTE = struct.Struct("<IIII")
FORMAT_FLOAT2 = 1
FORMAT_FLOAT3 = 2
FORMAT_FLOAT4 = 3
FORMAT_UNORM8X4 = 4
FORMAT_UINT8X4 = 5


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _position_attribute(command: dict[str, Any]) -> dict[str, Any]:
    attributes = ((command.get("mesh") or {}).get("vertex_layout") or {}).get("attributes") or []
    rows = [
        row for row in attributes
        if str(row.get("property_id")) == "200"
        and str(row.get("usage", "")).upper() == "POSITION"
        and int(row.get("usage_index", 0)) == 0
    ]
    if len(rows) != 1:
        raise ValueError("RenderCommand must expose exactly one POSITION0 property 200")
    row = dict(rows[0])
    if int(row.get("location", -1)) != 0:
        raise ValueError("Phase 208 Vulkan geometry shader requires POSITION0 at location 0")
    if str(row.get("android", "")).upper().replace("_", "") not in {"FLOAT32X3", "F32X3"} and str(row.get("storage", "")).upper().replace("_", "") not in {"FLOAT32X3", "F32X3"}:
        if str(row.get("d3d9", "")).upper() != "FLOAT3":
            raise ValueError("POSITION0 does not have a proven FLOAT3 representation")
    return row


def _vertices(mesh: dict[str, Any]) -> list[list[float]]:
    rows = mesh.get("vertices") or []
    if not isinstance(rows, list) or not rows:
        raise ValueError("mesh has no vertices")
    result: list[list[float]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, (list, tuple)) or len(row) < 3:
            raise ValueError(f"vertex {index} does not contain three coordinates")
        result.append([float(row[0]), float(row[1]), float(row[2])])
    return result


def _bounds(vertices: list[list[float]]) -> tuple[list[float], float]:
    lo = [min(row[i] for row in vertices) for i in range(3)]
    hi = [max(row[i] for row in vertices) for i in range(3)]
    center = [(lo[i] + hi[i]) * 0.5 for i in range(3)]
    extent = max(hi[i] - lo[i] for i in range(3))
    if extent <= 0.0:
        raise ValueError("degenerate vertex bounds")
    return center, 1.6 / extent





def _source_values(mesh: dict[str, Any], property_id: str) -> list[Any] | None:
    field_map = {
        "200": "vertices",
        "220": "normals",
        "240": "tangents",
        "250": "tangents2",
        "310": "bone_weights",
        "580": "bone_indices",
        "460": "colors",
        "461": "colors2",
    }
    field = field_map.get(property_id)
    if field is not None:
        value = mesh.get(field)
        return value if isinstance(value, list) else None
    uv_value = (mesh.get("uv_layers") or {}).get(property_id)
    if isinstance(uv_value, list):
        return uv_value
    return None


def _attribute_format(row: dict[str, Any]) -> int:
    storage = str(row.get("android") or row.get("storage") or "").upper().replace("_", "").replace("-", "")
    components = int(row.get("components", 0) or 0)
    normalized = bool(row.get("normalized"))
    property_id = str(row.get("property_id") or "")

    explicit_format = row.get("format")
    if isinstance(explicit_format, int):
        if explicit_format in {
            FORMAT_FLOAT2, FORMAT_FLOAT3, FORMAT_FLOAT4,
            FORMAT_UNORM8X4, FORMAT_UINT8X4,
        }:
            return explicit_format
    if storage in {"FLOAT32X2", "F32X2"} and components in {0, 2}:
        return FORMAT_FLOAT2
    if storage in {"FLOAT32X3", "F32X3"} and components in {0, 3}:
        return FORMAT_FLOAT3
    if storage in {"FLOAT32X4", "F32X4"} and components in {0, 4}:
        return FORMAT_FLOAT4
    if (storage.startswith("UINT8X4") or storage in {"UBYTE4", "UBYTE4N"}) and components in {0, 4}:
        if property_id == "460":
            if not normalized:
                raise ValueError("COLOR0 must remain normalized in Vulkan packet")
            return FORMAT_UNORM8X4
        if property_id == "580" and not normalized:
            return FORMAT_UINT8X4
        if normalized:
            return FORMAT_UNORM8X4
        return FORMAT_UINT8X4
    raise ValueError(
        f"RenderCommand property {property_id} has unsupported Vulkan source storage {storage!r}"
    )


def _pack_attribute_vertex(blob: bytearray, base: int, row: dict[str, Any], value: Any) -> None:
    property_id = str(row.get("property_id") or "")
    fmt = _attribute_format(row)
    offset = int(row.get("offset", 0))
    position = base + offset

    if fmt == FORMAT_FLOAT2:
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            raise ValueError(f"property {property_id} vertex does not contain float2")
        struct.pack_into("<2f", blob, position, float(value[0]), float(value[1]))
        return
    if fmt == FORMAT_FLOAT3:
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            raise ValueError(f"property {property_id} vertex does not contain float3")
        struct.pack_into(
            "<3f", blob, position,
            float(value[0]), float(value[1]), float(value[2])
        )
        return
    if fmt == FORMAT_FLOAT4:
        if not isinstance(value, (list, tuple)) or len(value) < 4:
            raise ValueError(f"property {property_id} vertex does not contain float4")
        struct.pack_into(
            "<4f", blob, position,
            float(value[0]), float(value[1]), float(value[2]), float(value[3])
        )
        return

    if not isinstance(value, (list, tuple)) or len(value) < 4:
        raise ValueError(f"property {property_id} vertex does not contain four bytes")
    raw = [max(0, min(255, int(value[i]))) for i in range(4)]
    if property_id == "460":
        # The executable-backed COLOR0 ABI is D3DCOLOR: source bytes are BGRA,
        # while the Vulkan normalized vertex value is consumed as RGBA.
        raw = [raw[2], raw[1], raw[0], raw[3]]
    blob[position:position + 4] = bytes(raw)


def _build_attributes(command: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = ((command.get("mesh") or {}).get("vertex_layout") or {}).get("attributes") or []
    if not rows:
        raise ValueError("RenderCommand contains no vertex attributes")
    result: list[dict[str, Any]] = []
    deferred: list[str] = []
    for raw in rows:
        row = dict(raw)
        pid = str(row.get("property_id") or "")
        try:
            fmt = _attribute_format(row)
        except (TypeError, ValueError) as exc:
            if pid != "200" and str(row.get("abi_status")) in {"ambiguous", "unknown"}:
                deferred.append(pid)
                continue
            raise exc
        source = row.get("abi_status")
        if pid == "461" and source != "proven":
            deferred.append(pid)
            continue
        if pid != "200" and source not in {"proven", "inferred"}:
            deferred.append(pid)
            continue
        result.append({
            "property_id": pid,
            "location": int(row.get("location")),
            "offset": int(row.get("offset", 0)),
            "stride": int(row.get("stride") or ((command.get("mesh") or {}).get("vertex_layout") or {}).get("buffer_stride", 0)),
            "format": fmt,
            "element_size": int(row.get("element_size") or 0),
            "abi_status": source,
        })
    positions = [x for x in result if x["property_id"] == "200" and x["location"] == 0]
    if len(positions) != 1:
        raise ValueError("Vulkan packet requires exactly one proven POSITION0 at location 0")
    return result, sorted(set(deferred))


def export_vulkan_geometry_packet(
    render_command: dict[str, Any] | str | Path,
    mesh: dict[str, Any] | str | Path,
    output: str | Path,
    *,
    submesh_index: int = 0,
) -> dict[str, Any]:
    command = _load(render_command) if isinstance(render_command, (str, Path)) else dict(render_command)
    mesh_data = _load(mesh) if isinstance(mesh, (str, Path)) else dict(mesh)

    if command.get("format") != "SHIFT.RenderCommand/1":
        raise ValueError("input is not SHIFT.RenderCommand/1")
    if mesh_data.get("vertices") is None or mesh_data.get("indices") is None:
        raise ValueError("mesh JSON must contain vertices and indices")

    vertex_attributes, deferred_properties = _build_attributes(command)
    layout = (command.get("mesh") or {}).get("vertex_layout") or {}
    stride = int(layout.get("buffer_stride", 0) or 0)
    if stride <= 0:
        stride = max(
            int(row["offset"]) + int(row["element_size"])
            for row in vertex_attributes
        )

    vertices = _vertices(mesh_data)
    indices = mesh_data["indices"]
    if not isinstance(indices, list) or not indices:
        raise ValueError("mesh has no indices")
    normalized_indices: list[int] = []
    for index, value in enumerate(indices):
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"index {index} is not an integer")
        if ivalue < 0 or ivalue >= len(vertices):
            raise ValueError(f"index {index} points outside vertex array")
        normalized_indices.append(ivalue)

    submeshes = command.get("submeshes") or []
    if submesh_index < 0 or submesh_index >= len(submeshes):
        raise ValueError(f"submesh index out of range: {submesh_index}")
    submesh = submeshes[submesh_index]
    first_index = int(submesh.get("first_index", 0))
    index_count = int(submesh.get("index_count", len(normalized_indices)))
    if first_index < 0 or index_count <= 0 or first_index + index_count > len(normalized_indices):
        raise ValueError("submesh index range is outside the supplied index buffer")
    if index_count % 3 != 0:
        raise ValueError("geometry packet requires a triangle-list index count")

    if len(vertices) != int((command.get("mesh") or {}).get("vertex_count") or len(vertices)):
        raise ValueError("mesh vertex_count disagrees with RenderCommand")

    sources = {
        row["property_id"]: _source_values(mesh_data, row["property_id"])
        for row in vertex_attributes
    }
    for row in vertex_attributes:
        source = sources[row["property_id"]]
        if not isinstance(source, list) or len(source) != len(vertices):
            raise ValueError(
                f"RenderCommand attribute {row['property_id']} has no complete neutral mesh source"
            )

    center, scale = _bounds(vertices)

    vertex_blob = bytearray(len(vertices) * stride)
    for index in range(len(vertices)):
        base = index * stride
        for row in vertex_attributes:
            _pack_attribute_vertex(vertex_blob, base, row, sources[row["property_id"]][index])

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    selected_indices = normalized_indices[first_index:first_index + index_count]
    if len(selected_indices) != index_count:
        raise ValueError("failed to materialize selected submesh index range")

    header = HEADER.pack(
        MAGIC,
        VERSION,
        len(vertices),
        len(selected_indices),
        stride,
        len(vertex_attributes),
        0,
        float(center[0]),
        float(center[1]),
        float(center[2]),
        float(scale),
    )
    attribute_blob = b"".join(
        ATTRIBUTE.pack(
            int(row["location"]),
            int(row["format"]),
            int(row["offset"]),
            int(row["stride"]),
        )
        for row in vertex_attributes
    )
    index_blob = struct.pack(f"<{len(selected_indices)}I", *selected_indices)
    output_path.write_bytes(header + attribute_blob + vertex_blob + index_blob)

    return {
        "format": FORMAT,
        "version": VERSION,
        "output": str(output_path),
        "command_format": command.get("format"),
        "command_ready": bool(command.get("ready")),
        "command_blocking_reasons": list(command.get("blocking_reasons", []) or []),
        "submesh_index": submesh_index,
        "source_first_index": first_index,
        "first_index": 0,
        "index_count": index_count,
        "vertex_count": len(vertices),
        "source_index_count": len(normalized_indices),
        "vertex_stride": stride,
        "attributes": vertex_attributes,
        "deferred_properties": deferred_properties,
        "normalization": {
            "center": center,
            "scale": scale,
            "source_space": "MEB object space",
            "target_space": "Vulkan clip-space cube",
            "purpose": "geometry-only checkpoint",
        },
        "binary_header": {
            "magic": "SVGP",
            "version": VERSION,
            "header_bytes": HEADER.size,
            "attribute_bytes": ATTRIBUTE.size,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export SHIFT.RenderCommand geometry to SHIFT.VulkanGeometryPacket/1")
    parser.add_argument("render_command")
    parser.add_argument("mesh")
    parser.add_argument("output")
    parser.add_argument("--submesh-index", type=int, default=0)
    args = parser.parse_args(argv)
    report = export_vulkan_geometry_packet(
        args.render_command,
        args.mesh,
        args.output,
        submesh_index=args.submesh_index,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
