from d3d9_draw_snapshot_schema import validate_draw_snapshot, validate_draw_snapshots


def _snapshot():
    return {
        "frame": 1,
        "draw_index": 0,
        "draw": {"primitive_count": 2, "start_index": 4, "base_vertex_index": 0},
        "vertex_declaration": {},
        "vertex_shader": {},
        "pixel_shader": {},
        "stream_sources": [],
        "active_stream_sources": [],
        "index_binding": {},
        "constant_writes": [],
        "constant_state": {"vertex": {}, "pixel": {}},
        "texture_bindings": [],
        "active_texture_bindings": [],
    }


def test_draw_snapshot_schema_accepts_complete_snapshot():
    assert validate_draw_snapshot(_snapshot()) == []


def test_draw_snapshot_schema_requires_exact_draw_identity():
    snapshot = _snapshot()
    snapshot.pop("draw_index")
    reasons = validate_draw_snapshot(snapshot)
    assert "draw_index:missing" in reasons
    assert "draw_index:invalid" in reasons


def test_draw_snapshot_schema_reports_batch_blockers():
    snapshot = _snapshot()
    snapshot["draw"]["start_index"] = "4"
    report = validate_draw_snapshots([snapshot])
    assert report["ready"] is False
    assert report["status"] == "invalid"
    assert report["blocking_reasons"] == [
        {"index": 0, "reason": "draw:start_index:invalid"}
    ]
