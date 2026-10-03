import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_production as runner


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _inputs(tmp_path: Path, *, include_object=True):
    values = {
        "base_audit": {"format": "SHIFT.D3D9RendererRequirementAudit/1", "requirements": [], "capture_blockers": []},
        "ambiguity_audit": {"format": "SHIFT.IMBDrawLocalAmbiguityAudit/1", "ambiguous_draws": []},
        "runtime_shader_targets": {"format": "SHIFT.IMBRuntimeShaderTargetSet/1", "binding_targets": []},
        "draw_local": {"format": "SHIFT.D3D9TargetDrawLocalEvidence/1", "draws": []},
        "capture_pipeline": {"format": "SHIFT.IMBRuntimeCapturePipeline/1", "pipeline_ready": True},
    }
    if include_object:
        values["object_candidate_join"] = {"format": "SHIFT.SGBRuntimeObjectCandidateJoin/1", "ready": True}
    paths = {name: _write(tmp_path / f"{name}.json", value) for name, value in values.items()}
    corpus = tmp_path / "corpus.zip"
    corpus.write_bytes(b"fixture-corpus")
    return paths, corpus


def _patch_pipeline(monkeypatch, *, repeated=1, repeated_remaining=0):
    monkeypatch.setattr(
        runner,
        "build_fxo_report",
        lambda *args, **kwargs: {
            "format": "SHIFT.IMBFXOPairProvenance/1",
            "ready": True,
            "summary": {"verified_pair_count": 1, "missing_required_pair_count": 0},
        },
    )
    monkeypatch.setattr(
        runner,
        "build_material_constant_report",
        lambda *args, **kwargs: {
            "format": "SHIFT.IMBMaterialConstantCandidateJoin/1",
            "summary": {"material_distinct_draw_count": 0, "single_candidate_draw_count": 0, "remaining_ambiguous_draw_count": 0},
        },
    )
    monkeypatch.setattr(
        runner,
        "build_material_texture_report",
        lambda *args, **kwargs: {
            "format": "SHIFT.IMBMaterialTextureCandidateJoin/1",
            "summary": {"input_unresolved_draw_count": 0, "single_candidate_draw_count": 0, "remaining_unresolved_draw_count": 0},
        },
    )
    monkeypatch.setattr(
        runner,
        "build_scene_reference_report",
        lambda *args, **kwargs: {
            "format": "SHIFT.IMBStaticSceneReferenceCandidateJoin/1",
            "summary": {"geometry_ambiguous_draw_count": repeated, "remaining_geometry_ambiguous_draw_count": repeated},
        },
    )
    monkeypatch.setattr(
        runner,
        "build_runtime_resource_draw_candidate_join",
        lambda *args, **kwargs: {
            "format": "SHIFT.IMBRuntimeResourceDrawCandidateJoin/1",
            "summary": {
                "input_geometry_draw_count": repeated,
                "exact_resource_draw_count": repeated,
                "exact_scene_resource_draw_count": 0 if repeated else 0,
                "repeated_scene_instance_draw_count": repeated,
                "remaining_scene_draw_ambiguity_count": repeated,
            },
        },
    )
    monkeypatch.setattr(
        runner,
        "build_repeated_scene_instance_transform_join",
        lambda *args, **kwargs: {
            "format": "SHIFT.IMBRepeatedSceneInstanceTransformJoin/1",
            "ready": repeated_remaining == 0,
            "summary": {
                "repeated_instance_input_draw_count": repeated,
                "resolved_repeated_instance_draw_count": repeated - repeated_remaining,
                "remaining_scene_draw_ambiguity_count": repeated_remaining,
            },
        },
    )

    def frontier(base, **kwargs):
        repeated_report = kwargs.get("repeated_instance_transforms")
        remaining = 0
        if repeated_report:
            remaining = repeated_report["summary"]["remaining_scene_draw_ambiguity_count"]
        return {
            "format": "SHIFT.D3D9RendererFrontierAudit/1",
            "status": "continue-offline",
            "summary": {"capture_required_now": False},
            "requirements": [{
                "requirement_id": "scene_resource_exact_draw_attribution",
                "status": "closed-offline-exact" if remaining == 0 else "ambiguous",
            }],
            "existing_data_requiring_tooling": [] if remaining == 0 else [{
                "requirement_id": "scene_resource_exact_draw_attribution",
                "status": "ambiguous",
                "next_step": "use existing spatial evidence",
            }],
            "genuinely_absent_capture_observations": [{
                "requirement_id": "vb_ib_payload_equality",
                "missing_observation": "buffer_payload",
            }],
            "capture_blockers": [],
            "conditional_minimal_capture": [],
        }

    monkeypatch.setattr(runner, "build_renderer_frontier_audit", frontier)


def _run(tmp_path, paths, corpus):
    return runner.run_production(
        output_dir=tmp_path / "out",
        corpus=[corpus],
        base_audit=paths["base_audit"],
        ambiguity_audit=paths["ambiguity_audit"],
        runtime_shader_targets=paths["runtime_shader_targets"],
        draw_local=paths["draw_local"],
        capture_pipeline=paths["capture_pipeline"],
        object_candidate_join=paths.get("object_candidate_join"),
    )


def test_full_pipeline_writes_provenance_and_closes_repeated_instance(monkeypatch, tmp_path):
    paths, corpus = _inputs(tmp_path)
    _patch_pipeline(monkeypatch, repeated=1, repeated_remaining=0)
    manifest = _run(tmp_path, paths, corpus)

    assert manifest["format"] == runner.FORMAT
    assert manifest["status"] == "completed"
    assert manifest["summary"]["completed_stage_count"] == 7
    assert manifest["summary"]["blocked_stage_count"] == 0
    assert manifest["summary"]["renderer_capture_required_now"] is False
    assert manifest["summary"]["frontier_requirement_status_counts"] == {"closed-offline-exact": 1}
    assert manifest["corpus"][0]["sha256"]
    assert all(row["sha256"] for row in manifest["stages"] if row["status"] == "completed")
    assert (tmp_path / "out" / "silverstone_renderer_production_run.json").is_file()
    assert manifest["renderer_frontier"]["genuinely_absent_capture_observations"][0]["missing_observation"] == "buffer_payload"
    assert manifest["renderer_frontier"]["capture_blockers"] == []


def test_repeated_instance_without_object_join_is_offline_input_blocker(monkeypatch, tmp_path):
    paths, corpus = _inputs(tmp_path, include_object=False)
    _patch_pipeline(monkeypatch, repeated=2, repeated_remaining=2)
    manifest = _run(tmp_path, paths, corpus)

    stage = next(row for row in manifest["stages"] if row["name"] == "phase625_repeated_instance")
    assert manifest["status"] == "blocked"
    assert stage["status"] == "blocked-missing-input"
    assert stage["blocking_reasons"] == ["object_candidate_join-required-for-repeated-instances"]
    assert any("object_candidate_join-required" in reason for reason in manifest["blocking_reasons"])
    assert manifest["summary"]["renderer_capture_required_now"] is False


def test_no_repeated_instances_skips_phase625_without_blocking(monkeypatch, tmp_path):
    paths, corpus = _inputs(tmp_path, include_object=False)
    _patch_pipeline(monkeypatch, repeated=0, repeated_remaining=0)
    manifest = _run(tmp_path, paths, corpus)

    stage = next(row for row in manifest["stages"] if row["name"] == "phase625_repeated_instance")
    assert manifest["status"] == "completed"
    assert stage["status"] == "not-needed"
    assert stage["blocking_reasons"] == []
    assert manifest["summary"]["not_needed_stage_count"] == 1


def test_wrong_input_format_fails_closed_and_preserves_manifest(monkeypatch, tmp_path):
    paths, corpus = _inputs(tmp_path)
    paths["ambiguity_audit"].write_text(json.dumps({"format": "wrong"}), encoding="utf-8")
    _patch_pipeline(monkeypatch, repeated=0)
    manifest = _run(tmp_path, paths, corpus)

    assert manifest["status"] == "blocked"
    assert any("input:ambiguity_audit:format-mismatch" in reason for reason in manifest["blocking_reasons"])
    fxo = next(row for row in manifest["stages"] if row["name"] == "phase619_fxo")
    scene = next(row for row in manifest["stages"] if row["name"] == "phase623_scene_geometry")
    assert fxo["status"] == "blocked-missing-input"
    assert scene["status"] == "blocked-missing-input"
    assert (tmp_path / "out" / "silverstone_renderer_production_run.json").is_file()


def test_stage_exception_is_reported_not_converted_to_candidate_evidence(monkeypatch, tmp_path):
    paths, corpus = _inputs(tmp_path)
    _patch_pipeline(monkeypatch, repeated=0)

    def fail(*args, **kwargs):
        raise RuntimeError("fixture failure")

    monkeypatch.setattr(runner, "build_fxo_report", fail)
    manifest = _run(tmp_path, paths, corpus)
    stage = next(row for row in manifest["stages"] if row["name"] == "phase619_fxo")
    assert manifest["status"] == "blocked"
    assert stage["status"] == "blocked-error"
    assert stage["blocking_reasons"] == ["RuntimeError:fixture failure"]
    assert manifest["boundary"]["missing_input_is_candidate_contradiction"] is False
    assert manifest["boundary"]["missing_capture_event_implies_recapture"] is False
