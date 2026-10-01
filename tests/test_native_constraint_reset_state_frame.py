import json
import struct

import pytest

from native_constraint_reset_state_frame import (
    FORMAT,
    INPUT_FORMAT,
    PACKET_FORMAT,
    build_native_constraint_reset_state_frame,
    build_native_constraint_reset_state_frame_file,
)


def _source():
    return {
        "format": INPUT_FORMAT,
        "version": 1,
        "verification_scope": "phase632-test",
        "runtime_flags_ready": True,
        "source_order_ready": True,
        "provider_absent": True,
        "body_count": 11,
        "joint_runtime_flags": [1, 0, 2, 3],
        "hinge_runtime_flags": [0, 2, 4, 8],
        "bar_runtime_flags": [1, 2, 3],
    }


def test_reset_state_packet_preserves_words_and_interprets_only_low_bit():
    report = build_native_constraint_reset_state_frame(_source())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["packet"]["format"] == PACKET_FORMAT
    assert report["packet"]["magic"] == "CRST"
    assert report["relation_counts"] == {
        "joint": 4,
        "hinge": 4,
        "bar": 3,
    }
    assert report["selected_low_bit_counts"] == {
        "joint": 2,
        "hinge": 0,
        "bar": 2,
    }
    assert report["boundary"]["stores_scalar_bases"] is False
    assert report["boundary"]["stores_reset_nodes"] is False
    assert report["boundary"]["interpreted_flag_mask"] == 1
    assert (
        report["boundary"]["preserves_uninterpreted_flag_bits"]
        is True
    )
    assert report["boundary"]["derives_runtime_flag_triggers"] is False

    packet = report["packet"]["bytes"]
    header = struct.unpack_from("<4s7I", packet, 0)
    assert header == (
        b"CRST",
        1,
        11,
        4,
        4,
        3,
        0x07,
        0,
    )
    flags = struct.unpack_from("<11I", packet, 32)
    assert flags == (1, 0, 2, 3, 0, 2, 4, 8, 1, 2, 3)


@pytest.mark.parametrize(
    "proof",
    [
        "runtime_flags_ready",
        "source_order_ready",
        "provider_absent",
    ],
)
def test_reset_state_requires_explicit_proofs(proof):
    source = _source()
    source[proof] = False
    with pytest.raises(ValueError, match=proof):
        build_native_constraint_reset_state_frame(source)


def test_reset_state_rejects_invalid_flag_word():
    source = _source()
    source["bar_runtime_flags"][0] = 0x100000000
    with pytest.raises(ValueError, match="uint32"):
        build_native_constraint_reset_state_frame(source)


def test_reset_state_rejects_empty_relation_domain():
    source = _source()
    source["joint_runtime_flags"] = []
    source["hinge_runtime_flags"] = []
    source["bar_runtime_flags"] = []
    with pytest.raises(ValueError, match="at least one relation"):
        build_native_constraint_reset_state_frame(source)


def test_reset_state_file_writes_packet_and_manifest(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(_source()), encoding="utf-8")

    report = build_native_constraint_reset_state_frame_file(
        source,
        tmp_path / "out",
    )

    packet = tmp_path / "out/constraint_reset_state.crst"
    manifest = tmp_path / "out/constraint_reset_state_manifest.json"
    assert packet.is_file()
    assert manifest.is_file()
    persisted = json.loads(manifest.read_text(encoding="utf-8"))
    assert persisted["packet"]["path"] == packet.name
    assert persisted["packet"]["sha256"] == report["packet"]["sha256"]
    assert "bytes" not in persisted["packet"]
