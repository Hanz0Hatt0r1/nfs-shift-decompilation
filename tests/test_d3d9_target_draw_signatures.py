import hashlib
import json
import struct

from d3d9_target_draw_signatures import (
    FORMAT,
    catalog_target_draw_signatures,
)


VS = bytes.fromhex("0000feff01000000")
PS = bytes.fromhex("0000ffff02000000")
VS_SHA = hashlib.sha256(VS).hexdigest()
PS_SHA = hashlib.sha256(PS).hexdigest()


def _reflected_pixel_shader():
    names = [b"diffuseMap\x00", b"environmentMap\x00"]
    header_size = 28
    info_size = 20 * len(names)
    type_size = 20
    offsets = []
    pos = header_size + info_size + type_size
    for name in names:
        offsets.append(pos)
        pos += len(name)

    payload = bytearray(b"CTAB")
    payload += struct.pack(
        "<7I",
        header_size,
        0,
        0xFFFF0300,
        len(names),
        header_size,
        0,
        0,
    )
    for index, name_offset in enumerate(offsets):
        payload += struct.pack(
            "<IHHHHII",
            name_offset,
            3,
            (0, 2)[index],
            1,
            0,
            header_size + info_size,
            0,
        )
    payload += struct.pack("<HHHHHHII", 4, 12, 1, 1, 1, 0, 0, 0)
    payload += b"".join(names)
    payload += b"\x00" * ((-len(payload)) % 4)
    return (
        struct.pack("<I", 0xFFFF0300)
        + struct.pack("<I", ((len(payload) // 4) << 16) | 0xFFFE)
        + payload
        + struct.pack("<I", 0xFFFF)
    )


def _line(value):
    return json.dumps(value, separators=(",", ":"))


def _targets():
    return {
        "families": [{
            "family": "basicinstanced",
            "pixel_shader_sha256": [PS_SHA],
        }]
    }


def test_target_draw_signature_catalog_aggregates_pipeline_and_resource_shapes():
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
            "event": "create_index_buffer",
            "frame": 1,
            "event_index": 5,
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
            "event_index": 6,
            "device_ptr": "0x1",
            "texture_ptr": "0x60",
            "width": 64,
            "height": 64,
            "levels": 1,
            "usage": 0,
            "format": 21,
            "pool": 1,
        }),
        _line({
            "event": "create_texture",
            "frame": 1,
            "event_index": 7,
            "device_ptr": "0x1",
            "texture_ptr": "0x61",
            "width": 128,
            "height": 128,
            "levels": 1,
            "usage": 0,
            "format": 21,
            "pool": 1,
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 2,
            "event_index": 8,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 9,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "set_vertex_declaration",
            "frame": 2,
            "event_index": 10,
            "device_ptr": "0x1",
            "declaration_ptr": "0x30",
        }),
        _line({
            "event": "set_stream_source",
            "frame": 2,
            "event_index": 11,
            "device_ptr": "0x1",
            "stream": 0,
            "vertex_buffer_ptr": "0x40",
            "offset_in_bytes": 0,
            "stride": 60,
        }),
        _line({
            "event": "set_indices",
            "frame": 2,
            "event_index": 12,
            "device_ptr": "0x1",
            "index_buffer_ptr": "0x50",
        }),
        _line({
            "event": "set_texture",
            "frame": 2,
            "event_index": 13,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": "0x60",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 14,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "base_vertex_index": 0,
            "start_index": 0,
            "primitive_count": 10,
        }),
        _line({
            "event": "set_texture",
            "frame": 3,
            "event_index": 15,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": "0x61",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 3,
            "event_index": 16,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "base_vertex_index": 0,
            "start_index": 0,
            "primitive_count": 10,
        }),
    ]

    report = catalog_target_draw_signatures(
        lines,
        target_inventory=_targets(),
    )

    assert report["format"] == FORMAT
    assert report["status"] == "observed"
    assert report["summary"]["target_draw_count"] == 2
    assert report["summary"]["target_draw_hash_count"] == 1
    assert report["summary"]["first_target_frame"] == 2
    assert report["summary"]["last_target_frame"] == 3
    assert report["summary"]["unique_pipeline_signature_count"] == 1
    assert report["summary"]["unique_layout_cohort_count"] == 1
    assert report["summary"]["unique_resource_shape_signature_count"] == 2
    assert report["summary"]["reflected_target_draw_count"] == 0
    assert report["summary"]["fallback_texture_state_draw_count"] == 2

    pipeline = report["pipeline_signatures"][0]
    assert pipeline["draw_count"] == 2
    assert pipeline["primitive_count_sum"] == 20
    assert pipeline["families"] == ["basicinstanced"]
    assert pipeline["target_pixel_hashes"] == [PS_SHA]
    assert pipeline["signature"]["vertex_shader_sha256"] == VS_SHA
    assert pipeline["signature"]["pixel_shader_sha256"] == PS_SHA
    assert pipeline["signature"]["stream_layout"] == [{
        "stream": 0,
        "stride": 60,
    }]
    assert pipeline["signature"]["index_format"] == 101

    cohort = report["layout_cohorts"][0]
    assert cohort["draw_count"] == 2
    assert cohort["families"] == ["basicinstanced"]
    assert cohort["vertex_shader_sha256s"] == [VS_SHA]
    assert cohort["pixel_shader_sha256s"] == [PS_SHA]
    assert cohort["layout"]["stream_layout"] == [{
        "stream": 0,
        "stride": 60,
    }]

    widths = sorted(
        row["signature"]["texture_stages"][0]["width"]
        for row in report["resource_shape_signatures"]
    )
    assert widths == [64, 128]


def test_target_draw_signature_catalog_respects_device_and_null_pixel_shader():
    lines = [
        _line({
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0xa",
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 2,
            "device_ptr": "0xa",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 3,
            "device_ptr": "0xb",
            "primitive_count": 1,
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 4,
            "device_ptr": "0xa",
            "primitive_count": 1,
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 3,
            "event_index": 5,
            "device_ptr": "0xa",
            "shader_ptr": None,
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 3,
            "event_index": 6,
            "device_ptr": "0xa",
            "primitive_count": 1,
        }),
    ]

    report = catalog_target_draw_signatures(
        lines,
        target_inventory=_targets(),
    )

    assert report["summary"]["target_draw_count"] == 1
    assert report["summary"]["first_target_frame"] == 2
    assert report["summary"]["last_target_frame"] == 2


def test_target_draw_signature_catalog_requires_target_hashes():
    try:
        catalog_target_draw_signatures([], target_inventory={})
    except ValueError as error:
        assert "no pixel shader hashes" in str(error)
    else:
        raise AssertionError("empty target inventory must fail")

def test_resource_shape_ignores_transient_stream_offsets_but_reports_them():
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
            "event": "create_vertex_buffer",
            "frame": 1,
            "event_index": 3,
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
            "event_index": 4,
            "device_ptr": "0x1",
            "vertex_buffer_ptr": "0x41",
            "length": 131072,
            "usage": 520,
            "fvf": 0,
            "pool": 0,
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 6,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "set_stream_source",
            "frame": 2,
            "event_index": 7,
            "device_ptr": "0x1",
            "stream": 0,
            "vertex_buffer_ptr": "0x40",
            "offset_in_bytes": 0,
            "stride": 80,
        }),
        _line({
            "event": "set_stream_source",
            "frame": 2,
            "event_index": 8,
            "device_ptr": "0x1",
            "stream": 1,
            "vertex_buffer_ptr": "0x41",
            "offset_in_bytes": 64,
            "stride": 64,
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 9,
            "device_ptr": "0x1",
            "primitive_count": 10,
        }),
        _line({
            "event": "set_stream_source",
            "frame": 3,
            "event_index": 10,
            "device_ptr": "0x1",
            "stream": 1,
            "vertex_buffer_ptr": "0x41",
            "offset_in_bytes": 128,
            "stride": 64,
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 3,
            "event_index": 11,
            "device_ptr": "0x1",
            "primitive_count": 10,
        }),
    ]

    report = catalog_target_draw_signatures(
        lines,
        target_inventory=_targets(),
    )

    assert report["summary"]["target_draw_count"] == 2
    assert report["summary"]["unique_resource_shape_signature_count"] == 1
    shape = report["resource_shape_signatures"][0]
    assert shape["draw_count"] == 2
    assert all(
        "offset_in_bytes" not in stream
        for stream in shape["signature"]["stream_resource_shapes"]
    )
    by_stream = {
        row["stream"]: row
        for row in shape["stream_offset_observations"]
    }
    assert by_stream[0]["unique_offset_count"] == 1
    assert by_stream[1]["unique_offset_count"] == 2
    assert by_stream[1]["min_offset_in_bytes"] == 64
    assert by_stream[1]["max_offset_in_bytes"] == 128

def test_resource_shape_filters_stale_texture_stages_with_pixel_ctab():
    reflected_ps = _reflected_pixel_shader()
    reflected_ps_sha = hashlib.sha256(reflected_ps).hexdigest()
    targets = {
        "families": [{
            "family": "basicinstanced",
            "pixel_shader_sha256": [reflected_ps_sha],
        }]
    }
    lines = [
        _line({
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": reflected_ps.hex(),
        }),
        *[
            _line({
                "event": "create_texture",
                "frame": 1,
                "event_index": 2 + stage,
                "device_ptr": "0x1",
                "texture_ptr": f"0x{0x60 + stage:x}",
                "width": 64 * (stage + 1),
                "height": 64,
                "levels": 1,
                "usage": 0,
                "format": 21,
                "pool": 1,
            })
            for stage in range(3)
        ],
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        *[
            _line({
                "event": "set_texture",
                "frame": 2,
                "event_index": 6 + stage,
                "device_ptr": "0x1",
                "stage": stage,
                "texture_ptr": f"0x{0x60 + stage:x}",
            })
            for stage in range(3)
        ],
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 9,
            "device_ptr": "0x1",
            "primitive_count": 1,
        }),
    ]

    report = catalog_target_draw_signatures(
        lines,
        target_inventory=targets,
    )

    assert report["summary"]["reflected_target_draw_count"] == 1
    assert report["summary"]["fallback_texture_state_draw_count"] == 0
    shape = report["resource_shape_signatures"][0]
    assert [
        texture["stage"]
        for texture in shape["signature"]["texture_stages"]
    ] == [0, 2]

