"""Render one real MEB resource directly from a SHIFT BFF archive.

This is a thin integration adapter: BFF/XMem decoding and MEB parsing remain
owned by the importer stack, while the existing desktop reference renderer
stays the only rasterization oracle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from meb_format import mesh_summary, mesh_to_jsonable, read_meb
from reference_renderer import orthographic_mvp, rasterize_mesh
from shift_importer import BFF, sha256

FORMAT = "SHIFT.BFFMEBReferenceRender/1"


def _normalize_ref(value: str) -> str:
    return value.replace("\\", "/").strip("/").lower()


def find_meb_entry(bff: BFF, resource: str):
    needle = _normalize_ref(resource)
    matches = [entry for entry in bff.entries if _normalize_ref(entry.path) == needle]
    if not matches:
        raise FileNotFoundError(f"MEB resource not found in {bff.path.name}: {resource}")
    if len(matches) > 1:
        raise ValueError(f"MEB resource reference is ambiguous in {bff.path.name}: {resource}")
    if not matches[0].path.lower().endswith(".meb"):
        raise ValueError(f"selected resource is not MEB: {matches[0].path}")
    return matches[0]


def _primitive_indices(indices: list[int], primitive: dict[str, Any]) -> list[int]:
    first = int(primitive.get("first_index", 0))
    count = int(primitive.get("index_count", 0))
    if first < 0 or count < 0 or first + count > len(indices):
        raise ValueError(
            f"primitive index range out of bounds: first={first} count={count} indices={len(indices)}"
        )
    if count % 3:
        raise ValueError("primitive index_count must be divisible by three")
    return [int(value) for value in indices[first:first + count]]


def render_bff_meb(
    archive: str | Path,
    resource: str,
    output: str | Path,
    *,
    width: int = 800,
    height: int = 600,
    primitive_index: int | None = None,
    vertex_colors: bool = False,
    mesh_json: str | Path | None = None,
) -> dict[str, Any]:
    """Decode a real BFF MEB entry and render it through the desktop oracle."""
    archive_path = Path(archive)
    output_path = Path(output)

    with BFF(archive_path) as bff:
        entry = find_meb_entry(bff, resource)
        decoded = bff.extract_entry(entry, type2="lzx")
        mesh = read_meb(decoded)
        mesh_dict = mesh_to_jsonable(mesh)

    if primitive_index is None:
        draw_indices = list(mesh.indices)
        selected_primitive = None
    else:
        if primitive_index < 0 or primitive_index >= len(mesh.primitives):
            raise IndexError(f"primitive index out of range: 0..{len(mesh.primitives) - 1}")
        primitive = mesh.primitives[primitive_index]
        draw_indices = _primitive_indices(
            mesh.indices,
            {"first_index": primitive.first_index, "index_count": primitive.index_count},
        )
        selected_primitive = {
            "index": primitive_index,
            "material": primitive.material.replace("\\", "/"),
            "first_index": primitive.first_index,
            "index_count": primitive.index_count,
        }

    mvp = orthographic_mvp(mesh.vertices)
    # COLOR0/1 is still an evidence-sensitive ABI. Geometry-only is therefore
    # the safe default; --vertex-colors is explicitly a debug visualization.
    image = rasterize_mesh(
        mesh.vertices,
        draw_indices,
        colors=mesh.colors if vertex_colors else (),
        width=width,
        height=height,
        mvp=mvp,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image)

    if mesh_json is not None:
        mesh_path = Path(mesh_json)
        mesh_path.parent.mkdir(parents=True, exist_ok=True)
        mesh_path.write_text(json.dumps(mesh_dict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "format": FORMAT,
        "status": "rendered",
        "archive": archive_path.name,
        "archive_path": str(archive_path),
        "resource": entry.path,
        "entry_index": entry.index,
        "entry_type": entry.type,
        "entry_compressed_size": entry.compressed_size,
        "entry_uncompressed_size": entry.uncompressed_size,
        "resource_sha256": sha256(decoded),
        "mesh": mesh_summary(mesh),
        "selected_primitive": selected_primitive,
        "render": {
            "width": width,
            "height": height,
            "output": str(output_path),
            "sha256": hashlib.sha256(image).hexdigest(),
            "color_mode": "vertex-color-debug" if vertex_colors else "flat-gray",
            "reference_renderer": "SHIFT.ReferenceRender/1",
        },
    }
    if mesh_json is not None:
        result["mesh_json"] = str(mesh_json)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render one real SHIFT MEB resource directly from a BFF")
    ap.add_argument("archive", type=Path, help="SHIFT BFF archive")
    ap.add_argument("resource", help="exact logical .meb path inside the BFF")
    ap.add_argument("output", type=Path, help="deterministic PPM output")
    ap.add_argument("--width", type=int, default=800)
    ap.add_argument("--height", type=int, default=600)
    ap.add_argument("--primitive-index", type=int, default=None)
    ap.add_argument("--vertex-colors", action="store_true")
    ap.add_argument("--mesh-json", type=Path)
    args = ap.parse_args(argv)
    result = render_bff_meb(
        args.archive,
        args.resource,
        args.output,
        width=args.width,
        height=args.height,
        primitive_index=args.primitive_index,
        vertex_colors=args.vertex_colors,
        mesh_json=args.mesh_json,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
