"""Reference decoder for proven persistent BODY origin/basis lanes.

This module exposes only the source-backed BODY record fields used by Phase 695.
It does not map a BODY record to a vehicle, scene object, coordinate convention,
or renderer world transform.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import struct

FORMAT = "SHIFT.PersistentBodyPoseSnapshotRuntime/1"
BODY_RECORD_SIZE = 0x170
ORIGIN_OFFSET = 0x00
BASIS_OFFSET = 0xD4


@dataclass(frozen=True)
class PersistentBodyPoseSnapshot:
    body_index: int
    origin: tuple[float, float, float]
    basis: tuple[float, float, float, float, float, float, float, float, float]


def decode_persistent_body_pose_snapshots(
    body_bytes: bytes,
    body_count: int,
) -> tuple[PersistentBodyPoseSnapshot, ...]:
    if body_count <= 0:
        raise ValueError("persistent BODY pose snapshot requires non-zero BODY count")
    if len(body_bytes) != body_count * BODY_RECORD_SIZE:
        raise ValueError("persistent BODY pose snapshot byte cardinality mismatch")

    snapshots: list[PersistentBodyPoseSnapshot] = []
    for body_index in range(body_count):
        base = body_index * BODY_RECORD_SIZE
        origin = struct.unpack_from("<3d", body_bytes, base + ORIGIN_OFFSET)
        basis = struct.unpack_from("<9f", body_bytes, base + BASIS_OFFSET)
        if not all(isfinite(value) for value in origin):
            raise ValueError("persistent BODY pose origin contains non-finite value")
        if not all(isfinite(value) for value in basis):
            raise ValueError("persistent BODY pose basis contains non-finite value")
        snapshots.append(
            PersistentBodyPoseSnapshot(
                body_index=body_index,
                origin=origin,
                basis=basis,
            )
        )
    return tuple(snapshots)


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "body_record_size": BODY_RECORD_SIZE,
        "origin_offsets": ["+0x00", "+0x08", "+0x10"],
        "origin_storage": "f64x3",
        "basis_offsets": [
            "+0xd4", "+0xd8", "+0xdc",
            "+0xe0", "+0xe4", "+0xe8",
            "+0xec", "+0xf0", "+0xf4",
        ],
        "basis_storage": "f32x9",
        "body_to_vehicle_identity_proven": False,
        "vehicle_world_transform_proven": False,
        "renderer_transport_enabled": False,
        "basis_transpose_or_remap": False,
    }


__all__ = [
    "FORMAT",
    "BODY_RECORD_SIZE",
    "PersistentBodyPoseSnapshot",
    "decode_persistent_body_pose_snapshots",
    "contract",
]
