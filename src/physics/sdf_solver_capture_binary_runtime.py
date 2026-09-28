"""Explicit-offset binary ingestion for captured SHIFT SDF solver state."""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any, Mapping

from sdf_solver_capture_runtime import normalize_solver_capture

FORMAT = "SHIFT.SDFSolverCaptureBinaryRuntime/1"


def _read_doubles(data: bytes, offset: int, count: int, *, name: str) -> list[float]:
    start = int(offset)
    size = int(count) * 8
    if start < 0:
        raise ValueError(f"{name} offset must be non-negative")
    if count < 0:
        raise ValueError(f"{name} count must be non-negative")
    end = start + size
    if end > len(data):
        raise ValueError(
            f"{name} exceeds capture bounds: offset={start} size={size} file={len(data)}"
        )
    if not count:
        return []
    return list(struct.unpack_from("<" + "d" * int(count), data, start))


def read_flat_solver_capture(
    data: bytes,
    *,
    scalar_count: int,
    rhs_offset: int,
    matrix_offset: int,
    row_indices: list[int] | None = None,
    runtime_identity_nodes: list[int] | None = None,
    frame: int | None = None,
    source: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read RHS and a contiguous row-major matrix from an arbitrary memory dump.

    The caller must provide byte offsets relative to the supplied capture blob.
    No memory layout is inferred from addresses outside the blob.
    """
    n = int(scalar_count)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")

    rhs = _read_doubles(data, rhs_offset, n, name="rhs")
    flat_matrix = _read_doubles(data, matrix_offset, n * n, name="matrix")
    matrix = [
        flat_matrix[row * n:(row + 1) * n]
        for row in range(n)
    ]

    capture: dict[str, Any] = {
        "scalar_count": n,
        "rhs": rhs,
        "matrix": matrix,
        "runtime_identity_nodes": list(runtime_identity_nodes or []),
        "metadata": dict(metadata or {}),
    }
    if row_indices is not None:
        capture["row_indices"] = [int(value) for value in row_indices]
    if frame is not None:
        capture["frame"] = int(frame)
    if source is not None:
        capture["source"] = source

    normalized = normalize_solver_capture(capture)
    return {
        **normalized,
        "binary": {
            "rhs_offset": int(rhs_offset),
            "matrix_offset": int(matrix_offset),
            "matrix_bytes": n * n * 8,
            "rhs_bytes": n * 8,
            "endianness": "little",
            "encoding": "IEEE-754 binary64",
        },
    }


def read_flat_solver_capture_file(
    path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    return read_flat_solver_capture(source.read_bytes(), source=str(source), **kwargs)


def capture_to_json(
    capture: Mapping[str, Any],
    output: str | Path,
) -> dict[str, Any]:
    import json

    normalized = normalize_solver_capture(capture)
    payload = dict(normalized)
    Path(output).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "format": "SHIFT.SDFSolverCaptureJsonExport/1",
        "version": 1,
        "ready": True,
        "output": str(output),
        "scalar_count": normalized["scalar_count"],
    }


def describe_sdf_solver_capture_binary_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "explicit-offset-binary-reader",
        "ready": True,
        "inputs": {
            "scalar_count": "required integer",
            "rhs_offset": "required byte offset",
            "matrix_offset": "required byte offset",
            "endianness": "little",
            "number_format": "IEEE-754 binary64",
        },
        "layout": {
            "rhs_bytes": "scalar_count * 8",
            "matrix_bytes": "scalar_count * scalar_count * 8",
            "matrix_order": "row-major",
            "optional_row_indices": "scalar_count 32-bit logical row offsets",
        },
        "fail_closed": [
            "negative offsets rejected",
            "truncated RHS rejected",
            "truncated matrix rejected",
            "schema shape violations rejected",
        ],
        "relationship_to_retail": {
            "scalar_count": "PhysicsSystem +0x34",
            "rhs_storage": "PhysicsSystem +0x40",
            "matrix_storage": "PhysicsSystem +0x3c / row-pointer storage",
        },
        "limitations": [
            "The byte offsets are capture-specific and are never inferred.",
            "A raw dump is not claimed to be a solver frame until the caller supplies correct offsets and metadata.",
        ],
    }


__all__ = [
    "read_flat_solver_capture",
    "read_flat_solver_capture_file",
    "capture_to_json",
    "describe_sdf_solver_capture_binary_contract",
]
