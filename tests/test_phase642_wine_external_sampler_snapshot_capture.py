from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "phase641_external_sampler_capture_plan.py"
    spec = importlib.util.spec_from_file_location(
        "phase641_external_sampler_capture_plan_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _requirement(
    *,
    binding_index: int,
    stage: int,
    sampler_type: str,
    reason: str = "snapshot-content-not-captured",
):
    if sampler_type == "sampler2D":
        resource_type = "texture2d"
        path_count = 1
        sampler = "shadowMap"
    else:
        resource_type = "cube_texture"
        path_count = 6
        sampler = "environmentMap"
    return {
        "binding_index": binding_index,
        "draw_order": binding_index,
        "register": stage,
        "sampler": sampler,
        "sampler_type": sampler_type,
        "reason": reason,
        "expected_d3d9_resource_type": resource_type,
        "required_snapshot_path_count": path_count,
        "requested_texture_stage": stage,
        "capture_frames": [120 + binding_index],
        "capture_draw_indices": [binding_index],
    }


def _handoff(requirements):
    rows = list(requirements)
    return {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "scene_set_ready": False,
        "boundary": {
            "capture_observation_required": bool(rows),
            "capture_observation_requirement_count": len(rows),
        },
        "existing_capture_completion": {
            "runtime_evidence_required": rows,
        },
    }


def test_phase642_plan_deduplicates_and_sorts_exact_texture_stages():
    mod = _module()
    report = mod.build_capture_plan(_handoff([
        _requirement(binding_index=17, stage=7, sampler_type="sampler2D"),
        _requirement(binding_index=18, stage=3, sampler_type="samplerCube"),
        _requirement(binding_index=19, stage=7, sampler_type="sampler2D"),
    ]))

    assert report["format"] == "SHIFT.Phase641ExternalSamplerCapturePlan/1"
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["blocking_reasons"] == []
    assert report["requirement_count"] == 3
    assert report["texture_stage_list"] == [3, 7]
    assert report["texture_stages"] == "3,7"
    assert report["boundary"]["generic_texture_recapture_requested"] is False
    assert report["boundary"]["sampler_register_inference_allowed"] is False


def test_phase642_plan_rejects_register_stage_mismatch():
    mod = _module()
    requirement = _requirement(
        binding_index=17,
        stage=7,
        sampler_type="sampler2D",
    )
    requirement["requested_texture_stage"] = 3
    report = mod.build_capture_plan(_handoff([requirement]))

    assert report["ready"] is False
    assert report["status"] == "blocked"
    assert any(
        reason.endswith("register-stage-mismatch")
        for reason in report["blocking_reasons"]
    )
    assert report["texture_stage_list"] == []


def test_phase642_plan_rejects_sampler_resource_type_invention():
    mod = _module()
    requirement = _requirement(
        binding_index=17,
        stage=7,
        sampler_type="sampler2D",
    )
    requirement["expected_d3d9_resource_type"] = "cube_texture"
    report = mod.build_capture_plan(_handoff([requirement]))

    assert report["ready"] is False
    assert any(
        reason.endswith("resource-type-mismatch")
        for reason in report["blocking_reasons"]
    )


def test_phase642_plan_reports_not_needed_without_phase641_frontier():
    mod = _module()
    report = mod.build_capture_plan(_handoff([]))

    assert report["ready"] is False
    assert report["status"] == "not-needed"
    assert report["blocking_reasons"] == []
    assert report["texture_stage_list"] == []
    assert report["texture_stages"] == ""


def test_phase642_print_stages_cli_is_machine_readable(tmp_path):
    root = Path(__file__).resolve().parents[1]
    handoff = tmp_path / "handoff.json"
    handoff.write_text(
        json.dumps(_handoff([
            _requirement(binding_index=17, stage=7, sampler_type="sampler2D"),
            _requirement(binding_index=18, stage=3, sampler_type="samplerCube"),
        ])),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "phase641_external_sampler_capture_plan.py"),
            str(handoff),
            "--print-stages",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "3,7"
    assert result.stderr == ""


def test_phase642_wine_wrapper_uses_existing_proxy_snapshot_controls():
    root = Path(__file__).resolve().parents[1]
    wrapper = root / "tools" / "run_phase641_snapshot_capture_wine.sh"
    text = wrapper.read_text(encoding="utf-8")

    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    assert "phase641_external_sampler_capture_plan.py" in text
    assert "run_shift_capture_wine.sh" in text
    assert "SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT=1" in text
    assert "SHIFT_D3D9_CAPTURE_TEXTURE_STAGES" in text
    assert "SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR" in text
    assert 'rm -rf "$texture_dir"' in text
    assert "forward=(--mode capture)" in text
    assert text.index("forward=(--mode capture)") < text.index('forward+=("$@")')
    assert "requires --mode capture" in text
    assert "exec bash \"$launcher\"" in text
