"""Serialize one D3D9 samplerCube resource into a Vulkan cube-image packet."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.VulkanCubeTexturePacket/1"
MAGIC = b"SVCP"
VERSION = 1
FACES = ("px", "nx", "py", "ny", "pz", "nz")
HEADER = struct.Struct("<4sIIIIII")
MODE_LINEAR_CLAMP = 4


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def build_vulkan_cube_packet(
    render_command: Mapping[str, Any] | str | Path,
    cube: Mapping[str, Any] | str | Path,
    output: str | Path,
    *,
    register: int = 3,
) -> dict[str, Any]:
    command = _load(render_command) if isinstance(render_command, (str, Path)) else dict(render_command)
    image = _load(cube) if isinstance(cube, (str, Path)) else dict(cube)

    if command.get("format") != "SHIFT.RenderCommand/1":
        raise ValueError("input is not SHIFT.RenderCommand/1")
    if image.get("format") != "SHIFT.ReferenceCubeTexture/1":
        raise ValueError("cube input must be SHIFT.ReferenceCubeTexture/1")
    if register != 3:
        raise ValueError("Phase 215 environment cube boundary is fixed to D3D9 sampler s3")

    textures = []
    for submesh in command.get("submeshes", []) or []:
        textures.extend(submesh.get("external_samplers", []) or [])
    matching = [
        row for row in textures
        if int(row.get("d3d9_sampler_register", row.get("slot", -1))) == register
        and str(row.get("sampler_type") or "") == "samplerCube"
    ]
    if len(matching) != 1:
        raise ValueError("RenderCommand must contain exactly one samplerCube external binding at s3")

    faces = image.get("faces") or {}
    if set(faces) != set(FACES):
        missing = sorted(set(FACES) - set(faces))
        extra = sorted(set(faces) - set(FACES))
        raise ValueError(f"cube faces mismatch: missing={missing}, extra={extra}")

    dimensions = {
        (int(face.get("width", 0)), int(face.get("height", 0)))
        for face in faces.values()
    }
    if len(dimensions) != 1:
        raise ValueError("cube faces must have identical dimensions")
    width, height = next(iter(dimensions))
    if width <= 0 or height <= 0:
        raise ValueError("cube dimensions must be positive")

    payloads: list[bytes] = []
    face_meta: list[dict[str, Any]] = []
    for face_name in FACES:
        face = faces[face_name]
        if face.get("pixel_format") != "RGBA8":
            raise ValueError(f"cube face {face_name} must be RGBA8")
        pixels = face.get("pixels")
        if isinstance(pixels, str):
            pixels = bytes.fromhex(pixels)
        elif isinstance(pixels, list):
            pixels = bytes(int(v) for v in pixels)
        if not isinstance(pixels, (bytes, bytearray)):
            raise ValueError(f"cube face {face_name} has no pixels")
        pixels = bytes(pixels)
        expected = width * height * 4
        if len(pixels) != expected:
            raise ValueError(f"cube face {face_name} payload size mismatch")
        payloads.append(pixels)
        face_meta.append({
            "face": face_name,
            "byte_size": len(pixels),
            "sha256": hashlib.sha256(pixels).hexdigest(),
        })

    if set(faces) == set(FACES):
        state = matching[0].get("sampler_state") or {}
        min_filter = str(state.get("min_filter") or "LINEAR").upper()
        mag_filter = str(state.get("mag_filter") or "LINEAR").upper()
        address = {
            str(state.get(key) or "CLAMP_TO_EDGE").upper()
            for key in ("address_u", "address_v", "address_w")
        }
        if min_filter not in {"LINEAR", "NEAREST"} or mag_filter not in {"LINEAR", "NEAREST"}:
            raise ValueError("Phase 215 supports only NEAREST/LINEAR cube filtering")
        if address != {"CLAMP_TO_EDGE"}:
            raise ValueError("Phase 215 cube sampler requires CLAMP_TO_EDGE on U/V/W")

    face_size = width * height * 4
    payload_offset = HEADER.size
    blob = bytearray(
        HEADER.pack(
            MAGIC,
            VERSION,
            register,
            width,
            height,
            len(FACES),
            face_size,
        )
    )
    for pixels in payloads:
        blob.extend(pixels)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(blob)

    return {
        "format": FORMAT,
        "version": VERSION,
        "output": str(output_path),
        "descriptor_set": 1,
        "register": register,
        "view_type": "VK_IMAGE_VIEW_TYPE_CUBE",
        "faces": face_meta,
        "width": width,
        "height": height,
        "face_bytes": face_size,
        "total_bytes": len(blob),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SHIFT.VulkanCubeTexturePacket/1")
    parser.add_argument("render_command")
    parser.add_argument("cube_json")
    parser.add_argument("output")
    parser.add_argument("--register", type=int, default=3)
    args = parser.parse_args(argv)
    result = build_vulkan_cube_packet(args.render_command, args.cube_json, args.output, register=args.register)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
