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
    assert bindings == [
        {"stage": 0, "texture_ptr": "0x1111", "line": None},
        {"stage": 3, "texture_ptr": "0x3333", "line": None},
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
