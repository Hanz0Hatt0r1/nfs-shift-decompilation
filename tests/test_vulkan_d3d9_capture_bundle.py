import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "render" / "vulkan"))
import vulkan_d3d9_capture_bundle as capture_bundle
from vulkan_d3d9_capture_bundle import (
    CAPTURE_GEOMETRY,
    GEOMETRY_ATTRIBUTE,
    GEOMETRY_HEADER,
    _captured_buffer_bytes,
    _captured_buffer_range,
    _captured_depth_surface,
    _captured_surface_formats,
    _capture_constants,
    _draw_bool_constants,
    _captured_shader_inputs,
    _captured_stream_frequency_contract,
    _capture_texture_packet,
    _interleave_vertex_streams,
    _payload_precedes_draw,
    _pipeline_state,
    _read_events,
    _sampler_state,
    _validate_texture_mip_filter,
    encode_capture_geometry,
)

PARTIAL_BUFFER_CAPTURE_OPTIONS = {
    "buffer_payload_capture_enabled": True,
    "partial_buffer_payload_capture_enabled": True,
    "partial_buffer_payload_length_filter": 0,
}


def test_draw_bool_constants_require_successful_exact_state_capture():
    from shader_asm import Instruction, Operand, ShaderProgram

    program = ShaderProgram(
        0, 0, "pixel", 3, 0,
        [Instruction(0, 40, "IF", 0, 1, 0, False, [
            Operand(token=0, kind="source", reg_type=14, index=0, swizzle="xxxx")
        ])],
        inputs=[], outputs=[], samplers=[], constants=[], temps=[],
        unsupported_opcodes=[], const_ints=[], const_bools=[0], sampler_types={},
    )
    captured = {"pixel_bool_constants_hr": 0, "pixel_bool_constants": [1] + [0] * 15}

    assert _draw_bool_constants(captured, "pixel", program) == {0: True}

    with pytest.raises(ValueError, match="no successful pixel boolean-constant query"):
        _draw_bool_constants({"pixel_bool_constants": [0] * 16}, "pixel", program)

    with pytest.raises(ValueError, match="incomplete pixel boolean constants"):
        _draw_bool_constants(
            {"pixel_bool_constants_hr": 0, "pixel_bool_constants": [0]},
            "pixel",
            program,
        )



def test_bool_hresult_packet_fallback_accepts_nonzero_dword():
    program = SimpleNamespace(const_bools=[0], instructions=[])
    draw = {"pixel_bool_constants_hr": 0, "pixel_bool_constants": [0xffffffff] + [0] * 15}
    assert _draw_bool_constants(draw, "pixel", program) == {0: True}
    draw["pixel_bool_constants_hr"] = -1
    with pytest.raises(ValueError, match="no successful pixel boolean-constant query"):
        _draw_bool_constants(draw, "pixel", program)


def test_guest_last_clear_without_target_proof_does_not_become_replay_clear(
    monkeypatch, tmp_path
):
    draw = {"primitive_type": 4}
    state = {
        "streams": {0: {"vertex_buffer_ptr": "vb"}},
        "indices": {"index_buffer_ptr": "ib"},
        "declaration": {"declaration_ptr": "decl"},
        "vertex_shader": {"shader_ptr": "vs"},
        "pixel_shader": {"shader_ptr": "ps"},
        "viewport": {"x": 0},
        "render_target": {"resource_signature": "rt"},
        "clear": {"guest_packet_last_clear_unproven_target": True},
        "clear_render_target": "rt",
    }
    monkeypatch.setattr(capture_bundle, "_read_events", lambda *_: (draw, state))
    with pytest.raises(ValueError, match="no target identity or ordering proof"):
        capture_bundle.build_vulkan_capture_bundle(
            tmp_path / "unused.jsonl", 7, tmp_path / "bundle"
        )


def test_packet_bool_constants_use_set_mask_and_dword_truth_value():
    from shader_asm import Instruction, Operand, ShaderProgram

    program = ShaderProgram(
        0, 0, "pixel", 3, 0,
        [Instruction(0, 40, "IF", 0, 1, 0, False, [
            Operand(token=0, kind="source", reg_type=14, index=0, swizzle="xxxx")
        ])],
        inputs=[], outputs=[], samplers=[], constants=[], temps=[],
        unsupported_opcodes=[], const_ints=[], const_bools=[0], sampler_types={},
    )
    packet_draw = {
        "pixel_bool_constants": [0xffffffff] + [0] * 15,
        "pixel_bool_constant_set_mask": 1,
    }
    assert _draw_bool_constants(packet_draw, "pixel", program) == {0: True}

    packet_draw["pixel_bool_constant_set_mask"] = 0
    with pytest.raises(ValueError, match="no written pixel boolean register b0"):
        _draw_bool_constants(packet_draw, "pixel", program)


def test_packet_float_constant_dwords_and_masks_survive_capture_packet(tmp_path):
    vertex_bits = [0x7fc12345, 0x80000000, 0, 0] + [0] * (256 * 4 - 4)
    pixel_bits = [0] * (224 * 4)
    rows = [
        {
            "event_index": 0,
            "frame": 0,
            "process_id": 1,
            "device_ptr": "dev",
            "event": "set_vertex_shader_constant_f",
            "start_register": 0,
            "vector4f_count": 1,
            "values_bits": vertex_bits[:4],
        },
        {
            "event_index": 1,
            "frame": 0,
            "process_id": 1,
            "device_ptr": "dev",
            "event": "draw_indexed_primitive",
            "vertex_float_constants_bits": vertex_bits,
            "vertex_float_constant_set_mask": [1] + [0] * 7,
            "pixel_float_constants_bits": pixel_bits,
            "pixel_float_constant_set_mask": [0] * 8,
        },
    ]
    capture = tmp_path / "capture.jsonl"
    capture.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    draw, state = _read_events(capture, 1)
    assert state["constant_register_bits"]["vertex"][:4] == vertex_bits[:4]
    assert state["packet_constant_snapshot"]["vertex"]["set_mask"] == [1] + [0] * 7
    output = tmp_path / "constants.svcp"
    report = _capture_constants(state, output)
    payload = output.read_bytes()
    assert report["vertex_populated"] == 1
    assert payload[28:44] == struct.pack("<4I", *vertex_bits[:4])
    assert draw["vertex_float_constant_set_mask"][0] == 1



def test_hresult_only_packet_keeps_exact_float_bits_without_fabricating_writes(
    tmp_path
):
    vertex_bits = [0x7fc12345, 0x80000000, 0, 0] + [0] * (256 * 4 - 4)
    pixel_bits = [0] * (224 * 4)
    capture = tmp_path / "capture.jsonl"
    capture.write_text(json.dumps({
        "event": "draw_indexed_primitive", "event_index": 0, "frame": 0,
        "process_id": 1, "device_ptr": "dev",
        "vertex_float_constants_bits": vertex_bits,
        "pixel_float_constants_bits": pixel_bits,
    }) + "\n", encoding="utf-8")
    draw, state = _read_events(capture, 0)
    assert draw["vertex_float_constants_bits"][:2] == vertex_bits[:2]
    assert state["packet_constant_snapshot"]["vertex"]["values_bits"][:2] == vertex_bits[:2]
    assert state["packet_constant_snapshot"]["vertex"]["set_mask"] is None
    assert state["constant_registers"]["vertex"] == set()
    with pytest.raises(ValueError, match="validity masks are missing"):
        capture_bundle.build_vulkan_capture_bundle(capture, 0, tmp_path / "bundle")


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
    payload = state["objects"]["payload"]["vb"][0]
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
    payload = state["objects"]["payload"]["vb"][0]
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
    assert _captured_surface_formats(21, 80, True) == (
        "VK_FORMAT_B8G8R8A8_UNORM",
        "VK_FORMAT_D16_UNORM",
    )
    with pytest.raises(ValueError, match="render-target format"):
        _captured_surface_formats(22, 75, True)
    with pytest.raises(ValueError, match="depth format"):
        _captured_surface_formats(114, 71, True)


def test_null_depth_stencil_binding_is_not_a_surface():
    assert _captured_depth_surface({"surface_ptr": None, "surface_descriptor_status": "null"}) is None
    surface = {"surface_ptr": "0x1234", "surface_width": 128, "surface_height": 128}
    assert _captured_depth_surface(surface) is surface


def test_capture_mip_filter_is_preserved_and_checked_against_texture_levels():
    sampler = _sampler_state({1: 1, 2: 1, 5: 2, 6: 2, 7: 2})
    assert sampler["mip_filter"] == "LINEAR"
    assert sampler["srgb"] is False
    _validate_texture_mip_filter(1, sampler)
    with pytest.raises(ValueError, match="mip-chain support"):
        _validate_texture_mip_filter(2, sampler)


def test_capture_sampler_preserves_border_color_and_srgb_state():
    sampler = _sampler_state({1: 4, 2: 4, 4: 0, 5: 2, 6: 2, 7: 0, 11: 1})
    assert sampler["address_u"] == "CLAMP_TO_BORDER"
    assert sampler["address_v"] == "CLAMP_TO_BORDER"
    assert sampler["border_color"] == "TRANSPARENT_BLACK"
    assert sampler["srgb"] is True


def test_capture_sampler_rejects_unsupported_border_color():
    with pytest.raises(ValueError, match="border color is unsupported"):
        _sampler_state({1: 4, 2: 4, 4: 0xFF000000, 5: 2, 6: 2, 7: 0})


def test_capture_pipeline_preserves_separate_alpha_blend_factors():
    pipeline = _pipeline_state({
        7: 0, 14: 0, 23: 8, 27: 1, 19: 5, 20: 6, 22: 3,
        168: 0xF, 171: 1, 206: 1, 207: 2, 208: 6,
    })
    assert pipeline["src_color_blend_factor"] == "VK_BLEND_FACTOR_SRC_ALPHA"
    assert pipeline["dst_color_blend_factor"] == "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA"
    assert pipeline["src_alpha_blend_factor"] == "VK_BLEND_FACTOR_ONE"
    assert pipeline["dst_alpha_blend_factor"] == "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA"
    assert pipeline["alpha_blend_op"] == "VK_BLEND_OP_ADD"


def test_capture_rejects_unknown_mip_filter():
    with pytest.raises(ValueError, match="sampler value is unsupported"):
        _sampler_state({1: 1, 2: 1, 5: 2, 6: 2, 7: 6})


def test_capture_texture_packet_preserves_all_used_pixel_sampler_registers(tmp_path, monkeypatch):
    capture_root = tmp_path / "capture"
    texture_dir = capture_root / "textures"
    texture_dir.mkdir(parents=True)
    texture_states = {}
    sampler_states = {}
    for register in range(5):
        name = f"s{register}.dds"
        (texture_dir / name).write_bytes(bytes([register]))
        texture_states[register] = {
            "snapshot_status": "captured",
            "snapshot_paths": [fr"C:\capture\textures\{name}"],
        }
        sampler_states[register] = {1: 1, 2: 1, 5: 2, 6: 2, 7: 2}

    monkeypatch.setattr(
        capture_bundle,
        "decode_dds",
        lambda _: {
            "format": "SHIFT.ReferenceTexture/1",
            "width": 1,
            "height": 1,
            "pixel_format": "RGBA8",
            "pixels": [1, 2, 3, 255],
            "mipmaps": 1,
        },
    )
    report, resources, samplers = _capture_texture_packet(
        {"textures": texture_states, "sampler_states": sampler_states},
        capture_root,
        SimpleNamespace(samplers=list(range(5)), sampler_types={}),
        tmp_path / "textures.svtp",
    )

    assert [row["register"] for row in report["textures"]] == [0, 1, 2, 3, 4]
    assert [row["register"] for row in resources] == [0, 1, 2, 3, 4]
    assert set(samplers) == {0, 1, 2, 3, 4}


def test_capture_texture_packet_fails_closed_for_missing_used_sampler_binding(tmp_path):
    with pytest.raises(ValueError, match="s4 has no captured texture binding"):
        _capture_texture_packet(
            {"textures": {}, "sampler_states": {}},
            tmp_path,
            SimpleNamespace(samplers=[4], sampler_types={}),
            tmp_path / "textures.svtp",
        )


def test_capture_texture_packet_is_omitted_for_untextured_pixel_shader(tmp_path):
    output = tmp_path / "textures.svtp"
    report, resources, samplers = _capture_texture_packet(
        {}, tmp_path, SimpleNamespace(samplers=[], sampler_types={}), output
    )

    assert report["status"] == "not-required"
    assert report["texture_count"] == 0
    assert resources == []
    assert samplers == {}
    assert not output.exists()


def test_capture_buffer_payload_ranges_reconstruct_full_buffer_in_capture_order(tmp_path):
    buffer_dir = tmp_path / "buffers"
    buffer_dir.mkdir()
    chunks = (("first.bin", b"ab", 0, 2), ("second.bin", b"cd", 2, 3), ("update.bin", b"XY", 1, 4))
    rows = []
    for event_index, (name, payload, offset, frame) in enumerate(chunks, 20):
        (buffer_dir / name).write_bytes(payload)
        rows.append({
            "event_index": event_index,
            "payload_capture_frame": frame,
            "buffer_length": 4,
            "offset": offset,
            "captured_byte_size": len(payload),
            "snapshot_status": "captured",
            "payload_path": fr"C:\capture\buffers\{name}",
        })

    data, used_rows = _captured_buffer_bytes(
        tmp_path,
        rows,
        {"event_index": 1, "frame": 0},
        {"event_index": 50, "frame": 5},
        PARTIAL_BUFFER_CAPTURE_OPTIONS,
        4,
        "vertex",
    )

    assert data == b"aXYd"
    assert [row["event_index"] for row in used_rows] == [20, 21, 22]


def test_capture_buffer_payload_ranges_reject_incomplete_coverage(tmp_path):
    buffer_dir = tmp_path / "buffers"
    buffer_dir.mkdir()
    (buffer_dir / "left.bin").write_bytes(b"ab")
    row = {
        "event_index": 20,
        "payload_capture_frame": 2,
        "buffer_length": 4,
        "offset": 0,
        "captured_byte_size": 2,
        "snapshot_status": "captured",
        "payload_path": r"C:\capture\buffers\left.bin",
    }

    with pytest.raises(ValueError, match="do not cover the required draw range"):
        _captured_buffer_bytes(
            tmp_path,
            [row],
            {"event_index": 1, "frame": 0},
            {"event_index": 50, "frame": 5},
            PARTIAL_BUFFER_CAPTURE_OPTIONS,
            4,
            "index",
        )


def test_capture_buffer_payload_discard_invalidates_older_ranges(tmp_path):
    buffer_dir = tmp_path / "buffers"
    buffer_dir.mkdir()
    (buffer_dir / "whole.bin").write_bytes(b"abcd")
    (buffer_dir / "discard.bin").write_bytes(b"XY")
    rows = [
        {
            "event_index": 20,
            "payload_capture_frame": 2,
            "buffer_length": 4,
            "offset": 0,
            "captured_byte_size": 4,
            "snapshot_status": "captured",
            "payload_path": r"C:\capture\buffers\whole.bin",
        },
        {
            "event_index": 21,
            "payload_capture_frame": 3,
            "buffer_length": 4,
            "offset": 1,
            "captured_byte_size": 2,
            "flags": 0x2000,
            "snapshot_status": "captured",
            "payload_path": r"C:\capture\buffers\discard.bin",
        },
    ]

    with pytest.raises(ValueError, match="do not cover the required draw range"):
        _captured_buffer_bytes(
            tmp_path,
            rows,
            {"event_index": 1, "frame": 0},
            {"event_index": 50, "frame": 5},
            PARTIAL_BUFFER_CAPTURE_OPTIONS,
            4,
            "vertex",
        )


def test_capture_buffer_payload_skips_late_same_frame_payload(tmp_path):
    row = {
        "event_index": 51,
        "frame": 5,
        "payload_capture_frame": 5,
        "buffer_length": 4,
        "offset": 0,
        "captured_byte_size": 4,
        "snapshot_status": "captured",
    }

    with pytest.raises(ValueError, match="do not cover the required draw range"):
        _captured_buffer_bytes(
            tmp_path,
            [row],
            {"event_index": 1, "frame": 0},
            {"event_index": 50, "frame": 5},
            PARTIAL_BUFFER_CAPTURE_OPTIONS,
            4,
            "vertex",
        )


@pytest.mark.parametrize(
    ("capture_options", "error"),
    [
        (
            {**PARTIAL_BUFFER_CAPTURE_OPTIONS, "partial_buffer_payload_capture_enabled": False},
            "requires confirmed partial Lock-range capture",
        ),
        (
            {**PARTIAL_BUFFER_CAPTURE_OPTIONS, "partial_buffer_payload_length_filter": 8},
            "excluded by the partial payload length filter",
        ),
    ],
)
def test_capture_buffer_payload_rejects_untracked_lock_history(tmp_path, capture_options, error):
    buffer_dir = tmp_path / "buffers"
    buffer_dir.mkdir()
    (buffer_dir / "full.bin").write_bytes(b"abcd")
    full_payload = {
        "event_index": 2,
        "payload_capture_frame": 1,
        "buffer_length": 4,
        "offset": 0,
        "captured_byte_size": 4,
        "snapshot_status": "captured",
        "payload_path": r"C:\capture\buffers\full.bin",
        "capture_scope": "locked-range",
        }

    with pytest.raises(ValueError, match=error):
        _captured_buffer_bytes(
            tmp_path,
            [full_payload],
            {"event_index": 1, "frame": 0},
            {"event_index": 50, "frame": 5},
            capture_options,
            4,
            "vertex",
        )


def test_capture_buffer_payload_accepts_full_snapshot_outside_partial_filter(tmp_path):
    buffer_dir = tmp_path / "buffers"
    buffer_dir.mkdir()
    (buffer_dir / "full.bin").write_bytes(b"abcd")
    row = {
        "event_index": 2,
        "payload_capture_frame": 1,
        "buffer_length": 4,
        "offset": 0,
        "captured_byte_size": 4,
        "snapshot_status": "captured",
        "capture_scope": "full-buffer",
        "payload_path": r"C:\capture\buffers\full.bin",
    }

    data, used_rows = _captured_buffer_bytes(
        tmp_path,
        [row],
        {"event_index": 1, "frame": 0},
        {"event_index": 50, "frame": 5},
        {**PARTIAL_BUFFER_CAPTURE_OPTIONS, "partial_buffer_payload_length_filter": 131072},
        4,
        "vertex",
    )

    assert data == b"abcd"
    assert used_rows == [row]


def test_capture_buffer_range_reconstructs_only_a_locked_slice(tmp_path):
    buffer_dir = tmp_path / "buffers"
    buffer_dir.mkdir()
    (buffer_dir / "first.bin").write_bytes(b"abcdef")
    (buffer_dir / "second.bin").write_bytes(b"gh")
    rows = [
        {
            "event_index": 2,
            "payload_capture_frame": 1,
            "buffer_length": 16,
            "offset": 0,
            "captured_byte_size": 6,
            "snapshot_status": "captured",
            "capture_scope": "locked-range",
            "payload_path": r"C:\capture\buffers\first.bin",
        },
        {
            "event_index": 3,
            "payload_capture_frame": 2,
            "buffer_length": 16,
            "offset": 6,
            "captured_byte_size": 2,
            "snapshot_status": "captured",
            "capture_scope": "locked-range",
            "payload_path": r"C:\capture\buffers\second.bin",
        },
    ]

    data, used_rows = _captured_buffer_range(
        tmp_path,
        rows,
        {"event_index": 1, "frame": 0},
        {"event_index": 50, "frame": 5},
        {**PARTIAL_BUFFER_CAPTURE_OPTIONS, "partial_buffer_payload_length_filter": 16},
        16,
        2,
        6,
        "vertex stream 1",
    )

    assert data == b"cdefgh"
    assert [row["event_index"] for row in used_rows] == [2, 3]


def test_captured_vertex_inputs_map_extra_texcoords_to_second_stream():
    program = SimpleNamespace(inputs=[
        {"usage": "POSITION", "index": 0, "register": "v0"},
        {"usage": "TEXCOORD", "index": 8, "register": "v1"},
    ])
    elements = [
        {"stream": 0, "offset": 0, "type": 2, "usage": 0, "usage_index": 0},
        {"stream": 1, "offset": 0, "type": 3, "usage": 5, "usage_index": 8},
    ]
    streams = {0: {"stride": 12}, 1: {"stride": 16, "offset_in_bytes": 64}}

    attributes, bindings = _captured_shader_inputs(program, elements, streams)

    assert [(row["location"], row["source_stream"]) for row in attributes] == [(0, 0), (1, 1)]
    assert bindings[1]["semantic"] == {"usage": "TEXCOORD", "index": 8}
    assert bindings[1]["source_stream_offset"] == 64


def test_interleave_vertex_streams_preserves_per_stream_offsets():
    attributes = [
        {
            "location": 0,
            "format": 2,
            "property_id": 0,
            "d3d_type": 2,
            "source_stream": 0,
            "source_offset": 0,
            "source_stride": 12,
            "source_stream_offset": 0,
        },
        {
            "location": 1,
            "format": 3,
            "property_id": 0,
            "d3d_type": 3,
            "source_stream": 1,
            "source_offset": 0,
            "source_stride": 16,
            "source_stream_offset": 16,
        },
    ]

    vertices, stride, output_attributes = _interleave_vertex_streams(
        attributes,
        {
            0: (0, b"abcdefghijklmnopqrstuvwx"),
            1: (16, b"1234567890abcdefABCDEFGHIJKLMNOP"),
        },
        0,
        1,
    )

    assert stride == 28
    assert [row["offset"] for row in output_attributes] == [0, 12]
    assert vertices == (
        b"abcdefghijkl" + b"1234567890abcdef"
        + b"mnopqrstuvwx" + b"ABCDEFGHIJKLMNOP"
    )


def test_single_instance_stream_is_repeated_for_each_indexed_vertex():
    attributes = [
        {"location": 0, "format": 2, "d3d_type": 2, "source_stream": 0,
         "source_offset": 0, "source_stride": 12, "source_stream_offset": 0},
        {"location": 1, "format": 3, "d3d_type": 3, "source_stream": 1,
         "source_offset": 0, "source_stride": 16, "source_stream_offset": 0},
    ]
    vertices, stride, _ = _interleave_vertex_streams(
        attributes,
        {0: (0, b"abcdefghijklmnopqrstuvwx"), 1: (0, b"1234567890abcdef")},
        0,
        1,
        instance_streams={1},
    )
    assert stride == 28
    assert vertices == (
        b"abcdefghijkl1234567890abcdef"
        + b"mnopqrstuvwx1234567890abcdef"
    )


def test_captured_stream_frequency_contract_accepts_single_instance():
    draw = {"stream_source_frequencies": [
        {"stream": 0, "setting": 0x40000001},
        {"stream": 1, "setting": 0x80000001},
    ]}
    assert _captured_stream_frequency_contract(
        draw, {"stream_source_freq_capture": True}
    ) == (1, {1}, {0: 0x40000001, 1: 0x80000001})


def test_captured_stream_frequency_contract_rejects_multidraw_instancing():
    draw = {"stream_source_frequencies": [
        {"stream": 0, "setting": 0x40000009},
        {"stream": 1, "setting": 0x80000001},
    ]}
    with pytest.raises(ValueError, match="uses 9 instances"):
        _captured_stream_frequency_contract(
            draw, {"stream_source_freq_capture": True}
        )


def test_captured_stream_frequency_contract_requires_capture_capability():
    with pytest.raises(ValueError, match="does not prove SetStreamSourceFreq"):
        _captured_stream_frequency_contract(
            {"stream_source_frequencies": []}, {}
        )


def test_read_events_retains_capture_payload_mode_for_the_draw_device(tmp_path):
    rows = [
        {
            "event_index": 0,
            "frame": 0,
            "process_id": 1,
            "device_ptr": "dev",
            "event": "device_hooks",
            **PARTIAL_BUFFER_CAPTURE_OPTIONS,
        },
        {
            "event_index": 1,
            "frame": 0,
            "process_id": 1,
            "device_ptr": "dev",
            "event": "draw_indexed_primitive",
        },
    ]
    capture = tmp_path / "capture.jsonl"
    capture.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    _, state = _read_events(capture, 1)

    assert state["capture_options"]["partial_buffer_payload_capture_enabled"] is True
