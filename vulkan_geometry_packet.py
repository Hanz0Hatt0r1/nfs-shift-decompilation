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
VERSION = 1
HEADER = struct.Struct("<4sIIIIII4f")
ATTRIBUTE = struct.Struct("<IIII")
FORMAT_FLOAT3 = 1


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

    vertex_attribute = _position_attribute(command)
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

    center, scale = _bounds(vertices)

    stride = 12
    vertex_blob = bytearray(len(vertices) * stride)
    for index, position in enumerate(vertices):
        struct.pack_into("<3f", vertex_blob, index * stride, *position)

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
        1,
        0,
        float(center[0]),
        float(center[1]),
        float(center[2]),
        float(scale),
    )
    attribute = ATTRIBUTE.pack(
        int(vertex_attribute.get("location", 0)),
        FORMAT_FLOAT3,
        0,
        stride,
    )
    index_blob = struct.pack(f"<{len(selected_indices)}I", *selected_indices)
    output_path.write_bytes(header + attribute + vertex_blob + index_blob)

    return {
        "format": FORMAT,
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
        "attributes": [
            {
                "location": int(vertex_attribute.get("location", 0)),
                "property_id": "200",
                "format": "FLOAT3",
                "offset": 0,
                "stride": stride,
            }
        ],
        "deferred_properties": [
            str(row.get("property_id"))
            for row in ((command.get("mesh") or {}).get("vertex_layout") or {}).get("attributes") or []
            if str(row.get("property_id")) != "200"
        ],
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
