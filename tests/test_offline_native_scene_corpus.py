from __future__ import annotations

import json
from pathlib import Path

import offline_native_scene_corpus as corpus


def _write_inputs(tmp_path: Path):
    catalog = tmp_path / "catalog.json"
    bootstrap = tmp_path / "bootstrap.json"
    catalog.write_text(
        json.dumps({"format": "SHIFT.OfflineResourceCatalog/1"}),
        encoding="utf-8",
    )
    bootstrap.write_text(
        json.dumps({"format": "SHIFT.SceneVehicleBootstrap/1", "ready": True}),
        encoding="utf-8",
    )
    return catalog, bootstrap


def test_ready_corpus_build_removes_manual_ir_and_sgb_paths(monkeypatch, tmp_path):
    catalog_path, bootstrap_path = _write_inputs(tmp_path)
    calls = []

    def scene_ir(inputs, output_dir, *, fail_fast=False):
        calls.append(("scene_ir", list(inputs), Path(output_dir), fail_fast))
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return {
            "format": corpus.SCENE_IR_FORMAT,
            "ready": True,
            "blocking_reasons": [],
        }

    def scene_root(catalog, bootstrap, ir_root):
        calls.append(("scene_root", catalog, bootstrap, Path(ir_root)))
        raw = Path(ir_root) / "raw" / "scene.sgb"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"sgb")
        return {
            "format": corpus.SCENE_ROOT_FORMAT,
            "ready": True,
            "blocking_reasons": [],
            "raw_sgb_path": str(raw),
        }

    def native_scene(sgb_path, ir_root, output_dir, **kwargs):
        calls.append(
            (
                "native_scene",
                Path(sgb_path),
                Path(ir_root),
                Path(output_dir),
                kwargs,
            )
        )
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return {
            "format": corpus.NATIVE_SCENE_FORMAT,
            "status": "static-resource-ready-runtime-draw-blocked",
            "static_resource_ready": True,
            "native_scene_runtime_ready": False,
            "blocking_reasons": [corpus.RUNTIME_DRAW_BLOCKER],
        }

    monkeypatch.setattr(corpus, "build_scene_ir", scene_ir)
    monkeypatch.setattr(corpus, "build_scene_root_ir_join", scene_root)
    monkeypatch.setattr(corpus, "build_native_scene_files", native_scene)

    consensus = tmp_path / "root-consensus.json"
    shader = tmp_path / "shader-admission.json"
    report = corpus.build_native_scene_corpus_files(
        [tmp_path / "Silverstone_Era3_.zip", tmp_path / "RENDER.bff"],
        catalog_path,
        bootstrap_path,
        tmp_path / "out",
        root_consensus_path=consensus,
        runtime_shader_admission_path=shader,
        fail_fast=True,
    )

    assert report["static_resource_ready"] is True
    assert report["native_scene_runtime_ready"] is False
    assert report["status"] == "static-resource-ready-runtime-draw-blocked"
    assert report["blocking_reasons"] == [corpus.RUNTIME_DRAW_BLOCKER]
    assert report["boundary"]["manual_ir_root_required"] is False
    assert report["boundary"]["manual_sgb_path_required"] is False
    assert calls[0][0] == "scene_ir"
    assert calls[0][3] is True
    assert calls[1][0] == "scene_root"
    assert calls[2][0] == "native_scene"
    assert calls[2][4]["root_consensus_path"] == consensus
    assert calls[2][4]["runtime_shader_admission_path"] == shader
    assert (tmp_path / "out" / "native_scene_corpus_build.json").is_file()
    assert (tmp_path / "out" / "scene_root_ir_join.json").is_file()


def test_blocked_scene_ir_skips_root_join_and_native_scene(monkeypatch, tmp_path):
    catalog_path, bootstrap_path = _write_inputs(tmp_path)
    monkeypatch.setattr(
        corpus,
        "build_scene_ir",
        lambda inputs, output_dir, fail_fast=False: {
            "format": corpus.SCENE_IR_FORMAT,
            "ready": False,
            "blocking_reasons": ["manifest-resource-errors:1"],
        },
    )

    def must_not_run(*args, **kwargs):
        raise AssertionError("downstream stage must not run")

    monkeypatch.setattr(corpus, "build_scene_root_ir_join", must_not_run)
    monkeypatch.setattr(corpus, "build_native_scene_files", must_not_run)

    report = corpus.build_native_scene_corpus_files(
        [tmp_path / "corpus.zip"],
        catalog_path,
        bootstrap_path,
        tmp_path / "out",
    )

    assert report["static_resource_ready"] is False
    assert "scene-ir:manifest-resource-errors:1" in report["blocking_reasons"]
    assert "scene-root:scene-ir-not-ready" in report["blocking_reasons"]
    assert "native-scene:scene-root-ir-join-not-ready" in report["blocking_reasons"]


def test_blocked_exact_scene_root_skips_native_scene(monkeypatch, tmp_path):
    catalog_path, bootstrap_path = _write_inputs(tmp_path)
    monkeypatch.setattr(
        corpus,
        "build_scene_ir",
        lambda inputs, output_dir, fail_fast=False: {
            "format": corpus.SCENE_IR_FORMAT,
            "ready": True,
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        corpus,
        "build_scene_root_ir_join",
        lambda catalog, bootstrap, ir_root: {
            "format": corpus.SCENE_ROOT_FORMAT,
            "ready": False,
            "blocking_reasons": ["ir-sgb-root-ambiguous:2"],
            "raw_sgb_path": None,
        },
    )

    def must_not_run(*args, **kwargs):
        raise AssertionError("native scene stage must not run")

    monkeypatch.setattr(corpus, "build_native_scene_files", must_not_run)

    report = corpus.build_native_scene_corpus_files(
        [tmp_path / "corpus.zip"],
        catalog_path,
        bootstrap_path,
        tmp_path / "out",
    )

    assert report["static_resource_ready"] is False
    assert "scene-root:ir-sgb-root-ambiguous:2" in report["blocking_reasons"]
    assert report["stages"]["native_scene"]["static_resource_ready"] is False
    assert report["boundary"]["basename_fallback_is_admission_proof"] is False


def test_native_scene_static_blocker_propagates_without_promoting_runtime(monkeypatch, tmp_path):
    catalog_path, bootstrap_path = _write_inputs(tmp_path)
    monkeypatch.setattr(
        corpus,
        "build_scene_ir",
        lambda inputs, output_dir, fail_fast=False: {
            "format": corpus.SCENE_IR_FORMAT,
            "ready": True,
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        corpus,
        "build_scene_root_ir_join",
        lambda catalog, bootstrap, ir_root: {
            "format": corpus.SCENE_ROOT_FORMAT,
            "ready": True,
            "blocking_reasons": [],
            "raw_sgb_path": str(tmp_path / "scene.sgb"),
        },
    )
    monkeypatch.setattr(
        corpus,
        "build_native_scene_files",
        lambda *args, **kwargs: {
            "format": corpus.NATIVE_SCENE_FORMAT,
            "static_resource_ready": False,
            "native_scene_runtime_ready": False,
            "blocking_reasons": [
                "exact_ir_closure:exact-ir-missing:<root>->tracks/a.imb",
                corpus.RUNTIME_DRAW_BLOCKER,
            ],
        },
    )

    report = corpus.build_native_scene_corpus_files(
        [tmp_path / "corpus.zip"],
        catalog_path,
        bootstrap_path,
        tmp_path / "out",
    )

    assert report["static_resource_ready"] is False
    assert report["native_scene_runtime_ready"] is False
    assert (
        "native-scene:exact_ir_closure:exact-ir-missing:<root>->tracks/a.imb"
        in report["blocking_reasons"]
    )
    assert report["blocking_reasons"].count(corpus.RUNTIME_DRAW_BLOCKER) == 1
