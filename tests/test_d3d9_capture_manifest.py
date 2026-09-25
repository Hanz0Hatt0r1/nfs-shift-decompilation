from pathlib import Path

from d3d9_capture_manifest import build_capture_manifest


def _events():
    return [
        {"event": "set_stream_source", "frame": 4, "event_index": 0, "stream": 0, "vertex_buffer_ptr": "0x1", "offset_in_bytes": 0, "stride": 32},
        {"event": "set_indices", "frame": 4, "event_index": 1, "index_buffer_ptr": "0x2"},
        {"event": "draw_indexed_primitive", "frame": 4, "event_index": 2, "primitive_count": 2, "start_index": 8, "base_vertex_index": 0},
        {"event": "present_screenshot", "frame": 4, "event_index": 3, "path": "frame.ppm"},
        {"event": "draw_indexed_primitive", "frame": 6, "event_index": 4, "primitive_count": 3, "start_index": 10, "base_vertex_index": 1},
    ]


def test_capture_manifest_records_hash_and_runtime_statistics(tmp_path):
    capture = tmp_path / "capture.jsonl"
    capture.write_text("\n".join('{"event":"draw_indexed_primitive","frame":1,"event_index":0,"primitive_count":1,"start_index":0,"base_vertex_index":0}' for _ in [0]), encoding="utf-8")
    report = build_capture_manifest(capture, events=_events())
    assert report["ready"] is True
    assert len(report["source"]["sha256"]) == 64
    assert report["statistics"]["event_count"] == 5
    assert report["statistics"]["draw_indexed_primitive_count"] == 2
    assert report["statistics"]["frame_count"] == 2
    assert report["statistics"]["first_frame"] == 4
    assert report["statistics"]["last_frame"] == 6
    assert report["authenticity"]["status"] == "unverified"


def test_capture_manifest_hashes_optional_producer_binary(tmp_path):
    capture = tmp_path / "capture.jsonl"
    capture.write_text("capture", encoding="utf-8")
    producer = tmp_path / "d3d9.dll"
    producer.write_bytes(b"producer")
    report = build_capture_manifest(capture, events=[], producer_binary=producer)
    assert report["ready"] is True
    assert report["producer"]["exists"] is True
    assert report["producer"]["size"] == len(b"producer")
    assert len(report["producer"]["sha256"]) == 64


def test_capture_manifest_missing_capture_is_blocked(tmp_path):
    report = build_capture_manifest(tmp_path / "missing.jsonl", events=[])
    assert report["ready"] is False
    assert report["authenticity"]["status"] == "unverified"
    assert report["blocking_reasons"] == ["capture:file-not-found"]


def test_capture_manifest_blocks_invalid_capture_schema(tmp_path):
    capture = tmp_path / "capture.jsonl"
    capture.write_text("invalid", encoding="utf-8")
    events = [
        {
            "event": "set_stream_source",
            "frame": 1,
            "event_index": 0,
            "stream": -1,
            "offset_in_bytes": 0,
            "stride": 32,
        }
    ]
    report = build_capture_manifest(capture, events=events)
    assert report["ready"] is False
    assert "capture-schema:stream:invalid" in report["blocking_reasons"]


def test_capture_manifest_blocks_noncontiguous_event_indices(tmp_path):
    capture = tmp_path / "capture.jsonl"
    capture.write_text("capture", encoding="utf-8")
    events = [
        {"event": "draw_indexed_primitive", "frame": 1, "event_index": 10, "primitive_count": 1, "start_index": 0, "base_vertex_index": 0},
        {"event": "draw_indexed_primitive", "frame": 1, "event_index": 12, "primitive_count": 1, "start_index": 3, "base_vertex_index": 0},
    ]
    report = build_capture_manifest(capture, events=events)
    assert report["ready"] is False
    assert report["integrity"]["event_index"]["status"] == "invalid"
    assert "capture-integrity:event-index-not-contiguous" in report["blocking_reasons"]
