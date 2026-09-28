"""Render a real BMW M3 MEB with a real DDS texture, without executing the paint shader.

This is a deliberately limited visual oracle:
BFF -> MEB + DDS -> UV0 sampling -> desktop reference rasterizer.
It proves the real texture/UV path while keeping BMT/FX/FXO material execution separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from meb_format import mesh_summary, mesh_to_jsonable, read_meb
from reference_renderer import orthographic_mvp, render_textured_static_draw
from texture_reference import decode_dds
from shift_importer import BFF, sha256

FORMAT = "SHIFT.BFFMEBTextureReferenceRender/1"
DEFAULT_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
DEFAULT_TEXTURE = "vehicles/textures/common_paint.dds"


def _norm(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def _find_exact(bff: BFF, path: str):
    target = _norm(path)
    matches = [e for e in bff.entries if _norm(e.path) == target]
    if len(matches) != 1:
        raise ValueError(
            f"resource must resolve exactly once: {path!r}; found {len(matches)}"
        )
    return matches[0]


def _draw_indices(mesh, primitive_index: int | None) -> list[int]:
    if primitive_index is None:
        return [int(i) for i in mesh.indices]
    if primitive_index < 0 or primitive_index >= len(mesh.primitives):
        raise IndexError(
            f"primitive index out of range: 0..{len(mesh.primitives) - 1}"
        )
    primitive = mesh.primitives[primitive_index]
    first = int(primitive.first_index)
    count = int(primitive.index_count)
    if count % 3:
        raise ValueError("primitive index_count must be divisible by three")
    return [int(i) for i in mesh.indices[first:first + count]]


def render_bff_textured(
    archive: str | Path,
    *,
    meb_resource: str = DEFAULT_MEB,
    texture_resource: str = DEFAULT_TEXTURE,
    output: str | Path,
    primitive_index: int | None = None,
    width: int = 1200,
    height: int = 800,
) -> dict[str, Any]:
    archive_path = Path(archive)
    output_path = Path(output)

    with BFF(archive_path) as bff:
        meb_entry = _find_exact(bff, meb_resource)
        texture_entry = _find_exact(bff, texture_resource)
        meb_bytes = bff.extract_entry(meb_entry, type2="lzx")
        texture_bytes = bff.extract_entry(texture_entry, type2="lzx")
        mesh = read_meb(meb_bytes)
        image = decode_dds(texture_bytes)

    if "130" not in mesh.uv_layers and "230" not in mesh.uv_layers:
        raise ValueError("real MEB has no evidence-backed UV0 property 130/230")

    draw_indices = _draw_indices(mesh, primitive_index)
    uv_layers = {str(k): v for k, v in mesh.uv_layers.items()}
    neutral_mesh = {
        "format": "SHIFT.MEB",
        "vertices": mesh.vertices,
        "indices": draw_indices,
        "uv_layers": uv_layers,
    }
    primitive = (
        None
        if primitive_index is None
        else {
            "index": primitive_index,
            "material": mesh.primitives[primitive_index].material,
            "first_index": mesh.primitives[primitive_index].first_index,
            "index_count": mesh.primitives[primitive_index].index_count,
        }
    )
    draw = {
        "format": "SHIFT.StaticDraw/1",
        "ready": True,
        "blocking_reasons": [],
        "world_matrix": None,
        "submeshes": [
            {
                "first_index": 0,
                "index_count": len(draw_indices),
                "material": {
                    "name": "BMW_M3_E36_TEXTURE_PREVIEW",
                    "status": "debug-texture-only",
                },
            }
        ],
    }
    sampler = {
        "min_filter": "LINEAR",
        "mag_filter": "LINEAR",
        "address_u": "WRAP",
        "address_v": "WRAP",
    }
    mvp = orthographic_mvp(mesh.vertices, padding=0.12)
    render_textured_static_draw(
        draw,
        neutral_mesh,
        image,
        output_path,
        sampler=sampler,
        width=width,
        height=height,
        mvp=mvp,
    )

    return {
        "format": FORMAT,
        "status": "rendered",
        "archive": archive_path.name,
        "meb": {
            "resource": meb_entry.path,
            "entry_index": meb_entry.index,
            "decoded_sha256": sha256(meb_bytes),
            "summary": mesh_summary(mesh),
        },
        "texture": {
            "resource": texture_entry.path,
            "entry_index": texture_entry.index,
            "decoded_sha256": sha256(texture_bytes),
            "source_format": image.get("source_format"),
            "width": image.get("width"),
            "height": image.get("height"),
            "mipmaps": image.get("mipmaps"),
        },
        "primitive": primitive,
        "render": {
            "width": width,
            "height": height,
            "output": str(output_path),
            "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
            "mode": "UV0-texture-only",
            "shader_execution": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Render a real SHIFT MEB with a real DDS texture, without executing the material shader"
    )
    ap.add_argument("archive", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--meb-resource", default=DEFAULT_MEB)
    ap.add_argument("--texture-resource", default=DEFAULT_TEXTURE)
    ap.add_argument("--primitive-index", type=int, default=None)
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=800)
    args = ap.parse_args(argv)
    result = render_bff_textured(
        args.archive,
        meb_resource=args.meb_resource,
        texture_resource=args.texture_resource,
        output=args.output,
        primitive_index=args.primitive_index,
        width=args.width,
        height=args.height,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
