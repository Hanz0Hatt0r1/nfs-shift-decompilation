#!/usr/bin/env python3
"""Interactive SHIFT BFF/MEB viewer with optional RENDER.bff shader/material library.

This tool is an integration UI over the project's current evidence-backed modules:
BFF/XMem-LZX, MEB, VHF scene assembly, BMT material parsing, DDS decode/sampling,
and FX/FXO shader metadata. The viewport is a deterministic CPU preview rather
than byte-for-byte execution of the original D3D9 FXO program.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import traceback
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from tkinter import BOTH, END, LEFT, RIGHT, X, Y, NW, Canvas, Checkbutton, Frame
from tkinter import Button, Label, Listbox, BooleanVar, PhotoImage, StringVar, Tk
from tkinter import filedialog, messagebox

from shift_importer import BFF, sha256
from meb_format import MEBPrimitive, read_meb
from resource_formats import parse_bmt_material
from shader_ir import parse_fx_source, parse_shader_blobs
from material_linker import parse_fx_samplers
from texture_reference import decode_dds, sample_texture_2d
from vhf_scene_preview import build_vhf_scene

FORMAT = "SHIFT.BFFViewer/2"


def norm_ref(value: str | os.PathLike[str] | None) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def identity_matrix() -> list[float]:
    return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def transform_point(m: list[float], p: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = p
    return (
        m[0] * x + m[1] * y + m[2] * z + m[3],
        m[4] * x + m[5] * y + m[6] * z + m[7],
        m[8] * x + m[9] * y + m[10] * z + m[11],
    )


def transform_dir_camera(v: tuple[float, float, float], yaw: float, pitch: float) -> tuple[float, float, float]:
    yr, pr = math.radians(yaw), math.radians(pitch)
    cy, sy = math.cos(yr), math.sin(yr)
    cp, sp = math.cos(pr), math.sin(pr)
    x, z = v[0] * cy + v[2] * sy, -v[0] * sy + v[2] * cy
    y = v[1]
    return (x, y * cp - z * sp, y * sp + z * cp)


def camera_point(
    p: tuple[float, float, float],
    yaw: float,
    pitch: float,
) -> tuple[float, float, float]:
    return transform_dir_camera(p, yaw, pitch)


def normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v) if n > 1e-12 else (0.0, 1.0, 0.0)


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def find_exact(archive: BFF, ref: str):
    target = norm_ref(ref)
    hits = [e for e in archive.entries if norm_ref(e.path) == target]
    if len(hits) != 1:
        raise ValueError(f"expected exactly one resource {ref!r}, found {len(hits)}")
    return hits[0]


@dataclass
class TextureRef:
    archive: BFF
    entry: Any
    image: dict[str, Any] | None = None


class ShaderLibrary:
    def __init__(self, archive: BFF):
        self.archive = archive
        self.fx = {
            norm_ref(e.path): e for e in archive.entries
            if norm_ref(e.path).endswith(".fx")
        }
        self.fxo = {
            norm_ref(e.path): e for e in archive.entries
            if norm_ref(e.path).endswith(".fxo")
        }
        self._cache: dict[str, dict[str, Any]] = {}

    def find_fx(self, shader_ref: str):
        target = norm_ref(shader_ref)
        if target in self.fx:
            return self.fx[target]
        base = target.rsplit("/", 1)[-1]
        hits = [e for p, e in self.fx.items() if p.rsplit("/", 1)[-1] == base]
        return hits[0] if len(hits) == 1 else None

    def describe(self, shader_ref: str) -> dict[str, Any]:
        key = norm_ref(shader_ref)
        if key in self._cache:
            return self._cache[key]
        entry = self.find_fx(shader_ref)
        if entry is None:
            result = {"status": "missing", "shader_ref": shader_ref}
            self._cache[key] = result
            return result
        source = self.archive.extract_entry(entry, type2="lzx")
        source_meta = parse_fx_source(source)
        sampler_meta = parse_fx_samplers(source)
        stem = Path(norm_ref(entry.path)).stem
        fxo_candidates = [
            e for p, e in self.fxo.items()
            if Path(p).stem.startswith("render_shaders_" + stem + "_")
            or Path(p).stem.startswith(stem + "_")
        ]
        # Keep the shader-cache relation explicit while decoding only the first
        # candidate lazily. Full permutation selection remains in material_linker.
        selected = fxo_candidates[0] if fxo_candidates else None
        blobs = []
        if selected is not None:
            try:
                payload = self.archive.extract_entry(selected, type2="lzx")
                blobs = [
                    {
                        "offset": b.offset,
                        "end": b.end,
                        "stage": b.stage,
                        "version": [b.major, b.minor],
                        "samplers": b.ctab_samplers,
                    }
                    for b in parse_shader_blobs(payload)
                ]
            except Exception:
                blobs = []
        result = {
            "status": "ready",
            "shader_ref": entry.path,
            "fx_entry": entry.index,
            "source": {
                **source_meta,
                "samplers": sampler_meta,
            },
            "fxo_count": len(fxo_candidates),
            "selected_fxo": None if selected is None else {
                "path": selected.path,
                "index": selected.index,
                "programs": blobs,
            },
        }
        self._cache[key] = result
        return result


class MaterialResolver:
    def __init__(self, archives: list[BFF], shaders: ShaderLibrary | None):
        self.archives = archives
        self.shaders = shaders
        self.material_cache: dict[str, dict[str, Any]] = {}
        self.texture_cache: dict[tuple[str, int], dict[str, Any] | None] = {}
        self.paint_cache: dict[str, TextureRef | None] = {}

    def find(self, ref: str):
        target = norm_ref(ref)
        aliases = [target]
        if target.endswith(".mtx"):
            aliases.append(target[:-4] + ".bmt")
        rows = []
        for archive in self.archives:
            for e in archive.entries:
                low = norm_ref(e.path)
                if low in aliases:
                    rows.append((archive, e))
        if not rows:
            return None
        for a, e in rows:
            if norm_ref(e.path) == target:
                return a, e
        return rows[0]

    def texture(self, archive: BFF, entry) -> dict[str, Any] | None:
        key = (str(archive.path), int(entry.index))
        if key in self.texture_cache:
            return self.texture_cache[key]
        try:
            image = decode_dds(archive.extract_entry(entry, type2="lzx"))
        except Exception:
            image = None
        self.texture_cache[key] = image
        return image

    def default_paint_texture(self) -> TextureRef | None:
        cache_key = "alpine-white"
        if cache_key in self.paint_cache:
            return self.paint_cache[cache_key]
        for archive in self.archives:
            for entry in archive.entries:
                low = norm_ref(entry.path)
                if "/_paint_colors/" not in low or not low.endswith(".bmt"):
                    continue
                try:
                    mat = parse_bmt_material(archive.extract_entry(entry, type2="lzx"))
                    for param in mat.get("shaderparams", []) or []:
                        if param.get("name") == "diffuseTexture" and isinstance(param.get("value"), str):
                            found = self.find(param["value"])
                            if found:
                                ref = TextureRef(found[0], found[1], self.texture(found[0], found[1]))
                                self.paint_cache[cache_key] = ref
                                return ref
                except Exception:
                    continue
        self.paint_cache[cache_key] = None
        return None

    def material(self, ref: str) -> dict[str, Any]:
        key = norm_ref(ref)
        if key in self.material_cache:
            return self.material_cache[key]
        found = self.find(ref)
        if not found:
            result = {"status": "missing", "ref": ref}
            self.material_cache[key] = result
            return result
        archive, entry = found
        try:
            raw = parse_bmt_material(archive.extract_entry(entry, type2="lzx"))
            params = raw.get("material", {}).get("shaderparams", [])
            shader_ref = str(raw.get("material", {}).get("shader") or "")
            textures: dict[str, TextureRef] = {}
            scalars: dict[str, float] = {}
            vectors: dict[str, tuple[float, ...]] = {}
            for row in params:
                name = row.get("name")
                value = row.get("value")
                if not isinstance(name, str):
                    continue
                if isinstance(value, str) and norm_ref(value).endswith(".dds"):
                    texture = self.find(value)
                    if texture:
                        textures[name] = TextureRef(texture[0], texture[1], self.texture(texture[0], texture[1]))
                elif isinstance(value, (int, float)):
                    scalars[name] = float(value)
                elif isinstance(value, list) and len(value) >= 3:
                    if all(isinstance(v, (int, float)) for v in value):
                        vectors[name] = tuple(float(v) for v in value)
            shader = self.shaders.describe(shader_ref) if self.shaders and shader_ref else {"status": "missing"}
            result = {
                "status": "ready",
                "name": raw.get("material", {}).get("name") or "",
                "technique": raw.get("material", {}).get("technique") or "",
                "shader": shader,
                "shader_ref": shader_ref,
                "textures": textures,
                "scalars": scalars,
                "vectors": vectors,
                "specializations": raw.get("material", {}).get("specializations") or [],
            }
        except Exception as exc:
            result = {"status": "error", "ref": ref, "error": f"{type(exc).__name__}: {exc}"}
        self.material_cache[key] = result
        return result


def material_lighting(
    albedo: tuple[float, float, float],
    normal: tuple[float, float, float],
    position: tuple[float, float, float],
    material: dict[str, Any],
) -> tuple[int, int, int]:
    n = normalize(normal)
    light_dir = normalize((0.40, 0.78, 0.47))
    view_dir = normalize((-position[0], -position[1], 2.8 - position[2]))
    ndotl = max(0.0, dot(n, light_dir))
    half_dir = normalize((light_dir[0] + view_dir[0], light_dir[1] + view_dir[1], light_dir[2] + view_dir[2]))
    ndoth = max(0.0, dot(n, half_dir))

    scalars = material.get("scalars") or {}
    max_power = max(4.0, min(128.0, float(scalars.get("maxSpecPower", 80.0))))
    spec_factor = max(0.0, min(2.0, float(scalars.get("globalSpecularFactor", 0.25))))
    fresnel_factor = max(0.0, min(1.0, float(scalars.get("fresnelFactor", 0.6))))
    env_factor = max(0.0, min(2.0, float(scalars.get("globalEMapFactor", 0.5))))

    diffuse = 0.22 + 0.88 * ndotl
    specular = (ndoth ** min(max_power, 64.0)) * spec_factor
    rim = ((1.0 - max(0.0, dot(n, view_dir))) ** 2) * 0.20 * fresnel_factor * env_factor
    return tuple(
        max(0, min(255, int(255.0 * (c * (diffuse + rim) + specular))))
        for c in albedo
    )


def render_scene(
    parts: list[dict[str, Any]],
    resolver: MaterialResolver | None,
    width: int,
    height: int,
    yaw: float,
    pitch: float,
    zoom: float,
) -> bytes:
    width = max(320, min(900, int(width)))
    height = max(240, min(700, int(height)))
    prepared = []
    all_points = []
    for part in parts:
        mesh = part["mesh"]
        world = part["world_matrix"]
        vertices = [camera_point(transform_point(world, p), yaw, pitch) for p in mesh.vertices]
        normals = [transform_dir_camera(n, yaw, pitch) for n in mesh.normals] if mesh.normals else [(0, 1, 0)] * len(vertices)
        prepared.append((part, mesh, vertices, normals))
        all_points.extend(vertices)
    if not all_points:
        return b"P6\n1 1\n255\n\0\0\0"

    min_x, max_x = min(p[0] for p in all_points), max(p[0] for p in all_points)
    min_y, max_y = min(p[1] for p in all_points), max(p[1] for p in all_points)
    span = max(max_x - min_x, max_y - min_y, 1e-6)
    scale = 0.88 * min(width, height) / span * zoom
    cx, cy = (min_x + max_x) * 0.5, (min_y + max_y) * 0.5

    def screen(p):
        return (width * 0.5 + (p[0] - cx) * scale, height * 0.5 - (p[1] - cy) * scale)

    pixels = bytearray([18, 20, 24]) * (width * height)
    depth = [float("inf")] * (width * height)

    for part, mesh, vertices, normals in prepared:
        primitives = mesh.primitives or [MEBPrimitive("", 0, len(mesh.indices))]
        for primitive in primitives:
            material = resolver.material(primitive.material) if resolver and primitive.material else {"status": "missing"}
            diffuse = None
            specular = None
            if material.get("status") == "ready":
                dref = (material.get("textures") or {}).get("diffuseTexture")
                sref = (material.get("textures") or {}).get("specularTexture")
                if dref:
                    diffuse = dref.image
                if sref:
                    specular = sref.image
                shader_ref = str(material.get("shader_ref") or "")
                if diffuse is None and "bodywork" in shader_ref.lower():
                    paint = resolver.default_paint_texture()
                    if paint:
                        diffuse = paint.image

            first = int(primitive.first_index)
            last = min(len(mesh.indices), first + int(primitive.index_count))
            last -= (last - first) % 3
            uv = mesh.uv_layers.get("130") or mesh.uv_layers.get("230")
            if uv is None:
                uv = [(0.0, 0.0)] * len(vertices)

            for i in range(first, last, 3):
                ia, ib, ic = mesh.indices[i:i + 3]
                if ia >= len(vertices) or ib >= len(vertices) or ic >= len(vertices):
                    continue
                a, b, c = vertices[ia], vertices[ib], vertices[ic]
                p0, p1, p2 = screen(a), screen(b), screen(c)
                area = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
                if abs(area) < 1e-10:
                    continue
                min_xi = max(0, int(math.floor(min(p0[0], p1[0], p2[0]))))
                max_xi = min(width - 1, int(math.ceil(max(p0[0], p1[0], p2[0]))))
                min_yi = max(0, int(math.floor(min(p0[1], p1[1], p2[1]))))
                max_yi = min(height - 1, int(math.ceil(max(p0[1], p1[1], p2[1]))))
                inv_area = 1.0 / area

                for y in range(min_yi, max_yi + 1):
                    py = y + 0.5
                    row = y * width
                    for x in range(min_xi, max_xi + 1):
                        px = x + 0.5
                        w0 = ((p1[0] - px) * (p2[1] - py) - (p1[1] - py) * (p2[0] - px)) * inv_area
                        w1 = ((p2[0] - px) * (p0[1] - py) - (p2[1] - py) * (p0[0] - px)) * inv_area
                        w2 = ((p0[0] - px) * (p1[1] - py) - (p0[1] - py) * (p1[0] - px)) * inv_area
                        if w0 < -1e-7 or w1 < -1e-7 or w2 < -1e-7:
                            continue
                        z = w0 * a[2] + w1 * b[2] + w2 * c[2]
                        offset = row + x
                        if z >= depth[offset]:
                            continue
                        depth[offset] = z
                        n = tuple(
                            w0 * normals[ia][k] + w1 * normals[ib][k] + w2 * normals[ic][k]
                            for k in range(3)
                        )
                        pos = tuple(
                            w0 * a[k] + w1 * b[k] + w2 * c[k]
                            for k in range(3)
                        )
                        uv0, uv1, uv2 = uv[ia], uv[ib], uv[ic]
                        u = w0 * uv0[0] + w1 * uv1[0] + w2 * uv2[0]
                        v = w0 * uv0[1] + w1 * uv1[1] + w2 * uv2[1]
                        if diffuse:
                            sampled = sample_texture_2d(
                                diffuse, u, v,
                                {"address_u": "REPEAT", "address_v": "REPEAT", "min_filter": "LINEAR", "mag_filter": "LINEAR"},
                            )
                            albedo = sampled[:3]
                        else:
                            albedo = (0.62, 0.64, 0.68)
                        rgb = material_lighting(albedo, n, pos, material)
                        if specular:
                            sp = sample_texture_2d(
                                specular, u, v,
                                {"address_u": "REPEAT", "address_v": "REPEAT", "min_filter": "LINEAR", "mag_filter": "LINEAR"},
                            )
                            add = int(26 * (sp[0] + sp[1] + sp[2]) / 3.0)
                            rgb = tuple(min(255, c + add) for c in rgb)
                        q = offset * 3
                        pixels[q:q + 3] = bytes(rgb)

    return b"P6\n%d %d\n255\n" % (width, height) + bytes(pixels)


def find_auto_vhf(archive: BFF) -> str | None:
    vhfs = [e for e in archive.entries if norm_ref(e.path).endswith(".vhf")]
    for entry in vhfs:
        try:
            root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).fromstring(
                archive.extract_entry(entry, type2="lzx")
            )
            names = [str(node.get("Name") or "").upper() for node in root.iter("NODE")]
            if any(name.startswith("BMW_M3_E36") and "KIT00" in name and name.endswith("LODA") for name in names):
                return entry.path
        except Exception:
            continue
    return vhfs[0].path if vhfs else None


class App:
    def __init__(self, root: Tk, vehicle_path: Path | None = None, render_path: Path | None = None):
        self.root = root
        self.root.title("Need for Speed SHIFT — BFF Viewer")
        self.vehicle: BFF | None = None
        self.render: BFF | None = None
        self.shaders: ShaderLibrary | None = None
        self.resolver: MaterialResolver | None = None
        self.parts: list[dict[str, Any]] = []
        self.meshes: dict[int, Any] = {}
        self.yaw, self.pitch, self.zoom = -28.0, -15.0, 1.0
        self.drag_start_state = None
        self.photo = None

        self.status = StringVar(value="Open a vehicle BFF")
        left = Frame(root)
        left.pack(side=LEFT, fill=Y)
        self.listbox = Listbox(left, width=55, exportselection=False)
        self.listbox.pack(side=LEFT, fill=Y)
        controls = Frame(left)
        controls.pack(side=LEFT, fill=Y)
        Button(controls, text="Open Vehicle BFF…", command=self.open_vehicle).pack(fill=X, padx=6, pady=4)
        Button(controls, text="Open RENDER.bff…", command=self.open_render).pack(fill=X, padx=6, pady=4)
        Button(controls, text="Auto vehicle", command=self.auto_vehicle).pack(fill=X, padx=6, pady=4)
        Button(controls, text="Show selected MEB", command=self.selected_meb).pack(fill=X, padx=6, pady=4)
        self.material_var = BooleanVar(value=True)
        Checkbutton(
            controls,
            text="Shader/material preview",
            variable=self.material_var,
            command=self.repaint,
        ).pack(fill=X, padx=6, pady=4)
        Button(controls, text="Extract all…", command=self.extract_all).pack(fill=X, padx=6, pady=4)
        Button(controls, text="Reset view (R)", command=self.reset_view).pack(fill=X, padx=6, pady=4)
        Label(controls, textvariable=self.status, wraplength=340, justify=LEFT).pack(fill=X, padx=6, pady=10)

        view = Frame(root)
        view.pack(side=RIGHT, fill=BOTH, expand=True)
        self.canvas = Canvas(view, background="#121418", highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.begin_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Button-4>", lambda e: self.wheel_delta(1))
        self.canvas.bind("<Button-5>", lambda e: self.wheel_delta(-1))
        self.canvas.bind("<Configure>", lambda e: self.repaint())
        root.bind("<KeyPress-r>", lambda e: self.reset_view())
        root.bind("<KeyPress-R>", lambda e: self.reset_view())
        root.protocol("WM_DELETE_WINDOW", self.close)

        if render_path:
            self.set_render(render_path)
        if vehicle_path:
            self.set_vehicle(vehicle_path)

    def set_render(self, path: Path):
        try:
            if self.render:
                self.render.close()
            self.render = BFF(path)
            self.shaders = ShaderLibrary(self.render)
            self.rebuild_resolver()
            self.status.set(
                f"RENDER: {path.name}\n"
                f"FX: {len(self.shaders.fx)} • FXO: {len(self.shaders.fxo)}\n"
                "Shader-aware material preview is enabled."
            )
            self.repaint()
        except Exception as exc:
            self.render = None
            self.shaders = None
            self.rebuild_resolver()
            messagebox.showerror("RENDER.bff error", f"{type(exc).__name__}: {exc}")

    def rebuild_resolver(self):
        archives = [a for a in (self.vehicle, self.render) if a is not None]
        self.resolver = MaterialResolver(archives, self.shaders) if archives else None

    def set_vehicle(self, path: Path):
        path = Path(path)
        try:
            if self.vehicle:
                self.vehicle.close()
            self.vehicle = BFF(path)
            self.listbox.delete(0, END)
            self.meshes.clear()
            for e in self.vehicle.entries:
                if norm_ref(e.path).endswith(".meb"):
                    self.meshes[self.listbox.size()] = e
                    self.listbox.insert(END, f"{e.index:5d}  {e.path}")

            if self.render is None:
                for candidate in (path.with_name("RENDER.bff"), path.with_name("render.bff")):
                    if candidate.is_file():
                        self.set_render(candidate)
                        break
            self.rebuild_resolver()
            self.auto_vehicle()
            self.status.set(
                f"{path.name}\n"
                f"Entries: {len(self.vehicle.entries)} • MEB: {len(self.meshes)}\n"
                + (f"RENDER: {self.render.path.name}" if self.render else "RENDER: not attached")
            )
        except Exception as exc:
            messagebox.showerror("BFF error", f"{type(exc).__name__}: {exc}")

    def open_vehicle(self):
        path = filedialog.askopenfilename(filetypes=[("SHIFT BFF", "*.bff *.pak"), ("All files", "*")])
        if path:
            self.set_vehicle(Path(path))

    def open_render(self):
        path = filedialog.askopenfilename(filetypes=[("SHIFT Render BFF", "*.bff *.pak"), ("All files", "*")])
        if path:
            self.set_render(Path(path))

    def auto_vehicle(self):
        if not self.vehicle:
            return
        resource = find_auto_vhf(self.vehicle)
        try:
            if resource:
                scene = build_vhf_scene(self.vehicle.path, resource)
                self.parts = scene["parts"]
            else:
                self.selected_meb()
                return
            self.reset_view()
            material_state = "shader/material" if self.render and self.material_var.get() else "geometry"
            self.status.set(
                f"Scene: {resource}\n"
                f"Parts: {len(self.parts)} • {material_state} preview\n"
                "LMB: orbit • wheel: zoom • R: reset"
            )
        except Exception as exc:
            self.status.set(f"Auto vehicle failed: {type(exc).__name__}: {exc}")
            self.selected_meb()

    def selected_meb(self):
        if not self.vehicle:
            return
        selection = self.listbox.curselection()
        if not selection:
            if not self.meshes:
                return
            selection = (0,)
        entry = self.meshes[selection[0]]
        try:
            data = self.vehicle.extract_entry(entry, type2="lzx")
            mesh = read_meb(data)
            self.parts = [{
                "name": entry.path,
                "resource": entry.path,
                "resource_sha256": sha256(data),
                "world_matrix": identity_matrix(),
                "mesh": mesh,
            }]
            self.reset_view()
        except Exception as exc:
            messagebox.showerror("MEB error", f"{type(exc).__name__}: {exc}")

    def extract_all(self):
        if not self.vehicle:
            return
        out_dir = filedialog.askdirectory(title="Choose extraction directory")
        if not out_dir:
            return
        self.status.set("Extracting…")
        self.root.update_idletasks()
        try:
            manifest_entries = []
            root = Path(out_dir)
            for entry in self.vehicle.entries:
                target = root / Path(entry.path)
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    payload = self.vehicle.extract_entry(entry, type2="lzx")
                    target.write_bytes(payload)
                    manifest_entries.append({
                        "index": entry.index,
                        "path": entry.path,
                        "status": "ok",
                        "type": entry.type,
                        "compressed_size": entry.compressed_size,
                        "uncompressed_size": entry.uncompressed_size,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    })
                except Exception as exc:
                    manifest_entries.append({
                        "index": entry.index,
                        "path": entry.path,
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                    })
            manifest = {
                "format": "SHIFT.BFFViewerExtraction/1",
                "archive": str(self.vehicle.path),
                "entries": manifest_entries,
            }
            (root / "manifest.json").write_text(
                __import__("json").dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            ok = sum(x["status"] == "ok" for x in manifest_entries)
            self.status.set(f"Extracted {ok}/{len(manifest_entries)} entries\n{root / 'manifest.json'}")
        except Exception as exc:
            messagebox.showerror("Extraction error", f"{type(exc).__name__}: {exc}")

    def reset_view(self):
        self.yaw, self.pitch, self.zoom = -28.0, -15.0, 1.0
        self.repaint()

    def begin_drag(self, event):
        self.drag_start_state = (event.x, event.y, self.yaw, self.pitch)
        if self.material_var.get():
            # During manipulation the gray geometry path keeps the UI responsive;
            # the shader/material image is restored on mouse release.
            self.repaint(geometry_only=True)

    def drag(self, event):
        if not self.drag_start_state:
            return
        x0, y0, yaw0, pitch0 = self.drag_start_state
        self.yaw = yaw0 + (event.x - x0) * 0.45
        self.pitch = max(-89.0, min(89.0, pitch0 + (event.y - y0) * 0.45))
        self.repaint(geometry_only=True)

    def end_drag(self, event):
        self.drag_start_state = None
        self.repaint()

    def wheel_delta(self, delta):
        self.zoom = max(0.25, min(4.0, self.zoom * (1.12 if delta > 0 else 1 / 1.12)))
        self.repaint()

    def wheel(self, event):
        self.wheel_delta(1 if event.delta > 0 else -1)

    def repaint(self, geometry_only: bool = False):
        self.canvas.delete("all")
        if not self.parts:
            self.canvas.create_text(
                max(20, self.canvas.winfo_width() // 2),
                max(20, self.canvas.winfo_height() // 2),
                text="No model loaded",
                fill="#cccccc",
                font=("TkDefaultFont", 16),
            )
            return

        use_materials = (
            not geometry_only
            and self.material_var.get()
            and self.render is not None
            and self.resolver is not None
        )
        width = min(720, max(320, self.canvas.winfo_width()))
        height = min(520, max(240, self.canvas.winfo_height()))
        try:
            ppm = render_scene(
                self.parts,
                self.resolver if use_materials else None,
                width,
                height,
                self.yaw,
                self.pitch,
                self.zoom,
            )
            self.photo = PhotoImage(data=ppm)
            self.canvas.create_image(width // 2, height // 2, image=self.photo)
            mode = "shader/material" if use_materials else "geometry"
            self.canvas.create_text(
                12, 12,
                text=f"yaw {self.yaw:.1f}°  pitch {self.pitch:.1f}°  zoom {self.zoom:.2f}×  |  {mode}",
                anchor=NW,
                fill="#dddddd",
            )
        except Exception as exc:
            traceback.print_exc()
            self.canvas.create_text(
                12, 32,
                text=f"Render error: {type(exc).__name__}: {exc}",
                anchor=NW,
                fill="#ff8888",
            )

    def close(self):
        if self.vehicle:
            self.vehicle.close()
        if self.render:
            self.render.close()
        self.root.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive SHIFT BFF/MEB viewer with RENDER.bff shader/material support")
    parser.add_argument("vehicle", type=Path, nargs="?")
    parser.add_argument("--render-bff", type=Path, default=None)
    args = parser.parse_args(argv)
    root = Tk()
    App(root, vehicle_path=args.vehicle, render_path=args.render_bff)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
