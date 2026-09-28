"""Convert runtime-captured PPM texture surfaces into reference-texture JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ppm_svg_snapshot import read_ppm
from texture_reference import CUBE_FACES, CUBE_FORMAT, FORMAT


def ppm_to_reference_texture(path: str | Path) -> dict[str, Any]:
    width, height, rgb = read_ppm(path)
    rgba = bytearray(width * height * 4)
    for index in range(width * height):
        src = index * 3
        dst = index * 4
        rgba[dst:dst + 4] = bytes((
            rgb[src],
            rgb[src + 1],
            rgb[src + 2],
            255,
        ))
    return {
        "format": FORMAT,
        "source_format": "D3D9_CAPTURE_PPM",
        "width": width,
        "height": height,
        "mipmaps": 1,
        "base_level_only": True,
        "storage": "uncompressed",
        "pixel_format": "RGBA8",
        "pixels": list(rgba),
        "byte_size": len(rgba),
        "source_path": str(path),
    }


def ppms_to_reference_cube(face_paths: dict[str, str | Path]) -> dict[str, Any]:
    missing = [face for face in CUBE_FACES if face not in face_paths]
    if missing:
        raise ValueError("cube faces missing: " + ", ".join(missing))

    faces = {
        face: ppm_to_reference_texture(face_paths[face])
        for face in CUBE_FACES
    }
    dimensions = {(int(image["width"]), int(image["height"])) for image in faces.values()}
    if len(dimensions) != 1:
        raise ValueError("cube face dimensions do not match")
    width, height = next(iter(dimensions))
    return {
        "format": CUBE_FORMAT,
        "source_format": "D3D9_CAPTURE_PPM_CUBE",
        "width": width,
        "height": height,
        "mipmaps": 1,
        "base_level_only": True,
        "storage": "uncompressed",
        "pixel_format": "RGBA8",
        "faces": faces,
        "byte_size": sum(int(image["byte_size"]) for image in faces.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a D3D9-captured PPM texture or cubemap to reference JSON"
    )
    parser.add_argument("output")
    parser.add_argument("--texture")
    for face in CUBE_FACES:
        parser.add_argument(f"--{face}")
    args = parser.parse_args(argv)

    if args.texture:
        result = ppm_to_reference_texture(args.texture)
    else:
        paths = {face: getattr(args, face) for face in CUBE_FACES}
        if any(not paths[face] for face in CUBE_FACES):
            parser.error("either --texture or all six cube-face options are required")
        result = ppms_to_reference_cube(paths)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "width": result["width"],
        "height": result["height"],
        "byte_size": result["byte_size"],
        "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
