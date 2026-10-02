import hashlib
import json

from d3d9_target_draw_signatures import catalog_target_draw_signatures
from d3d9_target_pointer_observations import (
    FORMAT,
    build_target_pointer_observations,
)


VS = bytes.fromhex("0000feff01000000")
PS = bytes.fromhex("0000ffff02000000")
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


def _base_lines():
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
            "length": 1200,
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
            "length": 131072,
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
            "length": 72,
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
            "height": 1024,
            "levels": 11,
            "usage": 0,
            "format": 894720068,
            "pool": 1,
        }),
        _line({
            "event": "create_texture",
            "frame": 1,
            "event_index": 8,
            "device_ptr": "0x1",
            "texture_ptr": "0x61",
            "width": 512,
            "height": 1024,
            "levels": 11,
            "usage": 0,
            "format": 894720068,
            "pool": 1,
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 2,
            "event_index": 9,
            "device_ptr": "0x1",
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 10,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "set_vertex_declaration",
            "frame": 2,
            "event_index": 11,
            "device_ptr": "0x1",
            "declaration_ptr": "0x30",
        }),
        _line({
            "event": "set_stream_source",
            "frame": 2,
            "event_index": 12,
            "device_ptr": "0x1",
            "stream": 0,
            "vertex_buffer_ptr": "0x40",
            "offset_in_bytes": 0,
            "stride": 60,
        }),
        _line({
            "event": "set_stream_source",
            "frame": 2,
            "event_index": 13,
            "device_ptr": "0x1",
            "stream": 1,
            "vertex_buffer_ptr": "0x41",
            "offset_in_bytes": 64,
            "stride": 64,
        }),
        _line({
            "event": "set_indices",
            "frame": 2,
            "event_index": 14,
            "device_ptr": "0x1",
            "index_buffer_ptr": "0x50",
        }),
        _line({
            "event": "set_texture",
            "frame": 2,
            "event_index": 15,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": "0x60",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 16,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "base_vertex_index": 0,
            "start_index": 0,
            "primitive_count": 12,
        }),
        _line({
            "event": "set_texture",
            "frame": 3,
            "event_index": 17,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": "0x61",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 3,
            "event_index": 18,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "base_vertex_index": 0,
            "start_index": 0,
            "primitive_count": 12,
        }),
    ]


def test_pointer_observations_preserve_shape_sha_but_split_texture_objects():
    lines = _base_lines()
    target_catalog = catalog_target_draw_signatures(
        lines,
        target_inventory=_targets(),
    )
    report = build_target_pointer_observations(
        lines,
        target_inventory=_targets(),
        target_catalog=target_catalog,
    )

    assert report["format"] == FORMAT
    summary = report["summary"]
    assert summary["target_draw_count"] == 2
    assert summary["resource_shape_observation_count"] == 1
    assert summary["unique_geometry_pointer_identity_count"] == 1
    assert summary["unique_material_pointer_identity_count"] == 2
    assert summary["unique_combined_pointer_identity_count"] == 2
    assert summary["complete_geometry_pointer_draw_count"] == 2
    assert summary["catalog_alignment_status"] == "exact"

    shape = report["resource_shapes"][0]
    assert shape["resource_shape_sha256"] == target_catalog[
        "resource_shape_signatures"
    ][0]["signature_sha256"]
    assert shape["draw_count"] == 2
    assert shape["geometry_pointer_identity_count"] == 1
    assert shape["material_pointer_identity_count"] == 2

    geometry = shape["geometry_pointer_observations"][0]["identity"]
    assert geometry["stream0_vertex_buffer_ptr"] == "0x40"
    assert geometry["stream0_vertex_buffer_creation_event_index"] == 4
    assert geometry["index_buffer_ptr"] == "0x50"
    assert geometry["index_buffer_creation_event_index"] == 6
    assert geometry["draw_range"]["primitive_count"] == 12

    texture_ptrs = sorted(
        row["identity"]["texture_stages"][0]["texture_ptr"]
        for row in shape["material_pointer_observations"]
    )
    assert texture_ptrs == ["0x60", "0x61"]


def test_pointer_observations_distinguish_reused_pointer_generations():
    lines = _base_lines()
    # Replace the second texture object with a recreation at the same COM
    # address. Descriptor identity stays equal, but creation generation must
    # keep the observations distinct.
    lines[7] = _line({
        "event": "create_texture",
        "frame": 1,
        "event_index": 8,
        "device_ptr": "0x1",
        "texture_ptr": "0x60",
        "width": 512,
        "height": 1024,
        "levels": 11,
        "usage": 0,
        "format": 894720068,
        "pool": 1,
    })
    lines[16] = _line({
        "event": "set_texture",
        "frame": 3,
        "event_index": 17,
        "device_ptr": "0x1",
        "stage": 0,
        "texture_ptr": "0x60",
    })

    report = build_target_pointer_observations(
        lines,
        target_inventory=_targets(),
    )

    shape = report["resource_shapes"][0]
    # Both draws occur after the second create, so the current generation is
    # the same. This deliberately verifies that the streaming state follows
    # the latest observed creation rather than the pointer string alone.
    assert shape["material_pointer_identity_count"] == 1
    identity = shape["material_pointer_observations"][0]["identity"]
    assert identity["texture_stages"][0][
        "texture_creation_event_index"
    ] == 8


def test_pointer_observations_reject_wrong_catalog_contract():
    try:
        build_target_pointer_observations(
            [],
            target_inventory=_targets(),
            target_catalog={"format": "wrong"},
        )
    except ValueError as error:
        assert "target catalog" in str(error)
    else:
        raise AssertionError("wrong target catalog contract must fail")
