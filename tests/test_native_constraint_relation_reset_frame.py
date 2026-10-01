import json
import struct

import pytest

from native_constraint_relation_reset_frame import (
    FORMAT,
    INPUT_FORMAT,
    PACKET_FORMAT,
    build_native_constraint_relation_reset_frame,
    build_native_constraint_relation_reset_frame_file,
)


def _reset_input():
    return {
        "format": INPUT_FORMAT,
        "version": 1,
        "verification_scope": "phase632-test",
        "relation_state_bit0_ready": True,
        "source_order_ready": True,
        "provider_absent": True,
        "joint_relation_state_bit0": [True, False],
        "hinge_relation_state_bit0": [False],
        "bar_relation_state_bit0": [True, True, False],
    }


def test_reset_frame_serializes_only_relation_state_bit0():
    report = build_native_constraint_relation_reset_frame(
        _reset_input()
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["relation_counts"] == {
        "joint": 2,
        "hinge": 1,
        "bar": 3,
    }
    assert report["selected_relation_counts"] == {
        "joint": 1,
        "hinge": 0,
        "bar": 2,
    }
    assert report["packet"]["format"] == PACKET_FORMAT
    assert report["packet"]["magic"] == "CRRF"
    assert report["packet"]["size"] == 28 + 6
    assert report["boundary"]["relation_state_offset"] == 0x70
    assert report["boundary"]["tested_bit"] == 0
    assert report["boundary"]["stores_scalar_bases"] is False
    assert report["boundary"]["stores_reset_nodes"] is False
    assert report["boundary"]["stores_matrix_rhs"] is False

    packet = report["packet"]["bytes"]
    header = struct.unpack_from("<4s6I", packet, 0)
    assert header == (
        b"CRRF",
        1,
        2,
        1,
        3,
        0x07,
        0,
    )
    assert packet[28:] == bytes((1, 0, 0, 1, 1, 0))


def test_reset_frame_file_writes_packet_and_manifest(tmp_path):
    source = tmp_path / "reset.json"
    source.write_text(
        json.dumps(_reset_input()),
        encoding="utf-8",
    )

    report = build_native_constraint_relation_reset_frame_file(
        source,
        tmp_path / "out",
    )

    packet = tmp_path / "out/constraint_relation_reset.crrf"
    manifest = (
        tmp_path / "out/constraint_relation_reset_manifest.json"
    )
    assert packet.is_file()
    assert manifest.is_file()
    persisted = json.loads(manifest.read_text(encoding="utf-8"))
    assert persisted["packet"]["path"] == packet.name
    assert persisted["packet"]["sha256"] == report["packet"]["sha256"]
    assert "bytes" not in persisted["packet"]


@pytest.mark.parametrize(
    "proof",
    [
        "relation_state_bit0_ready",
        "source_order_ready",
        "provider_absent",
    ],
)
def test_reset_frame_requires_explicit_proofs(proof):
    source = _reset_input()
    source[proof] = False
    with pytest.raises(ValueError, match=proof):
        build_native_constraint_relation_reset_frame(source)


def test_reset_frame_rejects_non_boolean_state():
    source = _reset_input()
    source["joint_relation_state_bit0"][0] = 1
    with pytest.raises(ValueError, match="must be a boolean"):
        build_native_constraint_relation_reset_frame(source)


def test_reset_frame_rejects_missing_relation_state():
    source = _reset_input()
    source["joint_relation_state_bit0"] = []
    source["hinge_relation_state_bit0"] = []
    source["bar_relation_state_bit0"] = []
    with pytest.raises(ValueError, match="at least one relation state bit"):
        build_native_constraint_relation_reset_frame(source)
