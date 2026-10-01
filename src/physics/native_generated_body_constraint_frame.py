"""Prepare BODY constraint sample/state inputs for native contribution generation.

Unlike SBEX, this packet does not contain generated solver-vector or
solver-matrix contribution values. Native code must derive them through the
Phase 624/625/626 chain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

INPUT_FORMAT = "SHIFT.NativeGeneratedBodyConstraintFrameInput/1"
FORMAT = "SHIFT.NativeGeneratedBodyConstraintFrame/1"
PACKET_FORMAT = "SHIFT.NativeGeneratedBodyConstraintFramePacket/1"
PACKET_MAGIC = b"GBCF"
PACKET_VERSION = 1

PROOF_SAMPLE_VALUES = 1 << 0
PROOF_BODY_ORDER = 1 << 1
PROOF_ROW_LAYOUT = 1 << 2
PROOF_PROVIDER_ABSENT = 1 << 3
REQUIRED_PROOF_FLAGS = (
    PROOF_SAMPLE_VALUES
    | PROOF_BODY_ORDER
    | PROOF_ROW_LAYOUT
    | PROOF_PROVIDER_ABSENT
)

_HEADER = struct.Struct("<4s6I")
_BODY_HEAD = struct.Struct("<6I")
_JOINT = struct.Struct("<3dIB3x")
_HINGE = struct.Struct("<12dIB3x")
_BAR = struct.Struct("<7dIB3x")


def _proof(source: Mapping[str, Any], key: str) -> None:
    if source.get(key) is not True:
        raise ValueError(f"{key} must be explicitly true")


def _finite_vector(
    value: Any,
    *,
    label: str,
    count: int,
) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError(f"{label} must be an array")
    result = [float(item) for item in value]
    if len(result) != count:
        raise ValueError(f"{label} must contain exactly {count} values")
    if any(not math.isfinite(item) for item in result):
        raise ValueError(f"{label} contains non-finite value")
    return result


def _matrix3(value: Any, *, label: str) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError(f"{label} must be a 3x3 array")
    rows = list(value)
    if len(rows) != 3:
        raise ValueError(f"{label} must be a 3x3 array")
    result: list[float] = []
    for row_index, row in enumerate(rows):
        result.extend(
            _finite_vector(
                row,
                label=f"{label}[{row_index}]",
                count=3,
            )
        )
    return result


def _finite_scalar(value: Any, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _side_flag(value: Any, *, label: str) -> int:
    result = int(value)
    if result not in (0, 1):
        raise ValueError(f"{label} must be 0 or 1")
    return result


def _scalar_base(
    value: Any,
    *,
    width: int,
    scalar_count: int,
    label: str,
) -> int:
    result = int(value)
    if result < 0 or result + width > scalar_count:
        raise ValueError(f"{label} is outside solver scalar domain")
    return result


def _joint_rows(
    value: Any,
    *,
    scalar_count: int,
    body_index: int,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"body[{body_index}].joints must be an array")
    result = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise ValueError(
                f"body[{body_index}].joints[{index}] must be an object"
            )
        result.append({
            "position": _finite_vector(
                row.get("position"),
                label=f"body[{body_index}].joints[{index}].position",
                count=3,
            ),
            "scalar_base": _scalar_base(
                row.get("scalar_base"),
                width=3,
                scalar_count=scalar_count,
                label=f"body[{body_index}].joints[{index}].scalar_base",
            ),
            "side_flag": _side_flag(
                row.get("side_flag"),
                label=f"body[{body_index}].joints[{index}].side_flag",
            ),
        })
    return result


def _hinge_rows(
    value: Any,
    *,
    scalar_count: int,
    body_index: int,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"body[{body_index}].hinges must be an array")
    result = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise ValueError(
                f"body[{body_index}].hinges[{index}] must be an object"
            )
        prefix = f"body[{body_index}].hinges[{index}]"
        result.append({
            "angular": _finite_vector(
                row.get("angular"), label=f"{prefix}.angular", count=3
            ),
            "linear": _finite_vector(
                row.get("linear"), label=f"{prefix}.linear", count=3
            ),
            "position": _finite_vector(
                row.get("position"), label=f"{prefix}.position", count=3
            ),
            "frame_offset": _finite_vector(
                row.get("frame_offset"),
                label=f"{prefix}.frame_offset",
                count=3,
            ),
            "scalar_base": _scalar_base(
                row.get("scalar_base"),
                width=2,
                scalar_count=scalar_count,
                label=f"{prefix}.scalar_base",
            ),
            "side_flag": _side_flag(
                row.get("side_flag"), label=f"{prefix}.side_flag"
            ),
        })
    return result


def _bar_rows(
    value: Any,
    *,
    scalar_count: int,
    body_index: int,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"body[{body_index}].bars must be an array")
    result = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise ValueError(
                f"body[{body_index}].bars[{index}] must be an object"
            )
        prefix = f"body[{body_index}].bars[{index}]"
        result.append({
            "point": _finite_vector(
                row.get("point"), label=f"{prefix}.point", count=3
            ),
            "direction": _finite_vector(
                row.get("direction"),
                label=f"{prefix}.direction",
                count=3,
            ),
            "side_bias": _finite_scalar(
                row.get("side_bias"), label=f"{prefix}.side_bias"
            ),
            "scalar_base": _scalar_base(
                row.get("scalar_base"),
                width=1,
                scalar_count=scalar_count,
                label=f"{prefix}.scalar_base",
            ),
            "side_flag": _side_flag(
                row.get("side_flag"), label=f"{prefix}.side_flag"
            ),
        })
    return result


def _body_rows(
    source: Mapping[str, Any],
    *,
    scalar_count: int,
) -> list[dict[str, Any]]:
    raw = source.get("bodies")
    if not isinstance(raw, list) or not raw:
        raise ValueError("bodies must be a non-empty array")
    if int(source.get("body_count", -1)) != len(raw):
        raise ValueError("body_count must equal bodies length")

    canonical_rows = [row * scalar_count for row in range(scalar_count)]
    result: list[dict[str, Any]] = []
    for ordinal, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise ValueError(f"body[{ordinal}] must be an object")
        if int(row.get("body_index", -1)) != ordinal:
            raise ValueError(
                "BODY order must be contiguous and match body_index"
            )
        row_indices = [int(value) for value in row.get("row_indices") or []]
        if row_indices != canonical_rows:
            raise ValueError(
                f"body[{ordinal}].row_indices must use canonical builtin layout"
            )
        matrix_double_count = int(
            row.get("matrix_double_count", scalar_count * scalar_count)
        )
        if matrix_double_count != scalar_count * scalar_count:
            raise ValueError(
                f"body[{ordinal}].matrix_double_count must equal N squared"
            )

        scales = row.get("scales")
        if not isinstance(scales, Mapping):
            raise ValueError(f"body[{ordinal}].scales must be an object")

        result.append({
            "body_index": ordinal,
            "body_position": _finite_vector(
                row.get("body_position"),
                label=f"body[{ordinal}].body_position",
                count=3,
            ),
            "body_correction": _finite_vector(
                row.get("body_correction"),
                label=f"body[{ordinal}].body_correction",
                count=3,
            ),
            "body_axis": _finite_vector(
                row.get("body_axis"),
                label=f"body[{ordinal}].body_axis",
                count=3,
            ),
            "angular_state": _finite_vector(
                row.get("angular_state"),
                label=f"body[{ordinal}].angular_state",
                count=3,
            ),
            "linear_state": _finite_vector(
                row.get("linear_state"),
                label=f"body[{ordinal}].linear_state",
                count=3,
            ),
            "inverse_scalar": _finite_scalar(
                row.get("inverse_scalar"),
                label=f"body[{ordinal}].inverse_scalar",
            ),
            "body_frame": _finite_vector(
                row.get("body_frame"),
                label=f"body[{ordinal}].body_frame",
                count=9,
            ),
            "body_tensor": _matrix3(
                row.get("body_tensor"),
                label=f"body[{ordinal}].body_tensor",
            ),
            "linear_scale": _finite_scalar(
                scales.get("linear_scale"),
                label=f"body[{ordinal}].scales.linear_scale",
            ),
            "quadratic_scale": _finite_scalar(
                scales.get("quadratic_scale"),
                label=f"body[{ordinal}].scales.quadratic_scale",
            ),
            "row_indices": row_indices,
            "matrix_double_count": matrix_double_count,
            "joints": _joint_rows(
                row.get("joints", []),
                scalar_count=scalar_count,
                body_index=ordinal,
            ),
            "hinges": _hinge_rows(
                row.get("hinges", []),
                scalar_count=scalar_count,
                body_index=ordinal,
            ),
            "bars": _bar_rows(
                row.get("bars", []),
                scalar_count=scalar_count,
                body_index=ordinal,
            ),
        })
    return result


def _serialize(
    bodies: Sequence[Mapping[str, Any]],
    *,
    scalar_count: int,
) -> bytes:
    matrix_double_count = scalar_count * scalar_count
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
        output += _BODY_HEAD.pack(
            int(body["body_index"]),
            len(body["joints"]),
            len(body["hinges"]),
            len(body["bars"]),
            len(body["row_indices"]),
            0,
        )
        output += struct.pack("<15d", *(
            body["body_position"]
            + body["body_correction"]
            + body["body_axis"]
            + body["angular_state"]
            + body["linear_state"]
        ))
        output += struct.pack("<d", body["inverse_scalar"])
        output += struct.pack("<9f", *body["body_frame"])
        output += struct.pack("<9d", *body["body_tensor"])
        output += struct.pack(
            "<2d",
            body["linear_scale"],
            body["quadratic_scale"],
        )
        output += struct.pack(
            "<" + "I" * scalar_count,
            *body["row_indices"],
        )
        for sample in body["joints"]:
            output += _JOINT.pack(
                *sample["position"],
                sample["scalar_base"],
                sample["side_flag"],
            )
        for sample in body["hinges"]:
            output += _HINGE.pack(
                *sample["angular"],
                *sample["linear"],
                *sample["position"],
                *sample["frame_offset"],
                sample["scalar_base"],
                sample["side_flag"],
            )
        for sample in body["bars"]:
            output += _BAR.pack(
                *sample["point"],
                *sample["direction"],
                sample["side_bias"],
                sample["scalar_base"],
                sample["side_flag"],
            )
    return bytes(output)


def build_native_generated_body_constraint_frame(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if source.get("format") != INPUT_FORMAT:
        raise ValueError(f"input must be {INPUT_FORMAT}")
    _proof(source, "sample_values_ready")
    _proof(source, "body_order_ready")
    _proof(source, "row_layout_ready")
    _proof(source, "provider_absent")

    scalar_count = int(source.get("solver_scalar_count", 0))
    if scalar_count <= 0 or scalar_count > 4096:
        raise ValueError("solver_scalar_count out of range")
    bodies = _body_rows(source, scalar_count=scalar_count)
    packet = _serialize(bodies, scalar_count=scalar_count)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "verification_scope": source.get("verification_scope"),
        "body_count": len(bodies),
        "solver_scalar_count": scalar_count,
        "solver_matrix_double_count": scalar_count * scalar_count,
        "sample_counts": {
            "joint": sum(len(row["joints"]) for row in bodies),
            "hinge": sum(len(row["hinges"]) for row in bodies),
            "bar": sum(len(row["bars"]) for row in bodies),
        },
        "proofs": {
            "sample_values_ready": True,
            "body_order_ready": True,
            "row_layout_ready": True,
            "provider_absent": True,
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
            "stores_generated_contribution_values": False,
            "derives_contributions_in_native": True,
            "sample_refresh_function": "FUN_007b3ed0",
            "sample_refresh_executed": False,
            "provider_present": False,
            "canonical_builtin_row_layout": True,
            "fixed_step_runtime_integration": False,
            "assigns_physical_units": False,
        },
    }


def build_native_generated_body_constraint_frame_file(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(source, Mapping):
        raise ValueError("input JSON must be an object")
    report = build_native_generated_body_constraint_frame(source)

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    packet = bytes(report["packet"].pop("bytes"))
    packet_path = root / "generated_body_constraints.gbcf"
    packet_path.write_bytes(packet)
    report["packet"]["path"] = packet_path.name
    (root / "generated_body_constraints_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output_dir")
    args = parser.parse_args(argv)
    report = build_native_generated_body_constraint_frame_file(
        args.input,
        args.output_dir,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "body_count": report["body_count"],
        "solver_scalar_count": report["solver_scalar_count"],
        "sample_counts": report["sample_counts"],
        "packet_sha256": report["packet"]["sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
