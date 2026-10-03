import hashlib
import json
import struct

from d3d9_target_draw_local_evidence import (
    FORMAT,
    build_target_draw_local_evidence,
)


def _shader(stage, constants):
    version = 0xFFFE0300 if stage == "vertex" else 0xFFFF0300
    names = [name.encode("ascii") + b"\x00" for name, *_ in constants]
    header_size = 28
    info_size = 20 * len(constants)
    type_size = 20
    name_offsets = []
    pos = header_size + info_size + type_size
    for name in names:
        name_offsets.append(pos)
        pos += len(name)

    payload = bytearray(b"CTAB")
    payload += struct.pack(
        "<7I",
        header_size,
        0,
        version,
        len(constants),
        header_size,
        0,
        0,
    )
    for name_offset, (_, register_set, register_index, register_count) in zip(
        name_offsets,
        constants,
    ):
        payload += struct.pack(
            "<IHHHHII",
            name_offset,
            register_set,
            register_index,
            register_count,
            0,
            header_size + info_size,
            0,
        )
    payload += struct.pack("<HHHHHHII", 4, 3, 4, 4, 1, 0, 0, 0)
    payload += b"".join(names)
    payload += b"\x00" * ((-len(payload)) % 4)
    return (
        struct.pack("<I", version)
        + struct.pack("<I", ((len(payload) // 4) << 16) | 0xFFFE)
        + payload
        + struct.pack("<I", 0xFFFF)
    )


VS = _shader("vertex", [("World", 2, 0, 4)])
PS = _shader(
    "pixel",
    [
        ("Tint", 2, 0, 1),
        ("diffuseMap", 3, 0, 1),
    ],
)
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


def _base_events():
    return [
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
            "event": "create_vertex_declaration",
            "frame": 1,
            "event_index": 3,
            "device_ptr": "0x1",
            "declaration_ptr": "0x30",
            "bytes_hex": "0000000002000000",
        }),
        _line({
            "event": "create_vertex_buffer",
            "frame": 1,
            "event_index": 4,
            "device_ptr": "0x1",
            "vertex_buffer_ptr": "0x40",
            "length": 4096,
            "usage": 0,
            "fvf": 0,
            "pool": 1,
        }),
        _line({
            "event": "create_vertex_buffer",
            "frame": 1,
            "event_index": 5,
            "device_ptr": "0x1",
            "vertex_buffer_ptr": "0x41",
            "length": 65536,
            "usage": 520,
            "fvf": 0,
            "pool": 0,
        }),
        _line({
            "event": "create_index_buffer",
            "frame": 1,
            "event_index": 6,
            "device_ptr": "0x1",
            "index_buffer_ptr": "0x50",
            "length": 1024,
            "usage": 0,
            "format": 101,
            "pool": 1,
        }),
        _line({
            "event": "create_texture",
            "frame": 1,
            "event_index": 7,
            "device_ptr": "0x1",
            "texture_ptr": "0x60",
            "width": 512,
            "height": 512,
            "levels": 1,
            "usage": 0,
            "format": 21,
            "pool": 1,
        }),
        _line({
            "event": "set_vertex_declaration",
            "frame": 2,
            "event_index": 8,
            "device_ptr": "0x1",
            "declaration_ptr": "0x30",
        }),
        _line({
            "event": "set_stream_source",
            "frame": 2,
            "event_index": 9,
            "device_ptr": "0x1",
            "stream": 0,
            "vertex_buffer_ptr": "0x40",
            "offset_in_bytes": 0,
            "stride": 60,
        }),
        _line({
            "event": "set_stream_source",
            "frame": 2,
            "event_index": 10,
            "device_ptr": "0x1",
            "stream": 1,
            "vertex_buffer_ptr": "0x41",
            "offset_in_bytes": 64,
            "stride": 64,
        }),
        _line({
            "event": "set_indices",
            "frame": 2,
            "event_index": 11,
            "device_ptr": "0x1",
            "index_buffer_ptr": "0x50",
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 2,
            "event_index": 12,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 13,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "set_texture",
            "frame": 2,
            "event_index": 14,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": "0x60",
        }),
        _line({
            "event": "set_vertex_shader_constant_f",
            "frame": 2,
            "event_index": 15,
            "device_ptr": "0x1",
            "start_register": 0,
            "vector4f_count": 4,
            "values": [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                10, 20, 30, 1,
            ],
        }),
        _line({
            "event": "set_pixel_shader_constant_f",
            "frame": 2,
            "event_index": 16,
            "device_ptr": "0x1",
            "start_register": 0,
            "vector4f_count": 1,
            "values": [1, 0.5, 0.25, 1],
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 17,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "base_vertex_index": 0,
            "min_vertex_index": 0,
            "num_vertices": 100,
            "start_index": 12,
            "primitive_count": 20,
        }),
    ]


def test_draw_local_evidence_reconstructs_exact_capture_local_state():
    lines = _base_events()
    report = build_target_draw_local_evidence(lines, target_inventory=_targets())

    assert report["format"] == FORMAT
    assert report["status"] == "observed"
    assert report["summary"]["target_draw_count"] == 1
    assert report["summary"]["strong_capture_local_draw_count"] == 1
    assert report["summary"]["unique_shader_pair_count"] == 1
    assert report["summary"]["unique_geometry_identity_count"] == 1

    draw = report["draws"][0]
    assert draw["classification"] == "strong-capture-local"
    assert draw["missing_capture_local_state"] == []
    assert draw["shader_pair"] == {
        "vertex_shader_sha256": VS_SHA,
        "pixel_shader_sha256": PS_SHA,
    }
    assert draw["shader_objects"]["vertex_shader_creation_event_index"] == 1
    assert draw["shader_objects"]["pixel_shader_creation_event_index"] == 2
    assert draw["geometry_identity"]["stream0_vertex_buffer_creation_event_index"] == 4
    assert draw["geometry_identity"]["index_buffer_creation_event_index"] == 6
    assert draw["draw_range"]["start_index"] == 12
    assert draw["streams"][1]["stream"] == 1
    assert draw["streams"][1]["offset_in_bytes"] == 64

    assert draw["vertex_constants"]["status"] == "complete"
    assert draw["vertex_constants"]["transform_name_match_count"] == 1
    assert draw["vertex_constants"]["transform_signature_sha256"]
    world = draw["vertex_constants"]["variables"][0]
    assert world["name"] == "World"
    assert world["registers"][3]["values"] == [10.0, 20.0, 30.0, 1.0]
    assert world["registers"][3]["last_write_event_index"] == 15

    assert draw["pixel_constants"]["status"] == "complete"
    assert draw["pixel_constants"]["variables"][0]["name"] == "Tint"
    assert draw["sampler_bindings"][0]["sampler_name"] == "diffuseMap"
    assert draw["sampler_bindings"][0]["texture_ptr"] == "0x60"
    assert draw["sampler_bindings"][0]["texture_creation_event_index"] == 7

    assert report["capture_requirements"]["draw_local_vertex_float_constants"]["status"] == "observed"
    assert report["capture_requirements"]["draw_local_pixel_float_constants"]["status"] == "observed"
    assert report["capture_requirements"]["buffer_payload"]["status"] == "missing"


def test_repeated_geometry_is_disambiguated_without_changing_geometry_identity():
    lines = _base_events()
    lines.extend([
        _line({
            "event": "set_stream_source",
            "frame": 3,
            "event_index": 18,
            "device_ptr": "0x1",
            "stream": 1,
            "vertex_buffer_ptr": "0x41",
            "offset_in_bytes": 128,
            "stride": 64,
        }),
        _line({
            "event": "set_vertex_shader_constant_f",
            "frame": 3,
            "event_index": 19,
            "device_ptr": "0x1",
            "start_register": 3,
            "vector4f_count": 1,
            "values": [40, 50, 60, 1],
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 3,
            "event_index": 20,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "base_vertex_index": 0,
            "min_vertex_index": 0,
            "num_vertices": 100,
            "start_index": 12,
            "primitive_count": 20,
        }),
    ])

    report = build_target_draw_local_evidence(lines, target_inventory=_targets())
    assert report["summary"]["target_draw_count"] == 2
    assert report["summary"]["unique_geometry_identity_count"] == 1
    assert report["summary"]["unique_instance_stream_identity_count"] == 2
    assert report["summary"]["unique_vertex_constant_signature_count"] == 2
    assert report["summary"]["unique_name_suggested_transform_signature_count"] == 2
    assert report["summary"]["repeated_geometry_group_count"] == 1
    assert report["summary"]["distinguished_repeated_geometry_group_count"] == 1

    first, second = report["draws"]
    assert first["geometry_identity_sha256"] == second["geometry_identity_sha256"]
    assert first["instance_stream_identity_sha256"] != second["instance_stream_identity_sha256"]
    assert first["vertex_constants"]["signature_sha256"] != second["vertex_constants"]["signature_sha256"]

    group = report["geometry_groups"][0]
    assert group["disambiguation_status"] == "distinguished-by-existing-capture"
    assert "instance-stream" in group["disambiguation_signals"]
    assert "name-suggested-transform-constants" in group["disambiguation_signals"]
    assert "vertex-float-constants" in group["disambiguation_signals"]


def test_missing_draw_state_stays_partial_and_report_is_deterministic():
    lines = [
        _line({
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 2,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 3,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "base_vertex_index": 0,
            "start_index": 0,
            "primitive_count": 1,
        }),
    ]

    first = build_target_draw_local_evidence(lines, target_inventory=_targets())
    second = build_target_draw_local_evidence(lines, target_inventory=_targets())
    assert first == second
    assert first["summary"]["strong_capture_local_draw_count"] == 0
    assert first["summary"]["partial_capture_local_draw_count"] == 1
    draw = first["draws"][0]
    assert draw["classification"] == "partial-capture-local"
    assert "vertex-shader-creation-unresolved" in draw["missing_capture_local_state"]
    assert "stream0-vertex-buffer-unbound" in draw["missing_capture_local_state"]
    assert "index-buffer-unbound" in draw["missing_capture_local_state"]
    assert "reflected-sampler-unbound" in draw["missing_capture_local_state"]
