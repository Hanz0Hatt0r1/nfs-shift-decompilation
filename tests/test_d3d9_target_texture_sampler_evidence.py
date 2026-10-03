import hashlib
import json
import struct

from d3d9_target_texture_sampler_evidence import (
    FORMAT,
    build_target_texture_sampler_evidence,
)


def _pixel_shader_with_sampler(name="diffuseMap", register=0):
    version = 0xFFFF0300
    encoded_name = name.encode("ascii") + b"\x00"
    header_size = 28
    info_size = 20
    type_size = 20
    name_offset = header_size + info_size + type_size
    payload = bytearray(b"CTAB")
    payload += struct.pack(
        "<7I",
        header_size,
        0,
        version,
        1,
        header_size,
        0,
        0,
    )
    payload += struct.pack(
        "<IHHHHII",
        name_offset,
        3,
        register,
        1,
        0,
        header_size + info_size,
        0,
    )
    payload += struct.pack("<HHHHHHII", 4, 3, 4, 4, 1, 0, 0, 0)
    payload += encoded_name
    payload += b"\x00" * ((-len(payload)) % 4)
    return (
        struct.pack("<I", version)
        + struct.pack("<I", ((len(payload) // 4) << 16) | 0xFFFE)
        + payload
        + struct.pack("<I", 0xFFFF)
    )


PS = _pixel_shader_with_sampler()
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
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "create_texture",
            "frame": 1,
            "event_index": 2,
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
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 3,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "set_texture",
            "frame": 2,
            "event_index": 4,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": "0x60",
        }),
    ]


def test_texture_sampler_evidence_preserves_create_bind_state_and_draw_provenance():
    lines = _base_events() + [
        _line({
            "event": "set_sampler_state",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
            "sampler": 0,
            "state": 6,
            "value": 2,
        }),
        _line({
            "event": "set_sampler_state",
            "frame": 2,
            "event_index": 6,
            "device_ptr": "0x1",
            "sampler": 0,
            "state": 5,
            "value": 2,
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 7,
            "device_ptr": "0x1",
            "primitive_type": 4,
            "start_index": 0,
            "primitive_count": 2,
        }),
    ]

    report = build_target_texture_sampler_evidence(
        lines,
        target_inventory=_targets(),
    )

    assert report["format"] == FORMAT
    assert report["status"] == "observed"
    assert report["summary"]["target_draw_count"] == 1
    assert report["summary"]["exact_capture_local_draw_count"] == 1
    assert report["summary"]["ctab_reflected_target_draw_count"] == 1
    assert report["summary"]["explicit_sampler_state_target_draw_count"] == 1
    assert report["capture_observations"]["explicit_sampler_state_history"]["status"] == "observed"

    draw = report["draws"][0]
    assert draw["classification"] == "exact-capture-local"
    assert draw["sampler_stage_source"] == "ctab-reflected"
    assert draw["families"] == ["basicinstanced"]
    binding = draw["sampler_bindings"][0]
    assert binding["stage"] == 0
    assert binding["sampler_name"] == "diffuseMap"
    assert binding["texture_ptr"] == "0x60"
    assert binding["texture_creation_event_index"] == 2
    assert binding["texture_bind_event_index"] == 4
    assert binding["texture_generation_ordinal"] == 1
    assert binding["texture_generation_sha256"]
    assert binding["texture_use_sha256"]
    assert binding["resource_scope"] == "runtime-object-generation-only"
    assert binding["sampler_state_status"] == "explicit-writes-observed"
    assert [row["state"] for row in binding["sampler_states"]] == [5, 6]
    assert binding["sampler_states"][0]["state_name"] == "D3DSAMP_MAGFILTER"
    assert binding["sampler_states"][0]["write_event_index"] == 6
    assert binding["sampler_states"][1]["state_name"] == "D3DSAMP_MINFILTER"
    assert binding["sampler_states"][1]["write_event_index"] == 5
    assert draw["sampler_use_signature_sha256"]


def test_texture_pointer_reuse_does_not_rewrite_previous_binding_generation():
    lines = _base_events() + [
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
        }),
        _line({
            "event": "set_texture",
            "frame": 3,
            "event_index": 6,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": None,
        }),
        _line({
            "event": "create_texture",
            "frame": 3,
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
            "event": "set_texture",
            "frame": 3,
            "event_index": 8,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": "0x60",
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 3,
            "event_index": 9,
            "device_ptr": "0x1",
        }),
    ]

    report = build_target_texture_sampler_evidence(
        lines,
        target_inventory=_targets(),
    )

    assert report["summary"]["texture_pointer_reuse_creation_count"] == 1
    assert report["summary"]["target_draw_count"] == 2
    first, second = report["draws"]
    first_binding = first["sampler_bindings"][0]
    second_binding = second["sampler_bindings"][0]
    assert first_binding["texture_ptr"] == second_binding["texture_ptr"] == "0x60"
    assert first_binding["texture_creation_event_index"] == 2
    assert second_binding["texture_creation_event_index"] == 7
    assert first_binding["texture_generation_ordinal"] == 1
    assert second_binding["texture_generation_ordinal"] == 2
    assert first_binding["texture_generation_sha256"] != second_binding["texture_generation_sha256"]
    assert first_binding["texture_use_sha256"] != second_binding["texture_use_sha256"]
    assert first["sampler_use_signature_sha256"] != second["sampler_use_signature_sha256"]


def test_no_sampler_state_event_keeps_exact_texture_provenance_and_reports_gap():
    lines = _base_events() + [
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
        }),
    ]

    report = build_target_texture_sampler_evidence(
        lines,
        target_inventory=_targets(),
    )

    assert report["summary"]["exact_capture_local_draw_count"] == 1
    assert report["summary"]["explicit_sampler_state_target_draw_count"] == 0
    observation = report["capture_observations"]["explicit_sampler_state_history"]
    assert observation["status"] == "not-observed-in-capture"
    assert observation["minimal_missing_event"] == "set_sampler_state"
    binding = report["draws"][0]["sampler_bindings"][0]
    assert binding["sampler_state_status"] == "no-explicit-write-observed"
    assert binding["sampler_states"] == []
    assert report["draws"][0]["classification"] == "exact-capture-local"


def test_portable_identity_and_snapshot_are_kept_without_promoting_material_identity():
    lines = _base_events()
    lines[1] = _line({
        "event": "create_texture",
        "frame": 1,
        "event_index": 2,
        "device_ptr": "0x1",
        "texture_ptr": "0x60",
        "width": 512,
        "height": 512,
        "levels": 1,
        "usage": 0,
        "format": 21,
        "pool": 1,
        "resource_path": "tracks/silverstone/diffuse.dds",
        "resource_sha256": "a" * 64,
        "snapshot_status": "captured",
        "snapshot_paths": ["diffuse.ppm"],
    })
    lines.append(_line({
        "event": "draw_indexed_primitive",
        "frame": 2,
        "event_index": 5,
        "device_ptr": "0x1",
    }))

    report = build_target_texture_sampler_evidence(lines, target_inventory=_targets())

    binding = report["draws"][0]["sampler_bindings"][0]
    assert binding["resource_scope"] == "portable-resource-identified"
    assert binding["portable_resource_identity"] == {
        "resource_path": "tracks/silverstone/diffuse.dds",
        "resource_sha256": "a" * 64,
        "resource_signature": None,
    }
    assert binding["snapshot_status"] == "captured"
    assert binding["snapshot_paths"] == ["diffuse.ppm"]
    assert report["capture_observations"]["portable_resource_path_sha_identity"]["status"] == "observed"
    assert report["capture_observations"]["captured_texture_snapshot"]["status"] == "observed"
    assert report["boundary"]["material_identity"] == "not claimed"


def test_missing_ctab_reflection_falls_back_but_stays_partial():
    raw_ps = bytes.fromhex("0000ffff02000000")
    raw_sha = hashlib.sha256(raw_ps).hexdigest()
    targets = {
        "families": [{
            "family": "raw",
            "pixel_shader_sha256": [raw_sha],
        }]
    }
    lines = [
        _line({
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 1,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
            "bytes_hex": raw_ps.hex(),
        }),
        _line({
            "event": "create_texture",
            "frame": 1,
            "event_index": 2,
            "device_ptr": "0x1",
            "texture_ptr": "0x60",
            "width": 32,
            "height": 32,
            "levels": 1,
            "format": 21,
            "pool": 1,
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 2,
            "event_index": 3,
            "device_ptr": "0x1",
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "set_texture",
            "frame": 2,
            "event_index": 4,
            "device_ptr": "0x1",
            "stage": 0,
            "texture_ptr": "0x60",
        }),
        _line({
            "event": "set_sampler_state",
            "frame": 2,
            "event_index": 5,
            "device_ptr": "0x1",
            "sampler": 0,
            "state": 6,
            "value": 2,
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 2,
            "event_index": 6,
            "device_ptr": "0x1",
        }),
    ]

    report = build_target_texture_sampler_evidence(lines, target_inventory=targets)

    assert report["summary"]["target_draw_count"] == 1
    assert report["summary"]["partial_capture_local_draw_count"] == 1
    draw = report["draws"][0]
    assert draw["sampler_stage_source"] == "reflection-unavailable-fallback"
    assert draw["classification"] == "partial-capture-local"
    assert "pixel-ctab-sampler-reflection-unavailable" in draw["missing_capture_local_state"]
    assert draw["sampler_bindings"][0]["stage"] == 0
