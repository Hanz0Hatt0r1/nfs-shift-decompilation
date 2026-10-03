import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_bundle_production as bundle_runner


REQUIRED = {
    "base.json": {
        "format": "SHIFT.D3D9RendererRequirementAudit/1",
        "requirements": [],
        "capture_blockers": [],
    },
    "ambiguity.json": {
        "format": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
        "ambiguous_draws": [],
    },
    "draw_local.json": {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "draws": [],
    },
    "capture_pipeline.json": {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
    },
}


def _bundle(path: Path, reports: dict[str, dict]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in reports.items():
            archive.writestr(name, json.dumps(value))
    return path


def _completed_production(**kwargs):
    return {
        "format": "SHIFT.SilverstoneRendererProductionRun/1",
        "status": "completed",
        "summary": {
            "completed_stage_count": 6,
            "blocked_stage_count": 0,
            "renderer_capture_required_now": False,
        },
        "blocking_reasons": [],
        "renderer_frontier": {
            "status": "continue-offline",
            "existing_data_requiring_tooling": [],
            "genuinely_absent_capture_observations": [],
            "capture_blockers": [],
            "conditional_minimal_capture": [],
        },
    }


def test_ready_bundle_runs_production_with_normalized_reports_and_default_targets(
    monkeypatch, tmp_path
):
    bundle = _bundle(tmp_path / "out.zip", REQUIRED)
    corpus = tmp_path / "corpus.zip"
    corpus.write_bytes(b"corpus")
    calls = []

    monkeypatch.setattr(
        bundle_runner,
        "_default_shader_targets",
        lambda: "/repo/evidence/default_targets.json",
    )

    def production(**kwargs):
        calls.append(kwargs)
        return _completed_production(**kwargs)

    monkeypatch.setattr(bundle_runner, "run_production", production)
    manifest = bundle_runner.run_bundle_production(
        bundles=[bundle],
        output_dir=tmp_path / "result",
        corpus=[corpus],
    )

    assert manifest["format"] == bundle_runner.FORMAT
    assert manifest["status"] == "completed"
    assert manifest["summary"]["bundle_index_ready"] is True
    assert manifest["summary"]["production_started"] is True
    assert manifest["summary"]["production_completed"] is True
    assert len(calls) == 1
    call = calls[0]
    assert Path(call["base_audit"]).name == "d3d9_renderer_requirement_audit.json"
    assert Path(call["ambiguity_audit"]).name == "silverstone_d3d9_draw_local_ambiguity_audit.json"
    assert Path(call["draw_local"]).name == "d3d9_target_draw_local_evidence.json"
    assert Path(call["capture_pipeline"]).name == "silverstone_imb_runtime_capture_pipeline.json"
    assert call["object_candidate_join"] is None
    assert call["runtime_shader_targets"] == "/repo/evidence/default_targets.json"
    assert call["corpus"] == [corpus]
    assert (tmp_path / "result" / "silverstone_renderer_bundle_production_run.json").is_file()


def test_bundle_runtime_shader_targets_override_default_only_by_embedded_format(
    monkeypatch, tmp_path
):
    reports = dict(REQUIRED)
    reports["renamed_anything.json"] = {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [],
    }
    bundle = _bundle(tmp_path / "handoff.zip", reports)
    calls = []

    monkeypatch.setattr(
        bundle_runner,
        "_default_shader_targets",
        lambda: (_ for _ in ()).throw(AssertionError("default should not be used")),
    )

    def production(**kwargs):
        calls.append(kwargs)
        return _completed_production(**kwargs)

    monkeypatch.setattr(bundle_runner, "run_production", production)
    manifest = bundle_runner.run_bundle_production(
        bundles=[bundle],
        output_dir=tmp_path / "result",
        corpus=[tmp_path / "corpus.zip"],
    )

    assert manifest["status"] == "completed"
    assert len(calls) == 1
    assert Path(calls[0]["runtime_shader_targets"]).name == "silverstone_era3_runtime_shader_targets.json"


def test_distinct_payload_ambiguity_blocks_before_production(monkeypatch, tmp_path):
    first = _bundle(tmp_path / "a.zip", REQUIRED)
    changed = dict(REQUIRED)
    changed["base.json"] = {
        "format": "SHIFT.D3D9RendererRequirementAudit/1",
        "requirements": [{"requirement_id": "different"}],
        "capture_blockers": [],
    }
    second = _bundle(tmp_path / "b.zip", changed)

    def should_not_run(**kwargs):
        raise AssertionError("production must not start for ambiguous bundle input")

    monkeypatch.setattr(bundle_runner, "run_production", should_not_run)
    manifest = bundle_runner.run_bundle_production(
        bundles=[first, second],
        output_dir=tmp_path / "result",
        corpus=[],
    )

    assert manifest["status"] == "blocked"
    assert manifest["summary"]["bundle_index_ready"] is False
    assert manifest["summary"]["production_started"] is False
    assert manifest["paths"]["production_run"] is None
    assert any(
        "base_audit:ambiguous-distinct-canonical-payloads" in reason
        for reason in manifest["blocking_reasons"]
    )
    assert manifest["boundary"]["filename_used_for_selection"] is False
    assert manifest["boundary"]["bundle_index_blocker_starts_production"] is False


def test_production_blocker_is_propagated_after_ready_index(monkeypatch, tmp_path):
    bundle = _bundle(tmp_path / "out.zip", REQUIRED)

    def blocked_production(**kwargs):
        value = _completed_production(**kwargs)
        value["status"] = "blocked"
        value["blocking_reasons"] = [
            "phase625_repeated_instance:object_candidate_join-required-for-repeated-instances"
        ]
        return value

    monkeypatch.setattr(bundle_runner, "run_production", blocked_production)
    manifest = bundle_runner.run_bundle_production(
        bundles=[bundle],
        output_dir=tmp_path / "result",
        corpus=[],
    )

    assert manifest["summary"]["bundle_index_ready"] is True
    assert manifest["summary"]["production_started"] is True
    assert manifest["summary"]["production_completed"] is False
    assert manifest["status"] == "blocked"
    assert manifest["blocking_reasons"] == [
        "phase625_repeated_instance:object_candidate_join-required-for-repeated-instances"
    ]
    assert manifest["boundary"]["new_capture_required"] is False
