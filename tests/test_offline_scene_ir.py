from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import offline_scene_ir as scene_ir
from offline_resource_pipeline import MaterializedArchive


@contextmanager
def _materialized(paths):
    yield [
        MaterializedArchive(str(path), None, path)
        for path in paths
    ]


def test_scene_ir_reuses_importer_and_includes_imb_imx(monkeypatch, tmp_path):
    first = tmp_path / "Track.bff"
    second = tmp_path / "RENDER.bff"
    first.write_bytes(b"track")
    second.write_bytes(b"render")

    monkeypatch.setattr(
        scene_ir,
        "materialize_bff_inputs",
        lambda inputs: _materialized([first, second]),
    )
    observed = {}

    def fake_build_ir(args):
        observed["input"] = Path(args.input)
        observed["ext"] = list(args.ext)
        observed["fail_fast"] = args.fail_fast
        staged = sorted(path.name for path in Path(args.input).rglob("*.bff"))
        observed["staged"] = staged
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text(
            json.dumps([
                {
                    "archive": "Track.bff",
                    "path": "tracks/test/tree.imb",
                    "entry_index": 7,
                    "sha256": "11" * 32,
                    "raw": "raw/fixture",
                    "output": "other/fixture.bin",
                    "dependencies": [
                        {
                            "ref": "tree.bmt",
                            "resolved": [
                                {
                                    "archive": "Track.bff",
                                    "path": "tracks/materials/tree.bmt",
                                    "method": "basename",
                                }
                            ],
                        }
                    ],
                }
            ]),
            encoding="utf-8",
        )
        (out / "stats.json").write_text(
            json.dumps({"resources": 1, "failed": 0}),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(scene_ir, "cmd_build_ir", fake_build_ir)
    out = tmp_path / "ir"
    report = scene_ir.build_scene_ir([tmp_path / "corpus.zip"], out)

    assert report["ready"] is True
    assert report["archive_count"] == 2
    assert observed["staged"] == ["RENDER.bff", "Track.bff"]
    assert ".imb" in observed["ext"]
    assert ".imx" in observed["ext"]
    assert report["boundary"]["legacy_manifest_dependency_hints_are_admission_proof"] is False
    assert report["boundary"]["legacy_basename_resolution_is_admission_proof"] is False
    assert report["boundary"]["resource_identity_admission"] == "must-be-performed-by-exact-ir-closure"
    assert (out / "scene_ir_materialization.json").is_file()
    assert len(report["artifacts"]["manifest"]["sha256"]) == 64


def test_scene_ir_propagates_importer_failure(monkeypatch, tmp_path):
    archive = tmp_path / "Track.bff"
    archive.write_bytes(b"track")
    monkeypatch.setattr(
        scene_ir,
        "materialize_bff_inputs",
        lambda inputs: _materialized([archive]),
    )

    def fake_build_ir(args):
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text(
            json.dumps([
                {
                    "archive": "Track.bff",
                    "path": "tracks/test/broken.imb",
                    "error": "ValueError: fixture",
                }
            ]),
            encoding="utf-8",
        )
        (out / "stats.json").write_text(
            json.dumps({"resources": 1, "failed": 1}),
            encoding="utf-8",
        )
        return 1

    monkeypatch.setattr(scene_ir, "cmd_build_ir", fake_build_ir)
    report = scene_ir.build_scene_ir([archive], tmp_path / "ir")

    assert report["ready"] is False
    assert report["manifest_error_count"] == 1
    assert "universal-importer-exit:1" in report["blocking_reasons"]
    assert "manifest-resource-errors:1" in report["blocking_reasons"]


def test_scene_ir_normalizes_explicit_extension_list(monkeypatch, tmp_path):
    archive = tmp_path / "Track.bff"
    archive.write_bytes(b"track")
    monkeypatch.setattr(
        scene_ir,
        "materialize_bff_inputs",
        lambda inputs: _materialized([archive]),
    )
    observed = {}

    def fake_build_ir(args):
        observed["ext"] = list(args.ext)
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text("[]", encoding="utf-8")
        (out / "stats.json").write_text("{}", encoding="utf-8")
        return 0

    monkeypatch.setattr(scene_ir, "cmd_build_ir", fake_build_ir)
    report = scene_ir.build_scene_ir(
        [archive],
        tmp_path / "ir",
        extensions=["IMB", ".IMX", "imb", "BMT"],
    )

    assert observed["ext"] == [".imb", ".imx", ".bmt"]
    assert report["extensions"] == [".imb", ".imx", ".bmt"]
