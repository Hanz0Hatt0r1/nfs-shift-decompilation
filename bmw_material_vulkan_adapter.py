"""Bridge an existing real BMW material-slice report into the Vulkan bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from bmw_vulkan_bundle import TARGET_MEB, build_bmw_vulkan_bundle

FORMAT = "SHIFT.BMWMaterialSliceVulkan/1"


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    path = Path(value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    payload["_source_path"] = str(path)
    payload["_source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload


def _find_render_command(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("format") == "SHIFT.RenderCommand/1":
        return dict(payload)

    candidates = [
        payload.get("render_command"),
        payload.get("command"),
        payload.get("render"),
        payload.get("packet"),
    ]
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            found = _find_render_command(candidate)
            if found:
                return found

    for value in payload.values():
        if isinstance(value, Mapping) and value.get("format") == "SHIFT.RenderCommand/1":
            return dict(value)

    raise ValueError("BMW material slice does not contain SHIFT.RenderCommand/1")


def _find_mesh(payload: Mapping[str, Any], command: Mapping[str, Any]) -> dict[str, Any]:
    mesh = command.get("neutral_mesh")
    if isinstance(mesh, Mapping):
        return dict(mesh)
    mesh = command.get("mesh_data")
    if isinstance(mesh, Mapping):
        return dict(mesh)

    for candidate in (
        command.get("mesh"),
        payload.get("mesh"),
        payload.get("neutral_mesh"),
        payload.get("mesh_json"),
    ):
        if isinstance(candidate, Mapping) and "vertices" in candidate and "indices" in candidate:
            return dict(candidate)

    for value in payload.values():
        if isinstance(value, Mapping) and "vertices" in value and "indices" in value:
            return dict(value)

    raise ValueError("BMW material slice does not contain a neutral mesh JSON payload")


def _validate_vulkan_shader_sources(command: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for index, submesh in enumerate(command.get("submeshes", []) or []):
        shader = submesh.get("shader") or {}
        if not isinstance(shader, Mapping):
            blockers.append(f"bmw-material-vulkan:shader-missing:{index}")
            continue
        for stage in ("vertex", "pixel"):
            if not shader.get(f"vulkan_{stage}_glsl"):
                blockers.append(f"bmw-material-vulkan:vulkan-{stage}-source-missing:{index}")
    return blockers


def build_bmw_vulkan_from_material_slice(
    material_slice: str | Path | Mapping[str, Any],
    output_dir: str | Path,
    *,
    textures: str | Path | Mapping[str, Any] | None = None,
    environment_cube: str | Path | Mapping[str, Any] | None = None,
    submesh_index: int = 0,
) -> dict[str, Any]:
    payload = _load(material_slice)
    command = _find_render_command(payload)
    mesh = _find_mesh(payload, command)

    mesh_ref = (command.get("mesh") or {}).get("ref")
    if mesh_ref != TARGET_MEB:
        raise ValueError(
            "BMW material slice is not the exact KIT00 body MEB required by Vulkan bundle"
        )

    shader_blockers = _validate_vulkan_shader_sources(command)
    if shader_blockers:
        return {
            "format": FORMAT,
            "status": "blocked",
            "ready": False,
            "blocking_reasons": shader_blockers,
            "source": {
                "material_slice_path": payload.get("_source_path"),
                "material_slice_sha256": payload.get("_source_sha256"),
                "mesh_ref": mesh_ref,
            },
        }

    binding = {
        "format": "SHIFT.RenderBinding/1",
        "render_commands": [command],
    }
    result = build_bmw_vulkan_bundle(
        binding,
        mesh,
        output_dir,
        textures=textures,
        environment_cube=environment_cube,
        command_index=0,
        submesh_index=submesh_index,
    )

    source_record = {
        "format": FORMAT,
        "material_slice_format": payload.get("format"),
        "material_slice_path": payload.get("_source_path"),
        "material_slice_sha256": payload.get("_source_sha256"),
        "render_command_format": command.get("format"),
        "render_command_identity": command.get("identity"),
        "mesh_ref": mesh_ref,
        "target_meb": TARGET_MEB,
        "submesh_index": submesh_index,
    }
    source_path = Path(output_dir) / "material_slice_source.json"
    source_path.write_text(
        json.dumps(source_record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result["source"] = source_record
    result["artifacts"]["material_slice_source"] = {
        "path": str(source_path.relative_to(Path(output_dir))),
        "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bridge a BMW material-slice JSON into SHIFT.BMWVulkanBundle/1"
    )
    parser.add_argument("material_slice")
    parser.add_argument("output_dir")
    parser.add_argument("--textures")
    parser.add_argument("--environment-cube")
    parser.add_argument("--submesh-index", type=int, default=0)
    args = parser.parse_args(argv)
    result = build_bmw_vulkan_from_material_slice(
        args.material_slice,
        args.output_dir,
        textures=args.textures,
        environment_cube=args.environment_cube,
        submesh_index=args.submesh_index,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
