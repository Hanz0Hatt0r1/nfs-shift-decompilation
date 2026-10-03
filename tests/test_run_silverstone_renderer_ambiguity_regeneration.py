import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_ambiguity_regeneration as regen


def _write(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value), encoding="utf-8")
    else:
        path.write_text(str(value), encoding="utf-8")
    return path


def _inputs(tmp_path: Path):
    capture = _write(tmp_path / "capture.jsonl", '{"event":"fixture"}\n')
    targets = _write(
        tmp_path / "targets.json",
        {
            "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
            "binding_targets": [],
        },
    )
    draw = _write(
        tmp_path / "draw.json",
        {
            "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
            "status": "observed",
            "draws": [],
        },
    )
    corpus = _write(tmp_path / "corpus.zip", "fixture")
    return capture, targets, draw, corpus


def _report(fmt: str, **extra):
    return {"format": fmt, "summary": {}, **extra}


def _install_success_builders(monkeypatch):
    calls = []

    def call(name, value):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return value
        return inner

    monkeypatch.setattr(
        regen,
        "catalog_target_draw_signatures",
        call("catalog", _report("SHIFT.D3D9TargetDrawSignatureCatalog/1")),
    )
    monkeypatch.setattr(
        regen,
        "audit_imb_corpus",
        call("corpus", _report("SHIFT.IMBCorpusAudit/1", rows=[])),
    )
    monkeypatch.setattr(
        regen,
        "build_runtime_pipeline_candidate_join",
        call("pipeline", _report("SHIFT.IMBRuntimePipelineCandidateJoin/1")),
    )
    monkeypatch.setattr(
        regen,
        "build_runtime_geometry_shape_candidate_join",
        call("geometry", _report("SHIFT.IMBRuntimeGeometryShapeCandidateJoin/1")),
    )
    monkeypatch.setattr(
        regen,
        "_build_material_support",
        call(
            "material-support",
            ({"a" * 64: []}, {}, {"fx_unique_source_count": 1}),
        ),
    )
    monkeypatch.setattr(
        regen,
        "build_runtime_material_descriptor_candidate_join",
        call(
            "material",
            _report("SHIFT.IMBRuntimeMaterialDescriptorCandidateJoin/1"),
        ),
    )
    monkeypatch.setattr(
        regen,
        "build_target_pointer_observations",
        call("pointer", _report("SHIFT.D3D9TargetPointerObservations/1")),
    )
    monkeypatch.setattr(
        regen,
        "build_runtime_geometry_pointer_candidate_join",
        call(
            "geometry-pointer",
            _report("SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1"),
        ),
    )
    monkeypatch.setattr(
        regen,
        "build_draw_local_static_candidate_join",
        call("static", _report("SHIFT.IMBDrawLocalStaticCandidateJoin/1")),
    )
    monkeypatch.setattr(
        regen,
        "build_draw_local_ambiguity_audit",
        call(
            "ambiguity",
            _report(
                "SHIFT.IMBDrawLocalAmbiguityAudit/1",
                ambiguous_draws=[],
            ),
        ),
    )
    return calls


def test_regenerates_complete_phase618_graph(monkeypatch, tmp_path):
    capture, targets, draw, corpus = _inputs(tmp_path)
    calls = _install_success_builders(monkeypatch)

    manifest = regen.run_ambiguity_regeneration(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        corpus=[corpus],
        output_dir=tmp_path / "out",
    )

    assert manifest["format"] == regen.FORMAT
    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert manifest["summary"]["completed_stage_count"] == 9
    assert manifest["summary"]["blocked_stage_count"] == 0
    assert manifest["summary"]["phase618_available"] is True
    assert manifest["blocking_reasons"] == []

    names = [name for name, _args, _kwargs in calls]
    assert names == [
        "catalog",
        "corpus",
        "pipeline",
        "pointer",
        "geometry",
        "material-support",
        "material",
        "geometry-pointer",
        "static",
        "ambiguity",
    ]

    expected_outputs = {
        "silverstone_target_draw_signature_catalog.json",
        "silverstone_imb_corpus_audit.json",
        "silverstone_runtime_pipeline_candidate_join.json",
        "silverstone_runtime_geometry_shape_candidate_join.json",
        "silverstone_runtime_material_descriptor_candidate_join.json",
        "silverstone_target_pointer_observations.json",
        "silverstone_runtime_geometry_pointer_candidate_join.json",
        "silverstone_draw_local_static_candidate_join.json",
        "silverstone_draw_local_ambiguity_audit.json",
        "silverstone_renderer_ambiguity_regeneration.json",
    }
    assert expected_outputs == {path.name for path in (tmp_path / "out").iterdir()}
    assert manifest["material_support"]["fx_unique_source_count"] == 1
    assert manifest["boundary"]["candidate_ranking_is_proof"] is False
    assert manifest["boundary"]["fx_conflicting_path_selects_winner"] is False
    assert manifest["boundary"]["new_capture_required"] is False


def test_catalog_failure_blocks_dependent_graph_without_destroying_corpus_audit(
    monkeypatch,
    tmp_path,
):
    capture, targets, draw, corpus = _inputs(tmp_path)
    calls = []

    def fail_catalog(*args, **kwargs):
        calls.append("catalog")
        raise ValueError("fixture catalog failure")

    monkeypatch.setattr(regen, "catalog_target_draw_signatures", fail_catalog)
    monkeypatch.setattr(
        regen,
        "audit_imb_corpus",
        lambda *args, **kwargs: _report("SHIFT.IMBCorpusAudit/1", rows=[]),
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("dependent stage must stay blocked")

    for name in (
        "build_runtime_pipeline_candidate_join",
        "build_runtime_geometry_shape_candidate_join",
        "_build_material_support",
        "build_runtime_material_descriptor_candidate_join",
        "build_target_pointer_observations",
        "build_runtime_geometry_pointer_candidate_join",
        "build_draw_local_static_candidate_join",
        "build_draw_local_ambiguity_audit",
    ):
        monkeypatch.setattr(regen, name, forbidden)

    manifest = regen.run_ambiguity_regeneration(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        corpus=[corpus],
        output_dir=tmp_path / "out",
    )

    assert calls == ["catalog"]
    assert manifest["status"] == "blocked"
    assert manifest["ready"] is False
    assert (tmp_path / "out" / "silverstone_imb_corpus_audit.json").is_file()
    assert not (tmp_path / "out" / "silverstone_draw_local_ambiguity_audit.json").exists()
    stages = {row["name"]: row for row in manifest["stages"]}
    assert stages["phase603_runtime_catalog"]["status"] == "blocked-error"
    assert "ValueError:fixture catalog failure" in stages["phase603_runtime_catalog"]["blocking_reasons"]
    assert stages["imb_corpus_audit"]["status"] == "completed"
    assert stages["phase606_pipeline_candidates"]["status"] == "blocked-missing-input"
    assert stages["phase613_pointer_observations"]["status"] == "blocked-missing-input"
    assert stages["phase618_ambiguity"]["status"] == "blocked-missing-input"


def test_missing_or_wrong_primary_inputs_fail_closed_before_builders(monkeypatch, tmp_path):
    capture, targets, draw, corpus = _inputs(tmp_path)
    targets.write_text(json.dumps({"format": "wrong"}), encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("builders must not run with invalid primary input")

    monkeypatch.setattr(regen, "catalog_target_draw_signatures", forbidden)
    monkeypatch.setattr(regen, "audit_imb_corpus", forbidden)

    manifest = regen.run_ambiguity_regeneration(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        corpus=[corpus],
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert any(
        "runtime_shader_targets:ValueError" in reason
        for reason in manifest["blocking_reasons"]
    )
    stages = {row["name"]: row for row in manifest["stages"]}
    assert stages["phase603_runtime_catalog"]["status"] == "blocked-missing-input"
    assert stages["imb_corpus_audit"]["status"] == "blocked-missing-input"


def test_equivalent_fx_duplicate_paths_are_collapsed_by_exact_bytes():
    payload = b"sampler2D Diffuse;"
    sources, summary = regen._merge_fx_sources(
        [
            (
                "Render/Car.fx",
                payload,
                {"archive": "render.bff", "path": "Render/Car.fx"},
            ),
            (
                "render\\car.fx",
                payload,
                {"archive": "copy.bff", "path": "render/car.fx"},
            ),
        ]
    )

    assert sources == {"render/car.fx": payload}
    assert summary["fx_occurrence_count"] == 2
    assert summary["fx_normalized_path_count"] == 1
    assert summary["fx_unique_source_count"] == 1
    assert summary["fx_duplicate_equivalent_path_count"] == 1
    assert summary["fx_conflicting_path_count"] == 0


def test_conflicting_fx_duplicate_paths_fail_closed_instead_of_selecting_by_order():
    with pytest.raises(ValueError, match="conflicting-fx-source-paths:render/car.fx"):
        regen._merge_fx_sources(
            [
                (
                    "Render/Car.fx",
                    b"first",
                    {"archive": "a.bff", "path": "Render/Car.fx"},
                ),
                (
                    "render/car.fx",
                    b"second",
                    {"archive": "b.bff", "path": "render/car.fx"},
                ),
            ]
        )


def test_draw_local_format_mismatch_is_not_treated_as_empty_evidence(monkeypatch, tmp_path):
    capture, targets, draw, corpus = _inputs(tmp_path)
    draw.write_text(json.dumps({"format": "wrong"}), encoding="utf-8")

    monkeypatch.setattr(
        regen,
        "catalog_target_draw_signatures",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("catalog must not run")
        ),
    )

    manifest = regen.run_ambiguity_regeneration(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        corpus=[corpus],
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert any("input:draw_local:ValueError" in reason for reason in manifest["blocking_reasons"])
    assert manifest["outputs"]["phase618_ambiguity"] is None
