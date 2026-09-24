"""Execute an exact captured BMW shader permutation offline.

Inputs are the runtime RenderContract plus the neutral MEB JSON. Material DDS
can be read directly from BMW_M3_E36.bff. Runtime external stages (s0/s3/s4)
are supplied as ReferenceTexture/1 or ReferenceCubeTexture/1 JSON resources.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bff_meb_render import find_meb_entry
from reference_renderer import rasterize_textured_mesh
from runtime_texture_reference import ppm_to_reference_texture
from shift_importer import BFF
from texture_reference import decode_dds, CUBE_FORMAT, FORMAT

FORMAT_OUT = "SHIFT.BMWRuntimeShaderRender/1"


def _json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _load_resource(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if path.suffix.lower() == ".dds":
        return decode_dds(path.read_bytes())
    value = _json(path)
    return value


def _stage_arg(value: str) -> tuple[int, str]:
    if "=" not in value:
        raise ValueError("stage resource must use STAGE=PATH")
    stage_text, path = value.split("=", 1)
    try:
        stage = int(stage_text)
    except ValueError as exc:
        raise ValueError(f"invalid sampler stage {stage_text!r}") from exc
    if stage < 0 or not path:
        raise ValueError("sampler stage/path is invalid")
    return stage, path


def _material_texture_images(
    material_input: dict[str, Any],
    primary_bff: str | Path,
    explicit: list[str],
) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    images: dict[int, dict[str, Any]] = {}
    resources: dict[int, dict[str, Any]] = {}
    explicit_by_stage: dict[int, str] = dict(_stage_arg(item) for item in explicit)

    bindings = (
        material_input.get("material_binding", {}).get("bindings")
        if isinstance(material_input.get("material_binding"), dict)
        else material_input.get("bindings")
    )
    bindings = [row for row in (bindings or []) if isinstance(row, dict)]

    with BFF(primary_bff) as archive:
        entry_map = {
            str(entry.path).replace("\", "/").strip("/").lower(): entry
            for entry in archive.entries
        }
        for binding in bindings:
            if binding.get("binding") != "material-texture":
                continue
            register = binding.get("d3d9_sampler_register")
            resolved = binding.get("texture_resolved")
            if register is None or not resolved:
                continue
            try:
                register = int(register)
            except (TypeError, ValueError):
                continue
            path = explicit_by_stage.get(register)
            if path:
                image = _load_resource(path)
            else:
                entry = entry_map.get(str(resolved).replace("\", "/").strip("/").lower())
                if entry is None:
                    continue
                image = decode_dds(archive.extract_entry(entry))
            if image.get("format") == CUBE_FORMAT:
                resources[register] = image
            else:
                images[register] = image

    for stage, path in explicit_by_stage.items():
        if stage in images or stage in resources:
            continue
        image = _load_resource(path)
        if image.get("format") == CUBE_FORMAT:
            resources[stage] = image
        else:
            images[stage] = image
    return images, resources


def _sampler_states(material_input: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = (
        material_input.get("material_binding", {}).get("bindings")
        if isinstance(material_input.get("material_binding"), dict)
        else material_input.get("bindings")
    )
    states: dict[int, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        register = row.get("d3d9_sampler_register")
        if register is None:
            continue
        try:
            register = int(register)
        except (TypeError, ValueError):
            continue
        states[register] = {
            key: row[key]
            for key in (
                "min_filter",
                "mag_filter",
                "mip_filter",
                "address_u",
                "address_v",
                "address_w",
                "srgb",
                "linear",
            )
            if key in row
        }
    return states


def _semantic_rows(mesh: dict[str, Any]) -> dict[tuple[str, int], Any]:
    rows: dict[tuple[str, int], Any] = {}
    for semantic, key in (
        (("POSITION", 0), "vertices"),
        (("COLOR", 0), "colors"),
        (("NORMAL", 0), "normals"),
        (("TANGENT", 0), "tangents"),
        (("BINORMAL", 0), "tangents2"),
        (("BLENDWEIGHT", 0), "bone_weights"),
        (("BLENDINDICES", 0), "bone_indices"),
    ):
        if mesh.get(key):
            rows[semantic] = mesh[key]
    return rows


def render_runtime_shader(
    contract_path: str | Path,
    material_input_path: str | Path,
    mesh_path: str | Path,
    primary_bff: str | Path,
    output: str | Path,
    *,
    external_resources: list[str] = (),
    width: int = 1200,
    height: int = 800,
) -> dict[str, Any]:
    contract = _json(contract_path)
    material_input = _json(material_input_path)
    mesh = _json(mesh_path)

    if contract.get("format") != "SHIFT.BMWRuntimeRenderContract/1":
        raise ValueError("invalid BMW runtime render contract format")
    if material_input.get("format") not in {
        "SHIFT.RealBMWMaterialBindingEvidence/1",
        "SHIFT.MaterialBinding/1",
    }:
        raise ValueError("invalid BMW material binding format")
    if mesh.get("format") not in {"SHIFT.MEB", "SHIFT.MEBEvidence"} and "vertices" not in mesh:
        raise ValueError("mesh JSON does not contain neutral MEB vertex payload")

    if contract.get("reference_render_ready") is not True:
        raise ValueError(
            "runtime render contract is not ready: "
            + ", ".join(contract.get("blocking_reasons") or [])
        )

    shader = contract.get("shader") or {}
    linked_pair = shader.get("linked_shader_pair") or {}
    vertex_program = linked_pair.get("vertex")
    pixel_program = linked_pair.get("pixel")
    if not vertex_program or not pixel_program:
        raise ValueError("runtime render contract has no linked VS/PS IR")

    texture_images, texture_resources = _material_texture_images(
        material_input,
        primary_bff,
        external_resources,
    )
    sampler_states = _sampler_states(material_input)

    # The reference renderer expects one conventional base image argument.
    base_image = texture_images.get(1)
    if base_image is None:
        base_image = next(iter(texture_images.values()), None)
    if base_image is None:
        raise ValueError("no material texture image is available")

    external_image_map = {
        stage: image
        for stage, image in texture_images.items()
        if stage not in {1, 2, 4}
    }
    external_image_map.update(texture_images)
    # Cubemaps must travel through external_texture_resources so the renderer can
    # select faces using the shader's samplerCube contract.
    for stage in list(texture_resources):
        external_image_map.pop(stage, None)

    constants = contract.get("constants") or {}
    vertex_constants = (constants.get("vertex") or {})
    pixel_constants = (constants.get("pixel") or {})
    vertex_constants = {
        key: value for key, value in vertex_constants.items()
    }
    pixel_constants = {
        key: value for key, value in pixel_constants.items()
    }

    uv_layers = mesh.get("uv_layers") or {}
    uv0 = uv_layers.get("130") or uv_layers.get(130)
    if not uv0:
        raise ValueError("MEB mesh has no proven TEXCOORD0 layer (130)")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_bytes = rasterize_textured_mesh(
        mesh.get("vertices") or [],
        mesh.get("indices") or [],
        uv0,
        base_image,
        width=width,
        height=height,
        pixel_program=pixel_program,
        vertex_program=vertex_program,
        vertex_shader_constants=vertex_constants.get("c") if isinstance(vertex_constants, dict) else None,
        pixel_shader_constants=pixel_constants.get("c") if isinstance(pixel_constants, dict) else None,
        shader_constants={
            "c": {
                int(register): values
                for register, values in (
                    (pixel_constants.get("c") or {})
                ).items()
            }
        },
        texture_images=texture_images,
        samplers_by_sampler=sampler_states,
        uv_layers=uv_layers,
        semantic_rows=_semantic_rows(mesh),
        external_texture_resources=texture_resources,
    )
    output_path.write_bytes(image_bytes)

    return {
        "format": FORMAT_OUT,
        "status": "rendered",
        "output": str(output_path),
        "width": width,
        "height": height,
        "shader_identity": shader.get("identity") or {},
        "candidate": shader.get("candidate") or {},
        "texture_stages": sorted(texture_images),
        "texture_resource_stages": sorted(texture_resources),
        "shader_execution": True,
        "reference_renderer": "rasterize_textured_mesh",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute an exact captured BMW VS/PS permutation offline"
    )
    parser.add_argument("contract")
    parser.add_argument("material_input")
    parser.add_argument("mesh_json")
    parser.add_argument("primary_bff")
    parser.add_argument("output")
    parser.add_argument(
        "--external-resource",
        action="append",
        default=[],
        help="STAGE=ReferenceTexture/1-or-DDs path; repeat for s0/s3/s4",
    )
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    args = parser.parse_args(argv)

    result = render_runtime_shader(
        args.contract,
        args.material_input,
        args.mesh_json,
        args.primary_bff,
        args.output,
        external_resources=args.external_resource,
        width=args.width,
        height=args.height,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
