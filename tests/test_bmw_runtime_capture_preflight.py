from bmw_runtime_capture_preflight import preflight_bmw_runtime


def _runtime(report_status="observed", same_instance_ready=False):
    return {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "status": report_status,
        "integrity": {"status": "observed"},
        "same_instance_gate": {
            "status": "proven" if same_instance_ready else "not-proven",
            "ready": same_instance_ready,
            "blocking_reasons": [] if same_instance_ready else ["draw:same-frame-indexed-draw-not-observed"],
        },
        "frames": [],
    }


def _snapshot(resource_sha, start_index, primitive_count, draw_index=0, source="draw-snapshot"):
    return {
        "format": "SHIFT.D3D9DrawStateSnapshot/1",
        "frame": 7,
        "draw_index": draw_index,
        "source": source,
        "vertex_declaration": {
            "resource_sha256": resource_sha,
            "resource_path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
        },
        "draw": {
            "start_index": start_index,
            "primitive_count": primitive_count,
            "base_vertex_index": 0,
        },
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
