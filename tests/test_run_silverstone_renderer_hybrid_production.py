import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_hybrid_production as hybrid


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _occ(value: dict, *, entry="report.json"):
    return {
        "bundle_ordinal": 0,
        "bundle_path": "out.zip",
        "bundle_sha256": "a" * 64,
        "entry": entry,
        "entry_size": 123,
        "raw_sha256": "b" * 64,
        "canonical_sha256": hybrid._canonical_sha(value),
    }


def _row(key: str, fmt: str, values: list[dict], *, required=False):
    identities = sorted({hybrid._canonical_sha(value) for value in values})
    return {
        "key": key,
        "format": fmt,
        "required_for_production": required,
        "status": (
            "missing"
            if not values
            else "exact-single-occurrence"
            if len(values) == 1
            else "content-equivalent-multiple-occurrences"
            if len(identities) == 1
            else "ambiguous-distinct-payloads"
        ),
        "occurrence_count": len(values),
        "distinct_canonical_payload_count": len(identities),
        "canonical_sha256": identities[0] if len(identities) == 1 else None,
        "output": None,
        "output_sha256": None,
        "occurrences": [
            _occ(value, entry=f"{key}-{index}.json")
            for index, value in enumerate(values)
        ],
    }


def _base():
    return {
        "format": "SHIFT.D3D9RendererRequirementAudit/1",
        "status": "continue-offline",
        "requirements": [],
        "capture_blockers": [],
    }


def _ambiguity():
    return {
        "format": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
        "ambiguous_draws": [],
        "summary": {},
    }


def _draw(tag="raw"):
    return {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "status": "observed",
        "summary": {"target_draw_count": 1},
        "draws": [{"tag": tag}],
    }


def _capture(tag="raw"):
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "status": "ready",
        "pipeline_ready": True,
        "attribution_complete": True,
        "summary": {"event_count": 1},
        "blocking_reasons": [],
        "resource_results": [{"tag": tag}],
    }


def _targets(tag="chosen"):
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "tag": tag,
        "binding_targets": [],
    }


def _index(tmp_path: Path, *, base_values=None, ambiguity_values=None, draw_values=None, capture_values=None, object_values=None, target_values=None):
    base_values = [_base()] if base_values is None else base_values
    ambiguity_values = [_ambiguity()] if ambiguity_values is None else ambiguity_values
    draw_values = [] if draw_values is None else draw_values
    capture_values = [] if capture_values is None else capture_values
    object_values = [] if object_values is None else object_values
    target_values = [] if target_values is None else target_values

    normalized = {}
    rows = []
    specs = [
        ("base_audit", "SHIFT.D3D9RendererRequirementAudit/1", base_values, True),
        ("ambiguity_audit", "SHIFT.IMBDrawLocalAmbiguityAudit/1", ambiguity_values, True),
        ("draw_local", "SHIFT.D3D9TargetDrawLocalEvidence/1", draw_values, True),
        ("capture_pipeline", "SHIFT.IMBRuntimeCapturePipeline/1", capture_values, True),
        ("object_candidate_join", "SHIFT.SGBRuntimeObjectCandidateJoin/1", object_values, False),
        ("runtime_shader_targets", "SHIFT.IMBRuntimeShaderTargetSet/1", target_values, False),
    ]
    blockers = []
    for key, fmt, values, required in specs:
        row = _row(key, fmt, values, required=required)
        rows.append(row)
        identities = sorted({hybrid._canonical_sha(value) for value in values})
        if len(identities) == 1:
            path = _write(tmp_path / "indexed" / f"{key}.json", values[0])
            normalized[key] = str(path)
            row["output"] = str(path)
        elif len(identities) > 1:
            blockers.append(
                f"report:{key}:ambiguous-distinct-canonical-payloads:{len(identities)}"
            )
        elif required:
            blockers.append(f"report:{key}:missing-from-bundles")

    return {
        "format": "SHIFT.SilverstoneRendererReportBundleIndex/1",
        "status": "blocked" if blockers else "ready",
        "ready": not blockers,
        "summary": {},
        "reports": rows,
        "normalized_outputs": normalized,
        "blocking_reasons": blockers,
    }


def _raw_manifest(tmp_path: Path, *, draw=None, capture=None, ready=True):
    draw = _draw() if draw is None else draw
    capture = _capture() if capture is None else capture
    draw_path = _write(tmp_path / "raw-generated" / "draw.json", draw)
    capture_path = _write(tmp_path / "raw-generated" / "capture.json", capture)
    return {
        "format": "SHIFT.SilverstoneRendererRawCaptureBootstrap/1",
        "status": "completed" if ready else "blocked",
        "ready": ready,
        "summary": {"draw_local_available": True, "capture_pipeline_available": True},
        "outputs": {
            "usage_map": str(tmp_path / "raw-generated" / "usage.json"),
            "draw_local": str(draw_path),
            "capture_pipeline": str(capture_path),
        },
        "blocking_reasons": [] if ready else ["fixture-raw-blocker"],
    }


def _production():
    return {
        "format": "SHIFT.SilverstoneRendererProductionRun/1",
        "status": "completed",
        "summary": {"completed_stage_count": 6},
        "blocking_reasons": [],
        "renderer_frontier": {
            "status": "continue-offline",
            "capture_blockers": [],
        },
    }


def _prepare(monkeypatch, tmp_path: Path, index, raw, production=None):
    targets_path = _write(tmp_path / "targets.json", _targets())
    calls = {"raw": [], "production": []}
    monkeypatch.setattr(hybrid, "index_report_bundles", lambda *args, **kwargs: index)

    def raw_call(**kwargs):
        calls["raw"].append(kwargs)
        return raw

    def prod_call(**kwargs):
        calls["production"].append(kwargs)
        return _production() if production is None else production

    monkeypatch.setattr(hybrid, "run_raw_capture_bootstrap", raw_call)
    monkeypatch.setattr(hybrid, "run_production", prod_call)
    return targets_path, calls


def test_missing_bundle_capture_reports_are_replaced_by_raw_regeneration(monkeypatch, tmp_path):
    index = _index(tmp_path)
    raw = _raw_manifest(tmp_path)
    targets_path, calls = _prepare(monkeypatch, tmp_path, index, raw)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[tmp_path / "corpus.zip"],
        runtime_shader_targets=targets_path,
    )

    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert manifest["summary"]["raw_bootstrap_ready"] is True
    assert len(calls["raw"]) == 1
    assert len(calls["production"]) == 1
    prod = calls["production"][0]
    assert prod["draw_local"] == raw["outputs"]["draw_local"]
    assert prod["capture_pipeline"] == raw["outputs"]["capture_pipeline"]
    assert prod["base_audit"] == index["normalized_outputs"]["base_audit"]
    assert prod["ambiguity_audit"] == index["normalized_outputs"]["ambiguity_audit"]
    assert prod["object_candidate_join"] is None
    checks = {row["key"]: row for row in manifest["capture_derived_report_crosschecks"]}
    assert checks["draw_local"]["status"] == "bundle-copy-absent-regenerated-source-used"
    assert checks["capture_pipeline"]["status"] == "bundle-copy-absent-regenerated-source-used"
    assert "report:draw_local:missing-from-bundles" in manifest["bundle_index"]["tolerated_raw_or_optional_report_blockers"]
    assert manifest["boundary"]["bundle_capture_reports_are_selection_authority"] is False


def test_exact_bundle_capture_reports_are_crosschecks_not_inputs(monkeypatch, tmp_path):
    draw = _draw()
    capture = _capture()
    index = _index(tmp_path, draw_values=[draw], capture_values=[capture])
    raw = _raw_manifest(tmp_path, draw=draw, capture=capture)
    targets_path, calls = _prepare(monkeypatch, tmp_path, index, raw)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets_path,
    )

    assert manifest["status"] == "completed"
    checks = {row["key"]: row for row in manifest["capture_derived_report_crosschecks"]}
    assert checks["draw_local"]["status"] == "exact-canonical-match"
    assert checks["capture_pipeline"]["status"] == "exact-canonical-match"
    assert calls["production"][0]["draw_local"] == raw["outputs"]["draw_local"]
    assert calls["production"][0]["draw_local"] != index["normalized_outputs"]["draw_local"]


def test_bundle_regenerated_mismatch_blocks_production(monkeypatch, tmp_path):
    index = _index(tmp_path, draw_values=[_draw("old")], capture_values=[_capture()])
    raw = _raw_manifest(tmp_path, draw=_draw("raw"), capture=_capture())
    targets_path, calls = _prepare(monkeypatch, tmp_path, index, raw)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets_path,
    )

    assert manifest["status"] == "blocked"
    assert calls["production"] == []
    assert "crosscheck:draw_local:bundle-regenerated-canonical-mismatch" in manifest["blocking_reasons"]
    checks = {row["key"]: row for row in manifest["capture_derived_report_crosschecks"]}
    assert checks["draw_local"]["status"] == "bundle-regenerated-canonical-mismatch"


def test_raw_exact_identity_can_disambiguate_multiple_derived_bundle_variants(monkeypatch, tmp_path):
    raw_draw = _draw("raw")
    index = _index(
        tmp_path,
        draw_values=[_draw("stale"), raw_draw],
        capture_values=[_capture()],
    )
    raw = _raw_manifest(tmp_path, draw=raw_draw, capture=_capture())
    targets_path, calls = _prepare(monkeypatch, tmp_path, index, raw)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets_path,
    )

    assert manifest["status"] == "completed"
    assert len(calls["production"]) == 1
    checks = {row["key"]: row for row in manifest["capture_derived_report_crosschecks"]}
    assert checks["draw_local"]["status"] == "exact-canonical-match-among-bundle-variants"
    assert checks["draw_local"]["bundle_distinct_canonical_payload_count"] == 2
    assert any(
        "report:draw_local:ambiguous-distinct-canonical-payloads:2" == reason
        for reason in manifest["bundle_index"]["tolerated_raw_or_optional_report_blockers"]
    )


def test_ambiguous_static_base_report_blocks_before_raw_bootstrap(monkeypatch, tmp_path):
    index = _index(tmp_path, base_values=[_base(), {**_base(), "variant": 2}])
    raw = _raw_manifest(tmp_path)
    targets_path, calls = _prepare(monkeypatch, tmp_path, index, raw)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets_path,
    )

    assert manifest["status"] == "blocked"
    assert calls["raw"] == []
    assert calls["production"] == []
    assert any(
        reason.startswith("bundle:report:base_audit:ambiguous-distinct-canonical-payloads")
        for reason in manifest["blocking_reasons"]
    )


def test_ambiguous_object_candidate_join_is_not_ranked_and_downstream_decides_need(monkeypatch, tmp_path):
    object_a = {"format": "SHIFT.SGBRuntimeObjectCandidateJoin/1", "variant": "a"}
    object_b = {"format": "SHIFT.SGBRuntimeObjectCandidateJoin/1", "variant": "b"}
    index = _index(tmp_path, object_values=[object_a, object_b])
    raw = _raw_manifest(tmp_path)
    blocked_production = _production()
    blocked_production["status"] = "blocked"
    blocked_production["blocking_reasons"] = [
        "phase625_repeated_instance:object_candidate_join-required-for-repeated-instances"
    ]
    targets_path, calls = _prepare(
        monkeypatch, tmp_path, index, raw, production=blocked_production
    )

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets_path,
    )

    assert len(calls["production"]) == 1
    assert calls["production"][0]["object_candidate_join"] is None
    assert manifest["object_candidate_join"]["ambiguity_selects_candidate"] is False
    assert manifest["status"] == "blocked"
    assert "production:phase625_repeated_instance:object_candidate_join-required-for-repeated-instances" in manifest["blocking_reasons"]


def test_chosen_shader_target_must_match_any_bundle_target_identity(monkeypatch, tmp_path):
    index = _index(tmp_path, target_values=[_targets("bundle-other")])
    raw = _raw_manifest(tmp_path)
    targets_path, calls = _prepare(monkeypatch, tmp_path, index, raw)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets_path,
    )

    assert manifest["status"] == "blocked"
    assert calls["raw"] == []
    assert calls["production"] == []
    assert manifest["runtime_shader_targets"]["crosscheck"] == "bundle-chosen-canonical-mismatch"
    assert "runtime_shader_targets:bundle-chosen-canonical-mismatch" in manifest["blocking_reasons"]
