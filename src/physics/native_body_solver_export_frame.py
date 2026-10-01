"""Prepare explicit per-BODY FUN_007ba570 contributions for native replay.

This contract does not derive BODY-local +0x150/+0x154 values. Callers must
supply them together with exact BODY order and global solver scalar shape.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

from sdf_body_solver_export_runtime import export_body_solver_contributions

INPUT_FORMAT = "SHIFT.NativeBodySolverExportFrameInput/1"
FORMAT = "SHIFT.NativeBodySolverExportFrame/1"
PACKET_FORMAT = "SHIFT.NativeBodySolverExportFramePacket/1"
PACKET_MAGIC = b"SBEX"
PACKET_VERSION = 1

PROOF_CONTRIBUTIONS = 1 << 0
PROOF_BODY_ORDER = 1 << 1
PROOF_DESTINATION_SHAPE = 1 << 2
REQUIRED_PROOF_FLAGS = (
    PROOF_CONTRIBUTIONS
    | PROOF_BODY_ORDER
    | PROOF_DESTINATION_SHAPE
)

_HEADER = struct.Struct("<4s6I")
_BODY_HEAD = struct.Struct("<III")


def _proof(source: Mapping[str, Any], key: str) -> None:
    if source.get(key) is not True:
        raise ValueError(f"{key} must be explicitly true")


def _finite_values(
    value: Any,
    *,
    label: str,
    limit: int,
) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError(f"{label} must be an array")
    rows = [float(item) for item in value]
    if len(rows) > limit:
        raise ValueError(f"{label} exceeds destination length")
    if any(not math.isfinite(item) for item in rows):
        raise ValueError(f"{label} contains non-finite value")
    return rows


def _body_rows(
    source: Mapping[str, Any],
    *,
    scalar_count: int,
    matrix_double_count: int,
) -> list[dict[str, Any]]:
    raw = source.get("bodies")
    if not isinstance(raw, list) or not raw:
        raise ValueError("bodies must be a non-empty array")

    expected_body_count = int(source.get("body_count", -1))
    if expected_body_count != len(raw):
        raise ValueError("body_count must equal bodies length")

    rows: list[dict[str, Any]] = []
    for ordinal, value in enumerate(raw):
        if not isinstance(value, Mapping):
            raise ValueError(f"body[{ordinal}] must be an object")
        body_index = int(value.get("body_index", -1))
        if body_index != ordinal:
            raise ValueError(
                "BODY order must be contiguous and match body_index"
            )
        rows.append({
            "body_index": body_index,
            "solver_vector": _finite_values(
                value.get("solver_vector"),
                label=f"body[{ordinal}].solver_vector",
                limit=scalar_count,
            ),
            "solver_matrix": _finite_values(
                value.get("solver_matrix"),
                label=f"body[{ordinal}].solver_matrix",
                limit=matrix_double_count,
            ),
        })
    return rows


def _oracle(
    bodies: Sequence[Mapping[str, Any]],
    *,
    scalar_count: int,
    matrix_double_count: int,
) -> tuple[list[float], list[float]]:
    vector = [0.0] * scalar_count
    matrix = [0.0] * matrix_double_count
    for body in bodies:
        result = export_body_solver_contributions(
            body["solver_vector"],
            body["solver_matrix"],
            vector,
            matrix,
        )
        vector = list(result["solver_vector"])
        matrix = list(result["solver_matrix"])
    return vector, matrix


def _serialize(
    bodies: Sequence[Mapping[str, Any]],
    *,
    scalar_count: int,
    matrix_double_count: int,
    expected_vector: Sequence[float],
    expected_matrix: Sequence[float],
) -> bytes:
    output = bytearray(_HEADER.pack(
        PACKET_MAGIC,
        PACKET_VERSION,
        len(bodies),
        scalar_count,
        matrix_double_count,
        REQUIRED_PROOF_FLAGS,
        0,
    ))
    for body in bodies:
        vector = body["solver_vector"]
        matrix = body["solver_matrix"]
        output += _BODY_HEAD.pack(
            int(body["body_index"]),
            len(vector),
            len(matrix),
        )
        if vector:
            output += struct.pack(
                "<" + "d" * len(vector),
                *vector,
            )
        if matrix:
            output += struct.pack(
                "<" + "d" * len(matrix),
                *matrix,
            )
    output += struct.pack(
        "<" + "d" * len(expected_vector),
        *expected_vector,
    )
    output += struct.pack(
        "<" + "d" * len(expected_matrix),
        *expected_matrix,
    )
    return bytes(output)


def build_native_body_solver_export_frame(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if source.get("format") != INPUT_FORMAT:
        raise ValueError(f"input must be {INPUT_FORMAT}")
    _proof(source, "contribution_values_ready")
    _proof(source, "body_order_ready")
    _proof(source, "destination_shape_ready")

    scalar_count = int(source.get("solver_scalar_count", 0))
    if scalar_count <= 0 or scalar_count > 4096:
        raise ValueError("solver_scalar_count out of range")
    matrix_double_count = scalar_count * scalar_count

    bodies = _body_rows(
        source,
        scalar_count=scalar_count,
        matrix_double_count=matrix_double_count,
    )
    expected_vector, expected_matrix = _oracle(
        bodies,
        scalar_count=scalar_count,
        matrix_double_count=matrix_double_count,
    )
    packet = _serialize(
        bodies,
        scalar_count=scalar_count,
        matrix_double_count=matrix_double_count,
        expected_vector=expected_vector,
        expected_matrix=expected_matrix,
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "verification_scope": source.get("verification_scope"),
        "source_function": "FUN_007ba570",
        "body_count": len(bodies),
        "solver_scalar_count": scalar_count,
        "solver_matrix_double_count": matrix_double_count,
        "body_contributions": [
            {
                "body_index": row["body_index"],
                "solver_vector_count": len(row["solver_vector"]),
                "solver_matrix_count": len(row["solver_matrix"]),
            }
            for row in bodies
        ],
        "proofs": {
            "contribution_values_ready": True,
            "body_order_ready": True,
            "destination_shape_ready": True,
        },
        "oracle": {
            "solver_vector": expected_vector,
            "solver_matrix": expected_matrix,
            "source": (
                "sequential Python FUN_007ba570 additive export"
            ),
        },
        "packet": {
            "format": PACKET_FORMAT,
            "magic": PACKET_MAGIC.decode("ascii"),
            "version": PACKET_VERSION,
            "size": len(packet),
            "sha256": hashlib.sha256(packet).hexdigest(),
            "bytes": packet,
        },
        "boundary": {
            "derives_body_contributions": False,
            "derives_constraint_projection": False,
            "derives_reset_selection": False,
            "zero_initializes_global_destinations": True,
            "ordered_fun_007ba570_replay": True,
            "fixed_step_runtime_integration": False,
            "assigns_physical_units": False,
        },
    }


def build_native_body_solver_export_frame_file(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = json.loads(
        Path(input_path).read_text(encoding="utf-8")
    )
    if not isinstance(source, Mapping):
        raise ValueError("input JSON must be an object")
    report = build_native_body_solver_export_frame(source)

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    packet = bytes(report["packet"].pop("bytes"))
    packet_path = root / "body_solver_export.sbex"
    packet_path.write_bytes(packet)
    report["packet"]["path"] = packet_path.name
    (root / "body_solver_export_manifest.json").write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output_dir")
    args = parser.parse_args(argv)
    report = build_native_body_solver_export_frame_file(
        args.input,
        args.output_dir,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "body_count": report["body_count"],
        "solver_scalar_count": report["solver_scalar_count"],
        "solver_matrix_double_count": (
            report["solver_matrix_double_count"]
        ),
        "packet_sha256": report["packet"]["sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
