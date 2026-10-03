from __future__ import annotations

import zipfile
from pathlib import Path

import offline_resource_pipeline as pipeline


class FakeEntry:
    def __init__(self, index: int, path: str, payload: bytes = b"x", typ: int = 0):
        self.index = index
        self.path = path
        self.type = typ
        self.compressed_size = len(payload)
        self.uncompressed_size = len(payload)
        self._payload = payload


class FakeBFF:
    entries_by_name: dict[str, list[FakeEntry]] = {}

    def __init__(self, path):
        self.path = Path(path)
        self.version = 3
        self.x12d = 0
        self.entries = list(self.entries_by_name[self.path.name])

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_entry(self, entry, type2="lzx"):
        return entry._payload

    def raw_payload(self, entry):
        return entry._payload


def test_materialize_bff_inputs_rejects_parent_traversal(tmp_path):
    source = tmp_path / "bad.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("../escape.bff", b"not-used")
    try:
        with pipeline.materialize_bff_inputs([source]):
            pass
    except ValueError as exc:
        assert "unsafe ZIP member" in str(exc)
    else:
        raise AssertionError("unsafe ZIP member was accepted")


def test_catalog_uses_semantic_edges_and_keeps_missing_dependency_explicit(monkeypatch, tmp_path):
    bff = tmp_path / "Scene.bff"
    bff.write_bytes(b"fixture")
    FakeBFF.entries_by_name = {
        "Scene.bff": [
            FakeEntry(0, "tracks/test/a.imb", b"imb"),
            FakeEntry(1, "tracks/test/a.bmt", b"bmt"),
            FakeEntry(2, "tracks/test/a.dds", b"dds"),
        ],
    }
    monkeypatch.setattr(pipeline, "BFF", FakeBFF)
    monkeypatch.setattr(pipeline, "classify", lambda path: "TEST")
    monkeypatch.setattr(
        pipeline,
        "analyze_decoded_resource",
        lambda path, payload: {"analysis": {"format": "fixture"}},
    )

    def fake_deps(path, payload, analysis):
        if path.endswith(".imb"):
            return ([{
                "ref": "tracks/test/a.bmt",
                "kind": "material",
                "scope": "same-archive-exact",
                "parser": "fixture.semantic",
                "evidence": "semantic-parser",
                "admissible": True,
            }], {"format": "FixtureIR/1"})
        if path.endswith(".bmt"):
            return ([
                {
                    "ref": "tracks/test/a.dds",
                    "kind": "texture",
                    "scope": "same-archive-exact",
                    "parser": "fixture.semantic",
                    "evidence": "semantic-parser",
                    "admissible": True,
                },
                {
                    "ref": "render/shaders/missing.fx",
                    "kind": "shader-source",
                    "scope": "global-exact",
                    "parser": "fixture.semantic",
                    "evidence": "semantic-parser",
                    "admissible": True,
                },
            ], {"format": "FixtureMaterial/1"})
        return ([], None)

    monkeypatch.setattr(pipeline, "_semantic_dependencies", fake_deps)
    materialized = [pipeline.MaterializedArchive(str(bff), None, bff)]
    catalog, graph, coverage = pipeline.build_catalog(materialized, decode_known=True)

    assert catalog["summary"]["resources"] == 3
    assert coverage["blocked"] == 0
    statuses = {(edge["ref"], edge["status"]) for edge in graph["edges"]}
    assert ("tracks/test/a.bmt", "resolved") in statuses
    assert ("tracks/test/a.dds", "resolved") in statuses
    assert ("render/shaders/missing.fx", "missing") in statuses
    assert graph["summary"]["blocking_admissible_edges"] == 1


def _resource(archive_id: str, index: int, path: str, *, parsed: bool = True):
    return {
        "id": f"{archive_id}#{index}",
        "archive_id": archive_id,
        "archive_name": archive_id + ".bff",
        "index": index,
        "path": path,
        "normalized_path": path.lower(),
        "extension": Path(path).suffix.lower(),
        "decode_status": "parsed" if parsed else "unsupported",
    }


def test_bootstrap_selects_exact_archives_and_never_bypasses_native_gate():
    catalog = {
        "format": pipeline.CATALOG_FORMAT,
        "archives": [
            {"id": "tv", "archive_name": "Silverstone_Era3_GrandPrix.bff"},
            {"id": "tp", "archive_name": "Silverstone_Era3_GrandPrix_Physics.bff"},
            {"id": "veh", "archive_name": "Ford_Mustang_2010.bff"},
        ],
        "resources": [
            _resource("tv", 0, "tracks/test/scene.sgb"),
            _resource("tv", 1, "tracks/test/data.trd"),
            _resource("tv", 2, "tracks/test/scene.lsd"),
            _resource("tv", 3, "tracks/test/mesh.imb"),
            _resource("tp", 0, "tracks/_data/aiw/test.aiw"),
            _resource("tp", 1, "tracks/test/physics/test.csm"),
            _resource("veh", 0, "vehicles/test/test.cdf"),
            _resource("veh", 1, "vehicles/test/test.edf"),
            _resource("veh", 2, "vehicles/test/test.gdf"),
            _resource("veh", 3, "vehicles/test/test.sdf"),
            _resource("veh", 4, "vehicles/test/test.tbf"),
            _resource("veh", 5, "vehicles/test/test.bbf"),
            _resource("veh", 6, "vehicles/test/test.vhf"),
        ],
    }
    graph = {"format": pipeline.GRAPH_FORMAT, "edges": []}
    bootstrap, admission = pipeline.build_bootstrap_manifest(
        catalog,
        graph,
        track="Silverstone_Era3_GrandPrix",
        vehicle="Ford_Mustang_2010",
    )
    assert bootstrap["ready"] is True
    assert bootstrap["status"] == "ready"
    assert admission["resource_bootstrap_ready"] is True
    assert admission["native_runtime_ready"] is False
    assert admission["status"] == "resource-ready-runtime-blocked"
    assert admission["boundary"]["provenance_gate_bypass"] is False


def test_bootstrap_fails_closed_on_ambiguous_required_root():
    catalog = {
        "format": pipeline.CATALOG_FORMAT,
        "archives": [
            {"id": "tv", "archive_name": "Track.bff"},
            {"id": "tp", "archive_name": "Track_Physics.bff"},
            {"id": "veh", "archive_name": "Car.bff"},
        ],
        "resources": [
            _resource("tv", 0, "a.sgb"),
            _resource("tv", 1, "b.sgb"),
            _resource("tv", 2, "a.trd"),
            _resource("tv", 3, "a.lsd"),
            _resource("tv", 4, "a.imb"),
            _resource("tp", 0, "a.aiw"),
            _resource("tp", 1, "a.csm"),
            *[_resource("veh", i, "v/x" + ext) for i, ext in enumerate(
                pipeline.VEHICLE_PHYSICS_EXTENSIONS + pipeline.VEHICLE_RENDER_ROOT_EXTENSIONS
            )],
        ],
    }
    bootstrap, admission = pipeline.build_bootstrap_manifest(
        catalog, {"edges": []}, track="Track", vehicle="Car"
    )
    assert bootstrap["ready"] is False
    assert any(
        reason.startswith("track-visual.sgb-ambiguous:2")
        for reason in bootstrap["blocking_reasons"]
    )
    assert admission["status"] == "resource-blocked"
