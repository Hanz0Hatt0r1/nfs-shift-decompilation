import hashlib
import json

import d3d9_raw_capture_audit as audit
from d3d9_raw_capture_audit import FORMAT, audit_capture_lines


VS = bytes.fromhex("0000feff01000000")
PS = bytes.fromhex("0000ffff02000000")
PS_SHA = hashlib.sha256(PS).hexdigest()


def _line(value):
    return json.dumps(value, separators=(",", ":"))


def test_raw_capture_audit_reports_shader_target_and_missing_payload_gates():
    lines = [
        _line({
            "event": "proxy_direct3dcreate9",
            "frame": 0,
            "event_index": 0,
            "tick_ms": 100,
        }),
        _line({
            "event": "create_vertex_shader",
            "frame": 4,
            "event_index": 10,
            "tick_ms": 110,
            "shader_ptr": "0x10",
            "bytes_hex": VS.hex(),
        }),
        _line({
            "event": "create_pixel_shader",
            "frame": 4,
            "event_index": 11,
            "tick_ms": 111,
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "create_vertex_declaration",
            "frame": 4,
            "event_index": 12,
            "tick_ms": 112,
            "declaration_ptr": "0x30",
            "bytes_hex": "0000000002000000ff00000011000000",
        }),
        _line({
            "event": "set_vertex_declaration",
            "frame": 4,
            "event_index": 13,
            "tick_ms": 113,
            "declaration_ptr": "0x30",
        }),
        _line({
            "event": "set_stream_source",
            "frame": 4,
            "event_index": 14,
            "tick_ms": 114,
            "vertex_buffer_ptr": "0x40",
            "stream": 0,
            "offset_in_bytes": 0,
            "stride": 32,
        }),
        _line({
            "event": "set_indices",
            "frame": 4,
            "event_index": 15,
            "tick_ms": 115,
            "index_buffer_ptr": "0x50",
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 4,
            "event_index": 16,
            "tick_ms": 116,
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 4,
            "event_index": 17,
            "tick_ms": 117,
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "set_vertex_shader_constant_f",
            "frame": 4,
            "event_index": 18,
            "tick_ms": 118,
            "start_register": 0,
            "vector4f_count": 1,
            "values": [1, 0, 0, 1],
        }),
        _line({
            "event": "create_texture",
            "frame": 4,
            "event_index": 19,
            "tick_ms": 119,
            "texture_ptr": "0x60",
            "width": 4,
            "height": 4,
            "levels": 1,
            "usage": 0,
            "format": 21,
            "pool": 1,
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 4,
            "event_index": 20,
            "tick_ms": 120,
            "primitive_type": 4,
            "base_vertex_index": 0,
            "start_index": 0,
            "primitive_count": 1,
        }),
    ]
    targets = {
        "families": [{
            "family": "test",
            "pixel_shader_sha256": [PS_SHA],
        }]
    }

    report = audit_capture_lines(lines, target_inventory=targets)

    assert report["format"] == FORMAT
    assert report["capture_profile"] == "shader-draw-state-only"
    assert report["summary"]["frame_min"] == 0
    assert report["summary"]["frame_max"] == 4
    assert report["summary"]["duration_ms"] == 20
    assert report["summary"]["unique_vertex_shader_count"] == 1
    assert report["summary"]["unique_pixel_shader_count"] == 1
    assert report["capabilities"]["phase569_shader_prefilter_input"] is True
    assert report["capabilities"]["programmable_draw_state_observed"] is True
    assert report["capabilities"]["exact_resource_identity_observed"] is False
    assert report["capabilities"]["phase590_sampler2d_snapshot_input"] is False
    assert report["capabilities"]["phase593_sampler_cube_snapshot_input"] is False
    assert report["capabilities"]["phase598_raw_input_candidate"] is False
    assert report["target_inventory"]["pixel_target_hash_count"] == 1
    assert report["target_inventory"]["matched_pixel_target_hash_count"] == 1
    assert report["target_inventory"]["target_pixel_shader_creation_count"] == 1


def test_raw_capture_audit_detects_duplicate_keys_before_json_collapses_them():
    line = (
        '{"event":"create_texture","frame":1,"event_index":1,'
        '"texture_ptr":"0x1","width":64,"height":32,'
        '"format":21,"pool":1,"width":64,"height":32,'
        '"format":21,"pool":1}'
    )

    report = audit_capture_lines([line])

    assert report["summary"]["duplicate_key_line_count"] == 1
    assert report["duplicate_key_counts"] == {
        "format": 1,
        "height": 1,
        "pool": 1,
        "width": 1,
    }
    assert "json:duplicate-object-keys-observed" in report["blocking_reasons"]


def test_raw_capture_audit_recognizes_exact_resource_and_snapshot_inputs():
    lines = [
        _line({
            "event": "create_vertex_shader",
            "frame": 1,
            "event_index": 1,
            "shader_ptr": "0x10",
            "bytes_hex": VS.hex(),
        }),
        _line({
            "event": "create_pixel_shader",
            "frame": 1,
            "event_index": 2,
            "shader_ptr": "0x20",
            "bytes_hex": PS.hex(),
        }),
        _line({
            "event": "create_vertex_declaration",
            "frame": 1,
            "event_index": 3,
            "declaration_ptr": "0x30",
        }),
        _line({
            "event": "set_vertex_declaration",
            "frame": 1,
            "event_index": 4,
            "declaration_ptr": "0x30",
            "resource_path": "tracks/silverstone/object.imb",
            "resource_sha256": "a" * 64,
        }),
        _line({
            "event": "set_stream_source",
            "frame": 1,
            "event_index": 5,
        }),
        _line({
            "event": "set_indices",
            "frame": 1,
            "event_index": 6,
        }),
        _line({
            "event": "set_vertex_shader",
            "frame": 1,
            "event_index": 7,
            "shader_ptr": "0x10",
        }),
        _line({
            "event": "set_pixel_shader",
            "frame": 1,
            "event_index": 8,
            "shader_ptr": "0x20",
        }),
        _line({
            "event": "set_vertex_shader_constant_f",
            "frame": 1,
            "event_index": 9,
        }),
        _line({
            "event": "create_texture",
            "frame": 1,
            "event_index": 10,
        }),
        _line({
            "event": "create_cube_texture",
            "frame": 1,
            "event_index": 11,
        }),
        _line({
            "event": "set_texture",
            "frame": 1,
            "event_index": 12,
            "resource_type_name": "texture2d",
            "snapshot_status": "captured",
            "snapshot_paths": ["s0.ppm"],
        }),
        _line({
            "event": "set_texture",
            "frame": 1,
            "event_index": 13,
            "resource_type_name": "cube_texture",
            "snapshot_status": "captured",
            "snapshot_paths": [
                "px.ppm", "nx.ppm", "py.ppm",
                "ny.ppm", "pz.ppm", "nz.ppm",
            ],
        }),
        _line({
            "event": "buffer_payload",
            "frame": 1,
            "event_index": 14,
        }),
        _line({
            "event": "draw_indexed_primitive",
            "frame": 1,
            "event_index": 15,
        }),
    ]

    report = audit_capture_lines(lines)

    assert report["capabilities"]["exact_resource_identity_observed"] is True
    assert report["capabilities"]["buffer_payload_input_observed"] is True
    assert report["capabilities"]["phase590_sampler2d_snapshot_input"] is True
    assert report["capabilities"]["phase593_sampler_cube_snapshot_input"] is True
    assert report["capabilities"]["phase598_raw_input_candidate"] is True
    assert report["capture_profile"] == "attribution-candidate"

def test_resolve_input_path_falls_back_to_repository_root(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    module_path = repo_root / "src" / "graphics" / "d3d9" / "module.py"
    evidence = repo_root / "evidence" / "targets.json"
    module_path.parent.mkdir(parents=True)
    evidence.parent.mkdir(parents=True)
    module_path.write_text("# fixture\n", encoding="utf-8")
    evidence.write_text("{}", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.setattr(audit, "__file__", str(module_path))

    resolved = audit.resolve_input_path("evidence/targets.json")

    assert resolved == evidence


def test_resolve_input_path_keeps_existing_cwd_relative_path(monkeypatch, tmp_path):
    local = tmp_path / "targets.json"
    local.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    resolved = audit.resolve_input_path("targets.json")

    assert resolved == local


def test_resolve_input_path_reports_cwd_and_repo_attempts(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    module_path = repo_root / "src" / "graphics" / "d3d9" / "module.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text("# fixture\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.setattr(audit, "__file__", str(module_path))

    try:
        audit.resolve_input_path("evidence/missing.json")
    except FileNotFoundError as error:
        message = str(error)
        assert "evidence/missing.json" in message
        assert str(repo_root / "evidence" / "missing.json") in message
    else:
        raise AssertionError("missing repository-relative input must fail")

