from __future__ import annotations

import hashlib
import json
from pathlib import Path

import offline_scene_root_ir as scene_root


def _fixture(tmp_path: Path):
    payload = b"SGB-fixture"
    digest = hashlib.sha256(payload).hexdigest()
    archive_id = "track-archive"
    resource_id = f"{archive_id}#7"
    path = "tracks/silverstone/silverstone.sgb"
    catalog = {
        "format": scene_root.CATALOG_FORMAT,
        "resources": [
            {
                "id": resource_id,
                "archive_id": archive_id,
                "archive_name": "Silverstone.bff",
                "index": 7,
                "path": path,
                "normalized_path": path,
                "extension": ".sgb",
                "decoded_sha256": digest,
            }
        ],
    }
    bootstrap = {
        "format": scene_root.BOOTSTRAP_FORMAT,
        "ready": True,
        "selected_archives": {
            "track_visual": {
                "id": archive_id,
                "archive_name": "Silverstone.bff",
            }
        },
        "roots": {
            "track_visual": {
                ".sgb": resource_id,
            }
        },
    }
    ir = tmp_path / "ir"
    raw = ir / "raw" / "fixture"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(payload)
    manifest = [
        {
            "archive": "Silverstone.bff",
            "entry_index": 7,
            "path": path,
            "sha256": digest,
            "raw": "raw/fixture",
            "output": "scenes/fixture.json",
        }
    ]
    (ir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return catalog, bootstrap, ir, manifest, digest


def test_scene_root_join_requires_exact_catalog_and_ir_identity(tmp_path):
    catalog, bootstrap, ir, _, digest = _fixture(tmp_path)

    report = scene_root.build_scene_root_ir_join(catalog, bootstrap, ir)

    assert report["ready"] is True
    assert report["root_resource_id"] == "track-archive#7"
    assert report["catalog_resource"]["decoded_sha256"] == digest
    assert report["ir_resource"]["sha256"] == digest
    assert Path(report["raw_sgb_path"]).read_bytes() == b"SGB-fixture"
    assert report["boundary"]["catalog_decoded_sha256_required"] is True
    assert report["boundary"]["basename_fallback"] is False
    assert report["boundary"]["first_duplicate_wins"] is False


def test_same_entry_index_in_wrong_archive_is_not_admitted(tmp_path):
    catalog, bootstrap, ir, manifest, _ = _fixture(tmp_path)
    manifest[0]["archive"] = "Other.bff"
    (ir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = scene_root.build_scene_root_ir_join(catalog, bootstrap, ir)

    assert report["ready"] is False
    assert "ir-sgb-root-missing" in report["blocking_reasons"]
    assert report["raw_sgb_path"] is None


def test_duplicate_exact_ir_rows_are_ambiguous(tmp_path):
    catalog, bootstrap, ir, manifest, _ = _fixture(tmp_path)
    manifest.append(dict(manifest[0]))
    (ir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = scene_root.build_scene_root_ir_join(catalog, bootstrap, ir)

    assert report["ready"] is False
    assert "ir-sgb-root-ambiguous:2" in report["blocking_reasons"]
    assert report["boundary"]["first_duplicate_wins"] is False


def test_catalog_and_ir_decoded_sha_must_match(tmp_path):
    catalog, bootstrap, ir, manifest, _ = _fixture(tmp_path)
    manifest[0]["sha256"] = "22" * 32
    (ir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = scene_root.build_scene_root_ir_join(catalog, bootstrap, ir)

    assert report["ready"] is False
    assert "ir-sgb-root-decoded-sha256-mismatch" in report["blocking_reasons"]
    assert "ir-sgb-root-raw-sha256-mismatch" in report["blocking_reasons"]


def test_catalog_decoded_sha_is_required_for_exact_scene_root_identity(tmp_path):
    catalog, bootstrap, ir, _, _ = _fixture(tmp_path)
    del catalog["resources"][0]["decoded_sha256"]

    report = scene_root.build_scene_root_ir_join(catalog, bootstrap, ir)

    assert report["ready"] is False
    assert "catalog-sgb-root-decoded-sha256-missing" in report["blocking_reasons"]
    assert report["boundary"]["catalog_decoded_sha256_required"] is True


def test_bootstrap_not_ready_keeps_join_blocked_even_when_identity_matches(tmp_path):
    catalog, bootstrap, ir, _, _ = _fixture(tmp_path)
    bootstrap["ready"] = False
    bootstrap["blocking_reasons"] = ["root-validation-blocked"]

    report = scene_root.build_scene_root_ir_join(catalog, bootstrap, ir)

    assert report["ready"] is False
    assert "bootstrap-not-ready" in report["blocking_reasons"]
    assert report["ir_resource"] is not None


def test_catalog_root_must_belong_to_selected_track_archive(tmp_path):
    catalog, bootstrap, ir, _, _ = _fixture(tmp_path)
    catalog["resources"][0]["archive_id"] = "different-archive"

    report = scene_root.build_scene_root_ir_join(catalog, bootstrap, ir)

    assert report["ready"] is False
    assert "catalog-root-selected-archive-id-mismatch" in report["blocking_reasons"]
