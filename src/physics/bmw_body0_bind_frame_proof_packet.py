#!/usr/bin/env python3
"""Build a positive-only native packet from SHIFT.BMWBody0BindFrameProof/1.

This adapter is deliberately fail-closed. It does not derive a bind frame and it
cannot turn a blocked/inferred artifact into retail truth. It only projects an
already-positive Process 1 proof into a compact packet that the native Process 2
runtime can load without embedding a general JSON parser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

PROOF_FORMAT = "SHIFT.BMWBody0BindFrameProof/1"
PACKET_FORMAT = "SHIFT.NativeBMWBody0BindFrameProofPacket/1"
BUILD_FORMAT = "SHIFT.NativeBMWBody0BindFrameProofPacketBuild/1"
MAGIC = b"BBFP"
VERSION = 1
BODY_INDEX = 0
BODY_NAME = "body"
FRAME_RELATION = "BODY0-local-to-VHF-vehicle-root"
MATRIX_CONVENTION = "row-major D3D row-vector affine"
HEADER = struct.Struct("<4sIIII16f")
MAX_SOURCE_TARGETS = 128
MAX_SOURCE_TARGET_BYTES = 4096


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("BODY0 bind proof must be a JSON object")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError(f"{label} must be an integer")


def _finite_matrix(value: Any) -> list[float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 16
    ):
        raise ValueError("BODY0 bind matrix must contain exactly 16 scalars")
    out: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError("BODY0 bind matrix contains a non-numeric value")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError("BODY0 bind matrix contains a non-finite value")
        out.append(number)
    if any(abs(out[index]) > 1.0e-6 for index in (3, 7, 11)):
        raise ValueError("BODY0 bind matrix is not D3D row-vector affine")
    if abs(out[15] - 1.0) > 1.0e-6:
        raise ValueError("BODY0 bind matrix homogeneous component is not one")
    a, b, c = out[0], out[1], out[2]
    d, e, f = out[4], out[5], out[6]
    g, h, i = out[8], out[9], out[10]
    determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if not math.isfinite(determinant) or abs(determinant) <= 1.0e-12:
        raise ValueError("BODY0 bind matrix linear block is singular")
    return out


def validate_positive_proof(value: Mapping[str, Any]) -> tuple[list[float], list[str]]:
    _require(value.get("format") == PROOF_FORMAT, f"expected {PROOF_FORMAT}")
    _require(value.get("ready") is True, "BODY0 bind proof is not ready")
    _require(value.get("status") == "ready", "BODY0 bind proof status is not ready")
    _require(value.get("evidence_state") == "proven-static", "BODY0 bind proof is not proven-static")
    _require(_int(value.get("body_index"), "body_index") == BODY_INDEX, "BODY0 bind proof index drift")
    _require(value.get("body_name") == BODY_NAME, "BODY0 bind proof name drift")
    _require(value.get("frame_relation") == FRAME_RELATION, "BODY0 bind frame relation drift")
    _require(value.get("matrix_convention") == MATRIX_CONVENTION, "BODY0 bind matrix convention drift")

    provenance = value.get("provenance")
    _require(isinstance(provenance, Mapping), "BODY0 bind proof provenance is missing")
    raw_targets = provenance.get("source_targets")
    _require(isinstance(raw_targets, list), "BODY0 bind proof source_targets must be a list")
    _require(0 < len(raw_targets) <= MAX_SOURCE_TARGETS, "BODY0 bind proof source target count is invalid")
    targets: list[str] = []
    for raw in raw_targets:
        _require(isinstance(raw, str) and bool(raw), "BODY0 bind proof contains an empty source target")
        encoded = raw.encode("utf-8")
        _require(len(encoded) <= MAX_SOURCE_TARGET_BYTES, "BODY0 bind proof source target is too long")
        _require(b"\0" not in encoded, "BODY0 bind proof source target contains NUL")
        targets.append(raw)

    scope = value.get("scope")
    _require(isinstance(scope, Mapping), "BODY0 bind proof scope is missing")
    _require(scope.get("identity_matrix_assumed") is False, "identity BODY0 bind assumption is not admissible")
    _require(scope.get("original_game_executed") is False, "BODY0 bind proof unexpectedly depends on original-game execution")
    _require(scope.get("new_runtime_capture_used") is False, "BODY0 bind proof unexpectedly depends on new runtime capture")

    matrix = _finite_matrix(value.get("body0_local_to_vhf_vehicle_root_row_matrix"))
    return matrix, targets


def build_packet(value: Mapping[str, Any]) -> bytes:
    matrix, targets = validate_positive_proof(value)
    target_blob = bytearray()
    for target in targets:
        encoded = target.encode("utf-8")
        target_blob.extend(struct.pack("<I", len(encoded)))
        target_blob.extend(encoded)
    header = HEADER.pack(
        MAGIC,
        VERSION,
        BODY_INDEX,
        len(targets),
        len(target_blob),
        *matrix,
    )
    return header + bytes(target_blob)


def build_from_path(input_path: Path, output_path: Path) -> dict[str, Any]:
    raw = input_path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("BODY0 bind proof must be a JSON object")
    packet = build_packet(value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(packet)
    _, targets = validate_positive_proof(value)
    return {
        "format": BUILD_FORMAT,
        "ready": True,
        "source_contract": PROOF_FORMAT,
        "packet_format": PACKET_FORMAT,
        "magic": MAGIC.decode("ascii"),
        "version": VERSION,
        "body_index": BODY_INDEX,
        "source_target_count": len(targets),
        "source_proof_sha256": hashlib.sha256(raw).hexdigest(),
        "packet_sha256": hashlib.sha256(packet).hexdigest(),
        "packet_bytes": len(packet),
        "retail_world_transform_admitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help=f"positive {PROOF_FORMAT} JSON")
    parser.add_argument("output", type=Path, help=f"{PACKET_FORMAT} binary packet")
    parser.add_argument("--report", type=Path, help=f"optional {BUILD_FORMAT} JSON report")
    args = parser.parse_args()
    report = build_from_path(args.input, args.output)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
