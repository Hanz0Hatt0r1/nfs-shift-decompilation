from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _module():
    root = Path(__file__).resolve().parents[1]
    tools = root / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location(
        "materialize_renderer_native_scene_capture_handoff_evidence_tested",
        tools / "materialize_renderer_native_scene_capture_handoff.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture(*, resource_type: str, stage: int, snapshot_status=None, paths=None):
    binding = {
        "stage": stage,
        "texture_ptr": "0x7000",
        "resource_creation_status": "observed",
        "resource_creation": {
            "resource_type": resource_type,
            "texture_ptr": "0x7000",
        },
    }
    if snapshot_status is not None:
        binding["snapshot_status"] = snapshot_status
    if paths is not None:
        binding["snapshot_paths"] = list(paths)
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
        "resource_results": [{
            "attributed_texture_observations": [{
                "binding_index": 17,
                "frame": 120,
                "draw_index": 9,
                "status": "observed",
                "active_texture_bindings": [binding],
            }],
        }],
    }


def _adapter_row(*, sampler_type: str, register: int, field: str = "rows"):
    adapter = {
        "format": "SHIFT.NativeSceneExternalSamplerCaptureAdapter/1",
        "ready": False,
        "rows": [],
        "cube_rows": [],
    }
    adapter[field] = [{
        "binding_index": 17,
        "draw_order": 4,
        "register": register,
        "sampler": "shadowMap" if sampler_type == "sampler2D" else "environmentMap",
        "sampler_type": sampler_type,
        "candidate_observation_count": 0,
        "snapshot_ready": False,
        "blocking_reasons": ["capture-observation-count:0"],
    }]
    return adapter


def test_exact_sampler2d_stage_with_observed_creation_but_no_snapshot_is_actionable():
    mod = _module()
    rows = mod._snapshot_runtime_evidence_required(
        _capture(resource_type="texture2d", stage=7),
        _adapter_row(sampler_type="sampler2D", register=7),
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["binding_index"] == 17
    assert row["draw_order"] == 4
    assert row["register"] == 7
    assert row["sampler"] == "shadowMap"
    assert row["sampler_type"] == "sampler2D"
    assert row["reason"] == "snapshot-content-not-captured"
    assert row["expected_d3d9_resource_type"] == "texture2d"
    assert row["required_snapshot_path_count"] == 1
    assert row["stage_binding_observation_count"] == 1
    assert row["typed_resource_creation_observation_count"] == 1
    assert row["valid_snapshot_observation_count"] == 0
    assert row["snapshot_status_counts"] == {"missing": 1}
    assert row["snapshot_path_counts"] == [0]
    assert row["capture_frames"] == [120]
    assert row["capture_draw_indices"] == [9]
    assert row["requested_texture_stage"] == 7


def test_existing_exact_sampler_snapshot_does_not_request_capture_observation():
    mod = _module()
    rows = mod._snapshot_runtime_evidence_required(
        _capture(
            resource_type="texture2d",
            stage=7,
            snapshot_status="captured",
            paths=[r"C:\\capture\\textures\\s7.ppm"],
        ),
        _adapter_row(sampler_type="sampler2D", register=7),
    )

    assert rows == []


def test_sampler_type_mismatch_does_not_invent_recapture_requirement():
    mod = _module()
    rows = mod._snapshot_runtime_evidence_required(
        _capture(resource_type="cube_texture", stage=7),
        _adapter_row(sampler_type="sampler2D", register=7),
    )

    assert rows == []


def test_sampler_cube_requires_six_face_snapshot_content_only_after_typed_observation():
    mod = _module()
    rows = mod._snapshot_runtime_evidence_required(
        _capture(
            resource_type="cube_texture",
            stage=3,
            snapshot_status="captured",
            paths=["px.ppm", "nx.ppm"],
        ),
        _adapter_row(
            sampler_type="samplerCube",
            register=3,
            field="cube_rows",
        ),
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["register"] == 3
    assert row["reason"] == "snapshot-content-incomplete"
    assert row["expected_d3d9_resource_type"] == "cube_texture"
    assert row["required_snapshot_path_count"] == 6
    assert row["snapshot_status_counts"] == {"captured": 1}
    assert row["snapshot_path_counts"] == [2]
