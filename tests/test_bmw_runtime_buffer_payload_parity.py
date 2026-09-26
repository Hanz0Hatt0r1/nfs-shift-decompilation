from pathlib import Path

import bmw_runtime_buffer_payload_parity as parity


def _geometry():
    return {
        "resource": {
            "path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
            "sha256": "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c",
        },
        "source": {"frame": 30444},
        "runtime_stream": {
            "vertex_buffer": "0x100",
            "stride": 76,
            "derived_vertex_buffer_bytes": 269800,
        },
    }


def _snapshot(vb_ptr="0x100", ib_ptr="0x200", primitive_count=2):
    return {
        "draw": {
            "event_index": 50,
            "primitive_count": primitive_count,
            "start_index": 0,
            "base_vertex_index": 0,
            "num_vertices": 3,
        },
        "active_stream_sources": [{
            "stream": 0,
            "vertex_buffer_ptr": vb_ptr,
            "stride": 76,
            "resource_creation": {"event_index": 10},
        }],
        "index_binding": {
            "index_buffer_ptr": ib_ptr,
            "resource_creation": {"event_index": 11},
        },
    }


def test_compare_payload_requires_exact_bytes(tmp_path):
    expected = b"abcdefgh"
    good = tmp_path / "good.bin"
    bad = tmp_path / "bad.bin"
    good.write_bytes(expected)
    bad.write_bytes(b"abcdegfh")
    assert parity.compare_payload(good, expected, label="x")["ready"] is True
    report = parity.compare_payload(bad, expected, label="x")
    assert report["ready"] is False
    assert "buffer-payload:sha256-mismatch:x" in report["blocking_reasons"][0]


def test_payload_rows_obey_creation_and_draw_boundaries(tmp_path):
    good = tmp_path / "good.bin"
    good.write_bytes(b"abcdefgh")
    runtime = {
        "buffer_payloads": [
            {
                "buffer_ptr": "0x100",
                "resource_type_name": "vertex_buffer",
                "offset": 0,
                "snapshot_status": "captured",
                "payload_path": str(good),
                "event_index": 5,
            },
            {
                "buffer_ptr": "0x100",
                "resource_type_name": "vertex_buffer",
                "offset": 0,
                "snapshot_status": "captured",
                "payload_path": str(good),
                "event_index": 20,
            },
            {
                "buffer_ptr": "0x100",
                "resource_type_name": "vertex_buffer",
                "offset": 4,
                "snapshot_status": "captured",
                "payload_path": str(good),
                "event_index": 30,
            },
            {
                "buffer_ptr": "0x100",
                "resource_type_name": "vertex_buffer",
                "offset": 0,
                "snapshot_status": "captured",
                "payload_path": str(good),
                "event_index": 60,
            },
        ]
    }
    rows = parity._payload_rows(
        runtime,
        "0x100",
        kind="vertex_buffer",
        creation_event_index=10,
        draw_event_index=50,
    )
    assert [row["event_index"] for row in rows] == [20]


def test_build_report_matches_vb_and_ib_payloads(tmp_path):
    vb = b"VB_BYTES" * (269800 // len(b"VB_BYTES"))
    ib = b"IB0" * 4
    vb_path = tmp_path / "vb.bin"
    ib_path = tmp_path / "ib.bin"
    vb_path.write_bytes(vb)
    ib_path.write_bytes(ib)

    runtime = {
        "frames": [{
            "frame": 30444,
            "draw_snapshots": [{
                **_snapshot(primitive_count=2),
                "draw": {
                    "event_index": 50,
                    "primitive_count": 2,
                    "start_index": 0,
                    "base_vertex_index": 0,
                    "num_vertices": 3550,
                },
            }]
        }],
        "buffer_payloads": [
            {
                "buffer_ptr": "0x100",
                "resource_type_name": "vertex_buffer",
                "offset": 0,
                "snapshot_status": "captured",
                "payload_path": str(vb_path),
                "event_index": 20,
            },
            {
                "buffer_ptr": "0x200",
                "resource_type_name": "index_buffer",
                "offset": 0,
                "snapshot_status": "captured",
                "payload_path": str(ib_path),
                "event_index": 21,
            }
        ],
    }
    geometry = _geometry()
    report = parity.build_report(
        runtime,
        geometry,
        expected_vb=vb_path,
        expected_ib16=ib_path,
    )
    assert report["matched_vertex_buffer"] is True
    assert report["matched_index_buffer_count"] == 1


def test_build_report_stays_unready_without_runtime_payload(tmp_path):
    expected_vb = tmp_path / "vb.bin"
    expected_ib = tmp_path / "ib.bin"
    expected_vb.write_bytes(b"v" * 269800)
    expected_ib.write_bytes(b"i")
    runtime = {
        "frames": [{
            "frame": 30444,
            "draw_snapshots": [{
                **_snapshot(primitive_count=1),
                "draw": {
                    "event_index": 50,
                    "primitive_count": 1,
                    "start_index": 0,
                    "base_vertex_index": 0,
                    "num_vertices": 3550,
                },
            }]
        }],
        "buffer_payloads": [],
    }
    report = parity.build_report(
        runtime,
        _geometry(),
        expected_vb=expected_vb,
        expected_ib16=expected_ib,
    )
    assert report["ready"] is False
    assert report["matched_vertex_buffer"] is False


def test_partial_payload_is_not_accepted_as_full_buffer(tmp_path):
    payload = tmp_path / "partial.bin"
    payload.write_bytes(b"short")
    rows = parity._payload_rows({
        "buffer_payloads": [{
            "buffer_ptr": "0x100",
            "resource_type_name": "vertex_buffer",
            "offset": 4,
            "snapshot_status": "captured",
            "payload_path": str(payload),
            "event_index": 20,
        }]
    }, "0x100", kind="vertex_buffer", creation_event_index=10, draw_event_index=30)
    assert rows == []
