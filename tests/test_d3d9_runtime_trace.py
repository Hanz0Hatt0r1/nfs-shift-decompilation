import json

from d3d9_runtime_trace import build_runtime_binding_evidence, load_events


def test_runtime_capture_correlates_declaration_and_same_meb_resource(tmp_path):
    trace = tmp_path / "trace.jsonl"
    rows = [
        {"event": "create_vertex_declaration", "frame": 7, "declaration_ptr": "0x1234", "bytes_hex": "0000000004000a00ffff000011000000"},
        {"event": "set_vertex_declaration", "frame": 7, "declaration_ptr": "0x1234", "resource_sha256": "abc", "resource_path": "vehicles/bmw/body.meb"},
        {"event": "set_stream_source", "frame": 7, "stream": 0, "vertex_buffer_ptr": "0x7777", "offset_in_bytes": 0, "stride": 32},
        {"event": "draw_indexed_primitive", "frame": 7, "primitive_count": 94, "start_index": 0, "base_vertex_index": 0},
    ]
    trace.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    events = load_events(trace)
    meb = {
        "resource": "vehicles/bmw/body.meb",
        "resource_sha256": "abc",
        "property_descriptors": [{"id": "460", "words": [4, 6, 0]}],
    }
    report = build_runtime_binding_evidence(events, meb_resource=meb, usage_ordinal_map={6: 10})

    assert report["status"] == "observed"
    assert report["frames"][0]["binding"]["same_meb_resource"] is True
    assert report["frames"][0]["binding"]["status"] == "observed"
    assert report["meb_correlation"]["descriptor_matches"][0]["status"] == "match"
    assert report["meb_correlation"]["descriptor_matches"][0]["property_id"] == "460"


def test_runtime_capture_does_not_guess_usage_mapping():
    events = load_events_from_rows([
        {"event": "create_vertex_declaration", "frame": 1, "declaration_ptr": "0x1", "bytes_hex": "0000000004000a00ffff000011000000"},
    ])
    meb = {"property_descriptors": [{"id": "460", "words": [4, 6, 0]}]}
    report = build_runtime_binding_evidence(events, meb_resource=meb)
    assert report["meb_correlation"]["descriptor_matches"][0]["status"] == "not-proven"
    assert report["evidence_boundary"]["usage_ordinal_mapping"] == "not-supplied"


def load_events_from_rows(rows):
    import tempfile
    with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(row) for row in rows))
        f.flush()
        return load_events(f.name)
