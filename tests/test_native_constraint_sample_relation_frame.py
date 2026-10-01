import json
import struct

import pytest

from native_constraint_sample_relation_frame import (
    FORMAT,
    INPUT_FORMAT,
    PACKET_FORMAT,
    build_native_constraint_sample_relation_frame,
    build_native_constraint_sample_relation_frame_file,
)


def _relation_input():
    return {
        "format": INPUT_FORMAT,
        "version": 1,
        "verification_scope": "phase630-test",
        "raw_sample_values_ready": True,
        "ownership_ready": True,
        "source_order_ready": True,
        "provider_absent": True,
        "body_count": 2,
        "joint_relations": [{
            "positive": {"body_index": 0, "sample_index": 0},
            "negative": {"body_index": 1, "sample_index": 0},
            "positive_local_position": [0.25, 0.5, 0.75],
            "negative_local_position": [-1.0, 0.5, 2.0],
        }],
        "hinge_relations": [{
            "positive": {"body_index": 0, "sample_index": 0},
            "negative": {"body_index": 1, "sample_index": 0},
            "positive_angular_local": [1.0, 2.0, 3.0],
            "positive_linear_local": [4.0, 5.0, 6.0],
        }],
        "bar_relations": [{
            "positive": {"body_index": 0, "sample_index": 0},
            "negative": {"body_index": 1, "sample_index": 0},
            "positive_local_point": [1.0, 0.0, 0.0],
            "negative_local_point": [0.0, 1.0, 0.0],
        }],
    }


def test_relation_frame_serializes_source_order_without_body_state():
    report = build_native_constraint_sample_relation_frame(
        _relation_input()
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["body_count"] == 2
    assert report["relation_counts"] == {
        "joint": 1,
        "hinge": 1,
        "bar": 1,
    }
    assert report["packet"]["format"] == PACKET_FORMAT
    assert report["packet"]["magic"] == "CSRF"
    assert report["packet"]["size"] == 32 + 3 * 64
    assert report["boundary"]["stores_body_frames"] is False
    assert report["boundary"]["stores_body_positions"] is False
    assert report["boundary"]["stores_sample_scalar_bases"] is False
    assert report["boundary"]["stores_sample_side_flags"] is False
    assert (
        report["boundary"]["stores_generated_contribution_values"]
        is False
    )

    packet = report["packet"]["bytes"]
    header = struct.unpack_from("<4s7I", packet, 0)
    assert header == (
        b"CSRF",
        1,
        2,
        1,
        1,
        1,
        0x0F,
        0,
    )
    relation = struct.unpack_from("<4I6d", packet, 32)
    assert relation[:4] == (0, 0, 1, 0)
    assert relation[4:] == pytest.approx(
        (0.25, 0.5, 0.75, -1.0, 0.5, 2.0)
    )


def test_relation_frame_file_writes_packet_and_manifest(tmp_path):
    source = tmp_path / "relations.json"
    source.write_text(
        json.dumps(_relation_input()),
        encoding="utf-8",
    )

    report = build_native_constraint_sample_relation_frame_file(
        source,
        tmp_path / "out",
    )

    packet = tmp_path / "out/constraint_sample_relations.csrf"
    manifest = (
        tmp_path / "out/constraint_sample_relations_manifest.json"
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
        "raw_sample_values_ready",
        "ownership_ready",
        "source_order_ready",
        "provider_absent",
    ],
)
def test_relation_frame_requires_explicit_proofs(proof):
    source = _relation_input()
    source[proof] = False
    with pytest.raises(ValueError, match=proof):
        build_native_constraint_sample_relation_frame(source)


def test_relation_frame_rejects_missing_relations():
    source = _relation_input()
    source["joint_relations"] = []
    source["hinge_relations"] = []
    source["bar_relations"] = []
    with pytest.raises(ValueError, match="at least one relation"):
        build_native_constraint_sample_relation_frame(source)


def test_relation_frame_rejects_invalid_body_endpoint():
    source = _relation_input()
    source["joint_relations"][0]["positive"]["body_index"] = 2
    with pytest.raises(ValueError, match="outside BODY domain"):
        build_native_constraint_sample_relation_frame(source)


def test_relation_frame_rejects_nonfinite_raw_input():
    source = _relation_input()
    source["bar_relations"][0]["positive_local_point"][1] = float("inf")
    with pytest.raises(ValueError, match="non-finite"):
        build_native_constraint_sample_relation_frame(source)
