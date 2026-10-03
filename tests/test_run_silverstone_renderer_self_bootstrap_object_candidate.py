import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_self_bootstrap_production as selfboot


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _prepare(monkeypatch, tmp_path: Path, *, bundle_object=None):
    target = _write(
        tmp_path / "target.json",
        {
            "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
            "binding_targets": [],
        },
    )
    draw = _write(
        tmp_path / "generated" / "draw.json",
        {"format": "SHIFT.D3D9TargetDrawLocalEvidence/1"},
    )
    capture = _write(
        tmp_path / "generated" / "capture.json",
        {"format": "SHIFT.IMBRuntimeCapturePipeline/1", "pipeline_ready": True},
    )
    ambiguity = _write(
        tmp_path / "generated" / "ambiguity.json",
        {"format": "SHIFT.IMBDrawLocalAmbiguityAudit/1"},
    )
    base = _write(
        tmp_path / "generated" / "base.json",
        {"format": "SHIFT.D3D9RendererRequirementAudit/1"},
    )
    normalized = {}
    if bundle_object is not None:
        normalized["object_candidate_join"] = str(bundle_object)
    index = {
        "format": "SHIFT.SilverstoneRendererReportBundleIndex/1",
        "status": "ready",
        "summary": {},
        "normalized_outputs": normalized,
        "blocking_reasons": [],
    }
    calls = {"production": [], "crosscheck": []}

    monkeypatch.setattr(
        selfboot,
        "index_report_bundles",
        lambda *args, **kwargs: index,
    )
    monkeypatch.setattr(selfboot, "_report_rows", lambda value: {})
    monkeypatch.setattr(
        selfboot,
        "_choose_shader_targets",
        lambda *args, **kwargs: (str(target), {"mode": "explicit"}, []),
    )

    def crosscheck(key, regenerated, row):
        calls["crosscheck"].append((key, regenerated, row))
        return ({
            "key": key,
            "status": "bundle-copy-absent-regenerated-source-used",
        }, [])

    monkeypatch.setattr(selfboot, "_crosscheck_report", crosscheck)
    monkeypatch.setattr(
        selfboot,
        "run_raw_capture_bootstrap",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererRawCaptureBootstrap/1",
            "status": "completed",
            "ready": True,
            "summary": {},
            "outputs": {
                "draw_local": str(draw),
                "capture_pipeline": str(capture),
            },
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        selfboot,
        "run_ambiguity_regeneration",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererAmbiguityRegeneration/1",
            "status": "completed",
            "ready": True,
            "outputs": {"phase618_ambiguity": str(ambiguity)},
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        selfboot,
        "regenerate_renderer_base_audit",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererBaseAuditRegeneration/1",
            "status": "completed",
            "ready": True,
            "outputs": {"base_audit": str(base)},
            "blocking_reasons": [],
        },
    )

    def production(**kwargs):
        calls["production"].append(kwargs)
        return {
            "format": "SHIFT.SilverstoneRendererProductionRun/1",
            "status": "completed",
            "summary": {},
            "renderer_frontier": {
                "status": "continue-offline",
                "capture_blockers": [],
            },
            "blocking_reasons": [],
        }

    monkeypatch.setattr(selfboot, "run_production", production)
    return target, capture, calls


def test_runtime_bootstrap_regenerated_join_is_passed_to_production(
    monkeypatch,
    tmp_path,
):
    _target, _capture, calls = _prepare(monkeypatch, tmp_path)
    generated_join = _write(
        tmp_path / "generated" / "object.json",
        {"format": "SHIFT.SGBRuntimeObjectCandidateJoin/1", "ready": True},
    )
    helper_calls = []

    def regenerate(**kwargs):
        helper_calls.append(kwargs)
        return {
            "format": "SHIFT.SilverstoneRendererObjectCandidateRegeneration/1",
            "status": "ready",
            "source_ready": True,
            "ready": True,
            "outputs": {"object_candidate_join": str(generated_join)},
            "blocking_reasons": [],
        }

    monkeypatch.setattr(selfboot, "regenerate_object_candidate_join", regenerate)
    runtime_bootstrap = tmp_path / "runtime_bootstrap.json"
    manifest = selfboot.run_self_bootstrap_production(
        bundles=[tmp_path / "empty.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[],
        runtime_shader_targets=tmp_path / "target.json",
        runtime_bootstrap=runtime_bootstrap,
    )

    assert manifest["status"] == "completed"
    assert len(helper_calls) == 1
    assert helper_calls[0]["runtime_bootstrap"] == runtime_bootstrap
    assert calls["production"][0]["object_candidate_join"] == str(generated_join)
    assert manifest["object_candidate_join"]["mode"] == "regenerated-from-runtime-bootstrap"
    assert manifest["object_candidate_join"]["regeneration_ready"] is True
    assert manifest["object_candidate_join"]["bundle_fallback_used"] is False
    assert any(key == "object_candidate_join" for key, *_ in calls["crosscheck"])


def test_unready_regenerated_join_does_not_fallback_to_bundle(
    monkeypatch,
    tmp_path,
):
    bundle_join = _write(
        tmp_path / "bundle-object.json",
        {"format": "SHIFT.SGBRuntimeObjectCandidateJoin/1", "ready": True},
    )
    _target, _capture, calls = _prepare(
        monkeypatch,
        tmp_path,
        bundle_object=bundle_join,
    )
    unresolved = _write(
        tmp_path / "generated" / "object-unresolved.json",
        {"format": "SHIFT.SGBRuntimeObjectCandidateJoin/1", "ready": False},
    )
    monkeypatch.setattr(
        selfboot,
        "regenerate_object_candidate_join",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererObjectCandidateRegeneration/1",
            "status": "optional-unresolved",
            "source_ready": True,
            "ready": False,
            "outputs": {"object_candidate_join": str(unresolved)},
            "blocking_reasons": ["object-candidate-join:not-ready"],
        },
    )

    manifest = selfboot.run_self_bootstrap_production(
        bundles=[tmp_path / "bundle.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[],
        runtime_shader_targets=tmp_path / "target.json",
        runtime_bootstrap=tmp_path / "runtime_bootstrap.json",
    )

    assert manifest["status"] == "completed"
    assert calls["production"][0]["object_candidate_join"] is None
    object_input = manifest["object_candidate_join"]
    assert object_input["bundle_normalized_path"] == str(bundle_join)
    assert object_input["selected_path"] is None
    assert object_input["bundle_fallback_used"] is False
    assert object_input["optional_unresolved_blocking_reasons"]
    assert manifest["boundary"]["unready_regenerated_object_join_may_fallback_to_bundle"] is False
