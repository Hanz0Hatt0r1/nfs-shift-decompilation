#!/usr/bin/env python3
from __future__ import annotations
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
if SOURCE_ROOT.is_dir():
    _SOURCE_PATHS = [SOURCE_ROOT]
    _SOURCE_PATHS.extend(
        sorted(
            (path for path in SOURCE_ROOT.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.parts), str(path)),
        )
    )
    for _source_path in reversed(_SOURCE_PATHS):
        _source_value = str(_source_path)
        if _source_value not in sys.path:
            sys.path.insert(0, _source_value)

from bmw_vulkan_bundle import TARGET_MEB
from bmw_material_vulkan_adapter import (
    build_bmw_vulkan_from_material_slice,
    build_bmw_vulkan_set_from_material_slice,
)
from vulkan_bundle_run import run_bmw_vulkan_bundle
from vulkan_bundle_set_prepare import prepare_bmw_vulkan_bundle_set
from vulkan_world_transform_packet import build_vulkan_world_transform_packet

VERTEX_GLSL = """#version 450
layout(location = 0) in vec3 position;
layout(location = 0) out vec2 v_uv;
layout(location = 1) out vec3 v_dir;
layout(set = 0, binding = 14, std140) uniform ShiftVertexConstants { vec4 c[256]; } vertex_constants;
void main() {
    gl_Position = vec4(position + vertex_constants.c[0].xyz, 1.0);
    v_uv = position.xy * 0.5 + vec2(0.5);
    v_dir = vec3(position.xy, 1.0);
}"""

PIXEL_GLSL = """#version 450
layout(location = 0) in vec2 v_uv;
layout(location = 1) in vec3 v_dir;
layout(location = 0) out vec4 out_color;
layout(set = 0, binding = 15, std140) uniform ShiftPixelConstants { vec4 c[256]; } pixel_constants;
layout(set = 1, binding = 1) uniform sampler2D tex1;
layout(set = 1, binding = 3) uniform samplerCube tex3;
void main() {
    out_color = texture(tex1, v_uv) * texture(tex3, normalize(v_dir)) * pixel_constants.c[1];
}"""

def render_command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "blocking_reasons": [],
        "validation": {"valid": True, "blocking_reasons": []},
        "mesh": {
            "ref": TARGET_MEB,
            "resolved": {"resource_sha256": "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"},
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 12,
                "attributes": [{
                    "property_id": "200", "usage": "POSITION", "usage_index": 0,
                    "location": 0, "offset": 0, "stride": 12,
                    "storage": "FLOAT32x3", "android": "FLOAT32x3",
                    "components": 3, "normalized": False, "element_size": 12,
                    "abi_status": "proven",
                }],
            },
        },
        "submeshes": [{
            "shader": {
                "vulkan_vertex_glsl": VERTEX_GLSL,
                "vulkan_pixel_glsl": PIXEL_GLSL,
                "source_payload_sha256": "c" * 64,
                "permutation_identity": {
                    "format": "SHIFT.ShaderPermutationIdentity/1",
                    "identity_sha256": "d" * 64,
                },
            },
            "constant_commands": [
                {"name": "ObjectOffset", "stage": "vertex", "register_index": 0, "register_count": 1},
                {"name": "Tint", "stage": "pixel", "register_index": 1, "register_count": 1},
            ],
            "constant_payload": {
                "format": "SHIFT.MaterialConstantPayload/1",
                "ready": True,
                "registers": [
                    {"register_index": 0, "values": [0.0,0.0,0.0,0.0]},
                    {"register_index": 1, "values": [1.0,1.0,1.0,1.0]},
                ],
            },
            "textures": [{
                "sampler": "diffuseMap", "d3d9_sampler_register": 1,
                "resource_binding_id": 1, "texture_id": 1, "sampler_id": 1,
                "sampler_state": {
                    "format": "SHIFT.SamplerState/1", "min_filter": "LINEAR",
                    "mag_filter": "LINEAR", "address_u": "REPEAT", "address_v": "REPEAT",
                },
            }],
            "external_samplers": [{
                "sampler": "environmentMap", "sampler_type": "samplerCube",
                "d3d9_sampler_register": 3,
                "sampler_state": {
                    "min_filter": "LINEAR", "mag_filter": "LINEAR",
                    "address_u": "CLAMP_TO_EDGE", "address_v": "CLAMP_TO_EDGE",
                    "address_w": "CLAMP_TO_EDGE",
                },
            }],
            "first_index": 0, "index_count": 3,
        }],
    }

def mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [[-0.65,-0.55,0.0],[0.65,-0.55,0.0],[0.0,0.65,0.0]],
        "indices": [0,1,2],
    }


def affine_render_command():
    command = deepcopy(render_command())
    command["mesh"]["vertex_layout"] = {
        "format": "SHIFT.VertexLayout/1",
        "buffer_stride": 48,
        "attributes": [
            {
                "property_id": "200", "usage": "POSITION", "usage_index": 0,
                "location": 0, "offset": 0, "stride": 48,
                "storage": "FLOAT32x3", "android": "FLOAT32x3",
                "components": 3, "normalized": False, "element_size": 12,
                "abi_status": "proven",
            },
            {
                "property_id": "220", "usage": "NORMAL", "usage_index": 0,
                "location": 1, "offset": 12, "stride": 48,
                "storage": "FLOAT32x3", "android": "FLOAT32x3",
                "components": 3, "normalized": False, "element_size": 12,
                "abi_status": "proven",
            },
            {
                "property_id": "240", "usage": "TANGENT", "usage_index": 0,
                "location": 2, "offset": 24, "stride": 48,
                "storage": "FLOAT32x3", "android": "FLOAT32x3",
                "components": 3, "normalized": False, "element_size": 12,
                "abi_status": "proven",
            },
            {
                "property_id": "250", "usage": "TANGENT", "usage_index": 1,
                "location": 3, "offset": 36, "stride": 48,
                "storage": "FLOAT32x3", "android": "FLOAT32x3",
                "components": 3, "normalized": False, "element_size": 12,
                "abi_status": "proven",
            },
        ],
    }
    return command


def affine_mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        "normals": [
            [1.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ],
        "tangents": [
            [1.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ],
        "tangents2": [
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ],
        "indices": [0, 1, 2],
    }


def multidraw_command():
    command = deepcopy(render_command())
    command["mesh"]["vertex_count"] = 4
    command["mesh"]["triangle_count"] = 2
    first = command["submeshes"][0]
    second = deepcopy(first)
    second["shader"]["source_payload_sha256"] = "e" * 64
    second["shader"]["permutation_identity"]["identity_sha256"] = "f" * 64
    second["constant_payload"]["registers"][1]["values"] = [0.65, 0.85, 1.0, 1.0]
    second["first_index"] = 3
    second["index_count"] = 3
    command["submeshes"].append(second)
    return command

def multidraw_mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [
            [-0.8,-0.6,0.0],
            [0.0,-0.6,0.0],
            [0.0,0.6,0.0],
            [0.8,0.6,0.0],
        ],
        "indices": [0,1,2,1,3,2],
    }

def texture():
    return {
        "format": "SHIFT.ReferenceTexture/1",
        "width": 1, "height": 1, "pixel_format": "RGBA8",
        "pixels": [255,96,96,255],
    }

def cube():
    colors = [96,255,96,255]
    faces = {}
    for face in ("px","nx","py","ny","pz","nz"):
        faces[face] = {
            "format": "SHIFT.ReferenceTexture/1", "width": 1, "height": 1,
            "pixel_format": "RGBA8", "pixels": colors,
        }
    return {"format": "SHIFT.ReferenceCubeTexture/1", "faces": faces}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("--executable", default="native_vulkan/build/shift_vulkan_bundle_execute")
    parser.add_argument("--validator", default="glslangValidator")
    parser.add_argument("--validation", action="store_true")
    args = parser.parse_args()

    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    bundle_dir = root / "bundle"
    material_slice = {
        "format": "SHIFT.BMWRealMaterialSlice/1",
        "render_command": render_command(),
        "mesh": mesh(),
    }
    adapter_result = build_bmw_vulkan_from_material_slice(
        material_slice,
        bundle_dir,
        textures={"1": texture()},
        environment_cube=cube(),
    )
    if not adapter_result["ready"]:
        raise SystemExit(
            "material-slice adapter blocked: "
            + ", ".join(adapter_result["blocking_reasons"])
        )

    # Phase 582: prove the actual material executor consumes the dedicated
    # SVWT sidecar without assigning any retail material constant register.
    build_vulkan_world_transform_packet(
        {
            "world_matrix": [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.10, 0.0, 0.0, 1.0,
            ]
        },
        bundle_dir / "world_transform.svwt",
    )

    result = run_bmw_vulkan_bundle(
        bundle_dir,
        executable=args.executable,
        validation=args.validation,
        validator=args.validator,
        output=bundle_dir / "bundle.ppm",
    )
    (root / "smoke_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    if result["status"] != "rendered":
        raise SystemExit(2)
    if result["native"].get("world_transform_present") is not True:
        raise SystemExit("material executor did not observe SVWT")
    if result["native"].get("world_transform_executed") is not True:
        raise SystemExit("material executor did not execute SVWT translation")
    if result["native"].get("world_translation_xyz") != [0.1, 0, 0]:
        raise SystemExit("material executor reported unexpected SVWT translation")
    output = Path(result["native"]["output"])
    if output.read_bytes()[:2] != b"P6":
        raise SystemExit("not a PPM")

    # Phase 584: execute a real semantic-aware affine SVWT over POSITION,
    # NORMAL, TANGENT and TANGENT2. The linear part combines a 90-degree
    # rotation with non-uniform positive scale, so normal and tangent probes
    # diverge unless inverse-transpose handling is correct.
    affine_bundle_dir = root / "affine_bundle"
    affine_slice = {
        "format": "SHIFT.BMWRealMaterialSlice/1",
        "render_command": affine_render_command(),
        "mesh": affine_mesh(),
    }
    affine_adapter = build_bmw_vulkan_from_material_slice(
        affine_slice,
        affine_bundle_dir,
        textures={"1": texture()},
        environment_cube=cube(),
    )
    if not affine_adapter["ready"]:
        raise SystemExit(
            "affine material-slice adapter blocked: "
            + ", ".join(affine_adapter["blocking_reasons"])
        )
    build_vulkan_world_transform_packet(
        {
            "world_matrix": [
                0.0, 2.0, 0.0, 0.0,
                -3.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 4.0, 0.0,
                10.0, 20.0, 30.0, 1.0,
            ]
        },
        affine_bundle_dir / "world_transform.svwt",
    )
    affine_result = run_bmw_vulkan_bundle(
        affine_bundle_dir,
        executable=args.executable,
        validation=args.validation,
        validator=args.validator,
        output=affine_bundle_dir / "affine.ppm",
    )
    (root / "affine_result.json").write_text(
        json.dumps(
            affine_result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    if affine_result["status"] != "rendered":
        raise SystemExit("affine material executor did not render")
    affine_native = affine_result["native"]
    if affine_native.get("world_transform_mode") != "semantic-affine-svgp-v3":
        raise SystemExit("affine executor did not report semantic SVGP v3 mode")
    if not math.isclose(
        float(affine_native.get("world_transform_determinant")),
        24.0,
        rel_tol=0.0,
        abs_tol=1.0e-5,
    ):
        raise SystemExit("affine executor reported wrong determinant")
    if affine_native.get("world_transform_properties") != [200, 220, 240, 250]:
        raise SystemExit("affine executor transformed unexpected semantics")
    probes = affine_native.get("world_transform_probe") or {}

    def assert_vec3(name, expected):
        actual = probes.get(name)
        if not isinstance(actual, list) or len(actual) != 3:
            raise SystemExit(f"missing affine {name} probe")
        if any(
            not math.isclose(
                float(value),
                float(target),
                rel_tol=0.0,
                abs_tol=2.0e-4,
            )
            for value, target in zip(actual, expected)
        ):
            raise SystemExit(
                f"affine {name} probe mismatch: {actual} != {expected}"
            )

    assert_vec3("position", [10.0, 22.0, 30.0])
    assert_vec3(
        "normal",
        [-0.5547001962, 0.8320502943, 0.0],
    )
    assert_vec3(
        "tangent",
        [-0.8320502943, 0.5547001962, 0.0],
    )
    assert_vec3("tangent2", [0.0, 0.0, 1.0])

    bundle_set_dir = root / "bundle_set"
    multi_material_slice = {
        "format": "SHIFT.BMWRealMaterialSlice/1",
        "render_command": multidraw_command(),
        "mesh": multidraw_mesh(),
    }
    material_set = build_bmw_vulkan_set_from_material_slice(
        multi_material_slice,
        bundle_set_dir,
        textures={"1": texture()},
        environment_cube=cube(),
    )
    bundle_set = material_set["bundle_set"]
    if not bundle_set["ready"]:
        raise SystemExit(
            "bundle-set preparation blocked: "
            + ", ".join(bundle_set["blocking_reasons"])
        )
    set_prepare = prepare_bmw_vulkan_bundle_set(
        bundle_set_dir,
        validator=args.validator,
    )
    (root / "multidraw_prepare.json").write_text(
        json.dumps(set_prepare, ensure_ascii=False, indent=2, sort_keys=True)
        + chr(10),
        encoding="utf-8",
    )
    if not set_prepare["ready"] or set_prepare["draw_count"] != 2:
        raise SystemExit(
            "bundle-set compile/interface preparation failed: "
            + ", ".join(set_prepare["blocking_reasons"])
        )

    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "output": str(output),
        "output_bytes": output.stat().st_size,
        "bundle_set_prepare_format": set_prepare["format"],
        "bundle_set_draws": set_prepare["draw_count"],
        "world_transform_executed": True,
        "affine_world_transform_executed": True,
        "affine_world_transform_properties": [200, 220, 240, 250],
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
