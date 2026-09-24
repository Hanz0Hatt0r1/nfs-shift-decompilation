"""Pure-Python desktop reference rasterizer for SHIFT mesh IR.

This is a geometry oracle, not the final material renderer. It consumes neutral
MEB JSON (or an equivalent mesh dictionary) and produces deterministic PPM output
without reading BFF archives or invoking the original game runtime.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import hashlib
from pathlib import Path
from typing import Any, Iterable

from render_command import validate_render_command
from skinned_reference import skin_mesh_reference
from static_draw import build_static_draw_contract
from texture_reference import sample_texture_2d
from shader_reference import (
    ReferenceShaderState,
    material_constants_from_payload,
    material_constants_from_uniform_binding,
    shader_program_from_ir,
    validate_pixel_program_inputs,
    validate_vertex_program_inputs,
)


RGBA = tuple[int, int, int, int]


def _mat4_vec4(m: list[list[float]], v: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    return tuple(sum(float(m[r][c]) * v[c] for c in range(4)) for r in range(4))  # type: ignore[return-value]


def _bounds(vertices: list[tuple[float, float, float]]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def orthographic_mvp(
    vertices: Iterable[Iterable[float]],
    *,
    padding: float = 0.08,
    near: float = -1.0,
    far: float = 1.0,
) -> list[list[float]]:
    verts = [tuple(float(x) for x in v) for v in vertices]
    if not verts:
        raise ValueError("cannot build MVP for empty vertex set")
    lo, hi = _bounds(verts)
    cx = (lo[0] + hi[0]) * 0.5
    cy = (lo[1] + hi[1]) * 0.5
    cz = (lo[2] + hi[2]) * 0.5
    sx = max(hi[0] - lo[0], 1.0e-6)
    sy = max(hi[1] - lo[1], 1.0e-6)
    sz = max(hi[2] - lo[2], 1.0e-6)
    scale = max(sx, sy)
    scale *= 1.0 + max(0.0, padding)
    return [
        [2.0 / scale, 0.0, 0.0, -2.0 * cx / scale],
        [0.0, 2.0 / scale, 0.0, -2.0 * cy / scale],
        [0.0, 0.0, 2.0 / max(sz, 1.0e-6), -2.0 * cz / max(sz, 1.0e-6)],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _project(
    vertices: list[tuple[float, ...]],
    mvp: list[list[float]],
    width: int,
    height: int,
) -> list[tuple[float, float, float, float]]:
    out = []
    for v in vertices:
        w = float(v[3]) if len(v) >= 4 else 1.0
        clip = _mat4_vec4(mvp, (float(v[0]), float(v[1]), float(v[2]), w))
        if abs(clip[3]) <= 1.0e-12:
            out.append((math.nan, math.nan, math.nan, clip[3]))
            continue
        inv_w = 1.0 / clip[3]
        ndc = (clip[0] * inv_w, clip[1] * inv_w, clip[2] * inv_w)
        sx = (ndc[0] * 0.5 + 0.5) * (width - 1)
        sy = (1.0 - (ndc[1] * 0.5 + 0.5)) * (height - 1)
        sz = ndc[2] * 0.5 + 0.5
        out.append((sx, sy, sz, clip[3]))
    return out


def _edge(a: tuple[float, float], b: tuple[float, float], p: tuple[float, float]) -> float:
    return (p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])


def _vertex_color(colors: list[RGBA], index: int) -> RGBA:
    if index >= len(colors):
        return (210, 210, 210, 255)
    c = colors[index]
    if len(c) != 4:
        return (210, 210, 210, 255)
    return tuple(max(0, min(255, int(x))) for x in c)  # type: ignore[return-value]



def _register_index(register: Any) -> int:
    match = re.search(r"(\d+)$", str(register))
    if not match:
        raise ValueError(f"shader register has no numeric index: {register}")
    return int(match.group(1))


def _semantic_key(item: dict[str, Any]) -> tuple[str, int]:
    return (str(item.get("usage") or "").upper(), int(item.get("index", 0)))


def _execute_vertex_program(
    program,
    vertices: list[tuple[float, ...]],
    layer_rows: dict[int, list[tuple[float, ...]]],
    semantic_data: dict[tuple[str, int], list[tuple[float, ...]]],
    *,
    shader_constants: dict[str, dict[int, Iterable[float]]] | None,
) -> tuple[
    list[tuple[float, float, float, float]],
    list[dict[tuple[str, int], tuple[float, float, float, float]]],
]:
    validation = validate_vertex_program_inputs(
        program,
        available_semantics=semantic_data.keys(),
    )
    if not validation["valid"]:
        raise ValueError(
            "vertex shader input contract is not supported: "
            + ", ".join(validation["blocking_reasons"])
        )

    output_items: dict[tuple[str, int], dict[str, Any]] = {}
    for item in program.outputs:
        key = _semantic_key(item)
        if key in output_items:
            raise ValueError(
                f"vertex shader has duplicate output semantic: {key[0]}{key[1]}"
            )
        output_items[key] = item

    position_item = output_items.get(("POSITION", 0))
    if position_item is None:
        raise ValueError("vertex shader has no POSITION0 output")

    clip_positions: list[tuple[float, float, float, float]] = []
    varying_results: list[dict[tuple[str, int], tuple[float, float, float, float]]] = []

    for vertex_index, vertex in enumerate(vertices):
        shader_inputs: dict[int, tuple[float, float, float, float]] = {}
        for item in program.inputs:
            register = _register_index(item.get("register"))
            semantic = _semantic_key(item)
            usage, semantic_index = semantic

            if usage == "POSITION" and semantic_index == 0:
                values = list(vertex[:3])
                while len(values) < 3:
                    values.append(0.0)
                shader_inputs[register] = (values[0], values[1], values[2], 1.0)
                continue

            if usage == "TEXCOORD" and 0 <= semantic_index <= 4:
                layer = layer_rows.get(semantic_index)
                if layer is None:
                    layer = semantic_data.get(semantic)
            elif usage in {
                "NORMAL", "TANGENT", "BINORMAL", "BLENDWEIGHT", "BLENDINDICES"
            } and semantic_index == 0:
                layer = semantic_data.get(semantic)
            else:
                layer = semantic_data.get(semantic)

            if layer is None:
                raise ValueError(
                    f"vertex shader requires {usage}{semantic_index} but mesh has no matching attribute"
                )
            row = layer[vertex_index]
            values = list(row[:4])
            while len(values) < 3:
                values.append(0.0)
            shader_inputs[register] = (
                values[0],
                values[1],
                values[2],
                values[3] if len(values) > 3 else 1.0,
            )

        execution = ReferenceShaderState(
            program,
            inputs=shader_inputs,
            constants=shader_constants,
        ).execute()
        if execution["status"] != "executed":
            raise ValueError(
                "vertex shader execution failed: "
                + ", ".join(execution.get("blocking_reasons", []) or ["unknown failure"])
            )

        outputs = execution.get("outputs") or {}
        position_register = _register_index(position_item.get("register"))
        position = outputs.get(str(position_register))
        if position is None:
            raise ValueError(
                f"vertex shader did not write POSITION0 register {position_register}"
            )
        if len(position) != 4 or not all(math.isfinite(float(x)) for x in position):
            raise ValueError("vertex shader produced a non-finite POSITION0")
        clip_positions.append(tuple(float(x) for x in position))

        semantics: dict[tuple[str, int], tuple[float, float, float, float]] = {}
        for key, item in output_items.items():
            if key == ("POSITION", 0):
                continue
            register = _register_index(item.get("register"))
            value = outputs.get(str(register))
            if value is None:
                raise ValueError(
                    f"vertex shader did not write output register {register} for "
                    f"{key[0]}{key[1]}"
                )
            semantics[key] = tuple(float(x) for x in value)
        varying_results.append(semantics)

    return clip_positions, varying_results


def _interp_varying(
    values: tuple[
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
    ],
    projected: tuple[
        tuple[float, float, float, float],
        tuple[float, float, float, float],
        tuple[float, float, float, float],
    ],
    weights: tuple[float, float, float],
) -> tuple[float, float, float, float]:
    denominator = 0.0
    numerator = [0.0, 0.0, 0.0, 0.0]
    for value, point, weight in zip(values, projected, weights):
        clip_w = float(point[3])
        if abs(clip_w) <= 1.0e-12:
            raise ValueError("cannot interpolate varying with zero clip-space w")
        factor = weight / clip_w
        denominator += factor
        for component in range(4):
            numerator[component] += value[component] * factor
    if abs(denominator) <= 1.0e-12:
        raise ValueError("cannot interpolate varying with zero perspective denominator")
    return tuple(component / denominator for component in numerator)



def rasterize_textured_mesh(
    vertices: Iterable[Iterable[float]],
    indices: Iterable[int],
    uvs: Iterable[Iterable[float]],
    image: dict[str, Any],
    *,
    width: int = 512,
    height: int = 512,
    mvp: list[list[float]] | None = None,
    sampler: dict[str, Any] | None = None,
    clear: RGBA = (12, 12, 12, 255),
    pixel_program: dict[str, Any] | None = None,
    shader_constants: dict[str, dict[int, Iterable[float]]] | None = None,
    texture_images: dict[int, dict[str, Any]] | None = None,
    samplers_by_sampler: dict[int, dict[str, Any]] | None = None,
    uv_layers: dict[str | int, Iterable[Iterable[float]]] | None = None,
    semantic_rows: dict[tuple[str, int], Iterable[Iterable[float]]] | None = None,
    vertex_program: dict[str, Any] | None = None,
    external_texture_images: dict[int, dict[str, Any]] | None = None,
    external_texture_resources: dict[int, dict[str, Any]] | None = None,
) -> bytes:
    """Rasterize one UV-mapped RGBA8 texture as a deterministic material oracle."""
    if width <= 0 or height <= 0:
        raise ValueError("render target dimensions must be positive")
    verts = [tuple(float(x) for x in v) for v in vertices]
    idx = [int(x) for x in indices]
    uv_rows = [tuple(float(x) for x in uv) for uv in uvs]
    if len(uv_rows) != len(verts):
        raise ValueError("UV vertex count must match vertex count")
    uv_candidates: dict[int, dict[int, list[tuple[float, ...]]]] = {}
    for key, rows in (uv_layers or {}).items():
        try:
            layer_id = int(str(key))
        except (TypeError, ValueError):
            raise ValueError(f"invalid UV layer key {key!r}")
        if 130 <= layer_id <= 134 or 230 <= layer_id <= 234:
            semantic_index = layer_id - 130 if layer_id < 200 else layer_id - 230
            parsed = [tuple(float(x) for x in row) for row in rows]
            if len(parsed) != len(verts):
                raise ValueError(
                    f"UV layer {layer_id} vertex count {len(parsed)} != {len(verts)}"
                )
            uv_candidates.setdefault(semantic_index, {})[layer_id] = parsed

    layer_rows: dict[int, list[tuple[float, ...]]] = {}
    for semantic_index, candidates in sorted(uv_candidates.items()):
        property_ids = sorted(candidates)
        if len(property_ids) > 1:
            raise ValueError(
                f"TEXCOORD{semantic_index} has conflicting MEB UV families: "
                + " and ".join(str(value) for value in property_ids)
            )
        layer_rows[semantic_index] = candidates[property_ids[0]]

    if 0 not in layer_rows:
        layer_rows[0] = uv_rows
    if any(len(uv) < 2 for uv in uv_rows):
        raise ValueError("each UV row must contain at least two components")
    semantic_data = {
        key: [tuple(float(x) for x in row) for row in rows]
        for key, rows in (semantic_rows or {}).items()
        if rows
    }
    for key, rows in semantic_data.items():
        if len(rows) != len(verts):
            raise ValueError(
                f"semantic layer {key!r} vertex count {len(rows)} != {len(verts)}"
            )
    if len(idx) % 3:
        raise ValueError("triangle index buffer length must be divisible by three")
    if any(i < 0 or i >= len(verts) for i in idx):
        raise ValueError("triangle index exceeds vertex count")

    vertex_shader = None
    vertex_varyings: list[dict[tuple[str, int], tuple[float, float, float, float]]] | None = None
    if vertex_program is not None:
        vertex_shader = shader_program_from_ir(vertex_program)
        clip_vertices, vertex_varyings = _execute_vertex_program(
            vertex_shader,
            [tuple(v) for v in verts],
            layer_rows,
            semantic_data,
            shader_constants=shader_constants,
        )
        projected = _project(clip_vertices, _identity4(), width, height)
    else:
        matrix = mvp or orthographic_mvp(verts)
        projected = _project(verts, matrix, width, height)
    pixels = bytearray(clear * (width * height))
    depth = [float("inf")] * (width * height)

    shader = None
    shader_textures = {
        int(k): v
        for k, v in (texture_images if texture_images is not None else {0: image}).items()
    }
    for register, external_image in (external_texture_images or {}).items():
        shader_textures[int(register)] = external_image
    for register, external_resource in (external_texture_resources or {}).items():
        shader_textures[int(register)] = external_resource
    shader_samplers = {
        int(k): dict(v)
        for k, v in (samplers_by_sampler or ({0: sampler or {}})).items()
    }
    if pixel_program is not None:
        shader = shader_program_from_ir(pixel_program)
        available_pixel_semantics = set(semantic_data)
        if vertex_shader is not None:
            available_pixel_semantics.update(
                _semantic_key(output) for output in vertex_shader.outputs
            )
        input_validation = validate_pixel_program_inputs(
            shader,
            available_semantics=available_pixel_semantics,
        )
        if not input_validation["valid"]:
            raise ValueError(
                "pixel shader input contract is not supported: "
                + ", ".join(input_validation["blocking_reasons"])
            )
        missing_samplers = [int(x) for x in shader.samplers if int(x) not in shader_textures]
        if missing_samplers:
            raise ValueError(
                "pixel shader reference path missing texture images for samplers: "
                + ", ".join(f"s{x}" for x in missing_samplers)
            )
        preflight_inputs = {}
        for item in shader.inputs:
            register = _register_index(item.get("register"))
            semantic = _semantic_key(item)
            if vertex_varyings is not None:
                matches = [
                    output
                    for output in (vertex_shader.outputs if vertex_shader is not None else [])
                    if _semantic_key(output) == semantic
                ]
                if not matches:
                    raise ValueError(
                        f"pixel shader semantic has no matching vertex output: {semantic[0]}{semantic[1]}"
                    )
                sample = vertex_varyings[0].get(semantic)
                if sample is None:
                    raise ValueError(
                        f"vertex shader did not produce pixel semantic: {semantic[0]}{semantic[1]}"
                    )
                preflight_inputs[register] = sample
                continue
            usage, semantic_index = semantic
            layer = (
                layer_rows.get(semantic_index)
                if usage == "TEXCOORD"
                else None
            )
            if layer is None:
                layer = semantic_data.get(semantic)
            if layer is None:
                target = "UV layer" if usage == "TEXCOORD" else "attribute"
                raise ValueError(
                    f"pixel shader requires {usage}{semantic_index} but mesh has no matching {target}"
                )
            row = layer[0]
            values = list(row[:3])
            while len(values) < 3:
                values.append(0.0)
            preflight_inputs[register] = tuple(values[:3] + [1.0])
        preflight = ReferenceShaderState(
            shader,
            inputs=preflight_inputs,
            constants=shader_constants,
            textures=shader_textures,
            samplers=shader_samplers,
        ).execute()
        if preflight["status"] != "executed":
            raise ValueError(
                "pixel shader preflight failed: "
                + ", ".join(preflight["blocking_reasons"])
            )

    for base in range(0, len(idx), 3):
        ia, ib, ic = idx[base:base + 3]
        a, b, c = projected[ia], projected[ib], projected[ic]
        if not all(math.isfinite(x) for q in (a, b, c) for x in q[:3]):
            continue
        p0 = (a[0], a[1]); p1 = (b[0], b[1]); p2 = (c[0], c[1])
        area = _edge(p0, p1, p2)
        if abs(area) <= 1.0e-12:
            continue
        min_x = max(0, int(math.floor(min(p0[0], p1[0], p2[0]))))
        max_x = min(width - 1, int(math.ceil(max(p0[0], p1[0], p2[0]))))
        min_y = max(0, int(math.floor(min(p0[1], p1[1], p2[1]))))
        max_y = min(height - 1, int(math.ceil(max(p0[1], p1[1], p2[1]))))
        inv_area = 1.0 / area
        for y in range(min_y, max_y + 1):
            py = y + 0.5
            for x in range(min_x, max_x + 1):
                px = x + 0.5
                p = (px, py)
                w0 = _edge(p1, p2, p) * inv_area
                w1 = _edge(p2, p0, p) * inv_area
                w2 = _edge(p0, p1, p) * inv_area
                if w0 < -1.0e-7 or w1 < -1.0e-7 or w2 < -1.0e-7:
                    continue
                z = w0 * a[2] + w1 * b[2] + w2 * c[2]
                offset = y * width + x
                if z >= depth[offset]:
                    continue
                u = w0 * uv_rows[ia][0] + w1 * uv_rows[ib][0] + w2 * uv_rows[ic][0]
                v = w0 * uv_rows[ia][1] + w1 * uv_rows[ib][1] + w2 * uv_rows[ic][1]
                if shader is None:
                    color = sample_texture_2d(image, u, v, sampler)
                else:
                    shader_inputs = {}
                    for item in shader.inputs:
                        register = _register_index(item.get("register"))
                        semantic = _semantic_key(item)
                        if vertex_varyings is not None:
                            varying_values = (
                                vertex_varyings[ia].get(semantic),
                                vertex_varyings[ib].get(semantic),
                                vertex_varyings[ic].get(semantic),
                            )
                            if any(value is None for value in varying_values):
                                raise ValueError(
                                    f"pixel shader semantic has no complete vertex varying: {semantic[0]}{semantic[1]}"
                                )
                            shader_inputs[register] = _interp_varying(
                                varying_values,
                                (a, b, c),
                                (w0, w1, w2),
                            )
                            continue
                        usage, semantic_index = semantic
                        layer = (
                            layer_rows.get(semantic_index)
                            if usage == "TEXCOORD"
                            else None
                        )
                        if layer is None:
                            layer = semantic_data.get(semantic)
                        if layer is None:
                            target = "UV layer" if usage == "TEXCOORD" else "attribute"
                            raise ValueError(
                                f"pixel shader requires {usage}{semantic_index} but mesh has no matching {target}"
                            )
                        samples = (layer[ia], layer[ib], layer[ic])
                        sample_width = min(4, max(len(row) for row in samples))
                        values = []
                        for channel in range(sample_width):
                            values.append(
                                w0 * (samples[0][channel] if channel < len(samples[0]) else 0.0)
                                + w1 * (samples[1][channel] if channel < len(samples[1]) else 0.0)
                                + w2 * (samples[2][channel] if channel < len(samples[2]) else 0.0)
                            )
                        while len(values) < 3:
                            values.append(0.0)
                        shader_inputs[register] = tuple(values[:3] + [1.0])
                    execution = ReferenceShaderState(
                        shader,
                        inputs=shader_inputs,
                        constants=shader_constants,
                        textures=shader_textures,
                        samplers=shader_samplers,
                    ).execute()
                    if execution["status"] != "executed" or execution.get("color") is None:
                        reasons = execution.get("blocking_reasons", []) or [
                            "pixel shader produced no color"
                        ]
                        raise ValueError("pixel shader execution failed: " + ", ".join(reasons))
                    color = execution["color"]
                depth[offset] = z
                pixels[offset * 4:offset * 4 + 4] = bytes(
                    max(0, min(255, int(round(component * 255.0))))
                    for component in color
                )

    rgb = bytearray()
    for i in range(width * height):
        rgb.extend(pixels[i * 4:i * 4 + 3])
    return b"P6\n%d %d\n255\n" % (width, height) + bytes(rgb)


def render_textured_static_draw(
    draw: dict[str, Any],
    mesh: dict[str, Any],
    image: dict[str, Any],
    output: str | Path,
    *,
    sampler: dict[str, Any] | None = None,
    width: int = 512,
    height: int = 512,
    mvp: list[list[float]] | None = None,
    pixel_program: dict[str, Any] | None = None,
    shader_constants: dict[str, dict[int, Iterable[float]]] | None = None,
    texture_images: dict[int, dict[str, Any]] | None = None,
    samplers_by_sampler: dict[int, dict[str, Any]] | None = None,
    semantic_rows: dict[tuple[str, int], Iterable[Iterable[float]]] | None = None,
    vertex_program: dict[str, Any] | None = None,
    external_texture_images: dict[int, dict[str, Any]] | None = None,
    external_texture_resources: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Render a validated StaticDraw, optionally executing the embedded vertex shader."""
    if draw.get("format") != "SHIFT.StaticDraw/1":
        raise ValueError("draw packet is not SHIFT.StaticDraw/1")
    if not draw.get("ready", False):
        raise ValueError(
            "draw packet is not ready: " + ", ".join(draw.get("blocking_reasons", []))
        )
    uv_layers = mesh.get("uv_layers") or {}
    uvs = (
        uv_layers.get("130")
        or uv_layers.get(130)
        or uv_layers.get("230")
        or uv_layers.get(230)
        or mesh.get("uvs")
        or []
    )
    if not uvs:
        raise ValueError("mesh has no UV0 (property 130 or 230)")
    vertices = mesh.get("vertices") or []
    indices = mesh.get("indices") or []
    draw_indices: list[int] = []
    for submesh in draw.get("submeshes", []) or []:
        first = int(submesh.get("first_index", 0))
        count = int(submesh.get("index_count", 0))
        if first < 0 or count < 0 or first + count > len(indices):
            raise ValueError(
                f"submesh index range out of bounds: first={first} count={count} indices={len(indices)}"
            )
        if count % 3:
            raise ValueError("submesh index_count must be divisible by three")
        draw_indices.extend(int(x) for x in indices[first:first + count])
    if not draw.get("submeshes"):
        draw_indices = [int(x) for x in indices]

    if vertex_program is None:
        world = _coerce_matrix(draw.get("world_matrix")) or _identity4()
        base_mvp = mvp or orthographic_mvp(vertices)
        final_mvp = _mat4_mul(base_mvp, world)
    else:
        final_mvp = _identity4()
    image_bytes = rasterize_textured_mesh(
        vertices,
        draw_indices,
        uvs,
        image,
        width=width,
        height=height,
        mvp=final_mvp,
        sampler=sampler,
        pixel_program=pixel_program,
        shader_constants=shader_constants,
        texture_images=texture_images,
        samplers_by_sampler=samplers_by_sampler,
        uv_layers=uv_layers,
        semantic_rows=semantic_rows,
        vertex_program=vertex_program,
        external_texture_images=external_texture_images,
        external_texture_resources=external_texture_resources,
    )
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(image_bytes)
    return {
        "format": "SHIFT.TexturedStaticDrawReference/1",
        "output": str(out),
        "width": width,
        "height": height,
        "vertex_count": len(vertices),
        "triangle_count": len(draw_indices) // 3,
        "texture_format": image.get("source_format"),
        "world_matrix_applied": vertex_program is None,
        "vertex_shader_executed": vertex_program is not None,
    }


def render_textured_render_command(
    command: dict[str, Any],
    mesh: dict[str, Any],
    image: dict[str, Any],
    output: str | Path,
    *,
    sampler: dict[str, Any] | None = None,
    width: int = 512,
    height: int = 512,
    mvp: list[list[float]] | None = None,
    shader_reference: bool = False,
    shader_constants: dict[str, dict[int, Iterable[float]]] | None = None,
    texture_images: dict[int, dict[str, Any]] | None = None,
    samplers_by_sampler: dict[int, dict[str, Any]] | None = None,
    external_texture_images: dict[int, dict[str, Any]] | None = None,
    external_texture_resources: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute a RenderCommand through the one-texture reference material path."""
    from render_command import validate_render_command

    validation = validate_render_command(command)
    if not validation["valid"]:
        raise ValueError(
            "render command is not valid: " + ", ".join(validation["blocking_reasons"])
        )
    if not command.get("ready", False):
        raise ValueError(
            "render command is not ready: " + ", ".join(command.get("blocking_reasons", []))
        )

    draw = {
        "format": "SHIFT.StaticDraw/1",
        "ready": True,
        "blocking_reasons": [],
        "world_matrix": command.get("world_matrix"),
        "submeshes": command.get("submeshes", []),
    }
    if sampler is None:
        sampler = {}
        for submesh in command.get("submeshes", []) or []:
            for texture in submesh.get("textures", []) or []:
                if texture.get("resource") != "external":
                    sampler = texture.get("sampler_state") or {}
                    if sampler:
                        break
            if sampler:
                break
    vertex_program = None
    pixel_program = None
    effective_texture_images = (
        {int(k): v for k, v in (texture_images or {}).items()}
        if texture_images is not None
        else None
    )
    external_requirements: dict[int, dict[str, Any]] = {}
    if shader_reference:
        programs = [
            (submesh.get("shader") or {}).get("vertex_program")
            for submesh in command.get("submeshes", []) or []
        ]
        vertex_program = next((program for program in programs if program), None)
        programs = [
            (submesh.get("shader") or {}).get("pixel_program")
            for submesh in command.get("submeshes", []) or []
        ]
        pixel_program = next((program for program in programs if program), None)
        if pixel_program is None:
            raise ValueError("RenderCommand has no embedded pixel_program for shader reference")

        external_requirements: dict[int, dict[str, Any]] = {}
        material_registers: set[int] = set()
        for submesh in command.get("submeshes", []) or []:
            for texture in submesh.get("textures", []) or []:
                if texture.get("resource") == "external":
                    continue
                register = texture.get("d3d9_sampler_register")
                if register is not None:
                    material_registers.add(int(register))
            for external in submesh.get("external_samplers", []) or []:
                register = external.get("d3d9_sampler_register")
                try:
                    register_value = int(register)
                except (TypeError, ValueError):
                    raise ValueError("RenderCommand external sampler has invalid register")
                sampler_type = str(external.get("sampler_type") or "").strip()
                existing = external_requirements.get(register_value)
                row = {
                    "sampler": external.get("sampler"),
                    "d3d9_sampler_register": register_value,
                    "sampler_type": sampler_type,
                }
                if existing is not None and existing != row:
                    raise ValueError(
                        f"RenderCommand has conflicting external sampler requirements for s{register_value}"
                    )
                external_requirements[register_value] = row
        overlap = sorted(material_registers.intersection(external_requirements))
        if overlap:
            raise ValueError(
                "RenderCommand has material/external sampler register collision: "
                + ", ".join(f"s{x}" for x in overlap)
            )
        shader_sampler_types = {
            int(register): str(sampler_type)
            for register, sampler_type in pixel_program.get("sampler_types", {}).items()
        }
        for register, requirement in sorted(external_requirements.items()):
            declared_type = shader_sampler_types.get(register)
            required_type = requirement["sampler_type"]
            if declared_type is not None and declared_type != required_type:
                raise ValueError(
                    f"external sampler s{register} type mismatch: "
                    f"RenderCommand={required_type} shader={declared_type}"
                )
            if required_type not in {"sampler2D", "samplerCube"}:
                raise ValueError(
                    f"external sampler s{register} ({required_type}) requires a dedicated reference resource implementation"
                )
            if required_type == "samplerCube":
                resource = (external_texture_resources or {}).get(register)
                if resource is None and register in (external_texture_images or {}):
                    raise ValueError(
                        f"external sampler s{register} requires ReferenceCubeTexture/1 resource"
                    )
        if effective_texture_images is None:
            effective_texture_images = {}
        if not effective_texture_images:
            legacy_register = None
            for submesh in command.get("submeshes", []) or []:
                for texture in submesh.get("textures", []) or []:
                    if texture.get("resource") == "external":
                        continue
                    register = texture.get("d3d9_sampler_register")
                    if register is not None:
                        legacy_register = int(register)
                        break
                if legacy_register is not None:
                    break
            if legacy_register is None and 0 not in external_requirements:
                legacy_register = 0
            if legacy_register is not None:
                effective_texture_images[legacy_register] = image
        for register, external_image in (external_texture_images or {}).items():
            register_value = int(register)
            if register_value in material_registers:
                raise ValueError(
                    f"external texture image s{register_value} collides with material texture"
                )
            effective_texture_images[register_value] = external_image
        if shader_constants is None:
            for submesh in command.get("submeshes", []) or []:
                payload = submesh.get("constant_payload")
                if payload is not None:
                    constant_result = material_constants_from_payload(payload)
                    if constant_result["status"] == "unsupported":
                        raise ValueError(
                            "material constant payload unsupported: "
                            + ", ".join(constant_result["blocking_reasons"])
                        )
                    shader_constants = constant_result["banks"]
                    break
                uniforms = submesh.get("uniforms") or {}
                if uniforms.get("bindings"):
                    constant_result = material_constants_from_uniform_binding(uniforms)
                    if constant_result["status"] == "unsupported":
                        raise ValueError(
                            "material constant reference unsupported: "
                            + ", ".join(constant_result["blocking_reasons"])
                        )
                    shader_constants = constant_result["banks"]
                    break
    if shader_reference and samplers_by_sampler is None:
        samplers_by_sampler = {}
        for submesh in command.get("submeshes", []) or []:
            for texture in submesh.get("textures", []) or []:
                register = texture.get("d3d9_sampler_register")
                if register is None:
                    continue
                samplers_by_sampler[int(register)] = texture.get("sampler_state") or {}
    result = render_textured_static_draw(
        draw,
        mesh,
        image,
        output,
        sampler=sampler,
        width=width,
        height=height,
        mvp=mvp,
        pixel_program=pixel_program,
        shader_constants=shader_constants,
        texture_images=effective_texture_images,
        samplers_by_sampler=samplers_by_sampler,
        vertex_program=vertex_program,
        external_texture_images=None,
        external_texture_resources=external_texture_resources,
        semantic_rows={
            key: rows
            for key, rows in {
                ("NORMAL", 0): mesh.get("normals"),
                ("TANGENT", 0): mesh.get("tangents"),
                ("BINORMAL", 0): mesh.get("tangents2"),
                ("BLENDWEIGHT", 0): mesh.get("bone_weights"),
                ("BLENDINDICES", 0): mesh.get("bone_indices"),
            }.items()
            if rows
        },
    )
    result["external_sampler_requirements"] = [
        row for _, row in sorted(external_requirements.items())
    ] if shader_reference else []
    result["command_contract"] = {
        "format": command.get("format"),
        "ready": command.get("ready"),
        "validation": validation,
    }
    return result

def rasterize_mesh(
    vertices: Iterable[Iterable[float]],
    indices: Iterable[int],
    *,
    colors: Iterable[Iterable[int]] = (),
    width: int = 512,
    height: int = 512,
    mvp: list[list[float]] | None = None,
    clear: RGBA = (12, 12, 12, 255),
) -> bytes:
    if width <= 0 or height <= 0:
        raise ValueError("render target dimensions must be positive")
    verts = [tuple(float(x) for x in v) for v in vertices]
    idx = [int(x) for x in indices]
    if len(idx) % 3:
        raise ValueError("triangle index buffer length must be divisible by three")
    if any(i < 0 or i >= len(verts) for i in idx):
        raise ValueError("triangle index exceeds vertex count")

    matrix = mvp or orthographic_mvp(verts)
    projected = _project(verts, matrix, width, height)
    color_rows = [tuple(int(x) for x in c) for c in colors]
    rgba = [_vertex_color(color_rows, i) for i in range(len(verts))]
    # If no colors were supplied, use deterministic flat gray.
    if not color_rows:
        rgba = [(210, 210, 210, 255)] * len(verts)

    pixels = bytearray(clear * (width * height))
    depth = [float("inf")] * (width * height)

    for base in range(0, len(idx), 3):
        ia, ib, ic = idx[base:base + 3]
        a, b, c = projected[ia], projected[ib], projected[ic]
        if not all(math.isfinite(x) for q in (a, b, c) for x in q[:3]):
            continue
        p0 = (a[0], a[1]); p1 = (b[0], b[1]); p2 = (c[0], c[1])
        area = _edge(p0, p1, p2)
        if abs(area) <= 1.0e-12:
            continue
        min_x = max(0, int(math.floor(min(p0[0], p1[0], p2[0]))))
        max_x = min(width - 1, int(math.ceil(max(p0[0], p1[0], p2[0]))))
        min_y = max(0, int(math.floor(min(p0[1], p1[1], p2[1]))))
        max_y = min(height - 1, int(math.ceil(max(p0[1], p1[1], p2[1]))))
        inv_area = 1.0 / area
        for y in range(min_y, max_y + 1):
            py = y + 0.5
            for x in range(min_x, max_x + 1):
                px = x + 0.5
                p = (px, py)
                w0 = _edge(p1, p2, p) * inv_area
                w1 = _edge(p2, p0, p) * inv_area
                w2 = _edge(p0, p1, p) * inv_area
                if w0 < -1.0e-7 or w1 < -1.0e-7 or w2 < -1.0e-7:
                    continue
                z = w0 * a[2] + w1 * b[2] + w2 * c[2]
                offset = y * width + x
                if z >= depth[offset]:
                    continue
                depth[offset] = z
                color = tuple(
                    int(round(
                        w0 * rgba[ia][k] + w1 * rgba[ib][k] + w2 * rgba[ic][k]
                    ))
                    for k in range(4)
                )
                pixels[offset * 4:offset * 4 + 4] = bytes(color)

    # PPM intentionally drops alpha; desktop image verification is color/depth only.
    rgb = bytearray()
    for i in range(width * height):
        rgb.extend(pixels[i * 4:i * 4 + 3])
    return b"P6\n%d %d\n255\n" % (width, height) + bytes(rgb)



def _mat4_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [
        [sum(float(a[r][k]) * float(b[k][c]) for k in range(4)) for c in range(4)]
        for r in range(4)
    ]


def _identity4() -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _coerce_matrix(value: Any) -> list[list[float]] | None:
    if isinstance(value, (list, tuple)) and len(value) == 4:
        if all(isinstance(row, (list, tuple)) and len(row) == 4 for row in value):
            return [[float(x) for x in row] for row in value]
    if isinstance(value, (list, tuple)) and len(value) == 16:
        vals = [float(x) for x in value]
        return [vals[r * 4:(r + 1) * 4] for r in range(4)]
    return None


def render_static_draw(
    draw: dict[str, Any],
    mesh: dict[str, Any],
    output: str | Path,
    *,
    width: int = 512,
    height: int = 512,
    mvp: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Render a validated SHIFT.StaticDraw/1 packet using neutral mesh data."""
    if draw.get("format") != "SHIFT.StaticDraw/1":
        raise ValueError("draw packet is not SHIFT.StaticDraw/1")
    if not draw.get("ready", False):
        raise ValueError("draw packet is not ready: " + ", ".join(draw.get("blocking_reasons", [])))

    world = _coerce_matrix(draw.get("world_matrix")) or _identity4()
    base_mvp = mvp or orthographic_mvp(mesh.get("vertices") or [])
    final_mvp = _mat4_mul(base_mvp, world)
    vertices = mesh.get("vertices") or []
    indices = mesh.get("indices") or []
    draw_indices: list[int] = []
    for submesh in draw.get("submeshes", []) or []:
        first = int(submesh.get("first_index", 0))
        count = int(submesh.get("index_count", 0))
        if first < 0 or count < 0 or first + count > len(indices):
            raise ValueError(
                f"submesh index range out of bounds: first={first} count={count} indices={len(indices)}"
            )
        if count % 3:
            raise ValueError("submesh index_count must be divisible by three")
        draw_indices.extend(int(x) for x in indices[first:first + count])

    # Legacy/simple draw contracts without submesh metadata still render the full mesh.
    if not (draw.get("submeshes") or []):
        draw_indices = [int(x) for x in indices]

    image = rasterize_mesh(
        vertices,
        draw_indices,
        colors=mesh.get("colors") or [],
        width=width,
        height=height,
        mvp=final_mvp,
    )
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(image)
    return {
        "format": "SHIFT.StaticDrawReference/1",
        "output": str(out),
        "width": width,
        "height": height,
        "vertex_count": len(mesh.get("vertices") or []),
        "triangle_count": len(mesh.get("indices") or []) // 3,
        "world_matrix_applied": True,
    }



def build_static_draw_from_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate a SHIFT.DrawPacket/1 and return its executable StaticDraw/1 contract."""
    if packet.get("schema") != "SHIFT.DrawPacket/1":
        raise ValueError("packet is not SHIFT.DrawPacket/1")
    return build_static_draw_contract(packet)



def render_render_command(
    command: dict[str, Any],
    mesh: dict[str, Any],
    output: str | Path,
    *,
    width: int = 512,
    height: int = 512,
    mvp: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Execute a validated RenderCommand with the geometry-only desktop oracle."""
    validation = validate_render_command(command)
    if not validation["valid"]:
        raise ValueError(
            "render command is not valid: "
            + ", ".join(validation["blocking_reasons"])
        )
    if not command.get("ready", False):
        raise ValueError(
            "render command is not ready: "
            + ", ".join(command.get("blocking_reasons", []))
        )

    vertices = mesh.get("vertices") or []
    indices = mesh.get("indices") or []
    expected_vertices = command.get("mesh", {}).get("vertex_count")
    if expected_vertices is not None and int(expected_vertices) != len(vertices):
        raise ValueError(
            f"mesh vertex count mismatch: command={expected_vertices} actual={len(vertices)}"
        )

    for submesh in command.get("submeshes", []) or []:
        first = int(submesh.get("first_index", 0))
        count = int(submesh.get("index_count", 0))
        if first < 0 or count < 0 or first + count > len(indices):
            raise ValueError(
                f"command index range out of bounds: first={first} count={count} indices={len(indices)}"
            )

    draw = {
        "format": "SHIFT.StaticDraw/1",
        "ready": True,
        "blocking_reasons": [],
        "world_matrix": command.get("world_matrix"),
        "submeshes": command.get("submeshes", []),
    }
    result = render_static_draw(
        draw,
        mesh,
        output,
        width=width,
        height=height,
        mvp=mvp,
    )
    result["command_contract"] = {
        "format": command.get("format"),
        "ready": command.get("ready"),
        "validation": validation,
    }
    return result


def render_render_command_json(
    command_path: str | Path,
    mesh_path: str | Path,
    output: str | Path,
    *,
    width: int = 512,
    height: int = 512,
) -> dict[str, Any]:
    """Render a RenderCommand JSON plus neutral mesh JSON and return a golden hash."""
    command = json.loads(Path(command_path).read_text(encoding="utf-8"))
    mesh = json.loads(Path(mesh_path).read_text(encoding="utf-8"))
    result = render_render_command(
        command,
        mesh,
        output,
        width=width,
        height=height,
    )
    result["sha256"] = hashlib.sha256(Path(output).read_bytes()).hexdigest()
    result["command"] = str(command_path)
    result["mesh"] = str(mesh_path)
    return result


def render_skinned_draw_reference(
    draw: dict[str, Any],
    mesh: dict[str, Any],
    output: str | Path,
    *,
    image: dict[str, Any] | None = None,
    width: int = 512,
    height: int = 512,
    mvp: list[list[float]] | None = None,
    normalize_weights: bool = False,
    strict_indices: bool = True,
    shader_reference: bool = False,
    vertex_program: dict[str, Any] | None = None,
    pixel_program: dict[str, Any] | None = None,
    shader_constants: dict[str, dict[int, Iterable[float]]] | None = None,
    texture_images: dict[int, dict[str, Any]] | None = None,
    samplers_by_sampler: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Render a SkinnedDraw after explicit SkinPose deformation.

    Shader execution is opt-in and uses the same embedded VS→PS reference path
    as RenderCommand textured draws. No animation or bind-pose inference occurs.
    """
    if draw.get("format") != "SHIFT.SkinnedDraw/1":
        raise ValueError("draw packet is not SHIFT.SkinnedDraw/1")

    skinned_mesh = skin_mesh_reference(
        draw,
        mesh,
        normalize_weights=normalize_weights,
        strict_indices=strict_indices,
    )
    static_draw = {
        "format": "SHIFT.StaticDraw/1",
        "ready": True,
        "blocking_reasons": [],
        "world_matrix": None,
        "submeshes": draw.get("submeshes", []) or [],
    }

    if shader_reference:
        if image is None:
            raise ValueError("shader_reference for SkinnedDraw requires an explicit reference image")
        if vertex_program is None or pixel_program is None:
            raise ValueError(
                "shader_reference for SkinnedDraw requires explicit vertex_program and pixel_program"
            )
        result = render_textured_static_draw(
            static_draw,
            skinned_mesh["mesh"],
            image,
            output,
            sampler=None,
            width=width,
            height=height,
            mvp=mvp,
            pixel_program=pixel_program,
            shader_constants=shader_constants,
            texture_images=texture_images,
            samplers_by_sampler=samplers_by_sampler,
            semantic_rows={
                key: rows
                for key, rows in {
                    ("NORMAL", 0): skinned_mesh["mesh"].get("normals"),
                    ("TANGENT", 0): skinned_mesh["mesh"].get("tangents"),
                    ("BINORMAL", 0): skinned_mesh["mesh"].get("tangents2"),
                    ("BLENDWEIGHT", 0): skinned_mesh["mesh"].get("bone_weights"),
                    ("BLENDINDICES", 0): skinned_mesh["mesh"].get("bone_indices"),
                }.items()
                if rows
            },
            vertex_program=vertex_program,
        )
    else:
        result = render_static_draw(
            static_draw,
            skinned_mesh["mesh"],
            output,
            width=width,
            height=height,
            mvp=mvp,
        )

    result["format"] = "SHIFT.SkinnedDrawReference/1"
    result["skinning"] = {
        "format": skinned_mesh["format"],
        "frame": skinned_mesh.get("frame"),
        "vertex_count": skinned_mesh["vertex_count"],
        "influence_validation": skinned_mesh["influence_validation"],
        "streams": skinned_mesh["streams"],
    }
    result["shader_reference"] = bool(shader_reference)
    return result

def render_draw_packet(
    packet: dict[str, Any],
    mesh: dict[str, Any],
    output: str | Path,
    *,
    width: int = 512,
    height: int = 512,
    mvp: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Render one DrawPacket through the validated StaticDraw/1 boundary."""
    draw = build_static_draw_from_packet(packet)
    result = render_static_draw(
        draw,
        mesh,
        output,
        width=width,
        height=height,
        mvp=mvp,
    )
    result["draw_contract"] = {
        "format": draw["format"],
        "ready": draw["ready"],
        "blocking_reasons": draw["blocking_reasons"],
    }
    return result

def render_draw_packet_json(
    packet_path: str | Path,
    mesh_path: str | Path,
    output: str | Path,
    *,
    width: int = 512,
    height: int = 512,
) -> dict[str, Any]:
    """Render a DrawPacket JSON through StaticDraw and return a golden hash."""
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    mesh = json.loads(Path(mesh_path).read_text(encoding="utf-8"))
    result = render_draw_packet(packet, mesh, output, width=width, height=height)
    digest = hashlib.sha256(Path(output).read_bytes()).hexdigest()
    result["sha256"] = digest
    result["packet"] = str(packet_path)
    result["mesh"] = str(mesh_path)
    return result


def render_mesh_json(mesh: dict[str, Any], output: str | Path, *, width: int = 512, height: int = 512) -> dict[str, Any]:
    vertices = mesh.get("vertices") or []
    indices = mesh.get("indices") or []
    colors = mesh.get("colors") or []
    image = rasterize_mesh(vertices, indices, colors=colors, width=width, height=height)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(image)
    return {
        "format": "SHIFT.ReferenceRender/1",
        "output": str(out),
        "width": width,
        "height": height,
        "vertex_count": len(vertices),
        "triangle_count": len(indices) // 3,
        "bytes": len(image),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render neutral SHIFT mesh JSON or a DrawPacket to deterministic PPM")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--mesh", type=Path, help="neutral mesh JSON used with --draw-packet")
    parser.add_argument("--draw-packet", action="store_true", help="treat input as SHIFT.DrawPacket/1 JSON")
    parser.add_argument("--render-command", action="store_true", help="treat input as SHIFT.RenderCommand/1 JSON")
    parser.add_argument("--textured", action="store_true", help="use the UV0 software texture reference path")
    parser.add_argument("--shader-reference", action="store_true", help="execute embedded pixel ShaderProgram/1 in software")
    parser.add_argument("--texture", type=Path, help="legacy DDS file used by --textured")
    parser.add_argument("--texture-binding", action="append", default=[], metavar="SLOT=PATH", help="explicit material sampler DDS mapping, repeatable")
    parser.add_argument("--external-texture-binding", action="append", default=[], metavar="SLOT=PATH", help="explicit external sampler2D DDS mapping, repeatable")
    parser.add_argument("--external-cube-face", action="append", default=[], metavar="SLOT=FACE=PATH", help="explicit samplerCube face DDS mapping, repeatable; FACE is px/nx/py/ny/pz/nz")
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    args = parser.parse_args(argv)
    if args.textured:
        if not args.render_command:
            parser.error("--textured requires --render-command")
        if args.mesh is None or args.texture is None:
            parser.error("--textured requires --mesh and --texture")
        command = json.loads(args.input.read_text(encoding="utf-8"))
        mesh = json.loads(args.mesh.read_text(encoding="utf-8"))
        from texture_reference import decode_dds

        texture_images: dict[int, dict[str, Any]] = {}
        external_texture_images: dict[int, dict[str, Any]] = {}
        external_texture_resources: dict[int, dict[str, Any]] = {}
        external_cube_faces: dict[int, dict[str, dict[str, Any]]] = {}

        def decode_binding(spec: str) -> tuple[int, dict[str, Any]]:
            register_text, separator, path_text = str(spec).partition("=")
            if not separator or not register_text.strip() or not path_text.strip():
                parser.error("expected SAMPLER_REGISTER=TEXTURE.dds")
            try:
                register = int(register_text, 10)
            except ValueError:
                parser.error(f"invalid sampler register: {register_text!r}")
            if register < 0:
                parser.error("sampler register must be non-negative")
            path = Path(path_text)
            if not path.exists():
                parser.error(f"texture file not found: {path}")
            return register, decode_dds(path.read_bytes())

        if args.texture is not None:
            legacy_register = None
            for submesh in command.get("submeshes", []) or []:
                for texture in submesh.get("textures", []) or []:
                    if texture.get("resource") != "external" and texture.get("d3d9_sampler_register") is not None:
                        legacy_register = int(texture["d3d9_sampler_register"])
                        break
                if legacy_register is not None:
                    break
            if legacy_register is None:
                legacy_register = 0
            texture_images[legacy_register] = decode_dds(args.texture.read_bytes())

        for spec in args.texture_binding:
            register, decoded = decode_binding(spec)
            texture_images[register] = decoded

        for spec in args.external_texture_binding:
            register, decoded = decode_binding(spec)
            external_texture_images[register] = decoded

        for spec in args.external_cube_face:
            left, separator, path_text = str(spec).partition("=")
            face_separator = left.rfind("=")
            if not separator or face_separator <= 0 or not path_text.strip():
                parser.error("expected SAMPLER_REGISTER=FACE=TEXTURE.dds")
            register_text = left[:face_separator]
            face = left[face_separator + 1:].strip().lower()
            if face not in {"px", "nx", "py", "ny", "pz", "nz"}:
                parser.error(f"invalid cube face {face!r}; expected px/nx/py/ny/pz/nz")
            try:
                register = int(register_text, 10)
            except ValueError:
                parser.error(f"invalid sampler register: {register_text!r}")
            if register < 0:
                parser.error("sampler register must be non-negative")
            path = Path(path_text)
            if not path.exists():
                parser.error(f"texture file not found: {path}")
            external_cube_faces.setdefault(register, {})[face] = decode_dds(path.read_bytes())

        for register, faces in external_cube_faces.items():
            missing = [face for face in ("px", "nx", "py", "ny", "pz", "nz") if face not in faces]
            if missing:
                parser.error(
                    f"external cube sampler s{register} is missing faces: " + ", ".join(missing)
                )
            external_texture_resources[register] = {
                "format": "SHIFT.ReferenceCubeTexture/1",
                "faces": faces,
            }

        image = next(iter(texture_images.values()), None)
        if image is None:
            image = next(iter(external_texture_images.values()), None)
        if image is None and external_texture_resources:
            image = next(iter(next(iter(external_texture_resources.values()))["faces"].values()))
        if image is None:
            parser.error(
                "--textured requires --texture, --texture-binding, --external-texture-binding, or --external-cube-face"
            )

        result = render_textured_render_command(
            command,
            mesh,
            image,
            args.output,
            width=args.width,
            height=args.height,
            shader_reference=args.shader_reference,
            texture_images=texture_images or None,
            external_texture_images=external_texture_images or None,
            external_texture_resources=external_texture_resources or None,
        )
        result["sha256"] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    elif args.render_command:
        if args.mesh is None:
            parser.error("--render-command requires --mesh")
        result = render_render_command_json(
            args.input,
            args.mesh,
            args.output,
            width=args.width,
            height=args.height,
        )
    elif args.draw_packet:
        if args.mesh is None:
            parser.error("--draw-packet requires --mesh")
        result = render_draw_packet_json(
            args.input,
            args.mesh,
            args.output,
            width=args.width,
            height=args.height,
        )
    else:
        mesh = json.loads(args.input.read_text(encoding="utf-8"))
        result = render_mesh_json(mesh, args.output, width=args.width, height=args.height)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
