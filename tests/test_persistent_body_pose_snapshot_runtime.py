from __future__ import annotations

import math
import struct

import pytest

from persistent_body_pose_snapshot_runtime import (
    BODY_RECORD_SIZE,
    contract,
    decode_persistent_body_pose_snapshots,
)


def _body_record(
    origin: tuple[float, float, float],
    basis: tuple[float, ...],
) -> bytes:
    record = bytearray([0x5A] * BODY_RECORD_SIZE)
    struct.pack_into("<3d", record, 0x00, *origin)
    struct.pack_into("<9f", record, 0xD4, *basis)
    return bytes(record)


def test_phase695_decodes_exact_origin_and_basis_lanes() -> None:
    identity = (
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    )
    body_bytes = (
        _body_record((1.0, 2.0, 3.0), identity)
        + _body_record((-4.0, 5.5, 6.25), identity)
    )

    snapshots = decode_persistent_body_pose_snapshots(body_bytes, 2)
    assert len(snapshots) == 2
    assert snapshots[0].body_index == 0
    assert snapshots[0].origin == (1.0, 2.0, 3.0)
    assert snapshots[0].basis == identity
    assert snapshots[1].body_index == 1
    assert snapshots[1].origin == (-4.0, 5.5, 6.25)
    assert snapshots[1].basis == identity


def test_phase695_rejects_invalid_cardinality_and_nonfinite_lanes() -> None:
    identity = (
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    )
    with pytest.raises(ValueError, match="non-zero BODY count"):
        decode_persistent_body_pose_snapshots(b"", 0)
    with pytest.raises(ValueError, match="byte cardinality mismatch"):
        decode_persistent_body_pose_snapshots(b"bad", 1)

    bad_origin = _body_record((math.nan, 2.0, 3.0), identity)
    with pytest.raises(ValueError, match="origin contains non-finite"):
        decode_persistent_body_pose_snapshots(bad_origin, 1)

    bad_basis = list(identity)
    bad_basis[4] = math.inf
    with pytest.raises(ValueError, match="basis contains non-finite"):
        decode_persistent_body_pose_snapshots(
            _body_record((1.0, 2.0, 3.0), tuple(bad_basis)),
            1,
        )


def test_phase695_contract_does_not_promote_vehicle_or_renderer_identity() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.PersistentBodyPoseSnapshotRuntime/1"
    assert payload["body_record_size"] == 0x170
    assert payload["origin_storage"] == "f64x3"
    assert payload["basis_storage"] == "f32x9"
    assert payload["body_to_vehicle_identity_proven"] is False
    assert payload["vehicle_world_transform_proven"] is False
    assert payload["renderer_transport_enabled"] is False
    assert payload["basis_transpose_or_remap"] is False
