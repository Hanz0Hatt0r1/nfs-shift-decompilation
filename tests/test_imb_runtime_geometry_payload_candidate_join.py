import hashlib
import json

from imb_runtime_geometry_payload_candidate_join import (
    FORMAT,
    _interleaved_vertex_buffer,
    _primitive_index_payloads,
    build_runtime_geometry_payload_candidate_join,
    collect_runtime_buffer_payloads,
)


def _sha(ch):
    return ch * 64


def _group(content, imb, *, primitive=0, triangles=2, stride=16):
    return {
        "content_group_sha256": _sha(content),
        "imb_sha256": _sha(imb),
        "imb_paths": [f"tracks/{imb}.imb"],
        "archives": ["Silverstone.bff"],
        "primitive_index": primitive,
        "draw_range": {
            "first_index": 0,
            "index_count": triangles * 3,
            "primitive_count": triangles,
        },
        "static_vertex_stride": stride,
    }


def _identity(groups, *, draws=7):
    return {
        "geometry_pointer_identity_sha256": _sha("9"),
        "geometry_pointer_identity": {
            "device_ptr": "0x1",
            "stream0_vertex_buffer_ptr": "0x40",
            "stream0_vertex_buffer_creation_event_index": 100,
            "index_buffer_ptr": "0x50",
            "index_buffer_creation_event_index": 101,
            "draw_range": {
                "primitive_type": 4,
                "base_vertex_index": 0,
                "start_index": 0,
                "primitive_count": 2,
            },
            "creation_identity_complete": True,
        },
        "draw_count": draws,
        "first_frame": 10,
        "last_frame": 11,
        "candidate_content_groups": groups,
    }


def _pointer_join(groups):
    return {
        "format": "SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1",
        "resource_shapes": [{
            "resource_shape_sha256": _sha("8"),
            "geometry_shape_sha256": _sha("7"),
            "pipeline_signature_sha256": _sha("6"),
            "families": ["foliageinstanced"],
            "resource_shape_draw_count": 7,
            "source_candidate_content_status": (
                "single-content-candidate"
                if len(groups) == 1
                else "ambiguous-content-candidates"
            ),
            "source_candidate_content_group_count": len(groups),
            "geometry_pointer_identities": [_identity(groups)],
        }],
    }


def _runtime(vb_sha, ib_sha, *, vb_status="stable", ib_status="stable"):
    return {
        "summary": {},
        "buffers": {
            "vertex_buffer|0x40|100": {
                "status": vb_status,
                "sha256": vb_sha if vb_status == "stable" else None,
                "sha256s": [vb_sha],
            },
            "index_buffer|0x50|101": {
                "status": ib_status,
                "sha256": ib_sha if ib_status == "stable" else None,
                "sha256s": [ib_sha],
            },
        },
    }


def _static_entry(imb, vb_sha, ib_sha, *, stride=16, triangles=2):
    return {
        "status": "ready",
        "ready": True,
        "imb_sha256": _sha(imb),
        "vertex_buffer": {
            "status": "ready",
            "ready": True,
            "sha256": vb_sha,
            "byte_size": 32,
            "vertex_count": 2,
            "stride": stride,
        },
        "primitives": {
            "0": {
                "status": "ready",
                "sha256": ib_sha,
                "byte_size": triangles * 6,
                "index_count": triangles * 3,
                "primitive_count": triangles,
                "index_format": 101,
            }
        },
    }


def _static(entries):
    return {
        "candidate_imb_sha256_count": len(entries),
        "found_imb_sha256_count": len(entries),
        "ready_imb_sha256_count": len(entries),
        "missing_imb_sha256s": [],
        "path_digest_mismatches": [],
        "by_imb_sha256": {
            _sha(key): value for key, value in entries.items()
        },
    }


def test_interleaves_source_streams_in_runtime_stride_order():
    stream0 = bytes(range(24))
    stream1 = bytes(range(24, 32))
    source = {
        "header": {"vertex_count": 2},
        "streams": {
            "runtime_vertex_stride": 16,
            "records": [
                {
                    "element_size_bytes": 12,
                    "runtime_element_offset": 0,
                    "type_ordinal": 2,
                    "usage_ordinal": 0,
                    "channel": 0,
                    "vertex_payload_hex": stream0.hex(),
                },
                {
                    "element_size_bytes": 4,
                    "runtime_element_offset": 12,
                    "type_ordinal": 4,
                    "usage_ordinal": 6,
                    "channel": 0,
                    "vertex_payload_hex": stream1.hex(),
                },
            ],
        },
    }
    expected = (
        stream0[:12] + stream1[:4] + stream0[12:] + stream1[4:]
    )
    row = _interleaved_vertex_buffer(source)
    assert row["ready"] is True
    assert row["byte_size"] == 32
    assert row["sha256"] == hashlib.sha256(expected).hexdigest()


def test_primitive_payload_is_exact_little_endian_u16():
    source = {
        "primitives": {
            "records": [{
                "index": 0,
                "triangle_count": 2,
                "indices_u16": [0, 2, 1, 1, 2, 3],
            }]
        }
    }
    row = _primitive_index_payloads(source)["0"]
    assert row["byte_size"] == 12
    assert row["index_count"] == 6
    assert row["sha256"] == hashlib.sha256(
        b"\x00\x00\x02\x00\x01\x00\x01\x00\x02\x00\x03\x00"
    ).hexdigest()


def test_exact_payload_reduces_ambiguous_candidates_to_one():
    group_a = _group("a", "1")
    group_b = _group("b", "2")
    vb_a, ib_a = _sha("c"), _sha("d")
    report = build_runtime_geometry_payload_candidate_join(
        _pointer_join([group_a, group_b]),
        _runtime(vb_a, ib_a),
        _static({
            "1": _static_entry("1", vb_a, ib_a),
            "2": _static_entry("2", _sha("e"), _sha("f")),
        }),
    )
    assert report["format"] == FORMAT
    identity = report["resource_shapes"][0][
        "geometry_pointer_identities"
    ][0]
    assert (
        identity["geometry_payload_gate_status"]
        == "reduced-by-exact-geometry-payload"
    )
    assert identity["candidate_content_group_count"] == 1
    assert identity["candidate_content_group_sha256s"] == [_sha("a")]
    assert report["summary"]["newly_single_payload_identity_count"] == 1
    assert report["summary"]["removed_candidate_count"] == 1


def test_identical_static_payload_remains_ambiguous():
    groups = [_group("a", "1"), _group("b", "2")]
    vb, ib = _sha("c"), _sha("d")
    report = build_runtime_geometry_payload_candidate_join(
        _pointer_join(groups),
        _runtime(vb, ib),
        _static({
            "1": _static_entry("1", vb, ib),
            "2": _static_entry("2", vb, ib),
        }),
    )
    identity = report["resource_shapes"][0][
        "geometry_pointer_identities"
    ][0]
    assert (
        identity["geometry_payload_gate_status"]
        == "payload-non-discriminating"
    )
    assert identity["candidate_content_group_count"] == 2
    assert report["summary"]["payload_reduced_identity_count"] == 0


def test_missing_or_unstable_runtime_payload_fails_open():
    groups = [_group("a", "1"), _group("b", "2")]
    static = _static({
        "1": _static_entry("1", _sha("c"), _sha("d")),
        "2": _static_entry("2", _sha("e"), _sha("f")),
    })
    missing = build_runtime_geometry_payload_candidate_join(
        _pointer_join(groups),
        {"summary": {}, "buffers": {}},
        static,
    )
    row = missing["resource_shapes"][0]["geometry_pointer_identities"][0]
    assert row["geometry_payload_gate_status"] == "runtime-payload-missing"
    assert row["candidate_content_group_count"] == 2

    unstable = build_runtime_geometry_payload_candidate_join(
        _pointer_join(groups),
        _runtime(_sha("c"), _sha("d"), vb_status="unstable"),
        static,
    )
    row = unstable["resource_shapes"][0][
        "geometry_pointer_identities"
    ][0]
    assert row["geometry_payload_gate_status"] == "runtime-payload-unstable"
    assert row["candidate_content_group_count"] == 2


def test_zero_match_and_incomplete_static_inventory_fail_open():
    groups = [_group("a", "1"), _group("b", "2")]
    mismatch = build_runtime_geometry_payload_candidate_join(
        _pointer_join(groups),
        _runtime(_sha("9"), _sha("8")),
        _static({
            "1": _static_entry("1", _sha("c"), _sha("d")),
            "2": _static_entry("2", _sha("e"), _sha("f")),
        }),
    )
    row = mismatch["resource_shapes"][0][
        "geometry_pointer_identities"
    ][0]
    assert (
        row["geometry_payload_gate_status"]
        == "exact-payload-no-static-match"
    )
    assert row["candidate_content_group_count"] == 2
    assert mismatch["summary"]["payload_conflict_identity_count"] == 1

    incomplete = _static({
        "1": _static_entry("1", _sha("c"), _sha("d"))
    })
    row = build_runtime_geometry_payload_candidate_join(
        _pointer_join(groups),
        _runtime(_sha("c"), _sha("d")),
        incomplete,
    )["resource_shapes"][0]["geometry_pointer_identities"][0]
    assert (
        row["geometry_payload_gate_status"]
        == "static-payload-inventory-incomplete"
    )
    assert row["candidate_content_group_count"] == 2


def test_collect_runtime_payloads_hashes_full_snapshot_by_generation(tmp_path):
    buffers = tmp_path / "buffers"
    buffers.mkdir()
    vb = b"vertex-bytes"
    ib = b"index-bytes"
    (buffers / "vb.bin").write_bytes(vb)
    (buffers / "ib.bin").write_bytes(ib)
    capture = tmp_path / "capture.jsonl"
    rows = [
        {
            "event": "create_vertex_buffer",
            "event_index": 100,
            "vertex_buffer_ptr": "0x40",
        },
        {
            "event": "create_index_buffer",
            "event_index": 101,
            "index_buffer_ptr": "0x50",
        },
        {
            "event": "buffer_payload",
            "buffer_ptr": "0x40",
            "resource_type_name": "vertex_buffer",
            "offset": 0,
            "buffer_length": len(vb),
            "captured_byte_size": len(vb),
            "snapshot_status": "captured",
            "payload_path": "buffers/vb.bin",
        },
        {
            "event": "buffer_payload",
            "buffer_ptr": "0x50",
            "resource_type_name": "index_buffer",
            "offset": 0,
            "buffer_length": len(ib),
            "captured_byte_size": len(ib),
            "snapshot_status": "captured",
            "payload_path": "buffers/ib.bin",
        },
    ]
    capture.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    report = collect_runtime_buffer_payloads(capture)
    assert report["summary"]["accepted_full_payload_event_count"] == 2
    assert (
        report["buffers"]["vertex_buffer|0x40|100"]["sha256"]
        == hashlib.sha256(vb).hexdigest()
    )
    assert (
        report["buffers"]["index_buffer|0x50|101"]["sha256"]
        == hashlib.sha256(ib).hexdigest()
    )


def test_wrong_pointer_join_contract_is_rejected():
    try:
        build_runtime_geometry_payload_candidate_join(
            {"format": "wrong"},
            {"buffers": {}},
            {"by_imb_sha256": {}},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("wrong Phase 615 contract must fail")
