import struct
import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "render" / "vulkan"))
from vulkan_d3d9_capture_bundle import (
    CAPTURE_GEOMETRY,
    GEOMETRY_ATTRIBUTE,
    GEOMETRY_HEADER,
    _captured_surface_formats,
    _payload_precedes_draw,
    _read_events,
    _sampler_state,
    _validate_texture_mip_filter,
    encode_capture_geometry,
)


def test_capture_bundle_uses_deferred_buffer_payload_captured_before_draw(tmp_path):
    rows = [
        {"event_index": 0, "frame": 2, "process_id": 1, "event": "create_vertex_buffer", "vertex_buffer_ptr": "vb"},
        {"event_index": 1, "frame": 2, "process_id": 1, "event": "create_index_buffer", "index_buffer_ptr": "ib"},
        {"event_index": 2, "frame": 8, "process_id": 1, "device_ptr": "dev", "event": "draw_indexed_primitive"},
        {"event_index": 3, "frame": 8, "process_id": 1, "event": "buffer_payload", "buffer_ptr": "vb", "payload_capture_frame": 7},
        {"event_index": 4, "frame": 8, "process_id": 1, "event": "buffer_payload", "buffer_ptr": "ib", "payload_capture_frame": 7},
    ]
    capture = tmp_path / "capture.jsonl"
    capture.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    draw, state = _read_events(capture, 2)
    payload = state["objects"]["payload"]["vb"]
    assert payload["event_index"] == 3
    assert _payload_precedes_draw(payload, draw)


def test_capture_bundle_rejects_same_frame_deferred_buffer_payload(tmp_path):
    rows = [
        {"event_index": 0, "frame": 2, "process_id": 1, "event": "create_vertex_buffer", "vertex_buffer_ptr": "vb"},
        {"event_index": 2, "frame": 8, "process_id": 1, "device_ptr": "dev", "event": "draw_indexed_primitive"},
        {"event_index": 3, "frame": 8, "process_id": 1, "event": "buffer_payload", "buffer_ptr": "vb", "payload_capture_frame": 8},
    ]
    capture = tmp_path / "capture.jsonl"
    capture.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    draw, state = _read_events(capture, 2)
    payload = state["objects"]["payload"]["vb"]
    assert not _payload_precedes_draw(payload, draw)


def test_capture_geometry_preserves_index16_and_draw_parameters():
    vertices = bytes(4 * 12)
    indices = struct.pack("<6H", 0, 1, 2, 1, 2, 3)
    packet = encode_capture_geometry(
        vertices,
        indices,
        stride=12,
        attributes=[{"location": 0, "format": 2, "offset": 0}],
        index_format_bits=16,
        first_index=0,
        draw_index_count=6,
        base_vertex=0,
    )

    header = GEOMETRY_HEADER.unpack_from(packet)
    assert header[:7] == (b"SVGP", 4, 4, 6, 12, 1, 0)
    attribute = GEOMETRY_ATTRIBUTE.unpack_from(packet, GEOMETRY_HEADER.size)
    assert attribute == (0, 2, 0, 12, 0)
    metadata_offset = GEOMETRY_HEADER.size + GEOMETRY_ATTRIBUTE.size
    assert CAPTURE_GEOMETRY.unpack_from(packet, metadata_offset) == (16, 6, 0, 0)
    index_offset = metadata_offset + CAPTURE_GEOMETRY.size + len(vertices)
    assert packet[index_offset:] == indices


@pytest.mark.parametrize(
    ("first_index", "draw_index_count"),
    [(1, 6), (0, 4)],
)
def test_capture_geometry_rejects_out_of_range_or_non_triangle_draw(first_index, draw_index_count):
    with pytest.raises(ValueError):
        encode_capture_geometry(
            bytes(4 * 12),
            struct.pack("<6H", 0, 1, 2, 1, 2, 3),
            stride=12,
            attributes=[{"location": 0, "format": 2, "offset": 0}],
            index_format_bits=16,
            first_index=first_index,
            draw_index_count=draw_index_count,
            base_vertex=0,
        )


def test_captured_surface_formats_cover_mobile_targets_and_existing_r32f():
    assert _captured_surface_formats(21, 75, True) == (
        "VK_FORMAT_B8G8R8A8_UNORM",
        "VK_FORMAT_D24_UNORM_S8_UINT",
    )
    assert _captured_surface_formats(113, 75, True) == (
        "VK_FORMAT_R16G16B16A16_SFLOAT",
        "VK_FORMAT_D24_UNORM_S8_UINT",
    )
    assert _captured_surface_formats(114, 75, True) == (
        "VK_FORMAT_R32_SFLOAT",
        "VK_FORMAT_D24_UNORM_S8_UINT",
    )
    with pytest.raises(ValueError, match="render-target format"):
        _captured_surface_formats(22, 75, True)
    with pytest.raises(ValueError, match="depth format"):
        _captured_surface_formats(114, 71, True)


def test_capture_mip_filter_is_preserved_and_checked_against_texture_levels():
    sampler = _sampler_state({1: 1, 2: 1, 5: 2, 6: 2, 7: 2})
    assert sampler["mip_filter"] == "LINEAR"
    _validate_texture_mip_filter(1, sampler)
    with pytest.raises(ValueError, match="mip-chain support"):
        _validate_texture_mip_filter(2, sampler)


def test_capture_rejects_unknown_mip_filter():
    with pytest.raises(ValueError, match="sampler value is unsupported"):
        _sampler_state({1: 1, 2: 1, 5: 2, 6: 2, 7: 6})
