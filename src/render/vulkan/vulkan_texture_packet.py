"""Serialize RenderCommand 2D texture resources for the Linux Vulkan backend."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.VulkanTexturePacket/1"
MAGIC = b"SVTP"
VERSION = 1
HEADER = struct.Struct("<4sIIII")
RECORD = struct.Struct("<IIIIII")
MODE_NEAREST_REPEAT = 1
MODE_LINEAR_REPEAT = 2
MODE_NEAREST_CLAMP = 3
MODE_LINEAR_CLAMP = 4


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sampler_mode(state: Mapping[str, Any] | None) -> int:
    state = state or {}
    min_filter = str(state.get("min_filter") or "NEAREST").upper()
    mag_filter = str(state.get("mag_filter") or "NEAREST").upper()
    address_u = str(state.get("address_u") or "REPEAT").upper()
    address_v = str(state.get("address_v") or "REPEAT").upper()

    if address_u != address_v or address_u not in {"REPEAT", "CLAMP_TO_EDGE"}:
        raise ValueError("Vulkan texture packet requires matching REPEAT or CLAMP_TO_EDGE addressing")
    if min_filter not in {"NEAREST", "LINEAR"} or mag_filter not in {"NEAREST", "LINEAR"}:
        raise ValueError("Vulkan texture packet supports only NEAREST/LINEAR filtering")
    linear = min_filter == "LINEAR" or mag_filter == "LINEAR"
    if linear and address_u == "REPEAT":
        return MODE_LINEAR_REPEAT
    if linear and address_u == "CLAMP_TO_EDGE":
        return MODE_LINEAR_CLAMP
    if address_u == "CLAMP_TO_EDGE":
        return MODE_NEAREST_CLAMP
    return MODE_NEAREST_REPEAT


def _pixels(image: Mapping[str, Any]) -> bytes:
    if image.get("format") != "SHIFT.ReferenceTexture/1":
        raise ValueError("texture input must be SHIFT.ReferenceTexture/1")
    if image.get("pixel_format") != "RGBA8":
        raise ValueError("texture input must be RGBA8")
    try:
        width = int(image.get("width"))
        height = int(image.get("height"))
    except (TypeError, ValueError):
        raise ValueError("texture dimensions are invalid")
    pixels = image.get("pixels")
    if isinstance(pixels, str):
        try:
            pixels = bytes.fromhex(pixels)
        except ValueError:
            raise ValueError("texture hex pixels are invalid")
    elif isinstance(pixels, list):
        pixels = bytes(int(value) for value in pixels)
    if not isinstance(pixels, (bytes, bytearray)):
        raise ValueError("texture pixels are missing")
    expected = width * height * 4
    if width <= 0 or height <= 0 or len(pixels) != expected:
        raise ValueError("texture RGBA8 payload size does not match dimensions")
    return bytes(pixels)


def build_vulkan_texture_packet(
    render_command: Mapping[str, Any] | str | Path,
    textures: Mapping[int, Mapping[str, Any]] | str | Path,
    output: str | Path,
) -> dict[str, Any]:
    command = _load(render_command) if isinstance(render_command, (str, Path)) else dict(render_command)
    if command.get("format") != "SHIFT.RenderCommand/1":
        raise ValueError("input is not SHIFT.RenderCommand/1")
    texture_map = (
        _load(textures) if isinstance(textures, (str, Path)) else dict(textures)
    )

    commands: dict[int, dict[str, Any]] = {}
    for submesh in command.get("submeshes", []) or []:
        for row in submesh.get("textures", []) or []:
            if row.get("resource") == "external":
                continue
            register = row.get("d3d9_sampler_register")
            try:
                register = int(register)
            except (TypeError, ValueError):
                raise ValueError("RenderCommand texture has invalid sampler register")
            if register < 0 or register > 15:
                raise ValueError(f"sampler register out of packet range: {register}")
            if register in commands and commands[register] != row:
                raise ValueError(f"sampler register collision in RenderCommand: s{register}")
            commands[register] = dict(row)

    missing = [str(register) for register in sorted(commands) if str(register) not in texture_map and register not in texture_map]
    if missing:
        raise ValueError("missing texture reference image for sampler(s): " + ", ".join("s" + x for x in missing))

    records: list[bytes] = []
    metadata: list[dict[str, Any]] = []
    for register in sorted(commands):
        row = commands[register]
        image_value = texture_map.get(register) or texture_map.get(str(register))
        if isinstance(image_value, (str, Path)):
            image = _load(image_value)
        elif isinstance(image_value, Mapping):
            image = dict(image_value)
        else:
            raise ValueError(f"invalid texture mapping for s{register}")

        pixels = _pixels(image)
        mode = _sampler_mode(row.get("sampler_state"))
        width = int(image["width"])
        height = int(image["height"])
        offset = HEADER.size + RECORD.size * len(commands) + sum(len(data) for data in records)
        records.append(pixels)
        metadata.append({
            "register": register,
            "width": width,
            "height": height,
            "pixel_offset": offset,
            "pixel_bytes": len(pixels),
            "sampler_mode": mode,
            "source_sha256": hashlib.sha256(pixels).hexdigest(),
            "resource_binding_id": row.get("resource_binding_id"),
            "texture_id": row.get("texture_id"),
            "sampler_id": row.get("sampler_id"),
        })

    header = HEADER.pack(MAGIC, VERSION, len(metadata), 1, 0)
    table = bytearray()
    for item in metadata:
        table.extend(RECORD.pack(
            item["register"], item["width"], item["height"],
            item["pixel_offset"], item["pixel_bytes"], item["sampler_mode"],
        ))
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(header + table + b"".join(records))

    return {
        "format": FORMAT,
        "version": VERSION,
        "output": str(output_path),
        "descriptor_set": 1,
        "texture_count": len(metadata),
        "textures": metadata,
        "byte_size": output_path.stat().st_size,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SHIFT.VulkanTexturePacket/1")
    parser.add_argument("render_command")
    parser.add_argument("textures_json", help="JSON object mapping sampler registers to ReferenceTexture/1 JSON or inline resource objects")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    result = build_vulkan_texture_packet(args.render_command, args.textures_json, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
