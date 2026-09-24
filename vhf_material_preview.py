"""Preview a real VHF vehicle with an evidence-backed BMT diffuse texture.

This remains a texture-only oracle. It proves scene assembly plus material
resource resolution without claiming the full bodywork FX/FXO execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from resource_formats import parse_bmt_material
from shift_importer import BFF, sha256
from texture_reference import decode_dds, sample_texture_2d
from vhf_scene_preview import build_vhf_scene

FORMAT = "SHIFT.VHFMaterialReferenceRender/1"
DEFAULT_MATERIAL = "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt"


def _norm(value: str) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _alias(value: str) -> str:
    value = _norm(value)
    if value.endswith(".mtx"):
        return value[:-4] + ".bmt"
    return value


def _find_exact(bff: BFF, path: str):
    target = _norm(path)
    hits = [entry for entry in bff.entries if _norm(entry.path) == target]
    if len(hits) != 1:
        raise ValueError(
            f"resource must resolve exactly once: {path!r}; found {len(hits)}"
        )
    return hits[0]


def _resolve_diffuse_reference(
    bff: BFF,
    material_resource: str,
    texture_override: str | None,
) -> tuple[str, dict[str, Any]]:
    material_entry = _find_exact(bff, material_resource)
    material_bytes = bff.extract_entry(material_entry, type2="lzx")
    parsed = parse_bmt_material(material_bytes)
    material = parsed.get("material") or {}
    diffuse_ref = texture_override
    if diffuse_ref is None:
        for row in material.get("shaderparams", []) or []:
            if str(row.get("name") or "") == "diffuseTexture":
                value = row.get("value")
                if isinstance(value, str):
                    diffuse_ref = value
                    break
    if not diffuse_ref:
        raise ValueError("material has no evidence-backed diffuseTexture reference")
    texture_entry = _find_exact(bff, diffuse_ref)
    texture_bytes = bff.extract_entry(texture_entry, type2="lzx")
    image = decode_dds(texture_bytes)
    return texture_entry.path, {
        "material": material,
        "material_entry": {
            "path": material_entry.path,
            "index": material_entry.index,
            "sha256": sha256(material_bytes),
        },
        "texture_entry": {
            "path": texture_entry.path,
            "index": texture_entry.index,
            "sha256": sha256(texture_bytes),
        },
        "texture_image": image,
    }


def _mat_point(matrix: list[float], vertex: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vertex
    return (
        matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3],
        matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7],
        matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11],
    )


def _mat_dir(matrix: list[float], normal: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = normal
    value = (
        matrix[0] * x + matrix[1] * y + matrix[2] * z,
        matrix[4] * x + matrix[5] * y + matrix[6] * z,
        matrix[8] * x + matrix[9] * y + matrix[10] * z,
    )
    length = math.sqrt(sum(item * item for item in value))
    if length <= 1.0e-12:
        return (0.0, 1.0, 0.0)
    return tuple(item / length for item in value)


def _camera(
    vertex: tuple[float, float, float],
    *,
    yaw_deg: float,
    pitch_deg: float,
) -> tuple[float, float, float]:
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x, z = vertex[0] * cy + vertex[2] * sy, -vertex[0] * sy + vertex[2] * cy
    y = vertex[1]
    return x, y * cp - z * sp, y * sp + z * cp


def _screen(
    point: tuple[float, float, float],
    *,
    center_x: float,
    center_y: float,
    scale: float,
    width: int,
    height: int,
) -> tuple[float, float]:
    return (
        (point[0] - center_x) / scale * (width - 1) + (width - 1) * 0.5,
        (height - 1) * 0.5 - (point[1] - center_y) / scale * (height - 1),
    )


def _primitive_for_index(mesh: Any, index_offset: int) -> Any | None:
    for primitive in mesh.primitives:
        first = int(primitive.first_index)
        last = first + int(primitive.index_count)
        if first <= index_offset < last:
            return primitive
    return None


def _render(
    scene: dict[str, Any],
    *,
    paint_material: str,
    texture_image: dict[str, Any],
    width: int,
    height: int,
    yaw_deg: float,
    pitch_deg: float,
) -> tuple[bytes, int]:
    prepared: list[dict[str, Any]] = []
    camera_vertices: list[tuple[float, float, float]] = []

    for part in scene["parts"]:
        mesh = part["mesh"]
        world = part["world_matrix"]
        vertices = [
            _camera(
                _mat_point(world, vertex),
                yaw_deg=yaw_deg,
                pitch_deg=pitch_deg,
            )
            for vertex in mesh.vertices
        ]
        normals = [
            _camera(
                _mat_dir(world, normal),
                yaw_deg=yaw_deg,
                pitch_deg=pitch_deg,
            )
            for normal in mesh.normals
        ] if mesh.normals else [(0.0, 1.0, 0.0)] * len(vertices)
        prepared.append({
            "part": part,
            "vertices": vertices,
            "normals": normals,
            "indices": list(mesh.indices),
        })
        camera_vertices.extend(vertices)

    if not camera_vertices:
        raise ValueError("scene contains no vertices")

    min_x = min(vertex[0] for vertex in camera_vertices)
    max_x = max(vertex[0] for vertex in camera_vertices)
    min_y = min(vertex[1] for vertex in camera_vertices)
    max_y = max(vertex[1] for vertex in camera_vertices)
    center_x = (min_x + max_x) * 0.5
    center_y = (min_y + max_y) * 0.5
    scale = max(max_x - min_x, max_y - min_y, 1.0e-6) * 1.08

    pixels = bytearray(bytes((12, 12, 12)) * (width * height))
    depth = [float("inf")] * (width * height)
    light = (0.35, 0.72, 0.61)
    light_len = math.sqrt(sum(item * item for item in light))
    light = tuple(item / light_len for item in light)

    painted_triangles = 0
    paint_material_norm = _alias(paint_material)

    for item in prepared:
        part = item["part"]
        mesh = part["mesh"]
        vertices = item["vertices"]
        normals = item["normals"]
        indices = item["indices"]
        uv_layers = mesh.uv_layers
        uv0 = uv_layers.get("130") or uv_layers.get("230")
        for base in range(0, len(indices), 3):
            ia, ib, ic = indices[base:base + 3]
            va, vb, vc = vertices[ia], vertices[ib], vertices[ic]
            p0 = _screen(va, center_x=center_x, center_y=center_y, scale=scale, width=width, height=height)
            p1 = _screen(vb, center_x=center_x, center_y=center_y, scale=scale, width=width, height=height)
            p2 = _screen(vc, center_x=center_x, center_y=center_y, scale=scale, width=width, height=height)
            area = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
            if abs(area) <= 1.0e-12:
                continue
            min_xi = max(0, int(math.floor(min(p0[0], p1[0], p2[0]))))
            max_xi = min(width - 1, int(math.ceil(max(p0[0], p1[0], p2[0]))))
            min_yi = max(0, int(math.floor(min(p0[1], p1[1], p2[1]))))
            max_yi = min(height - 1, int(math.ceil(max(p0[1], p1[1], p2[1]))))
            inverse_area = 1.0 / area
            primitive = _primitive_for_index(mesh, base)
            is_paint = bool(
                primitive is not None
                and _alias(primitive.material) == paint_material_norm
            )
            if is_paint and uv0:
                painted_triangles += 1

            for y in range(min_yi, max_yi + 1):
                py = y + 0.5
                for x in range(min_xi, max_xi + 1):
                    px = x + 0.5
                    w0 = ((p1[0] - px) * (p2[1] - py) - (p1[1] - py) * (p2[0] - px)) * inverse_area
                    w1 = ((p2[0] - px) * (p0[1] - py) - (p2[1] - py) * (p0[0] - px)) * inverse_area
                    w2 = ((p0[0] - px) * (p1[1] - py) - (p0[1] - py) * (p1[0] - px)) * inverse_area
                    if w0 < -1.0e-7 or w1 < -1.0e-7 or w2 < -1.0e-7:
                        continue
                    z = w0 * va[2] + w1 * vb[2] + w2 * vc[2]
                    offset = y * width + x
                    if z >= depth[offset]:
                        continue

                    normal = tuple(
                        w0 * normals[ia][component]
                        + w1 * normals[ib][component]
                        + w2 * normals[ic][component]
                        for component in range(3)
                    )
                    normal_len = math.sqrt(sum(item * item for item in normal)) or 1.0
                    lambert = max(
                        0.18,
                        min(
                            1.0,
                            0.20
                            + 0.80
                            * max(
                                0.0,
                                sum(
                                    (normal[component] / normal_len) * light[component]
                                    for component in range(3)
                                ),
                            ),
                        ),
                    )
                    if is_paint and uv0:
                        uv_a, uv_b, uv_c = uv0[ia], uv0[ib], uv0[ic]
                        u = w0 * uv_a[0] + w1 * uv_b[0] + w2 * uv_c[0]
                        v = w0 * uv_a[1] + w1 * uv_b[1] + w2 * uv_c[1]
                        sampled = sample_texture_2d(
                            texture_image,
                            u,
                            v,
                            {
                                "min_filter": "LINEAR",
                                "mag_filter": "LINEAR",
                                "address_u": "REPEAT",
                                "address_v": "REPEAT",
                            },
                        )
                        color = tuple(
                            max(0, min(255, int(round(sampled[channel] * 255.0 * lambert))))
                            for channel in range(3)
                        )
                    else:
                        value = int(round(208 * lambert))
                        color = (value, value, value)
                    depth[offset] = z
                    pixels[offset * 3:offset * 3 + 3] = bytes(color)

    return (
        b"P6\n%d %d\n255\n" % (width, height) + bytes(pixels),
        painted_triangles,
    )


def render_vhf_material(
    archive: str | Path,
    vhf_resource: str,
    output: str | Path,
    *,
    material_resource: str = DEFAULT_MATERIAL,
    texture_override: str | None = None,
    kit: str = "00",
    lod: str = "A",
    width: int = 1200,
    height: int = 800,
    yaw_deg: float = -28.0,
    pitch_deg: float = -15.0,
    scene_json: str | Path | None = None,
) -> dict[str, Any]:
    archive_path = Path(archive)
    scene = build_vhf_scene(
        archive_path,
        vhf_resource,
        kit=kit,
        lod=lod,
        include_generic=True,
        include_lightglows=False,
    )
    with BFF(archive_path) as bff:
        texture_resource, material_info = _resolve_diffuse_reference(
            bff,
            material_resource,
            texture_override,
        )

    image = material_info.pop("texture_image")
    ppm, painted_triangles = _render(
        scene,
        paint_material=material_resource,
        texture_image=image,
        width=width,
        height=height,
        yaw_deg=yaw_deg,
        pitch_deg=pitch_deg,
    )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(ppm)

    serializable_scene = {
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
                "mesh": {
                    "vertex_count": part["mesh"].vertex_count,
                    "triangle_count": part["mesh"].triangle_count,
                    "primitives": len(part["mesh"].primitives),
                },
            }
            for part in scene["parts"]
        ],
    }
    if scene_json is not None:
        scene_path = Path(scene_json)
        scene_path.parent.mkdir(parents=True, exist_ok=True)
        scene_path.write_text(
            json.dumps(
                {
                    "format": FORMAT,
                    "scene": serializable_scene,
                    "material": {
                        **material_info,
                        "texture_resource": texture_resource,
                    },
                    "render": {
                        "mode": "texture-only",
                        "paint_material": material_resource,
                        "painted_triangle_count": painted_triangles,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

    all_vertices = sum(part["mesh"].vertex_count for part in scene["parts"])
    all_triangles = sum(part["mesh"].triangle_count for part in scene["parts"])
    return {
        "format": FORMAT,
        "status": "rendered",
        "archive": archive_path.name,
        "vhf_resource": vhf_resource,
        "material_resource": material_resource,
        "texture_resource": texture_resource,
        "material_sha256": material_info["material_entry"]["sha256"],
        "texture_sha256": material_info["texture_entry"]["sha256"],
        "scene_parts": len(scene["parts"]),
        "vertex_count": all_vertices,
        "triangle_count": all_triangles,
        "painted_triangle_count": painted_triangles,
        "render": {
            "width": width,
            "height": height,
            "yaw_deg": yaw_deg,
            "pitch_deg": pitch_deg,
            "output": str(output_path),
            "sha256": hashlib.sha256(ppm).hexdigest(),
            "mode": "texture-only",
            "shader_execution": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render a real SHIFT VHF scene with a resolved material diffuse texture")
    ap.add_argument("archive", type=Path)
    ap.add_argument("vhf_resource")
    ap.add_argument("output", type=Path)
    ap.add_argument("--material-resource", default=DEFAULT_MATERIAL)
    ap.add_argument("--texture-override")
    ap.add_argument("--kit", default="00")
    ap.add_argument("--lod", default="A")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--yaw", type=float, default=-28.0)
    ap.add_argument("--pitch", type=float, default=-15.0)
    ap.add_argument("--scene-json", type=Path)
    args = ap.parse_args(argv)
    result = render_vhf_material(
        args.archive,
        args.vhf_resource,
        args.output,
        material_resource=args.material_resource,
        texture_override=args.texture_override,
        kit=args.kit,
        lod=args.lod,
        width=args.width,
        height=args.height,
        yaw_deg=args.yaw,
        pitch_deg=args.pitch,
        scene_json=args.scene_json,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
