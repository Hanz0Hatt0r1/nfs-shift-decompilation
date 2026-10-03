from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import materialize_renderer_native_scene_handoff as handoff


def _write(path: Path, value: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _capture() -> dict:
    selected = {
        "vertex_byte_sha256": "1" * 64,
        "pixel_byte_sha256": "2" * 64,
        "score": 100,
    }
    result = {
        "binding_index": 7,
        "attributed": True,
        "selected_variant": selected,
        "candidate_variants": [selected],
        "runtime_observations": [],
    }
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
        "resource_results": [{
            "resource_path": "tracks/silverstone/test.imb",
            "resource_sha256": "a" * 64,
            "candidate_binding_indices": [7],
            "variant_match": {
                "format": "SHIFT.IMBRuntimeShaderVariantMatch/1",
                "status": "ready",
                "ready": True,
                "candidate_binding_results": [result],
                "blocking_reasons": [],
            },
        }],
    }


def test_phase572_rehydration_is_exact_phase630_transport_only():
    capture = _capture()
    reports, blockers = handoff._rehydrate_phase572_matches(capture)
    assert blockers == []
    assert len(reports) == 1
    report = reports[0]
    assert report["format"] == "SHIFT.IMBRuntimeShaderVariantMatch/1"
    assert report["target_resource"] == {
        "resource_path": "tracks/silverstone/test.imb",
        "resource_sha256": "a" * 64,
    }
    assert report["binding_results"] == capture["resource_results"][0]["variant_match"][
        "candidate_binding_results"
    ]
    assert report["binding_results"] is not capture["resource_results"][0]["variant_match"][
        "candidate_binding_results"
    ]
    assert report["boundary"]["rehydrated_from_phase630_compact_transport"] is True
    assert report["boundary"]["new_attribution_performed"] is False


def test_phase572_rehydration_rejects_result_outside_routed_binding_set():
    capture = _capture()
    capture["resource_results"][0]["variant_match"]["candidate_binding_results"][0][
        "binding_index"
    ] = 8
    reports, blockers = handoff._rehydrate_phase572_matches(capture)
    assert reports == []
    assert any("binding-index-not-in-routed-set" in item for item in blockers)


def _fixture(tmp_path: Path):
    scene_ir = tmp_path / "resource" / "scene-ir" / "scene_ir_materialization.json"
    _write(scene_ir.parent / "manifest.json", [])
    _write(scene_ir, {"format": "SHIFT.OfflineSceneIRMaterialization/1"})

    static_admission = _write(
        tmp_path / "resource" / "native-scene" / "sgb_render_binding_admission.json",
        {
            "format": "SHIFT.SGBRenderBindingAdmission/1",
            "ready": True,
            "bindings": [],
        },
    )
    native_scene = _write(
        tmp_path / "resource" / "native-scene" / "native_scene_build.json",
        {
            "format": "SHIFT.OfflineNativeSceneBuild/1",
            "static_resource_ready": True,
            "artifacts": {
                "render_binding_admission": {
                    "path": str(static_admission),
                    "sha256": _sha(static_admission),
                },
            },
        },
    )
    runtime_bootstrap = _write(
        tmp_path / "resource" / "runtime_bootstrap.json",
        {
            "format": "SHIFT.OfflineRuntimeBootstrap/1",
            "offline_build_ready": True,
            "artifacts": {
                "native_scene": str(native_scene),
                "scene_ir": str(scene_ir),
            },
        },
    )

    target = _write(
        tmp_path / "renderer" / "targets.json",
        {
            "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
            "capture_ready": True,
            "binding_targets": [],
        },
    )
    capture = _write(
        tmp_path / "renderer" / "raw" / "capture.json",
        _capture(),
    )
    raw_manifest = _write(
        tmp_path / "renderer" / "raw" / "raw.json",
        {
            "format": "SHIFT.SilverstoneRendererRawCaptureBootstrap/1",
            "ready": True,
            "outputs": {"capture_pipeline": str(capture)},
        },
    )
    self_manifest = _write(
        tmp_path / "renderer" / "self" / "self.json",
        {
            "format": "SHIFT.SilverstoneRendererSelfBootstrapProductionRun/1",
            "ready": True,
            "raw_bootstrap": {"manifest": str(raw_manifest)},
        },
    )
    source = _write(
        tmp_path / "renderer" / "source.json",
        {
            "format": "SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1",
            "ready": True,
            "shader_targets": {"path": str(target)},
            "self_bootstrap": {"manifest": str(self_manifest)},
        },
    )
    return runtime_bootstrap, source, static_admission


def test_handoff_builds_scene_set_only_through_existing_proof_stages(
    monkeypatch,
    tmp_path,
):
    runtime_bootstrap, source, _static_admission = _fixture(tmp_path)
    calls = {}

    def phase574(target, reports):
        calls["phase574"] = (target, reports)
        return {
            "format": "SHIFT.IMBRuntimeShaderAdmission/1",
            "status": "partial",
            "ready": False,
            "blocking_reasons": [],
            "summary": {
                "admitted_binding_count": 1,
                "rejected_binding_count": 1,
            },
            "admitted_bindings": [{
                "binding_index": 7,
                "shader_selection_admitted": True,
            }],
            "rejected_bindings": [{"binding_index": 9}],
        }

    def bridge(static, ir_root, runtime_shader_admission=None):
        calls["bridge"] = (static, Path(ir_root), runtime_shader_admission)
        return {
            "format": "SHIFT.SGBRenderBindingBridge/1",
            "ready": True,
            "blocking_reasons": [],
            "render_binding": {},
            "runtime_shader_join": {"ready": True},
        }

    def bundle(value):
        calls["bundle"] = value
        return {
            "format": "SHIFT.NativeSceneBundle/1",
            "ready": True,
            "blocking_reasons": [],
            "draw_count": 1,
            "coverage": {"complete_scene_coverage": False},
            "draws": [{}],
        }

    def vulkan(scene, bridge_value, ir_root, output_dir, **kwargs):
        calls["vulkan"] = (scene, bridge_value, Path(ir_root), Path(output_dir), kwargs)
        output = Path(output_dir)
        _write(
            output / "bundle_set_manifest.json",
            {"format": "SHIFT.NativeSceneVulkanSet/1", "ready": True},
        )
        (output / "bundle_set.paths").write_text("draw_0000\n", encoding="utf-8")
        return {
            "format": "SHIFT.NativeSceneVulkanSet/1",
            "ready": True,
            "blocking_reasons": [],
            "native_scene_submission": {
                "ready": False,
                "blocking_reasons": ["draw-0:scene-world-transform-not-executed"],
            },
        }

    def prepare(path, **kwargs):
        calls["prepare"] = (Path(path), kwargs)
        _write(
            Path(path) / "bundle_set_prepare.json",
            {"format": "SHIFT.NativeSceneVulkanSetPrepare/1", "ready": True},
        )
        return {
            "format": "SHIFT.NativeSceneVulkanSetPrepare/1",
            "ready": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(handoff, "build_imb_runtime_shader_admission", phase574)
    monkeypatch.setattr(handoff, "build_sgb_render_binding_bridge", bridge)
    monkeypatch.setattr(handoff, "build_native_scene_bundle", bundle)
    monkeypatch.setattr(handoff, "build_native_scene_vulkan_set", vulkan)
    monkeypatch.setattr(handoff, "prepare_native_scene_vulkan_set", prepare)

    report = handoff.materialize_renderer_native_scene_handoff(
        runtime_bootstrap=runtime_bootstrap,
        renderer_source_bootstrap=source,
        output_dir=tmp_path / "out",
    )

    assert report["status"] == "ready"
    assert report["scene_set_ready"] is True
    assert report["summary"]["phase574_status"] == "partial"
    assert report["summary"]["phase574_admitted_binding_count"] == 1
    assert report["diagnostics"]["phase574_rejected_bindings"] == [
        {"binding_index": 9}
    ]
    assert calls["phase574"][1][0]["binding_results"] == _capture()["resource_results"][0][
        "variant_match"
    ]["candidate_binding_results"]
    assert calls["bridge"][2]["status"] == "partial"
    assert report["boundary"]["unproven_draw_promoted"] is False
    assert report["boundary"]["runtime_shader_admission_is_render_admission"] is False
    assert report["boundary"]["phase630_resource_identity_is_phase572_target_identity"] is True
    assert Path(report["artifacts"]["scene_set_prepare"]).is_file()


def test_handoff_hash_mismatch_stops_before_runtime_admission(monkeypatch, tmp_path):
    runtime_bootstrap, source, static_admission = _fixture(tmp_path)
    static_admission.write_text('{"tampered":true}', encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("Phase 574 must not run after static artifact hash mismatch")

    monkeypatch.setattr(handoff, "build_imb_runtime_shader_admission", forbidden)
    report = handoff.materialize_renderer_native_scene_handoff(
        runtime_bootstrap=runtime_bootstrap,
        renderer_source_bootstrap=source,
        output_dir=tmp_path / "out",
    )
    assert report["status"] == "blocked"
    assert report["scene_set_ready"] is False
    assert any("sha256-mismatch" in item for item in report["blocking_reasons"])
    assert report["artifacts"]["runtime_shader_admission"] is None
