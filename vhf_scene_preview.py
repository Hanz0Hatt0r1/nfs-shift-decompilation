"""Assemble and preview a real VHF vehicle scene from a SHIFT BFF.

This adapter is intentionally a geometry preview, not the material renderer.
It consumes the real VHF node/matrix hierarchy and exact MEB resources, then
rasterizes the selected static LOD parts into one deterministic PPM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from meb_format import mesh_summary, read_meb
from shift_importer import BFF, sha256

FORMAT = "SHIFT.VHFSceneReferenceRender/1"
_GENERIC_PREFIXES = (
    "BMW_M3_E36_WHEEL_",
    "BMW_M3_E36_TIRE_",
    "BMW_M3_E36_CALIPER_",
    "BMW_M3_E36_DISC_",
    "BMW_M3_E36_MIRROR_",
)


def _norm(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def _find_entry(bff: BFF, resource: str):
    target = _norm(resource)
    hits = [entry for entry in bff.entries if _norm(entry.path) == target]
    if len(hits) != 1:
        raise ValueError(
            f"expected exactly one VHF/resource entry {resource!r}, found {len(hits)}"
        )
    return hits[0]


def _mat_mul(a: list[float], b: list[float]) -> list[float]:
    return [
        sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4))
        for r in range(4)
        for c in range(4)
    ]


def _quat_matrix(q: list[float]) -> list[float]:
    x, y, z, w = q
    return [
        1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0,
        2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0,
        2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0,
        0, 0, 0, 1,
    ]


def _matrix_from_vhf(attrs: dict[str, str]) -> list[float]:
    offset = [float(x) for x in attrs.get("Offset", "0 0 0").split()[:3]]
    orientation = [float(x) for x in attrs.get("Orientation", "0 0 0 1").split()[:4]]
    if len(orientation) != 4:
        orientation = [0.0, 0.0, 0.0, 1.0]
    matrix = _quat_matrix(orientation)
    matrix[3], matrix[7], matrix[11] = offset
    return matrix


def _transform_point(matrix: list[float], point: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3],
        matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7],
        matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11],
    )


def _transform_direction(matrix: list[float], normal: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = normal
    out = (
        matrix[0] * x + matrix[1] * y + matrix[2] * z,
        matrix[4] * x + matrix[5] * y + matrix[6] * z,
        matrix[8] * x + matrix[9] * y + matrix[10] * z,
    )
    length = math.sqrt(sum(component * component for component in out))
    if length <= 1.0e-12:
        return (0.0, 1.0, 0.0)
    return tuple(component / length for component in out)


def _camera_point(
    point: tuple[float, float, float],
    *,
    yaw_deg: float,
    pitch_deg: float,
) -> tuple[float, float, float]:
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x, z = point[0] * cy + point[2] * sy, -point[0] * sy + point[2] * cy
    y = point[1]
    return (
        x,
        y * cp - z * sp,
        y * sp + z * cp,
    )


def _selected_node(name: str, *, kit: str, lod: str, include_generic: bool, include_lightglows: bool) -> bool:
    upper = name.upper()
    if "_DAMAGE" in upper:
        return False
    if not upper.endswith(f"LO{lod.upper()}"):
        return False
    if "LIGHTGLOWS" in upper and not include_lightglows:
        return False
    if "_KIT" in upper:
        return f"_KIT{kit}_" in upper
    return include_generic and upper.startswith(_GENERIC_PREFIXES)


def _read_scene_xml(bff: BFF, resource: str) -> tuple[dict[str, dict[str, str]], ET.Element]:
    entry = _find_entry(bff, resource)
    data = bff.extract_entry(entry, type2="lzx")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"VHF XML parse failed for {entry.path}: {exc}") from exc
    matrices = {
        matrix.attrib["id"]: dict(matrix.attrib)
        for matrix in root.iter("MATRIX")
        if matrix.attrib.get("id") is not None
    }
    return matrices, root


def _resolve_matrix(
    matrix_id: str | None,
    matrices: dict[str, dict[str, str]],
    cache: dict[str, list[float]],
    active: set[str],
) -> list[float]:
    key = str(matrix_id if matrix_id is not None else "0")
    if key in cache:
        return cache[key]
    if key in active:
        raise ValueError(f"VHF matrix parent cycle detected at id {key}")
    active.add(key)
    attrs = matrices.get(key, {"Offset": "0 0 0", "Orientation": "0 0 0 1"})
    local = _matrix_from_vhf(attrs)
    parent = attrs.get("parent")
    if parent is None:
        world = local
    else:
        world = _mat_mul(
            _resolve_matrix(parent, matrices, cache, active),
            local,
        )
    active.remove(key)
    cache[key] = world
    return world


def build_vhf_scene(
    archive: str | Path,
    vhf_resource: str,
    *,
    kit: str = "00",
    lod: str = "A",
    include_generic: bool = True,
    include_lightglows: bool = False,
) -> dict[str, Any]:
    archive_path = Path(archive)
    with BFF(archive_path) as bff:
        matrices, root = _read_scene_xml(bff, vhf_resource)
        entry_map = {_norm(entry.path): entry for entry in bff.entries}
        matrix_cache: dict[str, list[float]] = {}
        parts: list[dict[str, Any]] = []

        for node in root.iter("NODE"):
            if node.attrib.get("type", "").upper() != "OBJECT":
                continue
            name = str(node.attrib.get("Name") or "")
            if not _selected_node(
                name,
                kit=kit,
                lod=lod,
                include_generic=include_generic,
                include_lightglows=include_lightglows,
            ):
                continue
            resource_node = node.find("RESOURCE")
            if resource_node is None:
                continue
            resource = str(resource_node.attrib.get("Filename") or "")
            entry = entry_map.get(_norm(resource))
            if entry is None:
                raise FileNotFoundError(f"VHF resource is absent from BFF: {resource}")
            data = bff.extract_entry(entry, type2="lzx")
            mesh = read_meb(data)
            world = _resolve_matrix(
                node.attrib.get("MatrixNumber"),
                matrices,
                matrix_cache,
                set(),
            )
            parts.append({
                "name": name,
                "resource": entry.path,
                "matrix_number": node.attrib.get("MatrixNumber"),
                "resource_sha256": sha256(data),
                "world_matrix": world,
                "mesh": mesh,
            })

    if not parts:
        raise ValueError(
            f"VHF selection produced no renderable OBJECT nodes (kit={kit}, lod={lod})"
        )
    return {
        "format": "SHIFT.VHFScene/1",
        "archive": archive_path.name,
        "vhf_resource": vhf_resource,
        "selection": {
            "kit": kit,
            "lod": lod,
            "include_generic": include_generic,
            "include_lightglows": include_lightglows,
        },
        "parts": parts,
    }


def _render_scene_ppm(
    scene: dict[str, Any],
    *,
    width: int,
    height: int,
    yaw_deg: float,
    pitch_deg: float,
) -> bytes:
    if width <= 0 or height <= 0:
        raise ValueError("render target dimensions must be positive")

    prepared: list[dict[str, Any]] = []
    all_camera_vertices: list[tuple[float, float, float]] = []
    for part in scene["parts"]:
        mesh = part["mesh"]
        world = part["world_matrix"]
        vertices = [_camera_point(_transform_point(world, v), yaw_deg=yaw_deg, pitch_deg=pitch_deg) for v in mesh.vertices]
        normals = [_camera_point(_transform_direction(world, n), yaw_deg=yaw_deg, pitch_deg=pitch_deg) for n in mesh.normals]
        if not mesh.normals:
            normals = [(0.0, 1.0, 0.0)] * len(vertices)
        prepared.append({"part": part, "vertices": vertices, "normals": normals, "indices": list(mesh.indices)})
        all_camera_vertices.extend(vertices)

    min_x = min(v[0] for v in all_camera_vertices)
    max_x = max(v[0] for v in all_camera_vertices)
    min_y = min(v[1] for v in all_camera_vertices)
    max_y = max(v[1] for v in all_camera_vertices)
    center_x = (min_x + max_x) * 0.5
    center_y = (min_y + max_y) * 0.5
    span = max(max_x - min_x, max_y - min_y, 1.0e-6) * 1.08

    clear_rgb = (12, 12, 12)
    pixels = bytearray(clear_rgb * (width * height))
    depth = [float("inf")] * (width * height)
    light = (0.35, 0.72, 0.61)
    light_len = math.sqrt(sum(component * component for component in light))
    light = tuple(component / light_len for component in light)

    def screen(point: tuple[float, float, float]) -> tuple[float, float]:
        return (
            (point[0] - center_x) / span * (width - 1) + (width - 1) * 0.5,
            (height - 1) * 0.5 - (point[1] - center_y) / span * (height - 1),
        )

    for prepared_part in prepared:
        vertices = prepared_part["vertices"]
        normals = prepared_part["normals"]
        indices = prepared_part["indices"]
        for base in range(0, len(indices), 3):
            ia, ib, ic = indices[base:base + 3]
            a, b, c = vertices[ia], vertices[ib], vertices[ic]
            p0, p1, p2 = screen(a), screen(b), screen(c)
            area = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
            if abs(area) <= 1.0e-10:
                continue
            min_xi = max(0, int(math.floor(min(p0[0], p1[0], p2[0]))))
            max_xi = min(width - 1, int(math.ceil(max(p0[0], p1[0], p2[0]))))
            min_yi = max(0, int(math.floor(min(p0[1], p1[1], p2[1]))))
            max_yi = min(height - 1, int(math.ceil(max(p0[1], p1[1], p2[1]))))
            inverse_area = 1.0 / area
            for y in range(min_yi, max_yi + 1):
                py = y + 0.5
                for x in range(min_xi, max_xi + 1):
                    px = x + 0.5
                    w0 = ((p1[0] - px) * (p2[1] - py) - (p1[1] - py) * (p2[0] - px)) * inverse_area
                    w1 = ((p2[0] - px) * (p0[1] - py) - (p2[1] - py) * (p0[0] - px)) * inverse_area
                    w2 = ((p0[0] - px) * (p1[1] - py) - (p0[1] - py) * (p1[0] - px)) * inverse_area
                    if w0 < -1.0e-7 or w1 < -1.0e-7 or w2 < -1.0e-7:
                        continue
                    z = w0 * a[2] + w1 * b[2] + w2 * c[2]
                    offset = y * width + x
                    if z >= depth[offset]:
                        continue
                    depth[offset] = z
                    normal = tuple(
                        w0 * normals[ia][component]
                        + w1 * normals[ib][component]
                        + w2 * normals[ic][component]
                        for component in range(3)
                    )
                    normal_len = math.sqrt(sum(component * component for component in normal)) or 1.0
                    dot = max(0.0, sum((normal[component] / normal_len) * light[component] for component in range(3)))
                    value = max(0.15, min(1.0, 0.20 + 0.80 * dot))
                    gray = int(round(208 * value))
                    pixels[offset * 3:offset * 3 + 3] = bytes((gray, gray, gray))

    return b"P6\n%d %d\n255\n" % (width, height) + bytes(pixels)


def render_vhf_scene(
    archive: str | Path,
    vhf_resource: str,
    output: str | Path,
    *,
    kit: str = "00",
    lod: str = "A",
    width: int = 1200,
    height: int = 800,
    yaw_deg: float = -28.0,
    pitch_deg: float = -15.0,
    include_generic: bool = True,
    include_lightglows: bool = False,
    scene_json: str | Path | None = None,
) -> dict[str, Any]:
    scene = build_vhf_scene(
        archive,
        vhf_resource,
        kit=kit,
        lod=lod,
        include_generic=include_generic,
        include_lightglows=include_lightglows,
    )
    image = _render_scene_ppm(
        scene,
        width=width,
        height=height,
        yaw_deg=yaw_deg,
        pitch_deg=pitch_deg,
    )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image)

    if scene_json is not None:
        scene_json_path = Path(scene_json)
        scene_json_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            "format": scene["format"],
            "archive": scene["archive"],
            "vhf_resource": scene["vhf_resource"],
            "selection": scene["selection"],
            "parts": [
                {
                    "name": part["name"],
                    "resource": part["resource"],
                    "matrix_number": part["matrix_number"],
                    "resource_sha256": part["resource_sha256"],
                    "world_matrix": part["world_matrix"],
                    "mesh": mesh_summary(part["mesh"]),
                }
                for part in scene["parts"]
            ],
        }
        scene_json_path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    vertex_count = sum(part["mesh"].vertex_count for part in scene["parts"])
    triangle_count = sum(part["mesh"].triangle_count for part in scene["parts"])
    return {
        "format": FORMAT,
        "status": "rendered",
        "archive": scene["archive"],
        "vhf_resource": scene["vhf_resource"],
        "selection": scene["selection"],
        "parts": [
            {
                "name": part["name"],
                "resource": part["resource"],
                "matrix_number": part["matrix_number"],
                "resource_sha256": part["resource_sha256"],
                "vertex_count": part["mesh"].vertex_count,
                "triangle_count": part["mesh"].triangle_count,
                "primitives": len(part["mesh"].primitives),
            }
            for part in scene["parts"]
        ],
        "vertex_count": vertex_count,
        "triangle_count": triangle_count,
        "render": {
            "width": width,
            "height": height,
            "yaw_deg": yaw_deg,
            "pitch_deg": pitch_deg,
            "output": str(output_path),
            "sha256": hashlib.sha256(image).hexdigest(),
            "mode": "geometry-preview",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Preview a real SHIFT VHF vehicle scene from BFF")
    ap.add_argument("archive", type=Path)
    ap.add_argument("vhf_resource")
    ap.add_argument("output", type=Path)
    ap.add_argument("--kit", default="00")
    ap.add_argument("--lod", default="A")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--yaw", type=float, default=-28.0)
    ap.add_argument("--pitch", type=float, default=-15.0)
    ap.add_argument("--no-generic", action="store_true")
    ap.add_argument("--include-lightglows", action="store_true")
    ap.add_argument("--scene-json", type=Path)
    args = ap.parse_args(argv)
    result = render_vhf_scene(
        args.archive,
        args.vhf_resource,
        args.output,
        kit=args.kit,
        lod=args.lod,
        width=args.width,
        height=args.height,
        yaw_deg=args.yaw,
        pitch_deg=args.pitch,
        include_generic=not args.no_generic,
        include_lightglows=args.include_lightglows,
        scene_json=args.scene_json,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
