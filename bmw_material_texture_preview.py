"""Preview a real MEB material primitive with its BMT diffuse DDS texture.

This is a material-texture integration step, not the final BMW paint shader.
It proves the concrete resource path:

BFF -> MEB primitive -> BMT diffuseTexture -> DDS -> MEB UV0 -> reference rasterizer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from bmw_m3_paint_contract import PAINT_CONTRACT
from meb_format import mesh_summary, read_meb
from reference_renderer import orthographic_mvp, rasterize_textured_mesh
from resource_formats import parse_bmt_material
from shift_importer import BFF, sha256


FORMAT = "SHIFT.BMWMaterialTextureReference/1"


def _norm(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def _alias_material(value: str) -> str:
    normalized = _norm(value)
    return normalized[:-4] + ".bmt" if normalized.endswith(".mtx") else normalized


def _find_exact(bff: BFF, resource: str):
    target = _norm(resource)
    aliases = {target, _alias_material(target)}
    hits = [entry for entry in bff.entries if _norm(entry.path) in aliases]
    if len(hits) != 1:
        raise ValueError(
            f"expected exactly one resource {resource!r} (or .bmt alias), found {len(hits)}"
        )
    return hits[0]


def _find_texture(bff: BFF, resource: str):
    target = _norm(resource)
    exact = [entry for entry in bff.entries if _norm(entry.path) == target]
    if len(exact) == 1:
        return exact[0]
    basename = target.rsplit("/", 1)[-1]
    matches = [entry for entry in bff.entries if _norm(entry.path).rsplit("/", 1)[-1] == basename]
    if len(matches) != 1:
        raise ValueError(
            f"texture reference is not unique {resource!r}: found {len(matches)}"
        )
    return matches[0]


def _diffuse_reference(material: dict[str, Any]) -> str:
    for row in material.get("shaderparams", []) or []:
        if str(row.get("name") or "") == "diffuseTexture":
            value = row.get("value")
            if isinstance(value, str) and value:
                return value
    raise ValueError("BMT does not contain a string diffuseTexture shader parameter")


def _material_indices(mesh, material_ref: str) -> tuple[list[int], list[int]]:
    selected: list[int] = []
    primitive_indices: list[int] = []
    target = _alias_material(material_ref)
    for index, primitive in enumerate(mesh.primitives):
        if _alias_material(primitive.material) != target:
            continue
        first = int(primitive.first_index)
        count = int(primitive.index_count)
        if first < 0 or count < 0 or first + count > len(mesh.indices):
            raise ValueError(
                f"primitive {index} index range is invalid: first={first} count={count}"
            )
        if count % 3:
            raise ValueError(f"primitive {index} index_count is not divisible by three")
        selected.extend(mesh.indices[first:first + count])
        primitive_indices.append(index)
    if not selected:
        raise ValueError(f"MEB contains no primitive using material {material_ref!r}")
    return [int(value) for value in selected], primitive_indices


def render_bmw_material_texture(
    archive: str | Path,
    meb_resource: str,
    output: str | Path,
    *,
    material_ref: str = PAINT_CONTRACT["material_path"],
    width: int = 1200,
    height: int = 800,
    scene_name: str | None = None,
) -> dict[str, Any]:
    archive_path = Path(archive)
    output_path = Path(output)

    with BFF(archive_path) as bff:
        meb_entry = _find_exact(bff, meb_resource)
        meb_data = bff.extract_entry(meb_entry, type2="lzx")
        mesh = read_meb(meb_data)

        bmt_entry = _find_exact(bff, material_ref)
        bmt_data = bff.extract_entry(bmt_entry, type2="lzx")
        parsed = parse_bmt_material(bmt_data)
        material = parsed.get("material") or {}
        diffuse_ref = _diffuse_reference(material)

        texture_entry = _find_texture(bff, diffuse_ref)
        texture_data = bff.extract_entry(texture_entry, type2="lzx")

    indices, primitive_indices = _material_indices(mesh, material_ref)
    uv = mesh.uv_layers.get("130")
    if not uv:
        raise ValueError("MEB material texture preview requires TEXCOORD0 property 130")

    from texture_reference import decode_dds

    image = decode_dds(texture_data)
    sampler = {
        "min_filter": "Linear",
        "mag_filter": "Linear",
        "mip_filter": "Linear",
        "address_u": "Wrap",
        "address_v": "Wrap",
    }

    pixels = rasterize_textured_mesh(
        mesh.vertices,
        indices,
        uv,
        image,
        width=width,
        height=height,
        mvp=orthographic_mvp(mesh.vertices),
        sampler=sampler,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pixels)

    return {
        "format": FORMAT,
        "status": "rendered",
        "scene_name": scene_name or mesh.name,
        "archive": archive_path.name,
        "meb": {
            "path": meb_entry.path,
            "index": meb_entry.index,
            "sha256": sha256(meb_data),
            "summary": mesh_summary(mesh),
        },
        "material": {
            "path": bmt_entry.path,
            "index": bmt_entry.index,
            "sha256": sha256(bmt_data),
            "diffuse_parameter": "diffuseTexture",
            "diffuse_ref": diffuse_ref,
            "material_ref": material_ref,
            "primitive_indices": primitive_indices,
        },
        "texture": {
            "path": texture_entry.path,
            "index": texture_entry.index,
            "sha256": sha256(texture_data),
            "format": image.get("source_format"),
            "width": image.get("width"),
            "height": image.get("height"),
            "mipmaps": image.get("mipmaps"),
        },
        "render": {
            "width": width,
            "height": height,
            "output": str(output_path),
            "sha256": hashlib.sha256(pixels).hexdigest(),
            "mode": "material-diffuse-texture",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Render one real BMW M3 MEB material primitive with its BMT diffuse DDS"
    )
    ap.add_argument("archive", type=Path)
    ap.add_argument("meb_resource")
    ap.add_argument("output", type=Path)
    ap.add_argument("--material", default=PAINT_CONTRACT["material_path"])
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=800)
    args = ap.parse_args(argv)

    result = render_bmw_material_texture(
        args.archive,
        args.meb_resource,
        args.output,
        material_ref=args.material,
        width=args.width,
        height=args.height,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
