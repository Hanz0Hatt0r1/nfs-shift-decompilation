"""Source-backed partial decoder for SHIFT binary MeshInst (.imb) meshes.

The retail binary mesh loader FUN_00859800 reaches a fixed mesh header only
after a version-dependent prefix and embedded resource-name string. Phase 556
therefore requires the caller to provide that fixed-header offset explicitly.
This keeps the decoder deterministic while the prefix grammar remains open.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.IMBBinaryMeshSchema/1"
COMMON_HEADER_SIZE = 0x34
BONE_HEADER_SIZE = 0x08
STREAM_DESCRIPTOR_SIZE = 0x0C
BONE_SOURCE_MATRIX_SIZE = 0x30
RUNTIME_MATRIX_SIZE = 0x40
RUNTIME_PRIMITIVE_STRIDE = 0x50


def _require(data: bytes, offset: int, size: int, label: str) -> None:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError(
            f"{label} exceeds IMB payload: offset=0x{offset:x}, "
            f"size=0x{size:x}, payload=0x{len(data):x}"
        )


def _u32(data: bytes, offset: int) -> int:
    _require(data, offset, 4, "u32")
    return struct.unpack_from("<I", data, offset)[0]


def _f32(data: bytes, offset: int) -> float:
    _require(data, offset, 4, "f32")
    return struct.unpack_from("<f", data, offset)[0]


def _read_cstring(data: bytes, start: int, limit: int) -> tuple[str, int]:
    if start < 0 or start >= limit or limit > len(data):
        raise ValueError("invalid IMB string range")
    end = data.find(b"\x00", start, limit)
    if end < 0:
        raise ValueError("unterminated IMB bone name")
    return data[start:end].decode("utf-8", "replace"), end + 1


def _expand_source_matrix(values: list[float]) -> list[float]:
    if len(values) != 12:
        raise ValueError("IMB source bone matrix must contain 12 floats")
    return [
        values[0], values[1], values[2], 0.0,
        values[3], values[4], values[5], 0.0,
        values[6], values[7], values[8], 0.0,
        values[9], values[10], values[11], 1.0,
    ]


def parse_imb_binary_mesh_schema(
    data: bytes,
    *,
    header_offset: int,
    has_bone_block: bool,
) -> dict[str, Any]:
    """Decode the fixed IMB mesh header and stream descriptors.

    header_offset is the aligned fixed-header base reached by FUN_00859800
    after its version-dependent prefix and NUL-terminated resource name.
    has_bone_block corresponds to the loader's version/feature gate that
    controls the +0x34/+0x38 bone header.
    """
    header_offset = int(header_offset)
    _require(data, header_offset, COMMON_HEADER_SIZE, "IMB fixed header")

    vertex_count = _u32(data, header_offset + 0x00)
    stream_count = _u32(data, header_offset + 0x04)
    primitive_count = _u32(data, header_offset + 0x08)
    sphere = {
        "center_xyz": [
            _f32(data, header_offset + 0x0C),
            _f32(data, header_offset + 0x10),
            _f32(data, header_offset + 0x14),
        ],
        "radius": _f32(data, header_offset + 0x18),
    }
    aabb = {
        "min_xyz": [
            _f32(data, header_offset + 0x1C),
            _f32(data, header_offset + 0x20),
            _f32(data, header_offset + 0x24),
        ],
        "max_xyz": [
            _f32(data, header_offset + 0x28),
            _f32(data, header_offset + 0x2C),
            _f32(data, header_offset + 0x30),
        ],
    }

    bone_count = 0
    bone_names: list[str] = []
    bone_matrices: list[dict[str, Any]] = []
    if has_bone_block:
        _require(
            data,
            header_offset + COMMON_HEADER_SIZE,
            BONE_HEADER_SIZE,
            "IMB bone header",
        )
        bone_count = _u32(data, header_offset + 0x34)
        matrix_relative = _u32(data, header_offset + 0x38)
        names_start = header_offset + 0x3C
        matrices_start = names_start + matrix_relative
        if matrices_start < names_start or matrices_start > len(data):
            raise ValueError("IMB bone matrix block offset is outside payload")

        cursor = names_start
        for _ in range(bone_count):
            name, cursor = _read_cstring(data, cursor, matrices_start)
            bone_names.append(name)
        if cursor > matrices_start:
            raise ValueError("IMB bone names overlap matrix block")

        matrix_bytes = bone_count * BONE_SOURCE_MATRIX_SIZE
        _require(data, matrices_start, matrix_bytes, "IMB bone matrices")
        for index in range(bone_count):
            source_offset = matrices_start + index * BONE_SOURCE_MATRIX_SIZE
            values = list(struct.unpack_from("<12f", data, source_offset))
            bone_matrices.append({
                "index": index,
                "name": bone_names[index],
                "source_offset": source_offset,
                "source_storage": "12xf32 / four rows of xyz",
                "source_values": values,
                "runtime_matrix_4x4": _expand_source_matrix(values),
                "runtime_stride": RUNTIME_MATRIX_SIZE,
                "inverse_generated_by": "FUN_006308b0",
            })
        stream_section_offset = matrices_start + matrix_bytes
        bone_block = {
            "present": True,
            "count": bone_count,
            "count_source_offset": header_offset + 0x34,
            "matrix_block_relative_offset": matrix_relative,
            "names_offset": names_start,
            "matrices_offset": matrices_start,
            "names": bone_names,
            "matrices": bone_matrices,
            "runtime_name_array_offset": 0x64,
            "runtime_matrix_array_offset": 0x68,
            "runtime_inverse_matrix_array_offset": 0x6C,
        }
    else:
        stream_section_offset = header_offset + COMMON_HEADER_SIZE
        bone_block = {
            "present": False,
            "count": 0,
            "names": [],
            "matrices": [],
            "stream_section_reason": (
                "version/feature gate omits source +0x34/+0x38 bone header"
            ),
        }

    stream_bytes = stream_count * STREAM_DESCRIPTOR_SIZE
    _require(
        data,
        stream_section_offset,
        stream_bytes,
        "IMB stream descriptor table",
    )
    streams: list[dict[str, Any]] = []
    for index in range(stream_count):
        source_offset = stream_section_offset + index * STREAM_DESCRIPTOR_SIZE
        streams.append({
            "index": index,
            "source_offset": source_offset,
            "source_stride": STREAM_DESCRIPTOR_SIZE,
            "type_ordinal": _u32(data, source_offset + 0x00),
            "usage_ordinal": _u32(data, source_offset + 0x04),
            "channel": _u32(data, source_offset + 0x08),
            "runtime_declaration_stride": 0x08,
            "runtime_type_mapper": "FUN_00853c20",
            "runtime_usage_mapper": "FUN_00853c40",
        })

    vertex_payload_offset = stream_section_offset + stream_bytes

    return {
        "format": FORMAT,
        "version": 1,
        "status": "decoded",
        "decoded": True,
        "source": {
            "loader": "FUN_00859800",
            "retail_name": (
                "MWL::Renderer::WinRenderer::"
                "CMeshPrimitiveType::LoadBinaryMeshFromResource"
            ),
            "source_file": ".\\Source\\Platforms\\Win\\CPrimitiveType.cpp",
            "header_offset": header_offset,
            "prefix_auto_detection": False,
            "has_bone_block": bool(has_bone_block),
        },
        "header": {
            "common_size": COMMON_HEADER_SIZE,
            "vertex_count": vertex_count,
            "stream_count": stream_count,
            "primitive_count": primitive_count,
            "bounding_sphere": sphere,
            "aabb": aabb,
            "runtime_field_mapping": {
                "vertex_count": 0x18,
                "primitive_count": 0x28,
                "sphere_center_xyz": [0x30, 0x34, 0x38],
                "sphere_radius": 0x3C,
                "aabb_min_xyz": [0x40, 0x44, 0x48],
                "aabb_min_w": 0x4C,
                "aabb_max_xyz": [0x50, 0x54, 0x58],
                "aabb_max_w": 0x5C,
            },
        },
        "bones": bone_block,
        "streams": {
            "offset": stream_section_offset,
            "count": stream_count,
            "source_stride": STREAM_DESCRIPTOR_SIZE,
            "records": streams,
            "runtime_declaration_array_offset": 0x1C,
            "runtime_vertex_buffer_wrapper_offset": 0x24,
            "runtime_repack": (
                "source stream attributes are repacked into one interleaved "
                "runtime vertex buffer"
            ),
        },
        "vertex_payload_offset": vertex_payload_offset,
        "primitives": {
            "count": primitive_count,
            "runtime_array_offset": 0x2C,
            "runtime_stride": RUNTIME_PRIMITIVE_STRIDE,
            "source_section_offset": (
                "after variable-size vertex payload; not auto-derived in Phase 556"
            ),
            "known_runtime_fields": {
                "bounds_sphere": "record +0x00..+0x0c",
                "aabb_min": "record +0x10..+0x1c",
                "aabb_max": "record +0x20..+0x2c",
                "primitive_type": "record +0x30 = 4",
                "material_handle": "record +0x34",
                "primitive_count": "record +0x38",
                "index_count": "record +0x3c",
                "index_buffer": "record +0x40",
                "bone_palette_count": "record +0x44",
                "bone_palette": "record +0x48",
                "vertex_range_u16_pair": "record +0x4c/+0x4e",
            },
        },
        "boundary": {
            "fixed_header": "source-backed",
            "bone_block": "source-backed when caller supplies version gate",
            "stream_descriptor_triples": "source-backed",
            "vertex_payload_decode": "not-yet-implemented",
            "primitive_source_decode": "partially-mapped-not-yet-parsed",
            "variable_prefix": "unresolved",
            "meb_container_equivalence": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decode the source-backed fixed header of a SHIFT .imb mesh"
    )
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--header-offset", required=True, type=lambda x: int(x, 0))
    parser.add_argument("--has-bone-block", action="store_true")
    args = parser.parse_args(argv)

    data = Path(args.input).read_bytes()
    report = parse_imb_binary_mesh_schema(
        data,
        header_offset=args.header_offset,
        has_bone_block=args.has_bone_block,
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "vertex_count": report["header"]["vertex_count"],
        "stream_count": report["header"]["stream_count"],
        "primitive_count": report["header"]["primitive_count"],
        "bone_count": report["bones"]["count"],
        "vertex_payload_offset": report["vertex_payload_offset"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
