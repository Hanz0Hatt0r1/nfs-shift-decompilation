from d3d9_capture_schema import validate_capture_event
from d3d9_runtime_trace import build_runtime_binding_evidence


def test_set_texture_schema_accepts_bound_texture():
    row = {
        "event": "set_texture",
        "frame": 7,
        "event_index": 12,
        "stage": 3,
        "texture_ptr": "0x1234",
    }
    assert validate_capture_event(row) == []


def test_set_texture_schema_accepts_null_unbind():
    row = {
        "event": "set_texture",
        "frame": 7,
        "event_index": 13,
        "stage": 3,
        "texture_ptr": None,
    }
    assert validate_capture_event(row) == []


def test_set_texture_schema_rejects_negative_stage():
    row = {
        "event": "set_texture",
        "frame": 7,
        "stage": -1,
        "texture_ptr": "0x1234",
    }
    assert "texture:stage-invalid" in validate_capture_event(row)


def test_runtime_trace_keeps_texture_bindings_on_frame():
    events = [
        {
            "event": "set_texture",
            "frame": 7,
            "event_index": 0,
            "stage": 0,
            "texture_ptr": "0x1111",
        },
        {
            "event": "set_texture",
            "frame": 7,
            "event_index": 1,
            "stage": 3,
            "texture_ptr": "0x3333",
        },
    ]
    report = build_runtime_binding_evidence(events)
    assert report["trace"]["frame_count"] == 1
    bindings = report["frames"][0]["texture_bindings"]
    assert [(row["stage"], row["texture_ptr"], row["line"]) for row in bindings] == [
        (0, "0x1111", None),
        (3, "0x3333", None),
    ]

def test_set_texture_schema_accepts_resource_descriptor():
    row = {
        "event": "set_texture",
        "frame": 2,
        "event_index": 3,
        "stage": 3,
        "texture_ptr": "0x300",
        "resource_descriptor_status": "observed",
        "resource_type": 3,
        "resource_type_name": "cube_texture",
        "width": 256,
        "height": 256,
        "format": 21,
        "pool": 1,
        "level_count": 9,
    }
    assert validate_capture_event(row) == []


def test_runtime_trace_preserves_resource_descriptor():
    events = [{
        "event": "set_texture",
        "frame": 2,
        "event_index": 3,
        "stage": 3,
        "texture_ptr": "0x300",
        "resource_descriptor_status": "observed",
        "resource_type": 3,
        "resource_type_name": "cube_texture",
        "width": 256,
        "height": 256,
        "format": 21,
        "pool": 1,
        "level_count": 9,
    }]
    report = build_runtime_binding_evidence(events)
    descriptor = report["frames"][0]["texture_bindings"][0]["resource_descriptor"]
    assert descriptor["resource_type_name"] == "cube_texture"
    assert descriptor["width"] == 256
    assert descriptor["level_count"] == 9



def test_runtime_trace_preserves_texture_snapshot_metadata():
    events = [{
        "event": "set_texture",
        "frame": 3,
        "event_index": 0,
        "stage": 3,
        "texture_ptr": "0x3333",
        "resource_type_name": "cube_texture",
        "width": 128,
        "height": 128,
        "level_count": 8,
        "resource_descriptor_status": "observed",
        "snapshot_status": "captured",
        "snapshot_paths": [
            "frames/s3_face_px.ppm",
            "frames/s3_face_nx.ppm",
            "frames/s3_face_py.ppm",
            "frames/s3_face_ny.ppm",
            "frames/s3_face_pz.ppm",
            "frames/s3_face_nz.ppm",
        ],
    }]
    report = build_runtime_binding_evidence(events)
    binding = report["frames"][0]["texture_bindings"][0]
    descriptor = binding["resource_descriptor"]
    assert descriptor["resource_type_name"] == "cube_texture"
    assert descriptor["width"] == 128
    assert descriptor["level_count"] == 8
    assert binding["snapshot_status"] == "captured"
    assert len(binding["snapshot_paths"]) == 6



def _draw_texture_events(*, snapshot_ptr="0x700", draw_index=0):
    return [
        {
            "event": "create_texture",
            "frame": 5,
            "event_index": 0,
            "texture_ptr": "0x700",
            "width": 64,
            "height": 64,
            "levels": 1,
            "usage": 0,
            "format": 21,
            "pool": 0,
        },
        {
            "event": "set_texture",
            "frame": 5,
            "event_index": 1,
            "stage": 7,
            "texture_ptr": "0x700",
            "snapshot_status": "captured",
            "snapshot_paths": ["textures/set.ppm"],
        },
        {
            "event": "draw_indexed_primitive",
            "frame": 5,
            "event_index": 2,
            "draw_index": draw_index,
            "primitive_count": 2,
            "start_index": 6,
            "base_vertex_index": 0,
        },
        {
            "event": "draw_texture_snapshot",
            "frame": 5,
            "event_index": 3,
            "draw_index": draw_index,
            "stage": 7,
            "texture_ptr": snapshot_ptr,
            "resource_type_name": "texture2d",
            "resource_descriptor_status": "observed",
            "width": 64,
            "height": 64,
            "format": 21,
            "pool": 0,
            "level_count": 1,
            "snapshot_status": "captured",
            "snapshot_paths": [
                "textures/draw_f5_d0.ppm"
            ],
        },
    ]


def test_runtime_trace_attaches_draw_texture_snapshot_to_exact_draw():
    report = build_runtime_binding_evidence(
        _draw_texture_events()
    )
    snapshot = report["frames"][0]["draw_snapshots"][0]
    rows = snapshot["draw_texture_snapshots"]

    assert len(rows) == 1
    row = rows[0]
    assert row["draw_index"] == 0
    assert row["stage"] == 7
    assert row["texture_ptr"] == "0x700"
    assert row["active_binding_texture_ptr"] == "0x700"
    assert row["active_binding_match"] is True
    assert row["resource_creation_status"] == "observed"
    assert row["resource_creation"]["resource_type"] == "texture2d"
    assert row["snapshot_paths"] == [
        "textures/draw_f5_d0.ppm"
    ]
    assert report["trace"]["draw_texture_snapshot_event_count"] == 1


def test_runtime_trace_blocks_draw_texture_pointer_mismatch():
    report = build_runtime_binding_evidence(
        _draw_texture_events(snapshot_ptr="0x701")
    )
    snapshot = report["frames"][0]["draw_snapshots"][0]
    row = snapshot["draw_texture_snapshots"][0]

    assert row["active_binding_match"] is False
    assert any(
        blocker.get("reason")
        == "draw-texture-snapshot:active-binding-mismatch:s7"
        for blocker in report["blocking_reasons"]
    )


def test_runtime_trace_blocks_producer_draw_index_mismatch():
    events = _draw_texture_events(draw_index=4)
    report = build_runtime_binding_evidence(events)

    assert any(
        blocker.get("reason") == "draw-index:mismatch:0:4"
        for blocker in report["blocking_reasons"]
    )
    assert any(
        blocker.get("reason")
        == "draw-texture-snapshot:draw-not-found:4"
        for blocker in report["blocking_reasons"]
    )
