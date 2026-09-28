"""Assemble one real SHIFT vehicle from its VHF node graph and render it.

This adapter is intentionally geometry-only. It reuses the existing BFF decoder,
VHF scene parser, MEB reader, and desktop reference rasterizer. Material/shader
selection remains a separate evidence gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from meb_format import mesh_summary, read_meb
from reference_renderer import orthographic_mvp, rasterize_mesh
from resource_formats import parse_vhf_scene
from shift_importer import BFF, sha256

FORMAT = "SHIFT.BFFVehicleReferenceRender/1"

_SHARED_KIT00_PREFIXES = (
    "BMW_M3_E36_WHEEL_",
    "BMW_M3_E36_TIRE_",
    "BMW_M3_E36_DISC_",
    "BMW_M3_E36_CALIPER_",
    "BMW_M3_E36_MIRROR_",
    "BMW_M3_E36_LIGHTGLOWS_",
)


def _norm(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def _mat_mul(a: list[float], b: list[float]) -> list[float]:
    return [
        sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4))
        for r in range(4)
        for c in range(4)
    ]


def _vec(value: str, count: int) -> list[float]:
    parts = value.replace(",", " ").split()
    if len(parts) < count:
        raise ValueError(f"expected {count} numeric values, got {value!r}")
    return [float(x) for x in parts[:count]]


def _quat_matrix(q: list[float]) -> list[float]:
    x, y, z, w = q
    return [
        1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0.0,
        2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0.0,
        2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _matrix_from_vhf(record: dict[str, Any]) -> list[float]:
    matrix = _quat_matrix(_vec(record.get("orientation", "0 0 0 1"), 4))
    position = _vec(record.get("offset", "0 0 0"), 3)
    matrix[3], matrix[7], matrix[11] = position
    return matrix


def _resolve_matrix(
    matrices: dict[str, dict[str, Any]],
    matrix_id: str | None,
    cache: dict[str, list[float]],
) -> list[float]:
    key = str(matrix_id if matrix_id is not None else "0")
    if key in cache:
        return cache[key]
    record = matrices.get(key)
    if record is None:
        raise KeyError(f"VHF matrix {key!r} is missing")
    local = _matrix_from_vhf(record)
    parent = record.get("parent")
    world = (
        _mat_mul(_resolve_matrix(matrices, str(parent), cache), local)
        if parent is not None
        else local
    )
    cache[key] = world
    return world


def _transform_position(vertex: tuple[float, float, float], matrix: list[float]) -> tuple[float, float, float]:
    return tuple(
        sum(matrix[row * 4 + col] * vertex[col] for col in range(3)) + matrix[row * 4 + 3]
        for row in range(3)
    )


def _camera_transform(vertex: tuple[float, float, float], yaw_deg: float, pitch_deg: float) -> tuple[float, float, float]:
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x, y, z = vertex
    x1 = cy * x + sy * z
    z1 = -sy * x + cy * z
    y1 = cp * y - sp * z1
    z2 = sp * y + cp * z1
    return x1, y1, z2


def _iter_nodes(nodes: list[dict[str, Any]]):
    for node in nodes:
        yield node
        yield from _iter_nodes(node.get("children") or [])


def _select_node(node: dict[str, Any], profile: str) -> bool:
    name = str(node.get("name") or "")
    upper = name.upper()
    if str(node.get("type") or "").upper() != "OBJECT":
        return False
    if not upper.endswith("_LODA"):
        return False
    if upper.endswith("_LODA_DAMAGE") or upper.endswith("_DAMAGE"):
        return False
    if profile == "all":
        return True
    if profile == "kit00":
        return "KIT00" in upper or upper.startswith(_SHARED_KIT00_PREFIXES)
    raise ValueError(f"unknown vehicle profile {profile!r}")


def assemble_vehicle(
    archive: str | Path,
    vhf_resource: str,
    *,
    profile: str = "kit00",
) -> dict[str, Any]:
    archive_path = Path(archive)
    with BFF(archive_path) as bff:
        target = _norm(vhf_resource)
        matches = [e for e in bff.entries if _norm(e.path) == target]
        if len(matches) != 1:
            raise ValueError(
                f"VHF resource must resolve exactly once: {vhf_resource!r}, found {len(matches)}"
            )
        vhf_entry = matches[0]
        vhf_bytes = bff.extract_entry(vhf_entry, type2="lzx")
        scene = parse_vhf_scene(vhf_bytes)

        entries_by_path = {
            _norm(e.path): e
            for e in bff.entries
            if e.path.lower().endswith(".meb")
        }
        matrix_cache: dict[str, list[float]] = {}
        vertices: list[tuple[float, float, float]] = []
        indices: list[int] = []
        parts: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []

        for node in _iter_nodes(scene.get("nodes") or []):
            if not _select_node(node, profile):
                continue
            node_resources = node.get("resources") or []
            if not node_resources:
                unresolved.append({
                    "node": node.get("name"),
                    "reason": "node:resource-missing",
                })
                continue

            try:
                world = _resolve_matrix(
                    scene.get("matrices") or {},
                    node.get("matrix"),
                    matrix_cache,
                )
            except Exception as exc:
                unresolved.append({
                    "node": node.get("name"),
                    "reason": f"matrix:{type(exc).__name__}:{exc}",
                })
                continue

            for resource in node_resources:
                entry = entries_by_path.get(_norm(resource))
                if entry is None:
                    unresolved.append({
                        "node": node.get("name"),
                        "resource": resource,
                        "reason": "meb:resource-not-found",
                    })
                    continue
                decoded = bff.extract_entry(entry, type2="lzx")
                mesh = read_meb(decoded)
                if not mesh.vertices or not mesh.indices:
                    unresolved.append({
                        "node": node.get("name"),
                        "resource": entry.path,
                        "reason": "meb:empty-geometry",
                    })
                    continue

                base = len(vertices)
                vertices.extend(_transform_position(v, world) for v in mesh.vertices)
                indices.extend(base + int(i) for i in mesh.indices)
                parts.append({
                    "node": node.get("name"),
                    "matrix": node.get("matrix"),
                    "resource": entry.path,
                    "entry_index": entry.index,
                    "resource_sha256": sha256(decoded),
                    "vertex_count": mesh.vertex_count,
                    "triangle_count": mesh.triangle_count,
                    "primitive_count": len(mesh.primitives),
                    "materials": [p.material.replace("\\", "/") for p in mesh.primitives],
                    "world_matrix": world,
                })

    if not vertices or not indices:
        raise ValueError(
            "vehicle profile produced no renderable geometry; "
            + ", ".join(x.get("reason", "unknown") for x in unresolved)
        )

    return {
        "format": "SHIFT.BFFVehicleMesh/1",
        "profile": profile,
        "archive": archive_path.name,
        "vhf_resource": vhf_entry.path,
        "vhf_entry_index": vhf_entry.index,
        "vhf_resource_sha256": sha256(vhf_bytes),
        "scene": scene,
        "vertices": vertices,
        "indices": indices,
        "parts": parts,
        "unresolved": unresolved,
        "vertex_count": len(vertices),
        "triangle_count": len(indices) // 3,
    }


def render_vehicle(
    archive: str | Path,
    vhf_resource: str,
    output: str | Path,
    *,
    profile: str = "kit00",
    width: int = 1200,
    height: int = 800,
    yaw_deg: float = -28.0,
    pitch_deg: float = -15.0,
    mesh_json: str | Path | None = None,
) -> dict[str, Any]:
    vehicle = assemble_vehicle(archive, vhf_resource, profile=profile)
    view_vertices = [
        _camera_transform(tuple(v), yaw_deg, pitch_deg)
        for v in vehicle["vertices"]
    ]
    mvp = orthographic_mvp(view_vertices, padding=0.12)
    image = rasterize_mesh(
        view_vertices,
        vehicle["indices"],
        width=width,
        height=height,
        mvp=mvp,
    )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image)

    if mesh_json is not None:
        mesh_path = Path(mesh_json)
        mesh_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = dict(vehicle)
        serializable["vertices"] = [list(v) for v in vehicle["vertices"]]
        mesh_path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    report = {
        "format": FORMAT,
        "status": "rendered",
        "archive": vehicle["archive"],
        "vhf_resource": vehicle["vhf_resource"],
        "vhf_resource_sha256": vehicle["vhf_resource_sha256"],
        "profile": profile,
        "parts_count": len(vehicle["parts"]),
        "unresolved_count": len(vehicle["unresolved"]),
        "vertex_count": vehicle["vertex_count"],
        "triangle_count": vehicle["triangle_count"],
        "render": {
            "width": width,
            "height": height,
            "yaw_deg": yaw_deg,
            "pitch_deg": pitch_deg,
            "output": str(output_path),
            "sha256": hashlib.sha256(image).hexdigest(),
            "color_mode": "flat-gray-geometry",
            "reference_renderer": "SHIFT.ReferenceRender/1",
        },
    }
    if mesh_json is not None:
        report["mesh_json"] = str(mesh_json)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Assemble and render a real SHIFT VHF vehicle geometry")
    ap.add_argument("archive", type=Path)
    ap.add_argument("vhf_resource")
    ap.add_argument("output", type=Path)
    ap.add_argument("--profile", choices=("kit00", "all"), default="kit00")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--yaw", type=float, default=-28.0)
    ap.add_argument("--pitch", type=float, default=-15.0)
    ap.add_argument("--mesh-json", type=Path)
    args = ap.parse_args(argv)
    result = render_vehicle(
        args.archive,
        args.vhf_resource,
        args.output,
        profile=args.profile,
        width=args.width,
        height=args.height,
        yaw_deg=args.yaw,
        pitch_deg=args.pitch,
        mesh_json=args.mesh_json,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
