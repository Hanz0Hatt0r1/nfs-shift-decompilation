"""Pure-Python desktop reference rasterizer for SHIFT mesh IR.

This is a geometry oracle, not the final material renderer. It consumes neutral
MEB JSON (or an equivalent mesh dictionary) and produces deterministic PPM output
without reading BFF archives or invoking the original game runtime.
"""
from __future__ import annotations

import argparse
import json
import math
import hashlib
from pathlib import Path
from typing import Any, Iterable

from render_command import validate_render_command
from static_draw import build_static_draw_contract
from texture_reference import sample_texture_2d
from shader_reference import ReferenceShaderState, shader_program_from_ir, validate_pixel_program_inputs


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
    vertices: list[tuple[float, float, float]],
    mvp: list[list[float]],
    width: int,
    height: int,
) -> list[tuple[float, float, float, float]]:
    out = []
    for v in vertices:
        clip = _mat4_vec4(mvp, (v[0], v[1], v[2], 1.0))
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
) -> bytes:
    """Rasterize one UV-mapped RGBA8 texture as a deterministic material oracle."""
    if width <= 0 or height <= 0:
        raise ValueError("render target dimensions must be positive")
    verts = [tuple(float(x) for x in v) for v in vertices]
    idx = [int(x) for x in indices]
    uv_rows = [tuple(float(x) for x in uv) for uv in uvs]
    if len(uv_rows) != len(verts):
        raise ValueError("UV vertex count must match vertex count")
    if any(len(uv) < 2 for uv in uv_rows):
        raise ValueError("each UV row must contain at least two components")
    if len(idx) % 3:
        raise ValueError("triangle index buffer length must be divisible by three")
    if any(i < 0 or i >= len(verts) for i in idx):
        raise ValueError("triangle index exceeds vertex count")

    matrix = mvp or orthographic_mvp(verts)
    projected = _project(verts, matrix, width, height)
    pixels = bytearray(clear * (width * height))
    depth = [float("inf")] * (width * height)

    shader = None
    if pixel_program is not None:
        shader = shader_program_from_ir(pixel_program)
        input_validation = validate_pixel_program_inputs(shader)
        if not input_validation["valid"]:
            raise ValueError(
                "pixel shader input contract is not supported: "
                + ", ".join(input_validation["blocking_reasons"])
            )
        if any(int(x) != 0 for x in shader.samplers):
            raise ValueError(
                "pixel shader reference path currently supports only sampler s0"
            )
        preflight = ReferenceShaderState(
            shader,
            inputs={0: (0.0, 0.0, 0.0, 1.0)},
            constants=shader_constants,
            textures={0: image},
            samplers={0: sampler or {}},
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
                    execution = ReferenceShaderState(
                        shader,
                        inputs={0: (u, v, 0.0, 1.0)},
                        constants=shader_constants,
                        textures={0: image},
                        samplers={0: sampler or {}},
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
) -> dict[str, Any]:
    """Render a validated StaticDraw with one explicit UV0 texture input."""
    if draw.get("format") != "SHIFT.StaticDraw/1":
        raise ValueError("draw packet is not SHIFT.StaticDraw/1")
    if not draw.get("ready", False):
        raise ValueError(
            "draw packet is not ready: " + ", ".join(draw.get("blocking_reasons", []))
        )
    uv_layers = mesh.get("uv_layers") or {}
    uvs = uv_layers.get("130") or uv_layers.get(130) or mesh.get("uvs") or []
    if not uvs:
        raise ValueError("mesh has no UV0 (property 130)")
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

    world = _coerce_matrix(draw.get("world_matrix")) or _identity4()
    base_mvp = mvp or orthographic_mvp(vertices)
    final_mvp = _mat4_mul(base_mvp, world)
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
        "world_matrix_applied": True,
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
    pixel_program = None
    if shader_reference:
        programs = [
            (submesh.get("shader") or {}).get("pixel_program")
            for submesh in command.get("submeshes", []) or []
        ]
        pixel_program = next((program for program in programs if program), None)
        if pixel_program is None:
            raise ValueError("RenderCommand has no embedded pixel_program for shader reference")
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
    )
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
    parser.add_argument("--texture", type=Path, help="DDS file used by --textured")
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
        image = decode_dds(args.texture.read_bytes())
        result = render_textured_render_command(
            command,
            mesh,
            image,
            args.output,
            width=args.width,
            height=args.height,
            shader_reference=args.shader_reference,
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
