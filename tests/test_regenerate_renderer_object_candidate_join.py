import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import regenerate_renderer_object_candidate_join as regen


def _write(path: Path, value: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path):
    scene_dir = tmp_path / "bootstrap" / "native-scene"
    ir_root = tmp_path / "bootstrap" / "scene-ir"
    placement = _write(
        scene_dir / "sgb_scene_placement.json",
        {"format": "SHIFT.SGBScenePlacement/1", "ready": True},
    )
    handoffs = _write(
        scene_dir / "sgb_object_render_handoffs.json",
        {"format": "SHIFT.SGBObjectRenderHandoffSet/1", "ready": True},
    )
    native_scene = _write(
        scene_dir / "native_scene_build.json",
        {
            "format": "SHIFT.OfflineNativeSceneBuild/1",
            "static_resource_ready": True,
            "artifacts": {
                "scene_placement": {
                    "path": str(placement),
                    "sha256": _sha256(placement),
                },
                "object_render_handoffs": {
                    "path": str(handoffs),
                    "sha256": _sha256(handoffs),
                },
            },
        },
    )
    _write(ir_root / "manifest.json", [])
    scene_ir = _write(
        ir_root / "scene_ir_materialization.json",
        {"format": "SHIFT.OfflineSceneIRMaterialization/1", "ready": True},
    )
    runtime_bootstrap = _write(
        tmp_path / "bootstrap" / "runtime_bootstrap.json",
        {
            "format": "SHIFT.OfflineRuntimeBootstrap/1",
            "offline_build_ready": True,
            "artifacts": {
                "native_scene": str(native_scene),
                "scene_ir": str(scene_ir),
            },
        },
    )
    capture = _write(
        tmp_path / "capture.json",
        {"format": "SHIFT.IMBRuntimeCapturePipeline/1", "pipeline_ready": True},
    )
    return runtime_bootstrap, capture, placement, handoffs, ir_root


def _ready_join():
    return {
        "format": "SHIFT.SGBRuntimeObjectCandidateJoin/1",
        "status": "ambiguous",
        "ready": True,
        "identity_complete": False,
        "runtime_resource_count": 2,
        "matched_runtime_resource_count": 2,
        "blocking_reasons": [],
    }


def test_regeneration_resolves_hashed_scene_artifacts_and_reuses_phase595(
    monkeypatch,
    tmp_path,
):
    runtime_bootstrap, capture, placement, handoffs, ir_root = _fixture(tmp_path)
    calls = []

    def validate(scene_placement, object_handoffs, capture_pipeline, manifest_root):
        calls.append((
            Path(scene_placement),
            Path(object_handoffs),
            Path(capture_pipeline),
            Path(manifest_root),
        ))
        return _ready_join()

    monkeypatch.setattr(regen, "validate_files", validate)
    out = tmp_path / "out"
    report = regen.regenerate_object_candidate_join(
        runtime_bootstrap=runtime_bootstrap,
        capture_pipeline=capture,
        output_dir=out,
    )

    assert report["format"] == regen.FORMAT
    assert report["status"] == "ready"
    assert report["source_ready"] is True
    assert report["ready"] is True
    assert calls == [(placement, handoffs, capture, ir_root)]
    join_path = Path(report["outputs"]["object_candidate_join"])
    assert join_path.is_file()
    assert json.loads(join_path.read_text())["format"] == "SHIFT.SGBRuntimeObjectCandidateJoin/1"
    assert report["boundary"]["existing_phase595_builder_reused"] is True
    assert report["boundary"]["unique_candidate_is_render_admission"] is False


def test_native_scene_artifact_hash_mismatch_blocks_before_phase595(
    monkeypatch,
    tmp_path,
):
    runtime_bootstrap, capture, placement, _handoffs, _ir_root = _fixture(tmp_path)
    placement.write_text('{"tampered":true}', encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("Phase 595 must not run after artifact hash mismatch")

    monkeypatch.setattr(regen, "validate_files", forbidden)
    report = regen.regenerate_object_candidate_join(
        runtime_bootstrap=runtime_bootstrap,
        capture_pipeline=capture,
        output_dir=tmp_path / "out",
    )

    assert report["status"] == "blocked"
    assert report["source_ready"] is False
    assert report["ready"] is False
    assert any("scene_placement:sha256-mismatch" in reason for reason in report["blocking_reasons"])
    assert report["outputs"]["object_candidate_join"] is None


def test_valid_sources_preserve_optional_unresolved_join_without_promotion(
    monkeypatch,
    tmp_path,
):
    runtime_bootstrap, capture, *_ = _fixture(tmp_path)
    monkeypatch.setattr(
        regen,
        "validate_files",
        lambda *args, **kwargs: {
            "format": "SHIFT.SGBRuntimeObjectCandidateJoin/1",
            "status": "partial",
            "ready": False,
            "identity_complete": False,
            "runtime_resource_count": 2,
            "matched_runtime_resource_count": 1,
            "blocking_reasons": [
                "runtime-object-join:resource-1:logical-scene-resource-candidate-not-found"
            ],
        },
    )

    report = regen.regenerate_object_candidate_join(
        runtime_bootstrap=runtime_bootstrap,
        capture_pipeline=capture,
        output_dir=tmp_path / "out",
    )

    assert report["status"] == "optional-unresolved"
    assert report["source_ready"] is True
    assert report["ready"] is False
    assert Path(report["outputs"]["object_candidate_join"]).is_file()
    assert any(
        "logical-scene-resource-candidate-not-found" in reason
        for reason in report["blocking_reasons"]
    )
    assert report["boundary"]["unique_candidate_is_portable_resource_identity"] is False
