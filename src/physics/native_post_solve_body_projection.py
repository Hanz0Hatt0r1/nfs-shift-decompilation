"""Prepare exact FUN_007b4110 post-solve body projection for native parity.

The input must explicitly provide the solved scalar vector, initial BODY
accumulator state and all JOINT/HINGE/BAR rows. This module does not derive any
of those runtime-only values from static assets or from the builtin solver
frame.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

from sdf_post_solve_application_runtime import (
    apply_bar_solution,
    apply_hinge_solution,
    apply_joint_solution,
)

FORMAT = "SHIFT.NativePostSolveBodyProjection/1"
INPUT_FORMAT = "SHIFT.NativePostSolveBodyProjectionInput/1"
PACKET_FORMAT = "SHIFT.NativePostSolveBodyProjectionPacket/1"
PACKET_MAGIC = b"SBPS"
PACKET_VERSION = 1

PROOF_SOLVED_VECTOR = 1 << 0
PROOF_BODY_STATE = 1 << 1
PROOF_CONSTRAINT_ROWS = 1 << 2
REQUIRED_PROOF_FLAGS = (
    PROOF_SOLVED_VECTOR | PROOF_BODY_STATE | PROOF_CONSTRAINT_ROWS
)

_HEADER = struct.Struct("<4s8I")
_RECORD_HEAD = struct.Struct("<3I")


def _finite(value: Any, *, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _vec3(value: Any, *, label: str) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be a sequence")
    values = list(value)
    if len(values) != 3:
        raise ValueError(f"{label} must contain exactly three values")
    return [_finite(item, label=f"{label}[{index}]") for index, item in enumerate(values)]


def _proof(source: Mapping[str, Any], key: str) -> None:
    if source.get(key) is not True:
        raise ValueError(f"{key} must be explicitly true")


def _bodies(value: Any) -> list[dict[str, list[float]]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("bodies must be a sequence")
    rows = list(value)
    if not rows or len(rows) > 4096:
        raise ValueError("body count must be in range 1..4096")
    out = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"body {index} must be an object")
        out.append({
            "angular": _vec3(row.get("angular"), label=f"body[{index}].angular"),
            "linear": _vec3(row.get("linear"), label=f"body[{index}].linear"),
        })
    return out


def _solver(value: Any) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("solver_vector must be a sequence")
    rows = list(value)
    if not rows or len(rows) > 4096:
        raise ValueError("solver scalar count must be in range 1..4096")
    return [_finite(item, label=f"solver_vector[{index}]") for index, item in enumerate(rows)]


def _base_record(
    row: Mapping[str, Any],
    *,
    label: str,
    width: int,
    body_count: int,
    scalar_count: int,
) -> tuple[int, int, int]:
    pos = int(row.get("positive_body", -1))
    neg = int(row.get("negative_body", -1))
    base = int(row.get("scalar_base", -1))
    if pos < 0 or pos >= body_count or neg < 0 or neg >= body_count:
        raise ValueError(f"{label} body index out of range")
    if base < 0 or base + width > scalar_count:
        raise ValueError(f"{label} scalar range out of range")
    return pos, neg, base


def _records(
    source: Mapping[str, Any],
    *,
    body_count: int,
    scalar_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    joints: list[dict[str, Any]] = []
    hinges: list[dict[str, Any]] = []
    bars: list[dict[str, Any]] = []

    for index, raw in enumerate(source.get("joints") or []):
        if not isinstance(raw, Mapping):
            raise ValueError(f"joint {index} must be an object")
        pos, neg, base = _base_record(
            raw, label=f"joint[{index}]", width=3,
            body_count=body_count, scalar_count=scalar_count,
        )
        joints.append({
            "positive_body": pos,
            "negative_body": neg,
            "scalar_base": base,
            "positive_lever_arm": _vec3(
                raw.get("positive_lever_arm"),
                label=f"joint[{index}].positive_lever_arm",
            ),
            "negative_lever_arm": _vec3(
                raw.get("negative_lever_arm"),
                label=f"joint[{index}].negative_lever_arm",
            ),
        })

    for index, raw in enumerate(source.get("hinges") or []):
        if not isinstance(raw, Mapping):
            raise ValueError(f"hinge {index} must be an object")
        pos, neg, base = _base_record(
            raw, label=f"hinge[{index}]", width=2,
            body_count=body_count, scalar_count=scalar_count,
        )
        hinges.append({
            "positive_body": pos,
            "negative_body": neg,
            "scalar_base": base,
            "positive_angular_row": _vec3(
                raw.get("positive_angular_row"),
                label=f"hinge[{index}].positive_angular_row",
            ),
            "positive_linear_row": _vec3(
                raw.get("positive_linear_row"),
                label=f"hinge[{index}].positive_linear_row",
            ),
            "negative_angular_row": _vec3(
                raw.get("negative_angular_row"),
                label=f"hinge[{index}].negative_angular_row",
            ),
            "negative_linear_row": _vec3(
                raw.get("negative_linear_row"),
                label=f"hinge[{index}].negative_linear_row",
            ),
        })

    for index, raw in enumerate(source.get("bars") or []):
        if not isinstance(raw, Mapping):
            raise ValueError(f"bar {index} must be an object")
        pos, neg, base = _base_record(
            raw, label=f"bar[{index}]", width=1,
            body_count=body_count, scalar_count=scalar_count,
        )
        bars.append({
            "positive_body": pos,
            "negative_body": neg,
            "scalar_base": base,
            "positive_lever_arm": _vec3(
                raw.get("positive_lever_arm"),
                label=f"bar[{index}].positive_lever_arm",
            ),
            "negative_lever_arm": _vec3(
                raw.get("negative_lever_arm"),
                label=f"bar[{index}].negative_lever_arm",
            ),
            "direction": _vec3(
                raw.get("direction"),
                label=f"bar[{index}].direction",
            ),
        })
    return joints, hinges, bars


def _oracle(
    bodies: list[dict[str, list[float]]],
    solver: list[float],
    joints: list[dict[str, Any]],
    hinges: list[dict[str, Any]],
    bars: list[dict[str, Any]],
) -> list[dict[str, list[float]]]:
    state = [
        {"angular": list(row["angular"]), "linear": list(row["linear"])}
        for row in bodies
    ]

    for row in joints:
        pos = row["positive_body"]
        neg = row["negative_body"]
        result = apply_joint_solution(
            positive_state=state[pos],
            negative_state=state[neg],
            solver_vector=solver,
            scalar_base=row["scalar_base"],
            positive_lever_arm=row["positive_lever_arm"],
            negative_lever_arm=row["negative_lever_arm"],
        )
        state[pos] = {
            "angular": list(result["positive"]["angular"]),
            "linear": list(result["positive"]["linear"]),
        }
        state[neg] = {
            "angular": list(result["negative"]["angular"]),
            "linear": list(result["negative"]["linear"]),
        }

    for row in hinges:
        pos = row["positive_body"]
        neg = row["negative_body"]
        result = apply_hinge_solution(
            positive_angular=state[pos]["angular"],
            negative_angular=state[neg]["angular"],
            solver_vector=solver,
            scalar_base=row["scalar_base"],
            positive_angular_row=row["positive_angular_row"],
            positive_linear_row=row["positive_linear_row"],
            negative_angular_row=row["negative_angular_row"],
            negative_linear_row=row["negative_linear_row"],
        )
        state[pos]["angular"] = list(result["positive_angular"])
        state[neg]["angular"] = list(result["negative_angular"])

    for row in bars:
        pos = row["positive_body"]
        neg = row["negative_body"]
        result = apply_bar_solution(
            positive_state=state[pos],
            negative_state=state[neg],
            solver_vector=solver,
            scalar_base=row["scalar_base"],
            positive_lever_arm=row["positive_lever_arm"],
            negative_lever_arm=row["negative_lever_arm"],
            bar_direction=row["direction"],
        )
        state[pos] = {
            "angular": list(result["positive"]["angular"]),
            "linear": list(result["positive"]["linear"]),
        }
        state[neg] = {
            "angular": list(result["negative"]["angular"]),
            "linear": list(result["negative"]["linear"]),
        }
    return state


def _pack_vec(output: bytearray, values: Sequence[float]) -> None:
    output += struct.pack("<3d", *[float(value) for value in values])


def _serialize(
    bodies: list[dict[str, list[float]]],
    solver: list[float],
    joints: list[dict[str, Any]],
    hinges: list[dict[str, Any]],
    bars: list[dict[str, Any]],
    expected: list[dict[str, list[float]]],
) -> bytes:
    output = bytearray(_HEADER.pack(
        PACKET_MAGIC,
        PACKET_VERSION,
        len(bodies),
        len(solver),
        len(joints),
        len(hinges),
        len(bars),
        REQUIRED_PROOF_FLAGS,
        0,
    ))
    for body in bodies:
        _pack_vec(output, body["angular"])
        _pack_vec(output, body["linear"])
    output += struct.pack("<" + "d" * len(solver), *solver)

    for row in joints:
        output += _RECORD_HEAD.pack(
            row["positive_body"], row["negative_body"], row["scalar_base"]
        )
        _pack_vec(output, row["positive_lever_arm"])
        _pack_vec(output, row["negative_lever_arm"])

    for row in hinges:
        output += _RECORD_HEAD.pack(
            row["positive_body"], row["negative_body"], row["scalar_base"]
        )
        _pack_vec(output, row["positive_angular_row"])
        _pack_vec(output, row["positive_linear_row"])
        _pack_vec(output, row["negative_angular_row"])
        _pack_vec(output, row["negative_linear_row"])

    for row in bars:
        output += _RECORD_HEAD.pack(
            row["positive_body"], row["negative_body"], row["scalar_base"]
        )
        _pack_vec(output, row["positive_lever_arm"])
        _pack_vec(output, row["negative_lever_arm"])
        _pack_vec(output, row["direction"])

    for body in expected:
        _pack_vec(output, body["angular"])
        _pack_vec(output, body["linear"])
    return bytes(output)


def build_native_post_solve_body_projection(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if source.get("format") != INPUT_FORMAT:
        raise ValueError(f"input must be {INPUT_FORMAT}")
    for key in (
        "solved_vector_ready",
        "body_state_ready",
        "constraint_rows_ready",
    ):
        _proof(source, key)

    bodies = _bodies(source.get("bodies"))
    solver = _solver(source.get("solver_vector"))
    joints, hinges, bars = _records(
        source,
        body_count=len(bodies),
        scalar_count=len(solver),
    )
    expected = _oracle(bodies, solver, joints, hinges, bars)
    packet = _serialize(bodies, solver, joints, hinges, bars, expected)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "verification_scope": source.get("verification_scope"),
        "source_function": "FUN_007b4110",
        "body_count": len(bodies),
        "scalar_count": len(solver),
        "constraint_counts": {
            "JOINT": len(joints),
            "HINGE": len(hinges),
            "BAR": len(bars),
        },
        "proofs": {
            "solved_vector_ready": True,
            "body_state_ready": True,
            "constraint_rows_ready": True,
        },
        "oracle": {
            "format": "SHIFT.NativePostSolveBodyProjectionOracle/1",
            "bodies": expected,
            "source": "Python source-backed FUN_007b4110 projection",
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
            "derives_solved_vector": False,
            "derives_body_state": False,
            "derives_constraint_rows": False,
            "provider_path_supported": True,
            "fixed_step_runtime_integration": False,
            "fixed_step_runtime_consumer_available": True,
            "persistent_body_accumulator_mode_available": True,
            "persistent_vehicle_state_available": False,
            "assigns_physical_units": False,
        },
    }


def build_native_post_solve_body_projection_file(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(source, Mapping):
        raise ValueError("input JSON must be an object")
    report = build_native_post_solve_body_projection(source)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    packet = bytes(report["packet"].pop("bytes"))
    packet_path = root / "post_solve.sbps"
    packet_path.write_bytes(packet)
    report["packet"]["path"] = packet_path.name
    (root / "post_solve_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output_dir")
    args = parser.parse_args(argv)
    report = build_native_post_solve_body_projection_file(
        args.input, args.output_dir
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "body_count": report["body_count"],
        "scalar_count": report["scalar_count"],
        "constraint_counts": report["constraint_counts"],
        "packet_sha256": report["packet"]["sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
