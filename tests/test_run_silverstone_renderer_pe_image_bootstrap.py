import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_pe_image_hybrid_production as pe_hybrid
import run_silverstone_renderer_raw_capture_bootstrap as raw_bootstrap


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _pe_report():
    return {
        "format": "SHIFT.PEImageEvidence/1",
        "image": {"bytes": 4096, "image_base": "0x00400000"},
        "decoded_tables": {
            "usage": [
                {"ordinal": ordinal, "value": ordinal + 20}
                for ordinal in range(9)
            ]
        },
        "conclusions": {"usage_table_status": "decoded"},
    }


def _targets(path: Path) -> Path:
    return _write_json(
        path,
        {
            "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
            "binding_targets": [],
        },
    )


def _draw_report():
    return {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "status": "observed",
        "summary": {"target_draw_count": 1},
        "draws": [],
    }


def _pipeline_report():
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "status": "ready",
        "pipeline_ready": True,
        "attribution_complete": True,
        "summary": {"event_count": 1},
        "blocking_reasons": [],
    }


def test_raw_bootstrap_can_generate_pe_evidence_from_static_image(monkeypatch, tmp_path):
    image = tmp_path / "SHIFT.exe"
    image.write_bytes(b"MZ-static-fixture")
    capture = tmp_path / "capture.jsonl"
    capture.write_text('{"event":"fixture"}\n', encoding="utf-8")
    targets = _targets(tmp_path / "targets.json")
    analysis_calls = []
    pipeline_maps = []

    def analyze(path):
        analysis_calls.append(Path(path))
        return _pe_report()

    monkeypatch.setattr(raw_bootstrap, "analyze_d3d9_pe_image_file", analyze)
    monkeypatch.setattr(
        raw_bootstrap,
        "load_events",
        lambda *args, **kwargs: [{"event": "fixture", "event_index": 1}],
    )
    monkeypatch.setattr(
        raw_bootstrap,
        "build_target_draw_local_evidence",
        lambda *args, **kwargs: _draw_report(),
    )

    def build_pipeline(target_set, events, *, usage_ordinal_map):
        pipeline_maps.append(dict(usage_ordinal_map))
        return _pipeline_report()

    monkeypatch.setattr(
        raw_bootstrap,
        "build_imb_runtime_capture_pipeline",
        build_pipeline,
    )

    out = tmp_path / "out"
    manifest = raw_bootstrap.run_raw_capture_bootstrap(
        capture_jsonl=capture,
        pe_image=image,
        runtime_shader_targets=targets,
        output_dir=out,
    )

    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert analysis_calls == [image]
    assert manifest["summary"]["pe_evidence_source"] == "static-pe-image"
    assert manifest["summary"]["pe_evidence_generated"] is True
    assert manifest["inputs"]["pe_image"]["sha256"]
    assert manifest["inputs"]["pe_evidence"]["generated_from_pe_image"] is True
    assert manifest["outputs"]["pe_evidence"] == str(out / "d3d9_pe_evidence.json")
    assert json.loads((out / "d3d9_pe_evidence.json").read_text(encoding="utf-8"))["format"] == "SHIFT.PEImageEvidence/1"
    assert pipeline_maps == [{ordinal: ordinal + 20 for ordinal in range(9)}]
    assert manifest["boundary"]["static_pe_image_analysis_executes_image"] is False
    assert manifest["boundary"]["usage_map_allows_inference"] is False


def test_pe_analysis_failure_preserves_independent_draw_local_evidence(monkeypatch, tmp_path):
    image = tmp_path / "SHIFT.exe"
    image.write_bytes(b"not-a-valid-pe-fixture")
    capture = tmp_path / "capture.jsonl"
    capture.write_text('{"event":"fixture"}\n', encoding="utf-8")
    targets = _targets(tmp_path / "targets.json")

    def fail_analysis(path):
        raise ValueError("fixture PE failure")

    monkeypatch.setattr(raw_bootstrap, "analyze_d3d9_pe_image_file", fail_analysis)
    monkeypatch.setattr(
        raw_bootstrap,
        "load_events",
        lambda *args, **kwargs: [{"event": "fixture"}],
    )
    monkeypatch.setattr(
        raw_bootstrap,
        "build_target_draw_local_evidence",
        lambda *args, **kwargs: _draw_report(),
    )
    monkeypatch.setattr(
        raw_bootstrap,
        "build_imb_runtime_capture_pipeline",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("runtime pipeline must stay blocked")
        ),
    )

    out = tmp_path / "out"
    manifest = raw_bootstrap.run_raw_capture_bootstrap(
        capture_jsonl=capture,
        pe_image=image,
        runtime_shader_targets=targets,
        output_dir=out,
    )

    assert manifest["status"] == "blocked"
    assert manifest["summary"]["draw_local_available"] is True
    assert manifest["summary"]["usage_map_ready"] is False
    assert manifest["summary"]["capture_pipeline_available"] is False
    assert any(
        reason == "input:pe_image:analysis-failed:ValueError:fixture PE failure"
        for reason in manifest["blocking_reasons"]
    )
    assert (out / "d3d9_target_draw_local_evidence.json").is_file()
    assert not (out / "d3d9_pe_evidence.json").exists()
    assert not (out / "silverstone_imb_runtime_capture_pipeline.json").exists()


def test_raw_bootstrap_requires_exactly_one_pe_source(tmp_path):
    with pytest.raises(ValueError, match="exactly one"):
        raw_bootstrap.run_raw_capture_bootstrap(
            capture_jsonl=tmp_path / "capture.jsonl",
            runtime_shader_targets=tmp_path / "targets.json",
            output_dir=tmp_path / "none",
        )

    with pytest.raises(ValueError, match="exactly one"):
        raw_bootstrap.run_raw_capture_bootstrap(
            capture_jsonl=tmp_path / "capture.jsonl",
            pe_evidence=tmp_path / "pe.json",
            pe_image=tmp_path / "SHIFT.exe",
            runtime_shader_targets=tmp_path / "targets.json",
            output_dir=tmp_path / "both",
        )


def test_pe_image_hybrid_wrapper_generates_evidence_then_delegates(monkeypatch, tmp_path):
    image = tmp_path / "SHIFT.exe"
    image.write_bytes(b"MZ-wrapper-fixture")
    hybrid_calls = []

    monkeypatch.setattr(
        pe_hybrid,
        "analyze_d3d9_pe_image_file",
        lambda path: _pe_report(),
    )

    def run_hybrid(**kwargs):
        hybrid_calls.append(kwargs)
        return {
            "format": "SHIFT.SilverstoneRendererHybridProductionRun/1",
            "status": "completed",
            "ready": True,
            "summary": {"production_completed": True},
            "production": {
                "renderer_frontier": {
                    "status": "continue-offline",
                    "capture_blockers": [],
                }
            },
            "blocking_reasons": [],
        }

    monkeypatch.setattr(pe_hybrid, "run_hybrid_production", run_hybrid)

    out = tmp_path / "result"
    manifest = pe_hybrid.run_pe_image_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=image,
        output_dir=out,
        corpus=[tmp_path / "Silverstone_Era3_.zip"],
    )

    assert manifest["status"] == "completed"
    assert len(hybrid_calls) == 1
    call = hybrid_calls[0]
    assert call["pe_evidence"] == out / "static" / "d3d9_pe_evidence.json"
    assert json.loads(Path(call["pe_evidence"]).read_text(encoding="utf-8"))["format"] == "SHIFT.PEImageEvidence/1"
    assert manifest["generated_pe_evidence"]["source_pe_image_sha256"] == manifest["inputs"]["pe_image"]["sha256"]
    assert manifest["hybrid"]["renderer_frontier"]["status"] == "continue-offline"
    assert manifest["boundary"]["pe_image_is_executed"] is False
    assert manifest["boundary"]["hybrid_proof_semantics_changed"] is False


def test_pe_image_hybrid_wrapper_fails_closed_before_hybrid_on_bad_pe(monkeypatch, tmp_path):
    image = tmp_path / "SHIFT.exe"
    image.write_bytes(b"bad-pe")
    hybrid_called = False

    monkeypatch.setattr(
        pe_hybrid,
        "analyze_d3d9_pe_image_file",
        lambda path: (_ for _ in ()).throw(ValueError("bad static PE")),
    )

    def forbidden_hybrid(**kwargs):
        nonlocal hybrid_called
        hybrid_called = True
        raise AssertionError("hybrid runner must not start")

    monkeypatch.setattr(pe_hybrid, "run_hybrid_production", forbidden_hybrid)

    manifest = pe_hybrid.run_pe_image_hybrid_production(
        bundles=[tmp_path / "out.zip"],
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_image=image,
        output_dir=tmp_path / "result",
        corpus=[],
    )

    assert manifest["status"] == "blocked"
    assert hybrid_called is False
    assert any(
        reason == "pe_image:analysis-failed:ValueError:bad static PE"
        for reason in manifest["blocking_reasons"]
    )
    assert manifest["summary"]["pe_evidence_generated"] is False
    assert manifest["summary"]["hybrid_started"] is False
