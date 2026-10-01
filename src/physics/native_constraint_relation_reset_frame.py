"""Prepare source-order relation+0x70 bit0 state for FUN_007b3f40 reset selection.

The packet carries only the runtime low bit tested by retail. Scalar bases and
reset widths are derived natively from the GBCF/CSRF identity join.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping, Sequence

INPUT_FORMAT = "SHIFT.NativeConstraintRelationResetFrameInput/1"
FORMAT = "SHIFT.NativeConstraintRelationResetFrame/1"
PACKET_FORMAT = "SHIFT.NativeConstraintRelationResetFramePacket/1"
PACKET_MAGIC = b"CRRF"
PACKET_VERSION = 1

PROOF_RELATION_STATE_BIT0 = 1 << 0
PROOF_SOURCE_ORDER = 1 << 1
PROOF_PROVIDER_ABSENT = 1 << 2
REQUIRED_PROOF_FLAGS = (
    PROOF_RELATION_STATE_BIT0
    | PROOF_SOURCE_ORDER
    | PROOF_PROVIDER_ABSENT
)

_HEADER = struct.Struct("<4s6I")


def _require_proof(source: Mapping[str, Any], key: str) -> None:
    if source.get(key) is not True:
        raise ValueError(f"{key} must be explicitly true")


def _state_bits(value: Any, *, label: str) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError(f"{label} must be an array")

    result: list[int] = []
    for index, item in enumerate(value):
        if not isinstance(item, bool):
            raise ValueError(
                f"{label}[{index}] must be a boolean relation+0x70 bit0"
            )
        result.append(1 if item else 0)
    if len(result) > 4096:
        raise ValueError(f"{label} exceeds supported relation count")
    return result


def build_native_constraint_relation_reset_frame(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    if source.get("format") != INPUT_FORMAT:
        raise ValueError(f"input must be {INPUT_FORMAT}")

    _require_proof(source, "relation_state_bit0_ready")
    _require_proof(source, "source_order_ready")
    _require_proof(source, "provider_absent")

    joints = _state_bits(
        source.get("joint_relation_state_bit0", []),
        label="joint_relation_state_bit0",
    )
    hinges = _state_bits(
        source.get("hinge_relation_state_bit0", []),
        label="hinge_relation_state_bit0",
    )
    bars = _state_bits(
        source.get("bar_relation_state_bit0", []),
        label="bar_relation_state_bit0",
    )
    if not joints and not hinges and not bars:
        raise ValueError("at least one relation state bit is required")

    packet = bytearray(_HEADER.pack(
        PACKET_MAGIC,
        PACKET_VERSION,
        len(joints),
        len(hinges),
        len(bars),
        REQUIRED_PROOF_FLAGS,
        0,
    ))
    packet += bytes(joints)
    packet += bytes(hinges)
    packet += bytes(bars)
    packet_bytes = bytes(packet)

    selected = {
        "joint": sum(joints),
        "hinge": sum(hinges),
        "bar": sum(bars),
    }
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "verification_scope": source.get("verification_scope"),
        "relation_counts": {
            "joint": len(joints),
            "hinge": len(hinges),
            "bar": len(bars),
        },
        "selected_relation_counts": selected,
        "proofs": {
            "relation_state_bit0_ready": True,
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
            "source_function": "FUN_007b3f40",
            "reset_function": "FUN_007b2210",
            "relation_state_offset": 0x70,
            "tested_bit": 0,
            "stores_scalar_bases": False,
            "stores_reset_nodes": False,
            "stores_matrix_rhs": False,
            "requires_gbcf_csrf_identity_join": True,
            "provider_path_supported": False,
        },
    }


def build_native_constraint_relation_reset_frame_file(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(source, Mapping):
        raise ValueError("input JSON must be an object")

    report = build_native_constraint_relation_reset_frame(source)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    packet = bytes(report["packet"].pop("bytes"))
    packet_path = root / "constraint_relation_reset.crrf"
    packet_path.write_bytes(packet)
    report["packet"]["path"] = packet_path.name

    (root / "constraint_relation_reset_manifest.json").write_text(
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

    report = build_native_constraint_relation_reset_frame_file(
        args.input,
        args.output_dir,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "relation_counts": report["relation_counts"],
        "selected_relation_counts": report["selected_relation_counts"],
        "packet_sha256": report["packet"]["sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
