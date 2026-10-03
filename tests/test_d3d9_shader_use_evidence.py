import hashlib
import json

from d3d9_shader_use_evidence import FORMAT, build_shader_use_evidence


VS = bytes.fromhex("0000feff01000000")
PS = bytes.fromhex("0000ffff02000000")
VS_SHA = hashlib.sha256(VS).hexdigest()
PS_SHA = hashlib.sha256(PS).hexdigest()


def _line(value):
    return json.dumps(value, separators=(",", ":"))


def _targets():
    return {
        "families": [{
            "family": "basicinstanced",
            "pixel_shader_sha256": [PS_SHA],
        }]
    }


def test_shader_use_evidence_keeps_create_bind_and_draw_provenance_distinct():
    lines = [
        _line({
            "event": "create_vertex_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
            "bytes_hex": VS.hex(),
        }),
        _line({
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 2,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 2,
            "event_index": 3,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 4,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "start_index": 0,
            "primitive_count": 2,
        }),
    ]

    report = build_shader_use_evidence(lines, target_inventory=_targets())

    assert report["format"] == FORMAT
    assert report["status"] == "observed"
    assert report["summary"]["shader_creation_count"] == 2
    assert report["summary"]["shader_bind_event_count"] == 2
    assert report["summary"]["draw_count"] == 1
    assert report["summary"]["exact_capture_local_draw_count"] == 1
    assert report["summary"]["unique_shader_pair_count"] == 1
    assert report["summary"]["unique_shader_generation_pair_count"] == 1
    assert report["summary"]["unique_shader_use_pair_count"] == 1

    draw = report["draws"][0]
    assert draw["classification"] == "exact-capture-local"
    assert draw["missing_shader_use_state"] == []
    assert draw["families"] == ["basicinstanced"]
    assert draw["shader_pair"] == {
        "vertex_shader_sha256": VS_SHA,
        "pixel_shader_sha256": PS_SHA,
    }
    assert draw["vertex_shader"]["creation_event_index"] == 1
    assert draw["vertex_shader"]["bind_event_index"] == 3
    assert draw["pixel_shader"]["creation_event_index"] == 2
    assert draw["pixel_shader"]["bind_event_index"] == 4
    assert draw["shader_pair_sha256"]
    assert draw["shader_generation_pair_sha256"]
    assert draw["shader_use_pair_sha256"]
    assert draw["provenance"]["draw_event_index"] == 5


def test_reused_pointer_same_bytecode_keeps_generation_and_use_identity_distinct():
    lines = [
        _line({
            "event": "create_vertex_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
            "bytes_hex": VS.hex(),
        }),
        _line({
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 2,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 2,
            "event_index": 3,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 4,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 3,
            "event_index": 6,
            "device_ptr": "0x1",
            "shader_ptr": None,
        }),
        _line({
            "event": "create_pixel_shader",
            "frame": 3,
            "event_index": 7,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 3,
            "event_index": 8,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 3,
            "event_index": 9,
            "device_ptr": "0x1",
        }),
    ]

    report = build_shader_use_evidence(lines, target_inventory=_targets())

    assert report["summary"]["pointer_reuse_creation_count"] == 1
    assert report["summary"]["draw_count"] == 2
    assert report["summary"]["unique_shader_pair_count"] == 1
    assert report["summary"]["unique_shader_generation_pair_count"] == 2
    assert report["summary"]["unique_shader_use_pair_count"] == 2

    first, second = report["draws"]
    assert first["shader_pair_sha256"] == second["shader_pair_sha256"]
    assert first["pixel_shader"]["shader_ptr"] == second["pixel_shader"]["shader_ptr"] == "0x20"
    assert first["pixel_shader"]["shader_sha256"] == second["pixel_shader"]["shader_sha256"] == PS_SHA
    assert first["pixel_shader"]["creation_event_index"] == 2
    assert second["pixel_shader"]["creation_event_index"] == 7
    assert first["pixel_shader"]["generation_ordinal"] == 1
    assert second["pixel_shader"]["generation_ordinal"] == 2
    assert first["shader_generation_pair_sha256"] != second["shader_generation_pair_sha256"]
    assert first["shader_use_pair_sha256"] != second["shader_use_pair_sha256"]


def test_unresolved_bind_stays_partial_in_unfiltered_mode():
    lines = [
        _line({
            "event": "set_vertex_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 1,
            "event_index": 2,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 1,
            "event_index": 3,
            "device_ptr": "0x1",
        }),
    ]

    report = build_shader_use_evidence(lines)

    assert report["status"] == "observed"
    assert report["summary"]["draw_count"] == 1
    assert report["summary"]["exact_capture_local_draw_count"] == 0
    assert report["summary"]["partial_capture_local_draw_count"] == 1
    assert report["bind_resolution_counts"] == {"creation-not-observed": 2}
    draw = report["draws"][0]
    assert draw["classification"] == "partial-capture-local"
    assert "vertex-shader-creation-unresolved" in draw["missing_shader_use_state"]
    assert "pixel-shader-creation-unresolved" in draw["missing_shader_use_state"]
    assert draw["shader_pair_sha256"] is None
    assert draw["shader_generation_pair_sha256"] is None
    assert draw["shader_use_pair_sha256"] is None


def test_device_reset_clears_shader_use_state():
    lines = [
        _line({
            "event": "create_vertex_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
            "bytes_hex": VS.hex(),
        }),
        _line({
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 2,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 1,
            "event_index": 3,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 1,
            "event_index": 4,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "device_reset",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 6,
            "device_ptr": "0x1",
        }),
    ]

    report = build_shader_use_evidence(lines)
    draw = report["draws"][0]
    assert draw["classification"] == "partial-capture-local"
    assert "vertex-shader-bind-event-unresolved" in draw["missing_shader_use_state"]
    assert "vertex-shader-unbound" in draw["missing_shader_use_state"]
    assert "pixel-shader-bind-event-unresolved" in draw["missing_shader_use_state"]
    assert "pixel-shader-unbound" in draw["missing_shader_use_state"]
