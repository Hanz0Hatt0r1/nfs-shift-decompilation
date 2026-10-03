import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_raw_capture_bootstrap as bootstrap


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _inputs(tmp_path: Path):
    capture = tmp_path / "capture.jsonl"
    capture.write_text('{"event":"fixture"}\n', encoding="utf-8")
    pe = _write_json(
        tmp_path / "pe.json",
        {
            "format": "SHIFT.PEImageEvidence/1",
            "decoded_tables": {
                "usage": [
                    {"ordinal": ordinal, "value": ordinal + 10}
                    for ordinal in range(9)
                ]
            },
        },
    )
    targets = _write_json(
        tmp_path / "targets.json",
        {
            "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
            "binding_targets": [],
        },
    )
    return capture, pe, targets


def _ready_usage_report():
    return {
        "format": "SHIFT.D3D9UsageMap/1",
        "status": "ready",
        "ready": True,
        "usage_map": {str(index): index + 10 for index in range(9)},
        "entry_count": 9,
        "blocking_reasons": [],
    }


def _draw_report():
    return {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "status": "observed",
        "summary": {"target_draw_count": 1},
        "draws": [],
    }


def _pipeline_report(*, ready=True):
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "status": "ready" if ready else "blocked",
        "pipeline_ready": ready,
        "attribution_complete": ready,
        "summary": {"event_count": 1},
        "blocking_reasons": [] if ready else ["fixture-blocker"],
    }


def test_ready_bootstrap_parses_capture_once_and_reuses_exact_events(monkeypatch, tmp_path):
    capture, pe, targets = _inputs(tmp_path)
    events = [{"event": "fixture", "event_index": 7}]
    load_calls = []
    draw_event_objects = []
    pipeline_event_objects = []
    pipeline_usage_maps = []

    def load(path, *, skip_unsupported):
        load_calls.append((Path(path), skip_unsupported))
        return events

    def build_usage(pe_value):
        assert pe_value["format"] == "SHIFT.PEImageEvidence/1"
        return _ready_usage_report()

    def build_draw(event_rows, *, target_inventory):
        draw_event_objects.append(event_rows)
        assert target_inventory["format"] == "SHIFT.IMBRuntimeShaderTargetSet/1"
        return _draw_report()

    def build_pipeline(target_set, event_rows, *, usage_ordinal_map):
        pipeline_event_objects.append(event_rows)
        pipeline_usage_maps.append(usage_ordinal_map)
        assert target_set["format"] == "SHIFT.IMBRuntimeShaderTargetSet/1"
        return _pipeline_report()

    monkeypatch.setattr(bootstrap, "load_events", load)
    monkeypatch.setattr(bootstrap, "build_d3d9_usage_map", build_usage)
    monkeypatch.setattr(bootstrap, "build_target_draw_local_evidence", build_draw)
    monkeypatch.setattr(bootstrap, "build_imb_runtime_capture_pipeline", build_pipeline)

    out = tmp_path / "out"
    manifest = bootstrap.run_raw_capture_bootstrap(
        capture_jsonl=capture,
        pe_evidence=pe,
        runtime_shader_targets=targets,
        output_dir=out,
    )

    assert manifest["format"] == bootstrap.FORMAT
    assert manifest["status"] == "completed"
    assert manifest["ready"] is True
    assert manifest["summary"]["completed_stage_count"] == 3
    assert manifest["summary"]["capture_event_count"] == 1
    assert load_calls == [(capture, True)]
    assert len(draw_event_objects) == 1
    assert len(pipeline_event_objects) == 1
    assert draw_event_objects[0] == events
    assert pipeline_event_objects[0] == events
    assert pipeline_usage_maps == [{index: index + 10 for index in range(9)}]
    assert (out / "d3d9_usage_map.json").is_file()
    assert (out / "d3d9_target_draw_local_evidence.json").is_file()
    assert (out / "silverstone_imb_runtime_capture_pipeline.json").is_file()
    assert (out / "silverstone_renderer_raw_capture_bootstrap.json").is_file()
    assert manifest["boundary"]["usage_map_allows_inference"] is False
    assert manifest["boundary"]["original_game_execution_required"] is False


def test_partial_usage_map_preserves_draw_local_and_blocks_runtime_pipeline(monkeypatch, tmp_path):
    capture, pe, targets = _inputs(tmp_path)
    pipeline_called = False

    monkeypatch.setattr(bootstrap, "load_events", lambda *args, **kwargs: [{"event": "fixture"}])
    monkeypatch.setattr(
        bootstrap,
        "build_d3d9_usage_map",
        lambda value: {
            "format": "SHIFT.D3D9UsageMap/1",
            "status": "partial",
            "ready": False,
            "usage_map": {"0": 10},
            "entry_count": 1,
            "blocking_reasons": ["usage-map:missing-ordinal:1"],
        },
    )
    monkeypatch.setattr(
        bootstrap,
        "build_target_draw_local_evidence",
        lambda *args, **kwargs: _draw_report(),
    )

    def forbidden_pipeline(*args, **kwargs):
        nonlocal pipeline_called
        pipeline_called = True
        raise AssertionError("runtime pipeline must not run without a ready usage map")

    monkeypatch.setattr(bootstrap, "build_imb_runtime_capture_pipeline", forbidden_pipeline)

    out = tmp_path / "out"
    manifest = bootstrap.run_raw_capture_bootstrap(
        capture_jsonl=capture,
        pe_evidence=pe,
        runtime_shader_targets=targets,
        output_dir=out,
    )

    assert manifest["status"] == "blocked"
    assert manifest["ready"] is False
    assert pipeline_called is False
    assert manifest["summary"]["usage_map_ready"] is False
    assert manifest["summary"]["draw_local_available"] is True
    assert manifest["summary"]["capture_pipeline_available"] is False
    assert (out / "d3d9_usage_map.json").is_file()
    assert (out / "d3d9_target_draw_local_evidence.json").is_file()
    assert not (out / "silverstone_imb_runtime_capture_pipeline.json").exists()
    assert "usage_map:usage-map:missing-ordinal:1" in manifest["blocking_reasons"]
    assert "capture_pipeline:usage-map-not-ready" in manifest["blocking_reasons"]
    stage = next(row for row in manifest["stages"] if row["name"] == "capture_pipeline")
    assert stage["status"] == "blocked-missing-input"
    assert manifest["boundary"]["draw_local_can_survive_usage_map_blocker"] is True
    assert manifest["boundary"]["missing_usage_map_is_declaration_contradiction"] is False


def test_wrong_pe_format_fails_closed_but_does_not_destroy_capture_local_evidence(monkeypatch, tmp_path):
    capture, pe, targets = _inputs(tmp_path)
    pe.write_text(json.dumps({"format": "wrong"}), encoding="utf-8")

    monkeypatch.setattr(bootstrap, "load_events", lambda *args, **kwargs: [{"event": "fixture"}])
    monkeypatch.setattr(
        bootstrap,
        "build_target_draw_local_evidence",
        lambda *args, **kwargs: _draw_report(),
    )
    monkeypatch.setattr(
        bootstrap,
        "build_imb_runtime_capture_pipeline",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("pipeline must stay blocked")
        ),
    )

    out = tmp_path / "out"
    manifest = bootstrap.run_raw_capture_bootstrap(
        capture_jsonl=capture,
        pe_evidence=pe,
        runtime_shader_targets=targets,
        output_dir=out,
    )

    assert manifest["status"] == "blocked"
    assert any("input:pe_evidence:format-mismatch" in reason for reason in manifest["blocking_reasons"])
    usage = next(row for row in manifest["stages"] if row["name"] == "usage_map")
    draw = next(row for row in manifest["stages"] if row["name"] == "draw_local")
    pipeline = next(row for row in manifest["stages"] if row["name"] == "capture_pipeline")
    assert usage["status"] == "blocked-missing-input"
    assert draw["status"] == "completed"
    assert pipeline["status"] == "blocked-missing-input"
    assert (out / "d3d9_target_draw_local_evidence.json").is_file()


def test_wrong_target_format_prevents_capture_parse_and_runtime_outputs(monkeypatch, tmp_path):
    capture, pe, targets = _inputs(tmp_path)
    targets.write_text(json.dumps({"format": "wrong"}), encoding="utf-8")
    load_called = False

    def forbidden_load(*args, **kwargs):
        nonlocal load_called
        load_called = True
        raise AssertionError("capture must not be parsed without a valid target set")

    monkeypatch.setattr(bootstrap, "load_events", forbidden_load)
    monkeypatch.setattr(bootstrap, "build_d3d9_usage_map", lambda value: _ready_usage_report())

    out = tmp_path / "out"
    manifest = bootstrap.run_raw_capture_bootstrap(
        capture_jsonl=capture,
        pe_evidence=pe,
        runtime_shader_targets=targets,
        output_dir=out,
    )

    assert load_called is False
    assert manifest["status"] == "blocked"
    assert manifest["summary"]["usage_map_ready"] is True
    assert manifest["summary"]["draw_local_available"] is False
    assert manifest["summary"]["capture_pipeline_available"] is False
    assert any(
        "input:runtime_shader_targets:format-mismatch" in reason
        for reason in manifest["blocking_reasons"]
    )
    assert (out / "d3d9_usage_map.json").is_file()


def test_capture_read_failure_is_recorded_and_usage_report_survives(monkeypatch, tmp_path):
    capture, pe, targets = _inputs(tmp_path)
    monkeypatch.setattr(bootstrap, "build_d3d9_usage_map", lambda value: _ready_usage_report())

    def fail_load(*args, **kwargs):
        raise ValueError("fixture capture failure")

    monkeypatch.setattr(bootstrap, "load_events", fail_load)

    out = tmp_path / "out"
    manifest = bootstrap.run_raw_capture_bootstrap(
        capture_jsonl=capture,
        pe_evidence=pe,
        runtime_shader_targets=targets,
        output_dir=out,
    )

    assert manifest["status"] == "blocked"
    assert any(
        "capture-read-failed:ValueError:fixture capture failure" == reason
        for reason in manifest["blocking_reasons"]
    )
    assert (out / "d3d9_usage_map.json").is_file()
    assert not (out / "d3d9_target_draw_local_evidence.json").exists()
    assert not (out / "silverstone_imb_runtime_capture_pipeline.json").exists()
