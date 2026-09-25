"""Prepare one reproducible BMW RenderCommand for the Linux Vulkan backend."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from vulkan_constant_packet import build_vulkan_constant_packet
from vulkan_cube_packet import build_vulkan_cube_packet
from vulkan_geometry_packet import export_vulkan_geometry_packet
from vulkan_texture_packet import build_vulkan_texture_packet
from vulkan_sampler_contract import write_sampler_metadata, build_sampler_contract_report

FORMAT = "SHIFT.BMWVulkanBundle/1"
TARGET_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (bytes, bytearray)):
        path.write_bytes(bytes(value))
    else:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _shader_sources(command: Mapping[str, Any], output: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, submesh in enumerate(command.get("submeshes", []) or []):
        shader = submesh.get("shader") or {}
        for stage in ("vertex", "pixel"):
            source = shader.get(f"vulkan_{stage}_glsl") or shader.get(stage)
            if not source:
                continue
            target = output / "shaders" / f"submesh_{index}.{stage}.glsl"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(source), encoding="utf-8")
            rows.append({
                "submesh_index": index,
                "stage": stage,
                "path": str(target.relative_to(output)),
                "sha256": _hash(target),
                "source_format": "GLSL-from-RenderCommand/1",
                "vulkan_compilation": "not-run",
            })
    return rows


def build_bmw_vulkan_bundle(
    render_command: str | Path | Mapping[str, Any],
    mesh: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    textures: str | Path | Mapping[str, Any] | None = None,
    environment_cube: str | Path | Mapping[str, Any] | None = None,
    command_index: int = 0,
    submesh_index: int = 0,
) -> dict[str, Any]:
    command_source = _load(render_command) if isinstance(render_command, (str, Path)) else dict(render_command)
    mesh_source = _load(mesh) if isinstance(mesh, (str, Path)) else dict(mesh)

    input_format = command_source.get("format")
    if input_format not in {"SHIFT.RenderBinding/1", "SHIFT.RenderCommand/1"}:
        raise ValueError("input must be SHIFT.RenderBinding/1 or SHIFT.RenderCommand/1")
    if mesh_source.get("format") not in {"SHIFT.MEB", None}:
        raise ValueError("mesh must be neutral SHIFT.MEB JSON")

    if input_format == "SHIFT.RenderCommand/1":
        commands = [command_source]
    else:
        commands = command_source.get("render_commands") or []
    if command_index < 0 or command_index >= len(commands):
        raise ValueError(f"command index out of range: {command_index}")
    selected_command = commands[command_index]
    if not isinstance(selected_command, Mapping):
        raise ValueError(f"render command {command_index} is not an object")

    submeshes = selected_command.get("submeshes") or []
    if submesh_index < 0 or submesh_index >= len(submeshes):
        raise ValueError(f"submesh index out of range: {submesh_index}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    selected = dict(selected_command)
    selected["submeshes"] = [dict(submeshes[submesh_index])]
    if (selected.get("mesh") or {}).get("ref") != TARGET_MEB:
        raise ValueError("BMW Vulkan bundle requires the exact M3 KIT00 body MEB reference")

    geometry_path = out / "geometry.svpk"
    constants_path = out / "constants.svcp"
    geometry = export_vulkan_geometry_packet(
        selected,
        mesh_source,
        geometry_path,
        submesh_index=0,
    )
    constants = build_vulkan_constant_packet(selected, constants_path)

    texture_report = None
    texture_path = None
    if textures is not None:
        texture_path = out / "textures.svtp"
        texture_report = build_vulkan_texture_packet(
            selected,
            textures,
            texture_path,
        )

    cube_report = None
    cube_path = None
    has_s3_cube = any(
        str(row.get("sampler_type") or "") == "samplerCube"
        and int(row.get("d3d9_sampler_register", row.get("slot", -1))) == 3
        for row in (selected["submeshes"][0].get("external_samplers") or [])
    )
    if has_s3_cube and environment_cube is not None:
        cube_path = out / "environment_cube.svcp"
        cube_report = build_vulkan_cube_packet(
            selected,
            environment_cube,
            cube_path,
        )

    external = [
        {
            "sampler": row.get("sampler"),
            "sampler_type": row.get("sampler_type"),
            "d3d9_sampler_register": row.get("d3d9_sampler_register", row.get("slot")),
            "status": "requires-runtime-resource",
        }
        for row in selected["submeshes"][0].get("external_samplers") or []
    ]

    shader_rows = _shader_sources(selected, out)

    sampler_report = build_sampler_contract_report(selected)
    sampler_contract_path = out / "sampler_contracts.json"
    sampler_report = write_sampler_contract_report(sampler_report, sampler_contract_path)
    sampler_metadata_path = out / "sampler_contracts.meta.json"
    if texture_report is not None:
        sampler_metadata = write_sampler_metadata(
            sampler_report,
            texture_path,
            sampler_metadata_path,
        )
    else:
        sampler_metadata = None

    artifacts = {
        "geometry": {
            "path": str(geometry_path.relative_to(out)),
            "sha256": _hash(geometry_path),
            "ready": True,
        },
        "constants": {
            "path": str(constants_path.relative_to(out)),
            "sha256": _hash(constants_path),
            "ready": bool(constants.get("ready")),
            "blocking_reasons": constants.get("blocking_reasons") or [],
        },
        "textures": None if texture_report is None else {
            "path": str(texture_path.relative_to(out)),
            "sha256": _hash(texture_path),
            "ready": True,
            "texture_count": texture_report.get("texture_count"),
        },
        "environment_cube": None if cube_report is None else {
            "path": str(cube_path.relative_to(out)),
            "sha256": _hash(cube_path),
            "ready": True,
            "register": 3,
        },
        "shaders": shader_rows,
        "sampler_contracts": {
            "path": str(sampler_contract_path.relative_to(out)),
            "sha256": _hash(sampler_contract_path),
            "ready": bool(sampler_report.get("ready")),
            "blocking_reasons": sampler_report.get("blocking_reasons") or [],
            "metadata_path": (
                str(sampler_metadata_path.relative_to(out))
                if sampler_metadata is not None else None
            ),
            "metadata_sha256": (
                sampler_metadata.get("sha256")
                if sampler_metadata is not None else None
            ),
        },
    }

    blockers = list(constants.get("blocking_reasons") or [])
    if textures is None and selected["submeshes"][0].get("textures"):
        blockers.append("bmw-vulkan-bundle:material-textures-not-supplied")
    if has_s3_cube and environment_cube is None:
        blockers.append("bmw-vulkan-bundle:environment-cube-not-supplied")

    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not blockers else "partial",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "source": {
            "render_command_format": command_source.get("format"),
            "command_index": command_index,
            "submesh_index": submesh_index,
            "mesh_ref": (command_source.get("mesh") or {}).get("ref"),
            "mesh_sha256": ((command_source.get("mesh") or {}).get("resolved") or {}).get("resource_sha256"),
        },
        "target": {
            "meb": TARGET_MEB,
            "vertex_count": (command_source.get("mesh") or {}).get("vertex_count"),
            "triangle_count": (command_source.get("mesh") or {}).get("triangle_count"),
        },
        "artifacts": artifacts,
        "external_samplers": external,
        "native_execution": {
            "status": "not-run",
            "reason": "bundle preparation does not claim a native Vulkan render",
        },
    }
    _write(out / "bundle_manifest.json", report)
    report["manifest_sha256"] = _hash(out / "bundle_manifest.json")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare SHIFT.BMWVulkanBundle/1")
    parser.add_argument("render_command")
    parser.add_argument("mesh")
    parser.add_argument("output_dir")
    parser.add_argument("--textures")
    parser.add_argument("--environment-cube")
    parser.add_argument("--command-index", type=int, default=0)
    parser.add_argument("--submesh-index", type=int, default=0)
    args = parser.parse_args(argv)
    result = build_bmw_vulkan_bundle(
        args.render_command,
        args.mesh,
        args.output_dir,
        textures=args.textures,
        environment_cube=args.environment_cube,
        command_index=args.command_index,
        submesh_index=args.submesh_index,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
