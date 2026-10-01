"""Prepare runtime relation +0x70 state for native FUN_007b2210 selection.

CRST preserves the source-order runtime flag words of the top-level
JOINT/HINGE/BAR relation arrays. Only bit 0 is interpreted by the native reset
selection join; all other bits are retained without assigning semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

INPUT_FORMAT = "SHIFT.NativeConstraintResetStateFrameInput/1"
FORMAT = "SHIFT.NativeConstraintResetStateFrame/1"
PACKET_FORMAT = "SHIFT.NativeConstraintResetStateFramePacket/1"
PACKET_MAGIC = b"CRST"
PACKET_VERSION = 1

PROOF_RUNTIME_FLAGS = 1 << 0
PROOF_SOURCE_ORDER = 1 << 1
PROOF_PROVIDER_ABSENT = 1 << 2
REQUIRED_PROOF_FLAGS = (
    PROOF_RUNTIME_FLAGS
    | PROOF_SOURCE_ORDER
    | PROOF_PROVIDER_ABSENT
)

_HEADER = struct.Struct("<4s7I")


def _proof(source: Mapping[str, Any], key: str) -> None:
    if source.get(key) is not True:
        raise ValueError(f"{key} must be explicitly true")


def _runtime_flags(value: Any, *, label: str) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError(f"{label} must be an array")
    if len(value) > 4096:
        raise ValueError(f"{label} exceeds supported count")
    result = [int(item) for item in value]
    for index, flag in enumerate(result):
        if flag < 0 or flag > 0xFFFFFFFF:
            raise ValueError(
                f"{label}[{index}] is outside uint32 domain"
            )
    return result


def _serialize(
    *,
    body_count: int,
    joints: Sequence[int],
    hinges: Sequence[int],
    bars: Sequence[int],
) -> bytes:
    output = bytearray(_HEADER.pack(
        PACKET_MAGIC,
        PACKET_VERSION,
        body_count,
        len(joints),
        len(hinges),
        len(bars),
        REQUIRED_PROOF_FLAGS,
        0,
    ))
    for rows in (joints, hinges, bars):
        if rows:
            output += struct.pack(
                "<" + "I" * len(rows),
                *[int(value) for value in rows],
            )
    return bytes(output)


def build_native_constraint_reset_state_frame(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if source.get("format") != INPUT_FORMAT:
        raise ValueError(f"input must be {INPUT_FORMAT}")
    _proof(source, "runtime_flags_ready")
    _proof(source, "source_order_ready")
    _proof(source, "provider_absent")

    body_count = int(source.get("body_count", 0))
    if body_count <= 0 or body_count > 4096:
        raise ValueError("body_count out of range")

    joints = _runtime_flags(
        source.get("joint_runtime_flags", []),
        label="joint_runtime_flags",
    )
    hinges = _runtime_flags(
        source.get("hinge_runtime_flags", []),
        label="hinge_runtime_flags",
    )
    bars = _runtime_flags(
        source.get("bar_runtime_flags", []),
        label="bar_runtime_flags",
    )
    if not joints and not hinges and not bars:
        raise ValueError("at least one relation runtime flag is required")

    packet = _serialize(
        body_count=body_count,
        joints=joints,
        hinges=hinges,
        bars=bars,
    )
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
        "selected_low_bit_counts": {
            "joint": sum((value & 1) != 0 for value in joints),
            "hinge": sum((value & 1) != 0 for value in hinges),
            "bar": sum((value & 1) != 0 for value in bars),
        },
        "proofs": {
            "runtime_flags_ready": True,
            "source_order_ready": True,
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
            "source_frame_function": "FUN_007b3f40",
            "selection": "relation+0x70 & 1",
            "reset_function": "FUN_007b2210",
            "observed_low_bit_writer": "FUN_00757d2c",
            "stores_scalar_bases": False,
            "stores_reset_nodes": False,
            "stores_matrix_rhs": False,
            "interpreted_flag_mask": 1,
            "preserves_uninterpreted_flag_bits": True,
            "derives_runtime_flag_triggers": False,
        },
    }


def build_native_constraint_reset_state_frame_file(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(source, Mapping):
        raise ValueError("input JSON must be an object")
    report = build_native_constraint_reset_state_frame(source)

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    packet = bytes(report["packet"].pop("bytes"))
    packet_path = root / "constraint_reset_state.crst"
    packet_path.write_bytes(packet)
    report["packet"]["path"] = packet_path.name
    (
        root / "constraint_reset_state_manifest.json"
    ).write_text(
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
    report = build_native_constraint_reset_state_frame_file(
        args.input,
        args.output_dir,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "body_count": report["body_count"],
        "relation_counts": report["relation_counts"],
        "selected_low_bit_counts": report["selected_low_bit_counts"],
        "packet_sha256": report["packet"]["sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
