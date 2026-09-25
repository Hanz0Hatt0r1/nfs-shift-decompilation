from bmw_runtime_capture_preflight import preflight_bmw_runtime


def _runtime(report_status="observed", same_instance_ready=False):
    gate = {
        "status": "proven" if same_instance_ready else "not-proven",
        "ready": same_instance_ready,
        "blocking_reasons": [] if same_instance_ready else ["draw:same-frame-indexed-draw-not-observed"],
    }
    if same_instance_ready:
        gate["candidate_frames"] = [{"frame": 7, "draw_index": 1}]
    return {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "status": report_status,
        "integrity": {"status": "observed"},
        "same_instance_gate": gate,
        "frames": [],
    }


def _snapshot(resource_sha, start_index, primitive_count, draw_index=0, source="draw-snapshot"):
    return {
        "format": "SHIFT.D3D9DrawStateSnapshot/1",
        "frame": 7,
        "draw_index": draw_index,
        "source": source,
        "vertex_declaration": {
            "declaration_ptr": "0x1",
            "resource_sha256": resource_sha,
            "resource_path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
        },
        "draw": {
            "start_index": start_index,
            "primitive_count": primitive_count,
            "base_vertex_index": 0,
        },
        "vertex_shader": {"shader_ptr": "0x10"},
        "pixel_shader": {"shader_ptr": "0x20"},
        "stream_sources": [{"stream": 0}],
        "active_stream_sources": [{"stream": 0}],
        "index_binding": {"index_buffer_ptr": "0x30"},
        "constant_writes": [],
        "constant_state": {"vertex": {}, "pixel": {}},
        "texture_bindings": [],
        "active_texture_bindings": [],
        "shader_permutation_identity": {
            "identity_sha256": "shader-id",
        },
    }


def test_runtime_capture_preflight_finds_exact_bmw_paint_draw():
    runtime = _runtime(same_instance_ready=True)
    runtime["frames"] = [{
        "frame": 7,
        "draw_snapshots": [
            _snapshot("abc", 0, 50, draw_index=0),
            _snapshot("abc", 150, 2098, draw_index=1),
        ],
    }]
    report = preflight_bmw_runtime(runtime, expected_resource_sha="abc")
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["paint_draw_candidates"][0]["primitive_index"] == 1
    assert report["paint_draw_candidates"][0]["draw_index"] == 1


def test_runtime_capture_preflight_rejects_wrong_resource():
    runtime = _runtime(same_instance_ready=True)
    runtime["frames"] = [{
        "frame": 7,
        "draw_snapshots": [
            _snapshot("wrong", 150, 2098),
        ],
    }]
    report = preflight_bmw_runtime(runtime, expected_resource_sha="abc")
    assert report["ready"] is False
    assert report["paint_draw_candidates"] == []
    assert "runtime:target-paint-draw-not-observed" in report["blocking_reasons"]


def test_runtime_capture_preflight_requires_same_instance_gate():
    runtime = _runtime(same_instance_ready=False)
    runtime["frames"] = [{
        "frame": 7,
        "draw_snapshots": [
            _snapshot("abc", 150, 2098),
        ],
    }]
    report = preflight_bmw_runtime(runtime, expected_resource_sha="abc")
    assert report["ready"] is False
    assert "runtime:same-instance-not-proven" in report["blocking_reasons"]


def test_runtime_capture_preflight_prefers_draw_snapshots():
    runtime = _runtime(same_instance_ready=True)
    runtime["frames"] = [{
        "frame": 7,
        "draws": [{"start_index": 150, "primitive_count": 2098, "base_vertex_index": 0}],
        "draw_snapshots": [
            _snapshot("abc", 0, 50),
        ],
    }]
    report = preflight_bmw_runtime(runtime, expected_resource_sha="abc")
    assert report["paint_draw_candidates"] == []
    assert report["resource_draw_candidates"][0]["source"] == "draw-snapshot"


def test_runtime_capture_preflight_cli_writes_blocked_report(tmp_path):
    import json
    import subprocess
    import sys

    runtime_path = tmp_path / "runtime.json"
    output_path = tmp_path / "preflight.json"
    runtime_path.write_text(
        json.dumps(_runtime(same_instance_ready=False)),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "bmw_runtime_capture_preflight.py",
            str(runtime_path),
            str(output_path),
            "--resource-sha256",
            "abc",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["format"] == "SHIFT.BMWRuntimeCapturePreflight/1"
    assert report["ready"] is False
    assert "runtime:same-instance-not-proven" in report["blocking_reasons"]


def test_runtime_capture_preflight_reports_missing_runtime_components():
    runtime = _runtime(same_instance_ready=True)
    runtime["frames"] = [{
        "frame": 7,
        "draw_snapshots": [{
            "format": "SHIFT.D3D9DrawStateSnapshot/1",
            "frame": 7,
            "draw_index": 1,
            "draw": {"start_index": 150, "primitive_count": 2098, "base_vertex_index": 0},
            "vertex_declaration": {"declaration_ptr": "0x1", "resource_sha256": "abc"},
            "vertex_shader": {},
            "pixel_shader": {},
            "stream_sources": [],
            "active_stream_sources": [],
            "index_binding": {},
            "shader_permutation_identity": {"identity_sha256": "shader-id"},
        }],
    }]
    report = preflight_bmw_runtime(runtime, expected_resource_sha="abc")
    candidate = report["paint_draw_candidates"][0]
    assert candidate["state_complete"] is False
    assert candidate["missing_components"] == ["vertex_shader", "pixel_shader", "streams", "indices"]


def test_runtime_capture_preflight_rejects_paint_range_on_different_draw():
    runtime = _runtime(same_instance_ready=True)
    runtime["same_instance_gate"]["candidate_frames"] = [{
        "frame": 7,
        "draw_index": 0,
        "declaration_ptr": "0x1",
    }]
    runtime["frames"] = [{
        "frame": 7,
        "draw_snapshots": [
            _snapshot("abc", 0, 50, draw_index=0),
            _snapshot("abc", 150, 2098, draw_index=1),
        ],
    }]
    report = preflight_bmw_runtime(runtime, expected_resource_sha="abc")
    assert report["paint_draw_candidates"][0]["draw_index"] == 1
    assert report["proven_paint_draw_candidates"] == []
    assert report["ready"] is False
    assert "runtime:target-paint-draw-not-same-instance" in report["blocking_reasons"]


def test_runtime_capture_preflight_defaults_to_exact_retail_meb_sha():
    runtime = _runtime(same_instance_ready=True)
    runtime["same_instance_gate"]["candidate_frames"] = [{"frame": 7, "draw_index": 1}]
    runtime["frames"] = [{
        "frame": 7,
        "draw_snapshots": [
            _snapshot(
                "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c",
                150,
                2098,
                draw_index=1,
            ),
        ],
    }]
    report = preflight_bmw_runtime(runtime)
    assert report["target"]["resource_sha256"] == "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"
    assert report["target"]["resource_identity_mode"] == "exact-sha256"


def test_runtime_capture_preflight_reports_active_resource_state():
    runtime = _runtime(same_instance_ready=True)
    runtime["same_instance_gate"]["candidate_frames"] = [{"frame": 7, "draw_index": 1}]
    snapshot = _snapshot(
        "abc", 150, 2098, draw_index=1
    )
    snapshot.update({
        "vertex_shader": {"shader_ptr": "0x10"},
        "pixel_shader": {"shader_ptr": "0x20"},
        "stream_sources": [{"stream": 0}],
        "active_stream_sources": [{"stream": 0}],
        "index_binding": {"index_buffer_ptr": "0x30"},
        "constant_writes": [],
        "constant_state": {"vertex": {"4": [1.0, 0.0, 0.0, 1.0]}, "pixel": {}},
        "texture_bindings": [{"stage": 0, "texture_ptr": "0x40"}],
        "active_texture_bindings": [{"stage": 0, "texture_ptr": "0x40"}, {"stage": 3, "texture_ptr": "0x43"}],
    })
    runtime["frames"] = [{"frame": 7, "draw_snapshots": [snapshot]}]
    report = preflight_bmw_runtime(runtime, expected_resource_sha="abc")
    candidate = report["paint_draw_candidates"][0]
    assert candidate["state_complete"] is True
    assert candidate["snapshot_schema_status"] == "valid"
    assert candidate["active_texture_stages"] == [0, 3]
    assert candidate["constant_state_stages"] == ["vertex"]


def test_runtime_capture_preflight_reports_invalid_snapshot_schema():
    runtime = _runtime(same_instance_ready=True)
    runtime["frames"] = [{
        "frame": 7,
        "draw_snapshots": [{
            "format": "SHIFT.D3D9DrawStateSnapshot/999",
            "frame": 7,
            "draw_index": 1,
            "draw": {"start_index": 150, "primitive_count": 2098, "base_vertex_index": 0},
            "vertex_declaration": {"declaration_ptr": "0x1", "resource_sha256": "abc"},
        }],
    }]
    report = preflight_bmw_runtime(runtime, expected_resource_sha="abc")
    candidate = report["paint_draw_candidates"][0]
    assert candidate["snapshot_schema_status"] == "invalid"
    assert candidate["state_complete"] is False
    assert "draw-snapshot-schema" in candidate["missing_components"]
    assert "format:invalid" in candidate["snapshot_schema_blocking_reasons"]
