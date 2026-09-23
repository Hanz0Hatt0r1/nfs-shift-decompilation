#!/usr/bin/env python3
"""Minimal, evidence-based reader for SHIFT NXS MESH .CSM collision meshes."""
from __future__ import annotations

import json
import struct
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


class CSMError(ValueError):
    pass


MAGIC = b"NXS\x00MESH"
CMESH_MAGIC = b"CMES"
CMESH_VERSION = 1


@dataclass
class CSMesh:
    header_word0: int
    version: int
    parameter: float
    byte_flag: int
    unknown_u32: int
    vertex_count: int
    face_count: int
    vertices: list[tuple[float, float, float]]
    indices: list[int]
    tail: bytes

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3


def _u32be(data: bytes, off: int) -> int:
    if off + 4 > len(data):
        raise CSMError(f"truncated CSM at 0x{off:X}")
    return struct.unpack_from(">I", data, off)[0]


def _f32be(data: bytes, off: int) -> float:
    if off + 4 > len(data):
        raise CSMError(f"truncated CSM at 0x{off:X}")
    return struct.unpack_from(">f", data, off)[0]


def read_csm(data: bytes) -> CSMesh:
    if len(data) < 0x28 or data[4:12] != MAGIC:
        raise CSMError("expected NXS\\x00MESH signature at offset 4")
    header_word0 = _u32be(data, 0)
    version = _u32be(data, 12)
    parameter = _f32be(data, 20)
    byte_flag = data[24]
    unknown_u32 = _u32be(data, 28)
    vertex_count = _u32be(data, 32)
    face_count = _u32be(data, 36)

    vertex_off = 40
    vertex_end = vertex_off + vertex_count * 12
    face_off = vertex_end
    face_end = face_off + face_count * 6
    if vertex_count <= 0 or face_count <= 0:
        raise CSMError(f"invalid mesh counts: {vertex_count} vertices, {face_count} faces")
    if face_end > len(data):
        raise CSMError(f"truncated CSM mesh body: need 0x{face_end:X}, file is 0x{len(data):X}")

    vertices = [struct.unpack_from(">3f", data, vertex_off + i * 12) for i in range(vertex_count)]
    indices = list(struct.unpack_from(">%dH" % (face_count * 3), data, face_off))
    bad = [i for i in indices if i >= vertex_count]
    if bad:
        raise CSMError(f"CSM index exceeds vertex count: {max(bad)} >= {vertex_count}")

    return CSMesh(
        header_word0=header_word0,
        version=version,
        parameter=parameter,
        byte_flag=byte_flag,
        unknown_u32=unknown_u32,
        vertex_count=vertex_count,
        face_count=face_count,
        vertices=[tuple(map(float, v)) for v in vertices],
        indices=indices,
        tail=data[face_end:],
    )


def csm_summary(mesh: CSMesh) -> dict[str, Any]:
    xs = [v[0] for v in mesh.vertices]; ys = [v[1] for v in mesh.vertices]; zs = [v[2] for v in mesh.vertices]
    return {
        "format": "SHIFT.CSM.NXS_MESH",
        "header_word0": mesh.header_word0,
        "version": mesh.version,
        "parameter": mesh.parameter,
        "byte_flag": mesh.byte_flag,
        "unknown_u32": mesh.unknown_u32,
        "vertex_count": mesh.vertex_count,
        "triangle_count": mesh.triangle_count,
        "bbox": {"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]},
        "mesh_data_end": 40 + mesh.vertex_count * 12 + mesh.face_count * 6,
        "tail_bytes": len(mesh.tail),
        "indices_valid": all(0 <= i < mesh.vertex_count for i in mesh.indices),
    }


def mesh_to_jsonable(mesh: CSMesh) -> dict[str, Any]:
    return {
        **csm_summary(mesh),
        "vertices": mesh.vertices,
        "indices": mesh.indices,
    }


def write_cmesh(mesh: CSMesh, path: str | Path) -> None:
    """Write collision geometry as a small Android-neutral triangle mesh."""
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    meta = json.dumps({
        "source_format": "SHIFT.CSM.NXS_MESH",
        "source_header_word0": mesh.header_word0,
        "source_version": mesh.version,
        "source_parameter": mesh.parameter,
        "source_byte_flag": mesh.byte_flag,
        "source_unknown_u32": mesh.unknown_u32,
        "tail_bytes": len(mesh.tail),
    }, separators=(",", ":")).encode("utf-8")
    with p.open("wb") as f:
        f.write(struct.pack("<4sHHIIII", CMESH_MAGIC, CMESH_VERSION, 0,
                            len(mesh.vertices), len(mesh.indices), len(mesh.indices)//3, len(meta)))
        for v in mesh.vertices:
            f.write(struct.pack("<3f", *v))
        for i in mesh.indices:
            f.write(struct.pack("<I", i))
        f.write(meta)
