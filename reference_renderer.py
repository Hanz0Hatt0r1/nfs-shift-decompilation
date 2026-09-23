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

from static_draw import build_static_draw_contract


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
    image = rasterize_mesh(
        mesh.get("vertices") or [],
        mesh.get("indices") or [],
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
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    args = parser.parse_args(argv)
    if args.draw_packet:
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
