from __future__ import annotations

import json
from pathlib import Path

import offline_exact_ir_closure as closure


def _row(archive: str, path: str, index: int) -> dict:
    return {
        "archive": archive,
        "path": path,
        "entry_index": index,
        "sha256": f"{index + 1:064x}",
        "raw": f"raw/{index}",
        "output": f"out/{index}",
    }


def _write_manifest(root: Path, rows: list[dict]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(rows), encoding="utf-8")


def test_missing_exact_path_never_falls_back_to_same_basename(monkeypatch, tmp_path):
    _write_manifest(
        tmp_path,
        [_row("Track.bff", "tracks/other/tree.imb", 1)],
    )
    monkeypatch.setattr(closure, "_semantic_refs", lambda root, row: [])

    report = closure.build_exact_ir_resource_closure(
        tmp_path,
        ["tracks/scene/tree.imb"],
    )

    assert report["ready"] is False
    assert report["edges"][0]["status"] == "missing"
    assert report["edges"][0]["targets"] == []
    assert report["boundary"]["basename_fallback"] is False


def test_duplicate_exact_path_is_ambiguous_instead_of_first_hit(monkeypatch, tmp_path):
    _write_manifest(
        tmp_path,
        [
            _row("TrackA.bff", "tracks/shared/tree.imb", 1),
            _row("TrackB.bff", "tracks/shared/tree.imb", 2),
        ],
    )
    monkeypatch.setattr(closure, "_semantic_refs", lambda root, row: [])

    report = closure.build_exact_ir_resource_closure(
        tmp_path,
        ["tracks/shared/tree.imb"],
    )

    assert report["ready"] is False
    assert report["edges"][0]["status"] == "ambiguous"
    assert len(report["edges"][0]["targets"]) == 2
    assert report["boundary"]["first_duplicate_wins"] is False


def test_known_mtx_to_bmt_alias_is_exact_and_unique(monkeypatch, tmp_path):
    _write_manifest(
        tmp_path,
        [_row("Track.bff", "tracks/materials/body.bmt", 3)],
    )
    monkeypatch.setattr(closure, "_semantic_refs", lambda root, row: [])

    report = closure.build_exact_ir_resource_closure(
        tmp_path,
        ["tracks/materials/body.mtx"],
    )

    assert report["ready"] is True
    assert report["edges"][0]["status"] == "resolved"
    assert report["edges"][0]["targets"][0]["path"] == "tracks/materials/body.bmt"
    assert report["boundary"]["known_aliases"] == [".mtx->.bmt"]


def test_semantic_closure_requires_each_transitive_reference_to_resolve_exactly(
    monkeypatch,
    tmp_path,
):
    rows = [
        _row("Track.bff", "tracks/mesh/tree.imb", 1),
        _row("Track.bff", "tracks/material/tree.bmt", 2),
        _row("Render.bff", "render/shaders/tree.fx", 3),
        _row("Track.bff", "tracks/textures/tree.dds", 4),
    ]
    _write_manifest(tmp_path, rows)

    deps = {
        "tracks/mesh/tree.imb": [
            {"ref": "tracks/material/tree.bmt", "kind": "material"},
        ],
        "tracks/material/tree.bmt": [
            {"ref": "render/shaders/tree.fx", "kind": "shader-source"},
            {"ref": "tracks/textures/tree.dds", "kind": "texture"},
        ],
    }
    monkeypatch.setattr(
        closure,
        "_semantic_refs",
        lambda root, row: deps.get(row["path"], []),
    )

    report = closure.build_exact_ir_resource_closure(
        tmp_path,
        ["tracks/mesh/tree.imb"],
    )

    assert report["ready"] is True
    assert {edge["kind"] for edge in report["edges"]} == {
        "scene-resource",
        "material",
        "shader-source",
        "texture",
    }
    assert all(edge["status"] == "resolved" for edge in report["edges"])
    assert report["resolved_resource_count"] == 4


def test_semantic_closure_blocks_basename_only_transitive_match(monkeypatch, tmp_path):
    rows = [
        _row("Track.bff", "tracks/mesh/tree.imb", 1),
        _row("Track.bff", "other/material/tree.bmt", 2),
    ]
    _write_manifest(tmp_path, rows)
    monkeypatch.setattr(
        closure,
        "_semantic_refs",
        lambda root, row: (
            [{"ref": "tracks/material/tree.bmt", "kind": "material"}]
            if row["path"].endswith("tree.imb")
            else []
        ),
    )

    report = closure.build_exact_ir_resource_closure(
        tmp_path,
        ["tracks/mesh/tree.imb"],
    )

    assert report["ready"] is False
    material_edge = next(edge for edge in report["edges"] if edge["kind"] == "material")
    assert material_edge["status"] == "missing"
    assert "exact-ir-missing:tracks/mesh/tree.imb->tracks/material/tree.bmt" in report["blocking_reasons"]
