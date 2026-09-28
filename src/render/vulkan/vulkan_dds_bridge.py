"""Bridge real DDS files into the existing Vulkan texture/cube packet ABI."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from texture_reference import CUBE_FORMAT, FORMAT, decode_dds
from vulkan_cube_packet import build_vulkan_cube_packet
from vulkan_texture_packet import build_vulkan_texture_packet

FORMAT_BRIDGE = "SHIFT.VulkanDDSResourceBridge/1"


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _load_render_command(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    return _load_json(value) if isinstance(value, (str, Path)) else dict(value)


def _load_map(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    payload = _load_json(value) if isinstance(value, (str, Path)) else dict(value)
    return payload


def _decode_file(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    data = source.read_bytes()
    image = decode_dds(data)
    image["_source_path"] = str(source)
    image["_source_sha256"] = hashlib.sha256(data).hexdigest()
    image["_decoded_pixel_sha256"] = hashlib.sha256(bytes(
        b"".join(
            bytes(face["pixels"]) for face in image["faces"].values()
        )
    ) if image.get("format") == CUBE_FORMAT else bytes(image["pixels"])).hexdigest()
    return image


def _sampler_registers(render_command: Mapping[str, Any]) -> tuple[set[int], set[int]]:
    material_2d: set[int] = set()
    cubes: set[int] = set()
    for submesh in render_command.get("submeshes", []) or []:
        for row in submesh.get("textures", []) or []:
            if row.get("resource") == "external":
                continue
            register = row.get("d3d9_sampler_register")
            if register is None:
                raise ValueError("RenderCommand texture is missing d3d9_sampler_register")
            material_2d.add(int(register))
        for row in submesh.get("external_samplers", []) or []:
            register = row.get("d3d9_sampler_register", row.get("slot"))
            sampler_type = str(row.get("sampler_type") or "")
            if sampler_type == "samplerCube":
                cubes.add(int(register))
            elif sampler_type:
                material_2d.add(int(register))
    return material_2d, cubes


def bridge_bmw_dds_resources(
    render_command: str | Path | Mapping[str, Any],
    texture_dds_map: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    environment_cube_dds: str | Path | None = None,
) -> dict[str, Any]:
    command = _load_render_command(render_command)
    texture_map = _load_map(texture_dds_map)
    material_registers, cube_registers = _sampler_registers(command)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    decoded_textures: dict[int, dict[str, Any]] = {}
    source_records: list[dict[str, Any]] = []
    blockers: list[str] = []
    supplied_material_registers: set[int] = set()

    for register_text, value in texture_map.items():
        register = int(register_text)
        if register not in material_registers:
            blockers.append(
                f"dds-bridge:unbound-material-register:s{register}"
            )
            continue
        supplied_material_registers.add(register)
        try:
            image = _decode_file(value)
        except (OSError, ValueError, TypeError) as error:
            blockers.append(
                f"dds-bridge:decode-failed:s{register}:{type(error).__name__}"
            )
            continue
        if image.get("format") == CUBE_FORMAT:
            blockers.append(
                f"dds-bridge:cubemap-supplied-to-2d-register:s{register}"
            )
            continue
        if image.get("format") != FORMAT:
            blockers.append(f"dds-bridge:unsupported-decoded-format:s{register}")
            continue
        decoded_textures[register] = image
        source_records.append({
            "kind": "2d",
            "register": register,
            "source_path": image["_source_path"],
            "source_sha256": image["_source_sha256"],
            "decoded_pixel_sha256": image["_decoded_pixel_sha256"],
            "source_format": image.get("source_format"),
            "width": image.get("width"),
            "height": image.get("height"),
        })

    missing_2d = sorted(material_registers - supplied_material_registers)
    if missing_2d:
        blockers.extend(
            f"dds-bridge:missing-2d-ds:s{register}"
            for register in missing_2d
        )

    texture_report = None
    texture_path = None
    if decoded_textures:
        texture_path = out / "textures.svtp"
        try:
            texture_report = build_vulkan_texture_packet(
                command,
                decoded_textures,
                texture_path,
            )
        except (OSError, ValueError, TypeError) as error:
            blockers.append(
                f"dds-bridge:texture-packet-failed:{type(error).__name__}"
            )

    cube_report = None
    cube_path = None
    if cube_registers:
        if environment_cube_dds is None:
            blockers.extend(
                f"dds-bridge:missing-cube-ds:s{register}"
                for register in sorted(cube_registers)
            )
        else:
            try:
                image = _decode_file(environment_cube_dds)
            except (OSError, ValueError, TypeError) as error:
                blockers.append(
                    f"dds-bridge:environment-cube-decode-failed:{type(error).__name__}"
                )
                image = None
            if image is not None and image.get("format") != CUBE_FORMAT:
                blockers.append("dds-bridge:environment-cube-not-cubemap")
            elif image is not None and cube_registers != {3}:
                blockers.append(
                    "dds-bridge:only the proven BMW environment cube register s3 is supported"
                )
            elif image is not None:
                cube_path = out / "environment_cube.svcp"
                try:
                    cube_report = build_vulkan_cube_packet(
                        command,
                        image,
                        cube_path,
                        register=3,
                    )
                except (OSError, ValueError, TypeError) as error:
                    blockers.append(
                        f"dds-bridge:cube-packet-failed:{type(error).__name__}"
                    )
                    cube_report = None
                if cube_report is not None:
                    source_records.append({
                        "kind": "cube",
                        "register": 3,
                        "source_path": image["_source_path"],
                        "source_sha256": image["_source_sha256"],
                        "decoded_pixel_sha256": image["_decoded_pixel_sha256"],
                        "source_format": image.get("source_format"),
                        "width": image.get("width"),
                        "height": image.get("height"),
                    })

    provenance_path = out / "dds_sources.json"
    provenance = {
        "format": FORMAT_BRIDGE,
        "version": 1,
        "sources": source_records,
        "decoded_base_level_only": True,
    }
    provenance_path.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if texture_report is not None:
        texture_report["sources"] = [
            row for row in source_records if row["kind"] == "2d"
        ]
    if cube_report is not None:
        cube_report["source"] = next(
            row for row in source_records if row["kind"] == "cube"
        )

    report = {
        "format": FORMAT_BRIDGE,
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "render_command_format": command.get("format"),
        "material_2d_registers": sorted(material_registers),
        "environment_cube_registers": sorted(cube_registers),
        "decoded_sources": source_records,
        "packets": {
            "textures": None if texture_report is None else {
                "path": str(texture_path.relative_to(out)),
                "format": texture_report["format"],
                "version": texture_report["version"],
            },
            "environment_cube": None if cube_report is None else {
                "path": str(cube_path.relative_to(out)),
                "format": cube_report["format"],
                "version": cube_report["version"],
            },
        },
        "provenance": {
            "path": str(provenance_path.relative_to(out)),
            "sha256": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
        },
    }
    (out / "dds_bridge_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bridge DDS resources into SHIFT Vulkan packets"
    )
    parser.add_argument("render_command")
    parser.add_argument("texture_dds_map")
    parser.add_argument("output_dir")
    parser.add_argument("--environment-cube-dds")
    args = parser.parse_args(argv)
    result = bridge_bmw_dds_resources(
        args.render_command,
        args.texture_dds_map,
        args.output_dir,
        environment_cube_dds=args.environment_cube_dds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
