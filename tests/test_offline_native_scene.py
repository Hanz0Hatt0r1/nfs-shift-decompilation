from __future__ import annotations

from pathlib import Path

import offline_native_scene as scene


def _runtime(*, ready: bool = True):
    return {
        "format": "SHIFT.SGBRuntime/1",
        "ready": ready,
        "blockers": [] if ready else ["runtime-fixture-blocked"],
    }


def _ready(format_name: str, **values):
    return {
        "format": format_name,
        "ready": True,
        "blocking_reasons": [],
        **values,
    }


def _admission_bindings():
    return [
        {
            "binding_index": 0,
            "ready": True,
            "blocking_reasons": [],
            "scene_admission": {
                "admitted_to_generic_render_binding": True,
            },
            "object": {
                "resource_reference": "tracks/test/a.imb",
            },
        },
        {
            "binding_index": 1,
            "ready": True,
            "blocking_reasons": [],
            "scene_admission": {
                "admitted_to_generic_render_binding": True,
            },
            "object": {
                "resource_reference": "tracks/test/b.imx",
            },
        },
    ]


def _install_ready_chain(monkeypatch, calls):
    def placement_join(runtime):
        calls.append(("placement_join", runtime))
        return _ready("SHIFT.SGBPlacementJoin/1")

    def scene_placement(join):
        calls.append(("scene_placement", join))
        return _ready("SHIFT.SGBScenePlacement/1", placement_count=2)

    def object_handoffs(runtime, *, root_consensus=None):
        calls.append(("object_handoffs", runtime, root_consensus))
        return _ready("SHIFT.SGBObjectRenderHandoffSet/1", object_count=2)

    def admission(placements, handoffs):
        calls.append(("admission", placements, handoffs))
        return _ready(
            "SHIFT.SGBRenderBindingAdmission/1",
            admitted_binding_count=2,
            bindings=_admission_bindings(),
        )

    def exact_closure(ir_root, refs):
        calls.append(("exact_closure", Path(ir_root), list(refs)))
        return _ready(
            "SHIFT.OfflineExactIRResourceClosure/1",
            root_reference_count=len(refs),
            resolved_resource_count=4,
            edges=[],
            resources=[],
        )

    def bridge(admission_report, ir_root, *, runtime_shader_admission=None):
        calls.append(("bridge", admission_report, Path(ir_root), runtime_shader_admission))
        return _ready("SHIFT.SGBRenderBindingBridge/1", resolved_instance_count=2)

    monkeypatch.setattr(scene, "build_sgb_placement_join", placement_join)
    monkeypatch.setattr(scene, "build_sgb_scene_placement", scene_placement)
    monkeypatch.setattr(scene, "build_sgb_object_render_handoff_set", object_handoffs)
    monkeypatch.setattr(scene, "build_sgb_render_binding_admission", admission)
    monkeypatch.setattr(scene, "build_exact_ir_resource_closure", exact_closure)
    monkeypatch.setattr(scene, "build_sgb_render_binding_bridge", bridge)


def test_build_native_scene_collapses_static_contract_chain_without_claiming_draw(monkeypatch, tmp_path):
    calls = []
    _install_ready_chain(monkeypatch, calls)
    consensus = {"format": "SHIFT.SGBMultiMatrixRootConsensus/1", "ready": True}
    shader_admission = {"format": "SHIFT.IMBRuntimeShaderAdmission/1", "ready": True}

    report = scene.build_native_scene(
        _runtime(),
        tmp_path / "ir",
        root_consensus=consensus,
        runtime_shader_admission=shader_admission,
    )

    assert report["format"] == scene.FORMAT
    assert report["status"] == "static-resource-ready-runtime-draw-blocked"
    assert report["static_resource_ready"] is True
    assert report["native_scene_runtime_ready"] is False
    assert report["blocking_reasons"] == [scene.RUNTIME_DRAW_BLOCKER]
    assert report["summary"]["placement_count"] == 2
    assert report["summary"]["object_handoff_count"] == 2
    assert report["summary"]["admitted_binding_count"] == 2
    assert report["summary"]["admitted_resource_reference_count"] == 2
    assert report["summary"]["exact_ir_closure_ready"] is True
    assert report["summary"]["exact_ir_resolved_resource_count"] == 4
    assert report["summary"]["resolved_instance_count"] == 2
    assert report["boundary"]["static_render_binding_promoted_to_runtime_draw"] is False
    assert report["boundary"]["exact_ir_closure_required_before_legacy_renderer"] is True
    assert report["boundary"]["legacy_basename_resolution_is_admission_proof"] is False
    assert calls[2][2] is consensus
    assert calls[4][2] == ["tracks/test/a.imb", "tracks/test/b.imx"]
    assert calls[5][3] is shader_admission


def test_exact_ir_closure_blocks_legacy_bridge_on_ambiguous_identity(monkeypatch, tmp_path):
    calls = []
    _install_ready_chain(monkeypatch, calls)

    monkeypatch.setattr(
        scene,
        "build_exact_ir_resource_closure",
        lambda ir_root, refs: {
            "format": "SHIFT.OfflineExactIRResourceClosure/1",
            "ready": False,
            "status": "blocked",
            "blocking_reasons": [
                "exact-ir-ambiguous:<root>->tracks/test/a.imb"
            ],
            "resolved_resource_count": 0,
        },
    )

    def bridge_must_not_run(*args, **kwargs):
        raise AssertionError("legacy bridge must not run without exact IR closure")

    monkeypatch.setattr(scene, "build_sgb_render_binding_bridge", bridge_must_not_run)

    report = scene.build_native_scene(_runtime(), tmp_path / "ir")

    assert report["static_resource_ready"] is False
    assert report["native_scene_runtime_ready"] is False
    assert report["stages"]["render_binding_bridge"]["ready"] is False
    assert report["stages"]["render_binding_bridge"]["boundary"]["legacy_renderer_invoked"] is False
    assert (
        "exact_ir_closure:exact-ir-ambiguous:<root>->tracks/test/a.imb"
        in report["blocking_reasons"]
    )
    assert "render_binding_bridge:exact-ir-closure-not-ready" in report["blocking_reasons"]


def test_blocked_static_stage_closes_scene_resource_gate(monkeypatch, tmp_path):
    calls = []
    _install_ready_chain(monkeypatch, calls)
    monkeypatch.setattr(
        scene,
        "build_sgb_object_render_handoff_set",
        lambda runtime, *, root_consensus=None: {
            "format": "SHIFT.SGBObjectRenderHandoffSet/1",
            "ready": False,
            "blocking_reasons": ["object-render:numeric-world-matrix-not-ready"],
            "object_count": 1,
        },
    )

    report = scene.build_native_scene(_runtime(), tmp_path / "ir")

    assert report["static_resource_ready"] is False
    assert report["native_scene_runtime_ready"] is False
    assert report["status"] == "static-resource-blocked"
    assert (
        "object_render_handoffs:object-render:numeric-world-matrix-not-ready"
        in report["blocking_reasons"]
    )
    assert scene.RUNTIME_DRAW_BLOCKER in report["blocking_reasons"]


def test_runtime_sgb_blocker_is_preserved_even_if_downstream_fixture_is_ready(monkeypatch, tmp_path):
    calls = []
    _install_ready_chain(monkeypatch, calls)

    report = scene.build_native_scene(_runtime(ready=False), tmp_path / "ir")

    assert report["static_resource_ready"] is False
    assert "sgb_runtime:runtime-fixture-blocked" in report["blocking_reasons"]
    assert report["boundary"]["source_backed_scene_contracts_only"] is True


def test_exact_ir_preflight_error_is_fail_closed_and_skips_bridge(monkeypatch, tmp_path):
    calls = []
    _install_ready_chain(monkeypatch, calls)
    monkeypatch.setattr(
        scene,
        "build_exact_ir_resource_closure",
        lambda ir_root, refs: (_ for _ in ()).throw(ValueError("bad manifest")),
    )

    def bridge_must_not_run(*args, **kwargs):
        raise AssertionError("legacy bridge must not run after preflight error")

    monkeypatch.setattr(scene, "build_sgb_render_binding_bridge", bridge_must_not_run)

    report = scene.build_native_scene(_runtime(), tmp_path / "ir")

    assert report["static_resource_ready"] is False
    assert report["summary"]["exact_ir_closure_ready"] is False
    assert any(
        "exact-ir-preflight-error:ValueError:bad manifest" in reason
        for reason in report["blocking_reasons"]
    )


def test_file_builder_decodes_raw_sgb_and_writes_all_static_stage_artifacts(monkeypatch, tmp_path):
    raw = tmp_path / "scene.sgb"
    raw.write_bytes(b"fixture-sgb")
    ir = tmp_path / "ir"
    ir.mkdir()
    calls = []
    _install_ready_chain(monkeypatch, calls)
    monkeypatch.setattr(
        scene,
        "parse_sgb_runtime",
        lambda data, strict=False: _runtime(),
    )

    out = tmp_path / "out"
    report = scene.build_native_scene_files(raw, ir, out)

    assert report["static_resource_ready"] is True
    assert set(report["artifacts"]) == {
        "sgb_runtime",
        "placement_join",
        "scene_placement",
        "object_render_handoffs",
        "render_binding_admission",
        "exact_ir_closure",
        "render_binding_bridge",
    }
    assert (out / "native_scene_build.json").is_file()
    for artifact in report["artifacts"].values():
        assert Path(artifact["path"]).is_file()
        assert len(artifact["sha256"]) == 64
