from pathlib import Path


def test_post_capture_pipeline_writes_blocked_stage_reports(monkeypatch, tmp_path):
    import bmw_post_capture_pipeline as pipeline

    primary = tmp_path / "BMW_M3_E36.bff"
    render = tmp_path / "RENDER.bff"
    capture = tmp_path / "capture.jsonl"
    primary.write_bytes(b"primary")
    render.write_bytes(b"render")
    capture.write_text("{}", encoding="utf-8")

    material = {
        "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
        "status": "ready",
    }
    mesh = {
        "format": "SHIFT.MEBEvidence",
        "property_descriptors": [],
        "vertices": [],
    }
    runtime = {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "status": "observed",
        "frames": [],
    }
    selection = {
        "format": "SHIFT.BMWRuntimeShaderSelection/1",
        "status": "not-found",
        "ready": False,
        "blocking_reasons": [
            "runtime:exact-shader-and-resource-instance-not-found"
        ],
    }

    monkeypatch.setattr(pipeline, "build_real_bmw_material_binding", lambda *a, **k: material)
    monkeypatch.setattr(pipeline, "_load_target_mesh", lambda *a, **k: (mesh, b"meb"))
    monkeypatch.setattr(pipeline, "load_events", lambda path: [])
    monkeypatch.setattr(pipeline, "build_runtime_binding_evidence", lambda *a, **k: runtime)
    monkeypatch.setattr(pipeline, "select_runtime_shader", lambda *a, **k: selection)

    result = pipeline.run_pipeline(primary, render, capture, tmp_path / "out")

    assert result["ready"] is False
    assert result["stages"]["shader_selection"] == "not-found"
    assert (tmp_path / "out" / "material_binding.json").exists()
    assert (tmp_path / "out" / "mesh.json").exists()
    assert (tmp_path / "out" / "runtime_binding.json").exists()
    assert (tmp_path / "out" / "runtime_shader_selection.json").exists()
    assert (tmp_path / "out" / "pipeline_result.json").exists()
