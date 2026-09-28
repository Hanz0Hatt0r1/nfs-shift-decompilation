#!/usr/bin/env python3
"""Need for Speed SHIFT/SHIFT2 MEB mesh reader and Android-neutral mesh IR."""
from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import BinaryIO, Any
from skeleton_ir import parse_skeleton, skinning_contract


class MEBError(ValueError):
    pass


class MEBReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def need(self, n: int):
        if n < 0 or self.pos + n > len(self.data):
            raise MEBError(f"truncated MEB at 0x{self.pos:X}, need {n} bytes")

    def read(self, n: int) -> bytes:
        self.need(n)
        out = self.data[self.pos:self.pos+n]
        self.pos += n
        return out

    def align4(self):
        self.pos = (self.pos + 3) & ~3
        self.need(0)

    def u8(self) -> int:
        return self.read(1)[0]

    def u16(self) -> int:
        # SHIFT MEB uses little-endian integer fields.
        return struct.unpack("<H", self.read(2))[0]

    def u32(self) -> int:
        # SHIFT MEB integer and floating-point fields are little-endian.
        return struct.unpack("<I", self.read(4))[0]

    def f32(self) -> float:
        return struct.unpack("<f", self.read(4))[0]

    def bytes(self, n: int) -> bytes:
        return self.read(n)

    def cstr(self, max_len: int = 1 << 20) -> str:
        start = self.pos
        end = self.data.find(b"\x00", start, min(len(self.data), start + max_len))
        if end < 0:
            raise MEBError(f"unterminated MEB string at 0x{start:X}")
        self.pos = end + 1
        return self.data[start:end].decode("utf-8", "replace")


PROP_NAMES = {
    "200": "position",
    "220": "normal",
    "240": "tangent",
    "250": "tangent2",
    "460": "color",
    "461": "color2",
    "130": "uv0",
    "131": "uv1",
    "132": "uv2",
    "133": "uv3",
    "134": "uv4",
    "230": "uvw0",
    "231": "uvw1",
    "232": "uvw2",
    "233": "uvw3",
    "234": "uvw4",
    "033": "skip_033",
    "310": "bone_weights",
    "580": "bone_indices",
}

PROP_STRIDES = {
    "200": 12, "220": 12, "240": 12, "250": 12,
    "460": 4, "461": 4,
    "130": 8, "131": 8, "132": 8, "133": 8, "134": 8,
    "230": 12, "231": 12, "232": 12, "233": 12, "234": 12,
    "033": 4, "310": 16, "580": 4,
}


@dataclass
class MEBPrimitive:
    material: str
    first_index: int
    index_count: int


@dataclass
class MEBMesh:
    name: str
    version: int
    flags: int
    vertex_count: int
    vertex_properties: list[str]
    vertices: list[tuple[float, float, float]]
    normals: list[tuple[float, float, float]]
    tangents: list[tuple[float, float, float]]
    tangents2: list[tuple[float, float, float]]
    uv_layers: dict[str, list[tuple[float, ...]]]
    colors: list[tuple[int, int, int, int]]
    colors2: list[tuple[int, int, int, int]]
    bone_weights: list[tuple[float, float, float, float]]
    bone_indices: list[tuple[int, int, int, int]]
    vertex_index_hints: list[int]
    indices: list[int]
    primitives: list[MEBPrimitive]
    # Preserve the exact on-disk 12-byte property descriptors for binary provenance.
    property_descriptors: list[dict[str, Any]] = field(default_factory=list)
    # Physical MEB property payloads are contiguous arrays, not one interleaved stream.
    # Keep exact payload offsets so the Android importer can repack them deterministically.
    property_layouts: list[dict[str, Any]] = field(default_factory=list)
    # Raw skeleton section is retained until its exact bone layout is needed.
    skeleton: dict[str, Any] | None = None

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3


def _vec3s(r: BEReader, n: int) -> list[tuple[float, float, float]]:
    out = []
    for _ in range(n):
        out.append((r.f32(), r.f32(), r.f32()))
    return out


def _uvs(r: BEReader, n: int, width: int) -> list[tuple[float, ...]]:
    out = []
    for _ in range(n):
        vals = [r.f32() for _ in range(width)]
        # The original importer flips V only when emitting OBJ. Keep source UVs
        # in the IR so runtime/export can choose its target convention.
        out.append(tuple(vals))
    return out


def read_meb(data: bytes) -> MEBMesh:
    r = MEBReader(data)
    # The first two words are stored in the file header byte order used by the
    # original tooling. Geometry metadata that follows uses little-endian ints.
    version = struct.unpack(">I", r.read(4))[0]
    flags = struct.unpack(">I", r.read(4))[0]
    name = r.cstr()
    r.align4()
    vertex_count = r.u32()
    num_vert_props = r.u32()
    num_prims = r.u32()
    # Unknown fixed header / resource metadata. Preserve its location but the
    # fields are not needed to recover geometry.
    fixed_header = r.bytes(40)

    skeleton: dict[str, Any] | None = None
    # The public Shift importer checks the high byte read from the second dword.
    # Keep the same condition while preserving any unexpected non-zero flags.
    if ((flags >> 24) & 0xFF) == 1:
        num_bones = r.u32()
        num_chars = r.u32()
        char_blob = r.bytes(num_chars)
        bone_blob = r.bytes(num_bones * 48)
        skeleton = {
            "num_bones": num_bones,
            "num_chars": num_chars,
            "char_blob_hex": char_blob.hex(),
            "bone_blob_hex": bone_blob.hex(),
        }
        skeleton["ir"] = parse_skeleton(skeleton)

    props: list[str] = []
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    tangents: list[tuple[float, float, float]] = []
    tangents2: list[tuple[float, float, float]] = []
    uv_layers: dict[str, list[tuple[float, ...]]] = {}
    colors: list[tuple[int, int, int, int]] = []
    colors2: list[tuple[int, int, int, int]] = []
    bone_weights: list[tuple[float, float, float, float]] = []
    bone_indices: list[tuple[int, int, int, int]] = []
    vertex_index_hints: list[int] = []
    property_layouts: list[dict[str, Any]] = []
    property_descriptors: list[dict[str, Any]] = []

    # Vertex property descriptors and their payloads are interleaved.
    for _ in range(num_vert_props):
        descriptor_offset = r.pos
        descriptor_bytes = r.read(12)
        a, b, c = struct.unpack("<III", descriptor_bytes)
        prop = f"{a}{b}{c}"
        props.append(prop)
        property_descriptors.append({
            "id": prop,
            "offset": descriptor_offset,
            "words": [a, b, c],
            "raw_hex": descriptor_bytes.hex(),
        })
        payload_offset = r.pos
        stride = PROP_STRIDES.get(prop)
        if stride is None:
            raise MEBError(f"unsupported MEB vertex property {prop} at 0x{r.pos:X}")
        payload_bytes = stride * vertex_count
        if prop in {"460", "461"}: storage, components, normalized = "u8x4", 4, True
        elif prop in {"580"}: storage, components, normalized = "u8x4", 4, False
        elif prop in {"200", "220", "240", "250"}: storage, components, normalized = "f32x3", 3, False
        elif prop in {"310"}: storage, components, normalized = "f32x4", 4, False
        elif prop in {"130", "131", "132", "133", "134"}: storage, components, normalized = "f32x2", 2, False
        elif prop in {"230", "231", "232", "233", "234"}: storage, components, normalized = "f32x3", 3, False
        else: storage, components, normalized = "raw4", 4, False
        property_layouts.append({"id":prop,"name":PROP_NAMES.get(prop,"unknown"),"payload_offset":payload_offset,"stride":stride,"bytes":payload_bytes,"storage":storage,"components":components,"normalized":normalized})
        if prop == "200":
            positions = _vec3s(r, vertex_count)
        elif prop == "220":
            normals = _vec3s(r, vertex_count)
        elif prop == "240":
            tangents = _vec3s(r, vertex_count)
        elif prop == "250":
            tangents2 = _vec3s(r, vertex_count)
        elif prop == "460":
            colors = [tuple(r.u8() for _ in range(4)) for _ in range(vertex_count)]
        elif prop == "461":
            colors2 = [tuple(r.u8() for _ in range(4)) for _ in range(vertex_count)]
        elif prop in {"130", "131", "132", "133", "134"}:
            uv_layers[prop] = _uvs(r, vertex_count, 2)
        elif prop in {"230", "231", "232", "233", "234"}:
            uv_layers[prop] = _uvs(r, vertex_count, 3)
        elif prop == "033":
            r.bytes(vertex_count * 4)
        elif prop == "580":
            bone_indices = [tuple(r.u8() for _ in range(4)) for _ in range(vertex_count)]
        elif prop == "310":
            bone_weights = [tuple(r.f32() for _ in range(4)) for _ in range(vertex_count)]
        else:
            raise MEBError(f"unsupported MEB vertex property {prop} at 0x{r.pos:X}")

    if not positions:
        # Some non-geometry MEB resources exist; a mesh without position data
        # is still represented but cannot be rendered as triangles.
        positions = [(0.0, 0.0, 0.0)] * vertex_count

    indices: list[int] = []
    primitives: list[MEBPrimitive] = []
    for _ in range(num_prims):
        material_path = r.cstr()
        r.align4()
        r.bytes(4)
        num_faces = r.u32()
        if ((flags >> 24) & 0xFF) == 1:
            num_shorts = r.u32()
            r.bytes(num_shorts * 2)
        r.align4()
        first = len(indices)
        for _face in range(num_faces):
            i0, i1, i2 = r.u16(), r.u16(), r.u16()
            # Keep source winding. The old OBJ importer reversed it for OBJ.
            indices.extend((i0, i1, i2))
        primitives.append(MEBPrimitive(material=material_path.replace("\\", "/"), first_index=first, index_count=num_faces * 3))
        r.align4()
        r.bytes(4)  # two u16 values: unknown per-primitive metadata
        r.bytes(40)

    if any(i >= vertex_count for i in indices):
        raise MEBError(f"MEB index exceeds vertex count ({vertex_count})")

    if r.pos > len(data):
        raise MEBError("MEB parser overran resource")

    return MEBMesh(
        name=name,
        version=version,
        flags=flags,
        vertex_count=vertex_count,
        vertex_properties=props,
        vertices=positions,
        normals=normals,
        tangents=tangents,
        tangents2=tangents2,
        uv_layers=uv_layers,
        colors=colors,
        colors2=colors2,
        bone_weights=bone_weights,
        bone_indices=bone_indices,
        vertex_index_hints=vertex_index_hints,
        indices=indices,
        primitives=primitives,
        property_layouts=property_layouts,
        property_descriptors=property_descriptors,
        skeleton=skeleton,
    )


def mesh_summary(mesh: MEBMesh) -> dict[str, Any]:
    bbox = None
    if mesh.vertices:
        xs = [p[0] for p in mesh.vertices]; ys = [p[1] for p in mesh.vertices]; zs = [p[2] for p in mesh.vertices]
        bbox = {"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]}
    return {
        "format": "SHIFT.MEB",
        "version": mesh.version,
        "flags": mesh.flags,
        "name": mesh.name,
        "vertex_count": mesh.vertex_count,
        "triangle_count": mesh.triangle_count,
        "vertex_properties": [{"id": p, "name": PROP_NAMES.get(p, "unknown"), "stride": PROP_STRIDES.get(p)} for p in mesh.vertex_properties],
        "property_layouts": mesh.property_layouts,
        "property_descriptors": mesh.property_descriptors,
        "normal_count": len(mesh.normals),
        "tangent_count": len(mesh.tangents),
        "tangent2_count": len(mesh.tangents2),
        "uv_layers": {k: len(v) for k, v in mesh.uv_layers.items()},
        "color_count": len(mesh.colors),
        "color2_count": len(mesh.colors2),
        "bone_weight_count": len(mesh.bone_weights),
        "bone_index_count": len(mesh.bone_indices),
        "primitives": [asdict(p) for p in mesh.primitives],
        "bbox": bbox,
        "skeleton": None if mesh.skeleton is None else {
            "num_bones": mesh.skeleton["num_bones"],
            "num_chars": mesh.skeleton["num_chars"],
            "bone_names": mesh.skeleton["ir"]["bone_names"],
        },
        "skinning": skinning_contract(mesh.vertex_properties, mesh.skeleton["ir"] if mesh.skeleton else None),
    }


def mesh_to_jsonable(mesh: MEBMesh) -> dict[str, Any]:
    return {
        **mesh_summary(mesh),
        "vertices": mesh.vertices,
        "normals": mesh.normals,
        "tangents": mesh.tangents,
        "uv_layers": mesh.uv_layers,
        "colors": mesh.colors,
        "colors2": mesh.colors2,
        "bone_weights": mesh.bone_weights,
        "bone_indices": mesh.bone_indices,
        "indices": mesh.indices,
        "skeleton": mesh.skeleton,
    }


MGEO_MAGIC = b"MGEO"
MGEO_VERSION = 1


def write_mgeo(mesh: MEBMesh, path: str | Path) -> None:
    """Write a compact Android-neutral binary mesh.

    Layout (little-endian): header, positions, normals, tangent, UV layers,
    RGBA8 colors, uint32 indices, then a UTF-8 JSON material/submesh table.
    The explicit header keeps the runtime independent of the original MEB.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    uv_items = sorted(mesh.uv_layers.items())
    flags = 0
    if mesh.normals: flags |= 1
    if mesh.tangents: flags |= 2
    if mesh.colors: flags |= 4
    if uv_items: flags |= 8
    if mesh.tangents2: flags |= 16
    if mesh.colors2: flags |= 32
    if mesh.bone_indices: flags |= 64
    if mesh.bone_weights: flags |= 128
    meta = {
        "name": mesh.name,
        "vertex_properties": mesh.vertex_properties,
        "property_layouts": mesh.property_layouts,
        "primitives": [asdict(x) for x in mesh.primitives],
        "uv_layer_ids": [k for k, _ in uv_items],
        "skeleton": None if mesh.skeleton is None else {"num_bones": mesh.skeleton["num_bones"], "num_chars": mesh.skeleton["num_chars"], "char_blob_hex": mesh.skeleton["char_blob_hex"], "bone_blob_hex": mesh.skeleton["bone_blob_hex"]},
    }
    meta_blob = json.dumps(meta, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with p.open("wb") as f:
        f.write(struct.pack("<4sHHIIIIII", MGEO_MAGIC, MGEO_VERSION, flags,
                            len(mesh.vertices), len(mesh.indices), len(mesh.primitives),
                            len(uv_items), len(mesh.normals), len(meta_blob)))
        for v in mesh.vertices: f.write(struct.pack("<3f", *v))
        for v in mesh.normals: f.write(struct.pack("<3f", *v))
        for v in mesh.tangents: f.write(struct.pack("<3f", *v))
        for v in mesh.tangents2: f.write(struct.pack("<3f", *v))
        for _name, arr in uv_items:
            width = len(arr[0]) if arr else 2
            f.write(struct.pack("<I", width))
            for v in arr:
                if width == 2: f.write(struct.pack("<2f", *v))
                elif width == 3: f.write(struct.pack("<3f", *v))
                else: raise MEBError(f"unsupported UV width {width}")
        for c in mesh.colors: f.write(bytes(c))
        for c in mesh.colors2: f.write(bytes(c))
        for b in mesh.bone_indices: f.write(bytes(b))
        for w in mesh.bone_weights: f.write(struct.pack("<4f", *w))
        for i in mesh.indices: f.write(struct.pack("<I", i))
        f.write(meta_blob)
