from d3d9_capture_schema import validate_capture_event


def test_pointerless_draw_event_is_valid():
    row = {
        "event": "draw_indexed_primitive",
        "frame": 0,
        "event_index": 1,
        "primitive_count": 1,
        "start_index": 0,
        "base_vertex_index": 0,
    }
    assert validate_capture_event(row) == []


def test_pointerless_constant_event_is_valid():
    row = {
        "event": "set_vertex_shader_constant_f",
        "frame": 0,
        "event_index": 2,
        "start_register": 0,
        "vector4f_count": 1,
        "values": [0.0, 0.0, 0.0, 1.0],
    }
    assert validate_capture_event(row) == []
