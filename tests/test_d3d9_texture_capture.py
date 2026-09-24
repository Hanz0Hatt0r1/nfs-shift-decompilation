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
        {"stage": 0, "texture_ptr": "0x1111", "line": 1},
        {"stage": 3, "texture_ptr": "0x3333", "line": 2},
    ]
