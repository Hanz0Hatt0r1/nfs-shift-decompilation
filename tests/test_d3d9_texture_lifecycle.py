from d3d9_capture_schema import validate_capture_event
from d3d9_texture_lifecycle import build_texture_lifecycle


def test_capture_schema_accepts_create_texture():
    row = {
        "event": "create_texture",
        "frame": 2,
        "texture_ptr": "0x100",
        "width": 64,
        "height": 32,
        "levels": 4,
        "usage": 0,
        "format": 21,
        "pool": 1,
    }
    assert validate_capture_event(row) == []


def test_capture_schema_accepts_create_cube_texture():
    row = {
        "event": "create_cube_texture",
        "frame": 2,
        "texture_ptr": "0x200",
        "edge_length": 128,
        "levels": 8,
        "usage": 0,
        "format": 21,
        "pool": 1,
    }
    assert validate_capture_event(row) == []


def test_texture_lifecycle_links_set_texture_to_create_instance():
    events = [
        {
            "event": "create_texture",
            "frame": 7,
            "event_index": 10,
            "texture_ptr": "0x100",
            "width": 64,
            "height": 32,
            "levels": 1,
            "usage": 0,
            "format": 21,
            "pool": 1,
        },
        {
            "event": "set_texture",
            "frame": 7,
            "event_index": 11,
            "stage": 1,
            "texture_ptr": "0x100",
        },
    ]
    report = build_texture_lifecycle(events)
    assert report["ready"] is True
    assert report["resources"][0]["resource_type"] == "texture2d"
    assert report["bindings"][0]["resource_creation"]["texture_ptr"] == "0x100"
    assert report["boundary"]["dds_identity"] == "not-proven"


def test_texture_lifecycle_does_not_infer_unknown_pointer():
    events = [{
        "event": "set_texture",
        "frame": 7,
        "stage": 3,
        "texture_ptr": "0xdead",
    }]
    report = build_texture_lifecycle(events)
    assert report["ready"] is False
    assert report["unresolved_pointer_bindings"] == 1
    assert report["boundary"]["pointer_to_creation_instance"] == "not-proven"


def test_texture_lifecycle_preserves_cube_identity():
    events = [
        {
            "event": "create_cube_texture",
            "frame": 7,
            "texture_ptr": "0x200",
            "edge_length": 128,
            "levels": 8,
            "usage": 0,
            "format": 21,
            "pool": 1,
        },
        {
            "event": "set_texture",
            "frame": 7,
            "stage": 3,
            "texture_ptr": "0x200",
        },
    ]
    report = build_texture_lifecycle(events)
    assert report["ready"] is True
    assert report["resources"][0]["resource_type"] == "cube_texture"
    assert report["resources"][0]["edge_length"] == 128
