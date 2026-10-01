"""Prepare retail constraint relation ownership for native sample refresh.

CSRF carries only top-level relation ownership plus raw local endpoint inputs.
BODY frames/positions and static sample metadata remain authoritative in GBCF.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

INPUT_FORMAT = "SHIFT.NativeConstraintSampleRelationFrameInput/1"
FORMAT = "SHIFT.NativeConstraintSampleRelationFrame/1"
PACKET_FORMAT = "SHIFT.NativeConstraintSampleRelationFramePacket/1"
PACKET_MAGIC = b"CSRF"
PACKET_VERSION = 1

PROOF_RAW_SAMPLE_VALUES = 1 << 0
PROOF_OWNERSHIP = 1 << 1
PROOF_SOURCE_ORDER = 1 << 2
PROOF_PROVIDER_ABSENT = 1 << 3
REQUIRED_PROOF_FLAGS = (
    PROOF_RAW_SAMPLE_VALUES
    | PROOF_OWNERSHIP
    | PROOF_SOURCE_ORDER
    | PROOF_PROVIDER_ABSENT
)

_HEADER = struct.Struct("<4s7I")
_RELATION_HEAD = struct.Struct("<4I")
_RELATION_VALUES = struct.Struct("<6d")


def _proof(source: Mapping[str, Any], key: str) -> None:
    if source.get(key) is not True:
        raise ValueError(f"{key} must be explicitly true")


def _finite_vec3(value: Any, *, label: str) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError(f"{label} must be an array")
    result = [float(item) for item in value]
    if len(result) != 3:
        raise ValueError(f"{label} must contain exactly 3 values")
    if any(not math.isfinite(item) for item in result):
        raise ValueError(f"{label} contains non-finite value")
    return result


def _endpoint(
    value: Any,
    *,
    body_count: int,
    label: str,
) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    body_index = int(value.get("body_index", -1))
    sample_index = int(value.get("sample_index", -1))
    if body_index < 0 or body_index >= body_count:
        raise ValueError(f"{label}.body_index is outside BODY domain")
    if sample_index < 0 or sample_index > 0xFFFFFFFF:
        raise ValueError(f"{label}.sample_index is outside uint32 domain")
    return {
        "body_index": body_index,
        "sample_index": sample_index,
    }


def _relations(
    value: Any,
    *,
    body_count: int,
    kind: str,
    positive_field: str,
    negative_field: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{kind}_relations must be an array")
    if len(value) > 4096:
        raise ValueError(f"{kind}_relations exceeds supported count")

    result = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise ValueError(
                f"{kind}_relations[{index}] must be an object"
            )
        prefix = f"{kind}_relations[{index}]"
        result.append({
            "positive": _endpoint(
                row.get("positive"),
                body_count=body_count,
                label=f"{prefix}.positive",
            ),
            "negative": _endpoint(
                row.get("negative"),
                body_count=body_count,
                label=f"{prefix}.negative",
            ),
            positive_field: _finite_vec3(
                row.get(positive_field),
                label=f"{prefix}.{positive_field}",
            ),
            negative_field: _finite_vec3(
                row.get(negative_field),
                label=f"{prefix}.{negative_field}",
            ),
        })
    return result


def _serialize_relation(
    row: Mapping[str, Any],
    positive_field: str,
    negative_field: str,
) -> bytes:
    positive = row["positive"]
    negative = row["negative"]
    output = bytearray(_RELATION_HEAD.pack(
        int(positive["body_index"]),
        int(positive["sample_index"]),
        int(negative["body_index"]),
        int(negative["sample_index"]),
    ))
    output += _RELATION_VALUES.pack(
        *row[positive_field],
        *row[negative_field],
    )
    return bytes(output)


def build_native_constraint_sample_relation_frame(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if source.get("format") != INPUT_FORMAT:
        raise ValueError(f"input must be {INPUT_FORMAT}")
    _proof(source, "raw_sample_values_ready")
    _proof(source, "ownership_ready")
    _proof(source, "source_order_ready")
    _proof(source, "provider_absent")

    body_count = int(source.get("body_count", 0))
    if body_count <= 0 or body_count > 4096:
        raise ValueError("body_count out of range")

    joints = _relations(
        source.get("joint_relations", []),
        body_count=body_count,
        kind="joint",
        positive_field="positive_local_position",
        negative_field="negative_local_position",
    )
    hinges = _relations(
        source.get("hinge_relations", []),
        body_count=body_count,
        kind="hinge",
        positive_field="positive_angular_local",
        negative_field="positive_linear_local",
    )
    bars = _relations(
        source.get("bar_relations", []),
        body_count=body_count,
        kind="bar",
        positive_field="positive_local_point",
        negative_field="negative_local_point",
    )
    if not joints and not hinges and not bars:
        raise ValueError("at least one relation is required")

    packet = bytearray(_HEADER.pack(
        PACKET_MAGIC,
        PACKET_VERSION,
        body_count,
        len(joints),
        len(hinges),
        len(bars),
        REQUIRED_PROOF_FLAGS,
        0,
    ))
    for row in joints:
        packet += _serialize_relation(
            row,
            "positive_local_position",
            "negative_local_position",
        )
    for row in hinges:
        packet += _serialize_relation(
            row,
            "positive_angular_local",
            "positive_linear_local",
        )
    for row in bars:
        packet += _serialize_relation(
            row,
            "positive_local_point",
            "negative_local_point",
        )

    packet_bytes = bytes(packet)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "verification_scope": source.get("verification_scope"),
        "body_count": body_count,
        "relation_counts": {
            "joint": len(joints),
            "hinge": len(hinges),
            "bar": len(bars),
        },
        "proofs": {
            "raw_sample_values_ready": True,
            "ownership_ready": True,
            "source_order_ready": True,
            "provider_absent": True,
        },
        "packet": {
            "format": PACKET_FORMAT,
            "magic": PACKET_MAGIC.decode("ascii"),
            "version": PACKET_VERSION,
            "size": len(packet_bytes),
            "sha256": hashlib.sha256(packet_bytes).hexdigest(),
            "bytes": packet_bytes,
        },
        "boundary": {
            "stores_body_frames": False,
            "stores_body_positions": False,
            "stores_sample_scalar_bases": False,
            "stores_sample_side_flags": False,
            "stores_generated_contribution_values": False,
            "refresh_function": "FUN_007b3ed0",
            "relation_functions": [
                "FUN_007b2da0",
                "FUN_007b2de0",
                "FUN_007b2f70",
            ],
            "requires_gbcf_identity_join": True,
            "executes_fixed_step_runtime": False,
        },
    }


def build_native_constraint_sample_relation_frame_file(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(source, Mapping):
        raise ValueError("input JSON must be an object")
    report = build_native_constraint_sample_relation_frame(source)

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    packet = bytes(report["packet"].pop("bytes"))
    packet_path = root / "constraint_sample_relations.csrf"
    packet_path.write_bytes(packet)
    report["packet"]["path"] = packet_path.name
    (root / "constraint_sample_relations_manifest.json").write_text(
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
    report = build_native_constraint_sample_relation_frame_file(
        args.input,
        args.output_dir,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "body_count": report["body_count"],
        "relation_counts": report["relation_counts"],
        "packet_sha256": report["packet"]["sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
