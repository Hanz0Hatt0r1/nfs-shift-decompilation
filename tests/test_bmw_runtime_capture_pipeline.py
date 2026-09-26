import bmw_runtime_capture_pipeline as pipeline


def test_pipeline_keeps_partial_runtime_evidence_and_blockers(monkeypatch, tmp_path):
    primary = tmp_path / "BMW_M3_E36.bff"
    render = tmp_path / "RENDER.bff"
    trace = tmp_path / "capture.jsonl"
    primary.write_bytes(b"primary")
    render.write_bytes(b"render")
    trace.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        pipeline,
        "build_real_bmw_material_binding",
        lambda *args, **kwargs: {
            "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
            "ready": False,
            "blocking_reasons": ["shader-selection:ambiguous"],
            "material_binding": {},
            "provenance": {},
        },
    )
    monkeypatch.setattr(
        pipeline,
        "load_events",
        lambda path: [],
    )
    monkeypatch.setattr(
        pipeline,
        "build_runtime_binding_evidence",
        lambda *args, **kwargs: {
            "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
            "status": "partial",
            "blocking_reasons": [],
            "frames": [],
            "trace": {"event_count": 0, "frame_count": 0},
            "same_instance_gate": {
                "ready": False,
                "blocking_reasons": ["frame:same-meb-resource-not-observed"],
            },
        },
    )
    monkeypatch.setattr(
        pipeline,
        "select_runtime_shader",
        lambda *args, **kwargs: {
            "format": "SHIFT.BMWRuntimeShaderSelection/1",
            "ready": False,
            "status": "not-found",
            "blocking_reasons": ["runtime:exact-shader-and-resource-instance-not-found"],
        },
    )
    monkeypatch.setattr(
        pipeline,
        "build_runtime_render_contract",
        lambda *args, **kwargs: {
            "format": "SHIFT.BMWRuntimeRenderContract/1",
            "ready": False,
            "reference_render_ready": False,
            "blocking_reasons": ["shader-selection:not-ready"],
        },
    )

    report = pipeline.build_pipeline(
        primary,
        render,
        trace,
        cockpit_bff=None,
        usage_map=None,
    )

    assert report["format"] == "SHIFT.BMWRuntimeCapturePipeline/1"
    assert report["ready"] is False
    assert report["runtime_evidence"]["status"] == "partial"
    assert report["shader_selection"]["status"] == "not-found"
    assert "shader-selection:ambiguous" in report["blocking_reasons"]


def test_texture_snapshot_inventory_converts_real_ppm(tmp_path):
    ppm = tmp_path / "s3.ppm"
    ppm.write_bytes(b"P6\n1 1\n255\n" + bytes((9, 8, 7)))
    report = pipeline._texture_snapshot_inventory({
        "frames": [{
            "frame": 12,
            "texture_bindings": [{
                "stage": 3,
                "texture_ptr": "0x300",
                "resource_snapshot_paths": [str(ppm)],
            }],
        }]
    })
    assert report["capture_snapshot_count"] == 1
    assert report["converted_snapshot_count"] == 1
    snapshot = report["snapshots"][0]
    assert snapshot["stage"] == 3
    assert snapshot["reference_format"] == "SHIFT.ReferenceTexture/1"
    assert snapshot["source_path"] == str(ppm)
    assert "reference_resource" not in snapshot


def test_texture_snapshot_inventory_reads_native_snapshot_paths(tmp_path):
    ppm = tmp_path / "s1.ppm"
    ppm.write_bytes(b"P6\n1 1\n255\n" + bytes((1, 2, 3)))
    report = pipeline._texture_snapshot_inventory({
        "frames": [{
            "frame": 4,
            "texture_bindings": [{
                "stage": 1,
                "texture_ptr": "0x101",
                "snapshot_paths": [str(ppm)],
            }],
        }]
    })
    assert report["capture_snapshot_count"] == 1
    assert report["converted_snapshot_count"] == 1
    assert report["snapshots"][0]["stage"] == 1
