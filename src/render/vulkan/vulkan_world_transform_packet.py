"""Serialize a proven SHIFT scene world matrix for native Vulkan use.

SHIFT scene transforms are stored as row-major 4x4 matrices and consumed with
D3D row-vector semantics. GLSL mat4 storage is column-major by default. Uploading
the same 16 float bytes therefore presents the numeric transpose to GLSL, which
is exactly the column-vector equivalent of the original D3D transform.

This packet freezes that convention without assigning any retail shader
constant register.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.VulkanWorldTransformPacket/1"
MAGIC = b"SVWT"
VERSION = 1
CONVENTION_D3D_ROW_TO_GLSL_COLUMN = 1
HEADER = struct.Struct("<4sIII")
MATRIX = struct.Struct("<16f")


def _load(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _matrix(value: Any) -> list[float]:
    if isinstance(value, Mapping):
        value = value.get("world_matrix")
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and len(value) == 4
        and all(
            isinstance(row, Sequence)
            and not isinstance(row, (str, bytes, bytearray))
            and len(row) == 4
            for row in value
        )
    ):
        value = [item for row in value for item in row]

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) != 16
    ):
        raise ValueError("world matrix must contain exactly 16 scalars")

    result: list[float] = []
    for index, item in enumerate(value):
        if not isinstance(item, (int, float)):
            raise ValueError(f"world matrix scalar {index} is not numeric")
        scalar = float(item)
        if not math.isfinite(scalar):
            raise ValueError(f"world matrix scalar {index} is not finite")
        result.append(scalar)

    tolerance = 1e-5
    if (
        abs(result[3]) > tolerance
        or abs(result[7]) > tolerance
        or abs(result[11]) > tolerance
        or abs(result[15] - 1.0) > tolerance
    ):
        raise ValueError(
            "scene world matrix must be affine D3D row-vector form "
            "[m03,m13,m23,m33] = [0,0,0,1]"
        )
    return result


def transform_point_d3d_row_vector(
    matrix: Sequence[float],
    point_xyz: Sequence[float],
) -> list[float]:
    values = _matrix(matrix)
    if len(point_xyz) != 3:
        raise ValueError("point must contain exactly three scalars")
    point = [
        float(point_xyz[0]),
        float(point_xyz[1]),
        float(point_xyz[2]),
        1.0,
    ]
    return [
        sum(point[row] * values[row * 4 + column] for row in range(4))
        for column in range(4)
    ]


def build_vulkan_world_transform_packet(
    source: Mapping[str, Any] | Sequence[float] | str | Path,
    output: str | Path,
) -> dict[str, Any]:
    if isinstance(source, (str, Path)):
        source_value = _load(source)
    else:
        source_value = source
    matrix = _matrix(source_value)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = HEADER.pack(
        MAGIC,
        VERSION,
        CONVENTION_D3D_ROW_TO_GLSL_COLUMN,
        MATRIX.size,
    ) + MATRIX.pack(*matrix)
    output_path.write_bytes(payload)

    translation = matrix[12:15]
    return {
        "format": FORMAT,
        "version": VERSION,
        "output": str(output_path),
        "ready": True,
        "byte_size": len(payload),
        "matrix": matrix,
        "translation_xyz": translation,
        "binary": {
            "magic": "SVWT",
            "header_bytes": HEADER.size,
            "matrix_bytes": MATRIX.size,
            "convention": CONVENTION_D3D_ROW_TO_GLSL_COLUMN,
        },
        "semantics": {
            "source_storage": "row-major-4x4",
            "source_vector_convention": "D3D-row-vector",
            "source_equation": "p_world = p_object * world",
            "glsl_upload_bytes": "identical-to-source-row-major-bytes",
            "glsl_interpretation": "column-major-mat4",
            "glsl_numeric_matrix": "transpose(source-world)",
            "glsl_equation": "p_world_column = mat4(packet_bytes) * p_object_column",
            "retail_shader_register": "unassigned",
        },
        "boundary": {
            "serializes_world_transform": True,
            "executes_world_transform": False,
            "assigns_retail_constant_register": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        help="JSON containing world_matrix or SHIFT.RenderCommand/1 JSON",
    )
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = build_vulkan_world_transform_packet(args.input, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
