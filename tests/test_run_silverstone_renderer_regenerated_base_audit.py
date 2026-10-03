import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_base_audit_regeneration as regen
import run_silverstone_renderer_hybrid_production as hybrid


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _targets():
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [],
        "families": [
            {"family": "fixture", "pixel_shader_sha256": ["1" * 64]}
        ],
    }


def _draw_local():
    return {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "summary": {"target_draw_count": 1},
        "draws": [
            {
                "draw_range": {
                    "primitive_type": 4,
                    "base_vertex_index": 0,
                    "min_vertex_index": 0,
                    "num_vertices": 3,
                    "start_index": 0,
                    "primitive_count": 1,
                },
                "streams": [
                    {
                        "stream": 0,
                        "vertex_buffer_creation_event_index": 10,
                    }
                ],
                "index_binding": {
                    "index_buffer_creation_event_index": 11,
                },
                "vertex_constants": {
                    "variables": [
                        {
                            "name": "World",
                            "registers": [
                                {
                                    "register": 0,
                                    "values": [1.0, 0.0, 0.0, 0.0],
                                    "last_write_event_index": 20,
                                }
                            ],
                        }
                    ],
                    "transform_signature_sha256": "2" * 64,
                },
            }
        ],
    }


def _ambiguity():
    return {
        "format": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
        "summary": {
            "ambiguity_class_counts": {
                "material-distinct-candidates": 1,
                "shader-provenance-distinct-candidates": 0,
                "metadata-equivalent-lod-siblings": 0,
                "metadata-equivalent-geometry-alternatives": 0,
            }
        },
        "ambiguous_draws": [],
    }


def _shader_use():
    return {
        "format": "SHIFT.D3D9ShaderUseEvidence/1",
        "summary": {
            "shader_creation_count": 2,
            "exact_capture_local_draw_count": 1,
        },
        "draws": [{"shader_pair_sha256": "3" * 64}],
    }


def _texture_sampler():
    def missing(event):
        return {
            "status": "not-observed-in-capture",
            "observed_count": 0,
            "minimal_missing_event": event,
        }

    return {
        "format": "SHIFT.D3D9TargetTextureSamplerEvidence/1",
        "summary": {"exact_capture_local_draw_count": 1},
        "capture_observations": {
            "explicit_sampler_state_history": missing("set_sampler_state"),
            "portable_resource_path_sha_identity": missing(
                "resource_path + resource_sha256"
            ),
            "captured_texture_snapshot": missing("captured texture snapshot"),
            "buffer_payload": missing("buffer_payload"),
        },
        "draws": [],
    }


def _base(tag=None):
    value = {
        "format": "SHIFT.D3D9RendererRequirementAudit/1",
        "status": "continue-offline",
        "summary": {
            "hard_requirement_count": 0,
            "capture_required_now": False,
        },
        "requirements": [],
        "capture_blockers": [],
    }
    if tag is not None:
        value["tag"] = tag
    return value


def _capture_pipeline():
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "status": "ready",
        "pipeline_ready": True,
        "attribution_complete": True,
        "blocking_reasons": [],
    }


def _row(key: str, values: list[dict], *, required: bool):
    identities = sorted({hybrid._canonical_sha(value) for value in values})
    return {
        "key": key,
        "status": (
            "missing"
            if not values
            else "exact-single-occurrence"
            if len(values) == 1
            else "content-equivalent-multiple-occurrences"
            if len(identities) == 1
            else "ambiguous-distinct-payloads"
        ),
        "required_for_production": required,
        "occurrence_count": len(values),
        "occurrences": [
            {
                "canonical_sha256": hybrid._canonical_sha(value),
                "entry": f"{key}-{index}.json",
            }
            for index, value in enumerate(values)
        ],
    }


def _index(tmp_path: Path, *, base_values=None):
    base_values = [] if base_values is None else base_values
    ambiguity = _ambiguity()
    ambiguity_path = _write(tmp_path / "indexed" / "ambiguity.json", ambiguity)
    rows = [
        _row("base_audit", base_values, required=True),
        _row("ambiguity_audit", [ambiguity], required=True),
        _row("draw_local", [], required=True),
        _row("capture_pipeline", [], required=True),
        _row("object_candidate_join", [], required=False),
        _row("runtime_shader_targets", [], required=False),
    ]
    blockers = []
    base_row = rows[0]
    if not base_values:
        blockers.append("report:base_audit:missing-from-bundles")
    elif base_row["status"] == "ambiguous-distinct-payloads":
        blockers.append(
            f"report:base_audit:ambiguous-distinct-canonical-payloads:{len(set(x['canonical_sha256'] for x in base_row['occurrences']))}"
        )
    blockers.extend(
        [
            "report:draw_local:missing-from-bundles",
            "report:capture_pipeline:missing-from-bundles",
        ]
    )
    normalized = {"ambiguity_audit": str(ambiguity_path)}
    if base_row["status"] in {
        "exact-single-occurrence",
        "content-equivalent-multiple-occurrences",
    }:
        base_path = _write(tmp_path / "indexed" / "base.json", base_values[0])
        normalized["base_audit"] = str(base_path)
    return {
        "format": "SHIFT.SilverstoneRendererReportBundleIndex/1",
        "status": "blocked" if blockers else "ready",
        "ready": not blockers,
        "summary": {},
        "reports": rows,
        "normalized_outputs": normalized,
        "blocking_reasons": blockers,
    }


def _raw_manifest(tmp_path: Path):
    draw_path = _write(tmp_path / "raw" / "draw.json", _draw_local())
    capture_path = _write(
        tmp_path / "raw" / "capture.json", _capture_pipeline()
    )
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


def _base_regen_manifest(tmp_path: Path, value: dict):
    path = _write(tmp_path / "base-regenerated" / "base.json", value)
    return {
        "format": "SHIFT.SilverstoneRendererBaseAuditRegeneration/1",
        "status": "completed",
        "ready": True,
        "summary": {"capture_required_now": False},
        "outputs": {
            "shader_use": str(tmp_path / "base-regenerated" / "shader.json"),
            "texture_sampler": str(
                tmp_path / "base-regenerated" / "texture.json"
            ),
            "base_audit": str(path),
        },
        "blocking_reasons": [],
    }


def _production():
    return {
        "format": "SHIFT.SilverstoneRendererProductionRun/1",
        "status": "completed",
        "summary": {},
        "blocking_reasons": [],
        "renderer_frontier": {
            "status": "continue-offline",
            "capture_blockers": [],
        },
    }


def test_base_audit_regeneration_keeps_capture_absences_conditional(monkeypatch, tmp_path):
    capture = tmp_path / "capture.jsonl"
    capture.write_text('{"event":"fixture"}\n', encoding="utf-8")
    targets = _write(tmp_path / "targets.json", _targets())
    draw = _write(tmp_path / "draw.json", _draw_local())
    ambiguity = _write(tmp_path / "ambiguity.json", _ambiguity())

    monkeypatch.setattr(
        regen,
        "build_shader_use_evidence",
        lambda *args, **kwargs: _shader_use(),
    )
    monkeypatch.setattr(
        regen,
        "build_target_texture_sampler_evidence",
        lambda *args, **kwargs: _texture_sampler(),
    )

    manifest = regen.regenerate_renderer_base_audit(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        ambiguity_audit=ambiguity,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "completed"
    assert manifest["summary"]["capture_required_now"] is False
    base = json.loads(
        Path(manifest["outputs"]["base_audit"]).read_text(encoding="utf-8")
    )
    assert base["summary"]["hard_requirement_count"] == 0
    assert base["summary"]["capture_required_now"] is False
    assert base["capture_blockers"] == []
    absent = {
        row["requirement_id"]
        for row in base["genuinely_absent_capture_observations"]
    }
    assert {
        "sampler_state_snapshots",
        "portable_texture_resource_identity",
        "runtime_texture_payload_snapshot",
        "vb_ib_payload_equality",
    } <= absent
    assert manifest["boundary"]["hard_capture_requirements_supplied"] == []
    assert manifest["boundary"]["missing_capture_event_implies_recapture"] is False


def _prepare_hybrid(monkeypatch, tmp_path: Path, index, generated_base):
    targets = _write(tmp_path / "chosen-targets.json", _targets())
    raw = _raw_manifest(tmp_path)
    calls = {"raw": [], "base": [], "production": []}
    monkeypatch.setattr(hybrid, "index_report_bundles", lambda *args, **kwargs: index)

    def raw_call(**kwargs):
        calls["raw"].append(kwargs)
        return raw

    def base_call(**kwargs):
        calls["base"].append(kwargs)
        return _base_regen_manifest(tmp_path, generated_base)

    def production_call(**kwargs):
        calls["production"].append(kwargs)
        return _production()

    monkeypatch.setattr(hybrid, "run_raw_capture_bootstrap", raw_call)
    monkeypatch.setattr(hybrid, "regenerate_renderer_base_audit", base_call)
    monkeypatch.setattr(hybrid, "run_production", production_call)
    return targets, raw, calls


def test_regenerated_base_allows_missing_bundle_copy(monkeypatch, tmp_path):
    generated = _base("generated")
    index = _index(tmp_path, base_values=[])
    targets, raw, calls = _prepare_hybrid(monkeypatch, tmp_path, index, generated)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets,
        regenerate_base_audit=True,
    )

    assert manifest["status"] == "completed"
    assert len(calls["raw"]) == 1
    assert len(calls["base"]) == 1
    assert len(calls["production"]) == 1
    assert calls["production"][0]["base_audit"] == manifest["base_audit"]["path"]
    assert calls["production"][0]["draw_local"] == raw["outputs"]["draw_local"]
    assert manifest["base_audit"]["mode"] == "regenerated"
    assert manifest["base_audit"]["crosscheck"]["status"] == "bundle-copy-absent-regenerated-source-used"
    assert "report:base_audit:missing-from-bundles" in manifest["bundle_index"]["tolerated_raw_or_optional_report_blockers"]
    assert manifest["boundary"]["bundle_base_audit_is_selection_authority"] is False


def test_regenerated_base_mismatch_blocks_production(monkeypatch, tmp_path):
    index = _index(tmp_path, base_values=[_base("bundle-old")])
    generated = _base("generated-new")
    targets, _raw, calls = _prepare_hybrid(monkeypatch, tmp_path, index, generated)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets,
        regenerate_base_audit=True,
    )

    assert manifest["status"] == "blocked"
    assert calls["production"] == []
    assert manifest["base_audit"]["crosscheck"]["status"] == "bundle-regenerated-canonical-mismatch"
    assert "crosscheck:base_audit:bundle-regenerated-canonical-mismatch" in manifest["blocking_reasons"]


def test_regenerated_base_exactly_disambiguates_multiple_bundle_variants(monkeypatch, tmp_path):
    generated = _base("generated")
    index = _index(
        tmp_path,
        base_values=[_base("stale"), generated],
    )
    targets, _raw, calls = _prepare_hybrid(monkeypatch, tmp_path, index, generated)

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets,
        regenerate_base_audit=True,
    )

    assert manifest["status"] == "completed"
    assert len(calls["production"]) == 1
    assert manifest["base_audit"]["crosscheck"]["status"] == "exact-canonical-match-among-bundle-variants"
    assert "report:base_audit:ambiguous-distinct-canonical-payloads:2" in manifest["bundle_index"]["tolerated_raw_or_optional_report_blockers"]


def test_default_hybrid_mode_still_requires_exact_bundle_base(monkeypatch, tmp_path):
    index = _index(tmp_path, base_values=[])
    targets, _raw, calls = _prepare_hybrid(monkeypatch, tmp_path, index, _base())

    manifest = hybrid.run_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "result",
        corpus=[],
        runtime_shader_targets=targets,
        regenerate_base_audit=False,
    )

    assert manifest["status"] == "blocked"
    assert calls["raw"] == []
    assert calls["base"] == []
    assert calls["production"] == []
    assert any(
        reason.startswith("bundle:report:base_audit:missing-from-bundles")
        for reason in manifest["blocking_reasons"]
    )
