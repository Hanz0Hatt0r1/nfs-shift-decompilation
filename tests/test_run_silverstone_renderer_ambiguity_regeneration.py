import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_ambiguity_regeneration as ambiguity


def _write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _targets():
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "families": [
            {"family": "fixture", "pixel_shader_sha256": ["1" * 64]}
        ],
        "binding_targets": [],
    }


def _draw_local():
    return {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "summary": {"target_draw_count": 2},
        "draws": [],
    }


def _runtime_catalog(*, draw_count=2):
    return {
        "format": "SHIFT.D3D9TargetDrawSignatureCatalog/1",
        "status": "observed" if draw_count else "not-observed",
        "summary": {"target_draw_count": draw_count},
        "pipeline_signatures": [],
        "resource_shape_signatures": [],
    }


def _pointer():
    return {
        "format": "SHIFT.D3D9TargetPointerObservations/1",
        "catalog_alignment": {"status": "exact"},
        "resource_shapes": [],
    }


def _corpus(*, ready=True):
    return {
        "format": "SHIFT.IMBCorpusAudit/1",
        "status": "ready" if ready else "partial",
        "ready": ready,
        "resource_count": 2,
        "ready_count": 2 if ready else 1,
        "blocked_count": 0 if ready else 1,
        "rows": [],
    }


def _pipeline():
    return {
        "format": "SHIFT.IMBRuntimePipelineCandidateJoin/1",
        "pipeline_candidates": [],
    }


def _geometry():
    return {
        "format": "SHIFT.IMBRuntimeGeometryShapeCandidateJoin/1",
        "geometry_shapes": [],
    }


def _material():
    return {
        "format": "SHIFT.IMBRuntimeMaterialDescriptorCandidateJoin/1",
        "resource_shapes": [],
    }


def _geometry_pointer():
    return {
        "format": "SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1",
        "resource_shapes": [],
    }


def _static_join():
    return {
        "format": "SHIFT.IMBDrawLocalStaticCandidateJoin/1",
        "summary": {"ambiguous_draw_count": 1},
        "draws": [],
    }


def _audit():
    return {
        "format": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
        "summary": {
            "ambiguous_draw_count": 1,
            "ambiguity_class_counts": {
                "material-distinct-candidates": 1,
            },
        },
        "ambiguous_draws": [],
    }


def _inputs(tmp_path: Path, *, render_zip=False):
    capture = tmp_path / "capture.jsonl"
    capture.write_text('{"event":"fixture"}\n', encoding="utf-8")
    targets = _write_json(tmp_path / "targets.json", _targets())
    draw = _write_json(tmp_path / "draw.json", _draw_local())
    source = tmp_path / "Silverstone_Era3_.zip"
    source.write_bytes(b"source-corpus-fixture")
    if render_zip:
        render = tmp_path / "SHIFT_tail.zip"
        with zipfile.ZipFile(render, "w") as archive:
            archive.writestr("Game/render.bff", b"render-bff-fixture")
    else:
        render = tmp_path / "render.bff"
        render.write_bytes(b"render-bff-fixture")
    return capture, targets, draw, source, render


def _patch_full_chain(monkeypatch, *, draw_count=2, corpus_ready=True):
    calls = {
        "catalog": 0,
        "pointer": 0,
        "corpus": 0,
        "pipeline": 0,
        "geometry": 0,
        "material": [],
        "geometry_pointer": 0,
        "static": 0,
        "ambiguity": 0,
    }

    def catalog(*args, **kwargs):
        calls["catalog"] += 1
        return _runtime_catalog(draw_count=draw_count)

    def pointer(*args, **kwargs):
        calls["pointer"] += 1
        assert kwargs.get("target_catalog", {}).get("format") == "SHIFT.D3D9TargetDrawSignatureCatalog/1"
        return _pointer()

    def corpus(*args, **kwargs):
        calls["corpus"] += 1
        return _corpus(ready=corpus_ready)

    def pipeline(*args, **kwargs):
        calls["pipeline"] += 1
        return _pipeline()

    def geometry(*args, **kwargs):
        calls["geometry"] += 1
        return _geometry()

    def material(runtime_path, geometry_path, source_path, render_path):
        calls["material"].append(
            {
                "runtime": Path(runtime_path),
                "geometry": Path(geometry_path),
                "source": Path(source_path),
                "render": Path(render_path),
                "render_bytes": Path(render_path).read_bytes(),
            }
        )
        return _material()

    def geometry_pointer(*args, **kwargs):
        calls["geometry_pointer"] += 1
        return _geometry_pointer()

    def static(*args, **kwargs):
        calls["static"] += 1
        return _static_join()

    def audit(*args, **kwargs):
        calls["ambiguity"] += 1
        return _audit()

    monkeypatch.setattr(ambiguity, "catalog_target_draw_signatures", catalog)
    monkeypatch.setattr(ambiguity, "build_target_pointer_observations", pointer)
    monkeypatch.setattr(ambiguity, "audit_imb_corpus", corpus)
    monkeypatch.setattr(ambiguity, "build_runtime_pipeline_candidate_join", pipeline)
    monkeypatch.setattr(ambiguity, "build_runtime_geometry_shape_candidate_join", geometry)
    monkeypatch.setattr(ambiguity, "validate_material_descriptor_files", material)
    monkeypatch.setattr(
        ambiguity,
        "build_runtime_geometry_pointer_candidate_join",
        geometry_pointer,
    )
    monkeypatch.setattr(
        ambiguity,
        "build_draw_local_static_candidate_join",
        static,
    )
    monkeypatch.setattr(ambiguity, "build_draw_local_ambiguity_audit", audit)
    return calls


def test_full_offline_chain_produces_phase618(monkeypatch, tmp_path):
    capture, targets, draw, source, render = _inputs(tmp_path)
    calls = _patch_full_chain(monkeypatch)

    manifest = ambiguity.regenerate_renderer_ambiguity(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        source_archive=source,
        render_archive=render,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert manifest["summary"]["completed_stage_count"] == 9
    assert manifest["summary"]["blocking_reason_count"] == 0
    assert manifest["outputs"]["ambiguity_audit"]
    final = json.loads(
        Path(manifest["outputs"]["ambiguity_audit"]).read_text(
            encoding="utf-8"
        )
    )
    assert final["format"] == "SHIFT.IMBDrawLocalAmbiguityAudit/1"
    assert calls["material"][0]["render_bytes"] == b"render-bff-fixture"
    assert manifest["boundary"]["original_game_execution_required"] is False
    assert manifest["boundary"]["new_capture_required"] is False
    assert manifest["boundary"]["candidate_ranking_is_proof"] is False


def test_render_zip_uses_exactly_one_render_bff(monkeypatch, tmp_path):
    capture, targets, draw, source, render = _inputs(
        tmp_path,
        render_zip=True,
    )
    calls = _patch_full_chain(monkeypatch)

    manifest = ambiguity.regenerate_renderer_ambiguity(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        source_archive=source,
        render_archive=render,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "completed"
    assert calls["material"][0]["render"].name == "render.bff"
    materialization = manifest["inputs"]["render_archive"]["materialization"]
    assert materialization["source_kind"] == "zip"
    assert materialization["selected_entry"] == "Game/render.bff"
    assert materialization["selection_policy"] == "exactly-one-basename-render.bff"


def test_partial_corpus_blocks_geometry_and_phase618(monkeypatch, tmp_path):
    capture, targets, draw, source, render = _inputs(tmp_path)
    calls = _patch_full_chain(monkeypatch, corpus_ready=False)

    manifest = ambiguity.regenerate_renderer_ambiguity(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        source_archive=source,
        render_archive=render,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert manifest["summary"]["corpus_ready"] is False
    assert "corpus_audit:not-all-selected-imbs-ready" in manifest["blocking_reasons"]
    assert calls["geometry"] == 0
    assert calls["material"] == []
    assert calls["geometry_pointer"] == 0
    assert calls["static"] == 0
    assert calls["ambiguity"] == 0
    assert manifest["outputs"]["runtime_catalog"]
    assert manifest["outputs"]["pointer_observations"]
    assert manifest["outputs"]["ambiguity_audit"] is None


def test_ambiguous_render_zip_blocks_material_stage(monkeypatch, tmp_path):
    capture, targets, draw, source, _render = _inputs(tmp_path)
    render = tmp_path / "SHIFT_tail.zip"
    with zipfile.ZipFile(render, "w") as archive:
        archive.writestr("a/render.bff", b"a")
        archive.writestr("b/RENDER.BFF", b"b")
    calls = _patch_full_chain(monkeypatch)

    manifest = ambiguity.regenerate_renderer_ambiguity(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        source_archive=source,
        render_archive=render,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert calls["material"] == []
    assert any(
        reason.startswith("material_descriptor_join:ValueError:render ZIP must contain exactly one")
        for reason in manifest["blocking_reasons"]
    )
    assert manifest["outputs"]["ambiguity_audit"] is None


def test_zero_target_draws_never_produces_ready_manifest(monkeypatch, tmp_path):
    capture, targets, draw, source, render = _inputs(tmp_path)
    calls = _patch_full_chain(monkeypatch, draw_count=0)

    manifest = ambiguity.regenerate_renderer_ambiguity(
        capture_jsonl=capture,
        runtime_shader_targets=targets,
        draw_local=draw,
        source_archive=source,
        render_archive=render,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert manifest["summary"]["target_draw_count"] == 0
    assert "runtime_catalog:no-target-draws-observed" in manifest["blocking_reasons"]
    assert calls["ambiguity"] == 1
    assert manifest["outputs"]["ambiguity_audit"]
    assert manifest["ready"] is False
