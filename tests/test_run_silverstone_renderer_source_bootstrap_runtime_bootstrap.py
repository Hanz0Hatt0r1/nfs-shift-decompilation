import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_silverstone_renderer_source_bootstrap_production as sourceboot


def test_source_bootstrap_threads_runtime_bootstrap_to_self_bootstrap(
    monkeypatch,
    tmp_path,
):
    target_path = tmp_path / "targets.json"
    target_path.write_text(
        '{"format":"SHIFT.IMBRuntimeShaderTargetSet/1",'
        '"capture_ready":true,"binding_targets":[{}]}',
        encoding="utf-8",
    )
    calls = []

    monkeypatch.setattr(
        sourceboot,
        "regenerate_full_shader_target_set",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererShaderTargetRegeneration/1",
            "status": "completed",
            "ready": True,
            "outputs": {"runtime_shader_targets": str(target_path)},
            "blocking_reasons": [],
        },
    )

    def self_call(**kwargs):
        calls.append(kwargs)
        return {
            "format": "SHIFT.SilverstoneRendererSelfBootstrapProductionRun/1",
            "status": "completed",
            "ready": True,
            "summary": {
                "production_completed": True,
                "object_candidate_join_regeneration_ready": True,
            },
            "object_candidate_join": {
                "mode": "regenerated-from-runtime-bootstrap",
                "regeneration_ready": True,
                "selected_path": str(tmp_path / "object.json"),
            },
            "production": {
                "status": "completed",
                "renderer_frontier": {
                    "status": "continue-offline",
                    "capture_blockers": [],
                },
            },
            "blocking_reasons": [],
        }

    monkeypatch.setattr(sourceboot, "run_self_bootstrap_production", self_call)
    runtime_bootstrap = tmp_path / "runtime_bootstrap.json"
    report = sourceboot.run_source_bootstrap_production(
        capture_jsonl=tmp_path / "capture.jsonl",
        pe_evidence=tmp_path / "pe.json",
        output_dir=tmp_path / "out",
        corpus=[tmp_path / "Silverstone_Era3_.zip"],
        runtime_bootstrap=runtime_bootstrap,
    )

    assert report["status"] == "completed"
    assert len(calls) == 1
    assert calls[0]["runtime_bootstrap"] == runtime_bootstrap
    assert report["summary"]["runtime_bootstrap_supplied"] is True
    assert report["summary"]["object_candidate_join_regeneration_ready"] is True
    resource_scene = report["resource_scene_evidence"]
    assert resource_scene["runtime_bootstrap"] == str(runtime_bootstrap)
    assert resource_scene["object_candidate_join"]["selected_path"] == str(
        tmp_path / "object.json"
    )
    assert (
        report["boundary"][
            "manual_object_candidate_join_handoff_required_when_runtime_bootstrap_supplied"
        ]
        is False
    )
    assert report["boundary"]["unique_scene_candidate_is_render_admission"] is False
