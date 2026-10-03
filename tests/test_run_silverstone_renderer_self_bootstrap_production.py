import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_self_bootstrap_production as selfboot


def _write(path: Path, value: dict | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, dict):
        path.write_text(json.dumps(value), encoding="utf-8")
    else:
        path.write_text(value, encoding="utf-8")
    return path


def _canonical_sha(value: dict) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _row(key: str, values: list[dict]):
    return {
        "key": key,
        "status": "missing" if not values else "exact-single-occurrence",
        "occurrence_count": len(values),
        "occurrences": [
            {
                "canonical_sha256": _canonical_sha(value),
                "bundle_path": "out.zip",
                "entry": f"{key}-{index}.json",
            }
            for index, value in enumerate(values)
        ],
    }


def _index(*, ambiguity_values=None, base_values=None, object_path=None):
    ambiguity_values = [] if ambiguity_values is None else ambiguity_values
    base_values = [] if base_values is None else base_values
    reports = [
        _row("base_audit", base_values),
        _row("ambiguity_audit", ambiguity_values),
        _row("draw_local", []),
        _row("capture_pipeline", []),
        _row("object_candidate_join", []),
        _row("runtime_shader_targets", []),
    ]
    normalized = {}
    if object_path is not None:
        normalized["object_candidate_join"] = str(object_path)
    blockers = []
    for key in ("base_audit", "ambiguity_audit", "draw_local", "capture_pipeline"):
        row = next(value for value in reports if value["key"] == key)
        if not row["occurrences"]:
            blockers.append(f"report:{key}:missing-from-bundles")
    return {
        "format": "SHIFT.SilverstoneRendererReportBundleIndex/1",
        "status": "blocked" if blockers else "ready",
        "ready": not blockers,
        "summary": {},
        "reports": reports,
        "normalized_outputs": normalized,
        "blocking_reasons": blockers,
    }


def _target_set():
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [],
    }


def _draw():
    return {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "status": "observed",
        "draws": [],
    }


def _capture():
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "status": "ready",
        "pipeline_ready": True,
        "blocking_reasons": [],
    }


def _ambiguity(tag="generated"):
    return {
        "format": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
        "tag": tag,
        "ambiguous_draws": [],
        "summary": {},
    }


def _base(tag="generated"):
    return {
        "format": "SHIFT.D3D9RendererRequirementAudit/1",
        "tag": tag,
        "status": "continue-offline",
        "requirements": [],
        "capture_blockers": [],
    }


def _production():
    return {
        "format": "SHIFT.SilverstoneRendererProductionRun/1",
        "status": "completed",
        "summary": {"completed_stage_count": 7},
        "blocking_reasons": [],
        "renderer_frontier": {
            "status": "continue-offline",
            "capture_blockers": [],
        },
    }


def _prepare_success(monkeypatch, tmp_path: Path, *, index=None):
    index = _index() if index is None else index
    targets = _write(tmp_path / "targets.json", _target_set())
    draw_path = _write(tmp_path / "generated" / "draw.json", _draw())
    capture_path = _write(tmp_path / "generated" / "capture.json", _capture())
    ambiguity_path = _write(
        tmp_path / "generated" / "ambiguity.json",
        _ambiguity(),
    )
    base_path = _write(tmp_path / "generated" / "base.json", _base())
    calls = {"raw": [], "ambiguity": [], "base": [], "production": []}

    monkeypatch.setattr(
        selfboot,
        "index_report_bundles",
        lambda *args, **kwargs: index,
    )

    def raw_call(**kwargs):
        calls["raw"].append(kwargs)
        return {
            "format": "SHIFT.SilverstoneRendererRawCaptureBootstrap/1",
            "status": "completed",
            "ready": True,
            "summary": {},
            "outputs": {
                "draw_local": str(draw_path),
                "capture_pipeline": str(capture_path),
            },
            "blocking_reasons": [],
        }

    def ambiguity_call(**kwargs):
        calls["ambiguity"].append(kwargs)
        return {
            "format": "SHIFT.SilverstoneRendererAmbiguityRegeneration/1",
            "status": "completed",
            "ready": True,
            "summary": {},
            "outputs": {"phase618_ambiguity": str(ambiguity_path)},
            "blocking_reasons": [],
        }

    def base_call(**kwargs):
        calls["base"].append(kwargs)
        return {
            "format": "SHIFT.SilverstoneRendererBaseAuditRegeneration/1",
            "status": "completed",
            "ready": True,
            "summary": {},
            "outputs": {"base_audit": str(base_path)},
            "blocking_reasons": [],
        }

    def production_call(**kwargs):
        calls["production"].append(kwargs)
        return _production()

    monkeypatch.setattr(selfboot, "run_raw_capture_bootstrap", raw_call)
    monkeypatch.setattr(selfboot, "run_ambiguity_regeneration", ambiguity_call)
    monkeypatch.setattr(selfboot, "regenerate_renderer_base_audit", base_call)
    monkeypatch.setattr(selfboot, "run_production", production_call)
    return targets, calls, draw_path, capture_path, ambiguity_path, base_path


def test_self_bootstrap_orders_raw_ambiguity_base_then_production(monkeypatch, tmp_path):
    targets, calls, draw_path, capture_path, ambiguity_path, base_path = _prepare_success(
        monkeypatch,
        tmp_path,
    )

    manifest = selfboot.run_self_bootstrap_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[tmp_path / "corpus.zip"],
        runtime_shader_targets=targets,
    )

    assert manifest["format"] == selfboot.FORMAT
    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert manifest["summary"]["raw_bootstrap_ready"] is True
    assert manifest["summary"]["ambiguity_regeneration_ready"] is True
    assert manifest["summary"]["base_audit_regeneration_ready"] is True
    assert manifest["summary"]["production_completed"] is True
    assert len(calls["raw"]) == 1
    assert len(calls["ambiguity"]) == 1
    assert len(calls["base"]) == 1
    assert len(calls["production"]) == 1

    assert calls["ambiguity"][0]["draw_local"] == str(draw_path)
    assert calls["base"][0]["ambiguity_audit"] == str(ambiguity_path)
    production = calls["production"][0]
    assert production["draw_local"] == str(draw_path)
    assert production["capture_pipeline"] == str(capture_path)
    assert production["ambiguity_audit"] == str(ambiguity_path)
    assert production["base_audit"] == str(base_path)

    checks = {row["key"]: row for row in manifest["regenerated_report_crosschecks"]}
    for key in ("draw_local", "capture_pipeline", "ambiguity_audit", "base_audit"):
        assert checks[key]["status"] == "bundle-copy-absent-regenerated-source-used"
    assert manifest["summary"]["crosscheck_count"] == 4
    assert manifest["boundary"]["bundle_draw_capture_ambiguity_base_are_selection_authority"] is False
    assert manifest["boundary"]["new_capture_required"] is False


def test_phase618_bundle_mismatch_blocks_before_base_and_production(monkeypatch, tmp_path):
    index = _index(ambiguity_values=[_ambiguity("stale")])
    targets, calls, _draw_path, _capture_path, _ambiguity_path, _base_path = _prepare_success(
        monkeypatch,
        tmp_path,
        index=index,
    )

    manifest = selfboot.run_self_bootstrap_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[tmp_path / "corpus.zip"],
        runtime_shader_targets=targets,
    )

    assert manifest["status"] == "blocked"
    assert len(calls["raw"]) == 1
    assert len(calls["ambiguity"]) == 1
    assert calls["base"] == []
    assert calls["production"] == []
    assert "crosscheck:ambiguity_audit:bundle-regenerated-canonical-mismatch" in manifest["blocking_reasons"]
    assert manifest["ambiguity_audit"]["crosscheck"]["status"] == "bundle-regenerated-canonical-mismatch"


def test_compact_phase568_target_evidence_is_rejected_before_raw(monkeypatch, tmp_path):
    compact = _write(
        tmp_path / "compact-targets.json",
        {
            "format": "SHIFT.IMBRuntimeShaderTargetSetEvidence/1",
            "families": [],
        },
    )
    monkeypatch.setattr(
        selfboot,
        "index_report_bundles",
        lambda *args, **kwargs: _index(),
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("raw bootstrap must not run with compact target evidence")

    monkeypatch.setattr(selfboot, "run_raw_capture_bootstrap", forbidden)

    manifest = selfboot.run_self_bootstrap_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[],
        runtime_shader_targets=compact,
    )

    assert manifest["status"] == "blocked"
    assert manifest["summary"]["full_runtime_shader_target_set_ready"] is False
    assert any("full-SHIFT.IMBRuntimeShaderTargetSet/1-required" in reason for reason in manifest["blocking_reasons"])
    assert manifest["boundary"]["compact_phase568_target_evidence_is_sufficient"] is False


def test_pe_image_is_forwarded_directly_to_phase630(monkeypatch, tmp_path):
    targets, calls, *_ = _prepare_success(monkeypatch, tmp_path)
    pe_image = tmp_path / "SHIFT.exe"

    manifest = selfboot.run_self_bootstrap_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=pe_image,
        output_dir=tmp_path / "out",
        corpus=[tmp_path / "corpus.zip"],
        runtime_shader_targets=targets,
    )

    assert manifest["status"] == "completed"
    raw = calls["raw"][0]
    assert raw["pe_image"] == pe_image
    assert raw["pe_evidence"] is None


def test_exact_optional_object_candidate_join_is_forwarded_only_as_exact_bundle_output(
    monkeypatch,
    tmp_path,
):
    object_path = _write(
        tmp_path / "object.json",
        {"format": "SHIFT.SGBRuntimeObjectCandidateJoin/1"},
    )
    index = _index(object_path=object_path)
    targets, calls, *_ = _prepare_success(monkeypatch, tmp_path, index=index)

    manifest = selfboot.run_self_bootstrap_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[tmp_path / "corpus.zip"],
        runtime_shader_targets=targets,
    )

    assert manifest["status"] == "completed"
    assert calls["production"][0]["object_candidate_join"] == str(object_path)
    assert manifest["object_candidate_join"]["passed_to_production"] is True
