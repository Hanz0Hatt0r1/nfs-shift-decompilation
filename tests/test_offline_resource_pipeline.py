from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import offline_resource_pipeline as pipeline


class FakeEntry:
    def __init__(self, index: int, path: str, payload: bytes = b"x", typ: int = 0):
        self.index = index
        self.path = path
        self.offset = 0x1000 + index * 0x20
        self.type = typ
        self.compressed_size = len(payload)
        self.uncompressed_size = len(payload)
        self.crc32_field = 0xA000 + index
        self.fileext = 0
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


def test_catalog_inventory_is_content_addressed_without_decoding(monkeypatch, tmp_path):
    first = tmp_path / "A.bff"
    second = tmp_path / "B.bff"
    first.write_bytes(b"archive-a")
    second.write_bytes(b"archive-b")
    FakeBFF.entries_by_name = {
        "A.bff": [
            FakeEntry(0, "shared/one.fxo", b"same"),
            FakeEntry(1, "same/path.dds", b"left"),
        ],
        "B.bff": [
            FakeEntry(0, "other/two.fxo", b"same"),
            FakeEntry(1, "same/path.dds", b"right"),
        ],
    }
    monkeypatch.setattr(pipeline, "BFF", FakeBFF)
    monkeypatch.setattr(pipeline, "classify", lambda path: "TEST")

    materialized = [
        pipeline.MaterializedArchive(str(first), None, first),
        pipeline.MaterializedArchive(str(second), None, second),
    ]
    catalog, graph, coverage = pipeline.build_catalog(materialized, decode_known=False)

    assert graph["edges"] == []
    assert coverage["blocked"] == 0
    assert coverage["validation"] == {
        "total": 4,
        "supported": 2,
        "verified": 0,
        "blocked": 0,
        "unsupported": 2,
        "deferred": 2,
        "malformed": 0,
        "unknown_version_layout": 0,
        "unclassified_blocked": 0,
        "unresolved_dependency_edges": 0,
        "unresolved_dependency_resources": 0,
    }
    assert catalog["archives"][0]["sha256"] == hashlib.sha256(b"archive-a").hexdigest()
    assert catalog["archives"][0]["source_kind"] == "bff"
    assert catalog["archives"][0]["encryption"] == "none"

    first_resource = catalog["resources"][0]
    assert first_resource["offset"] == 0x1000
    assert first_resource["crc32_field"] == 0xA000
    assert first_resource["fileext"] == 0
    assert first_resource["encryption"] == "none"
    assert first_resource["raw_sha256"] == hashlib.sha256(b"same").hexdigest()
    assert "decoded_sha256" not in first_resource

    raw_groups = catalog["duplicate_identities"]["stored_payload_sha256"]
    assert len(raw_groups) == 1
    assert raw_groups[0]["occurrences"] == 2
    assert raw_groups[0]["paths"] == ["other/two.fxo", "shared/one.fxo"]

    path_groups = catalog["duplicate_identities"]["normalized_path"]
    assert len(path_groups) == 1
    assert path_groups[0]["identity"] == "same/path.dds"
    assert path_groups[0]["occurrences"] == 2
    assert catalog["duplicate_identities"]["decoded_payload_sha256"] == []
    assert catalog["summary"]["duplicate_stored_payload_groups"] == 1
    assert catalog["boundary"]["raw_sha256_semantics"] == "exact-stored-bff-payload-bytes"


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
    assert catalog["archives"][0]["sha256"] == hashlib.sha256(b"fixture").hexdigest()
    assert all(row.get("raw_sha256") for row in catalog["resources"])
    assert coverage["blocked"] == 0
    statuses = {(edge["ref"], edge["status"]) for edge in graph["edges"]}
    assert ("tracks/test/a.bmt", "resolved") in statuses
    assert ("tracks/test/a.dds", "resolved") in statuses
    assert ("render/shaders/missing.fx", "missing") in statuses
    assert graph["summary"]["blocking_admissible_edges"] == 1
    assert coverage["validation"]["verified"] == 3
    assert coverage["validation"]["unresolved_dependency_edges"] == 1
    assert coverage["validation"]["unresolved_dependency_resources"] == 1


def test_validation_taxonomy_never_guesses_generic_parser_failure(monkeypatch, tmp_path):
    bff = tmp_path / "Broken.bff"
    bff.write_bytes(b"fixture")
    FakeBFF.entries_by_name = {
        "Broken.bff": [FakeEntry(0, "tracks/test/broken.imb", b"broken")],
    }
    monkeypatch.setattr(pipeline, "BFF", FakeBFF)
    monkeypatch.setattr(pipeline, "classify", lambda path: "MESH_INSTANCE")
    monkeypatch.setattr(
        pipeline,
        "analyze_decoded_resource",
        lambda path, payload: {"analysis": {"format": "fixture"}},
    )

    def fail_semantic(*_):
        raise ValueError("unsupported mystery layout")

    monkeypatch.setattr(pipeline, "_semantic_dependencies", fail_semantic)
    materialized = [pipeline.MaterializedArchive(str(bff), None, bff)]
    _, _, coverage = pipeline.build_catalog(materialized, decode_known=True)

    validation = coverage["validation"]
    assert validation["total"] == 1
    assert validation["supported"] == 1
    assert validation["verified"] == 0
    assert validation["blocked"] == 1
    assert validation["malformed"] == 0
    assert validation["unknown_version_layout"] == 0
    assert validation["unclassified_blocked"] == 1
    assert coverage["validation_boundary"]["exception_text_classification"] is False


def test_imx_is_known_and_emits_exact_material_dependencies(monkeypatch):
    assert ".imx" in pipeline.KNOWN_DECODE_EXTENSIONS
    monkeypatch.setattr(
        pipeline,
        "build_imx_neutral_geometry",
        lambda payload: {
            "format": "SHIFT.IMXNeutralGeometry/1",
            "status": "ready",
            "ready": True,
            "primitive_count": 2,
            "decoded_properties": ["200", "130"],
            "deferred_stream_count": 0,
            "blocking_reasons": [],
            "primitives": [
                {"material": "tracks/test/body.mtx"},
                {"material": "tracks/test/glass.bmt"},
            ],
        },
    )

    deps, neutral = pipeline._semantic_dependencies(
        "tracks/test/car.imx",
        b"fixture-imx",
        {"analysis": {"format": "XML"}},
    )

    assert [(row["ref"], row["kind"], row["scope"], row["parser"]) for row in deps] == [
        (
            "tracks/test/body.bmt",
            "material",
            "same-archive-exact",
            "build_imx_neutral_geometry",
        ),
        (
            "tracks/test/glass.bmt",
            "material",
            "same-archive-exact",
            "build_imx_neutral_geometry",
        ),
    ]
    assert neutral == {
        "format": "SHIFT.IMXNeutralGeometry/1",
        "status": "ready",
        "ready": True,
        "primitive_count": 2,
        "decoded_properties": ["200", "130"],
        "deferred_stream_count": 0,
        "blocking_reasons": [],
    }


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
            _resource("tv", 4, "tracks/test/mesh_xml.imx"),
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
    assert bootstrap["roots"]["track_visual"]["imb_resource_ids"] == ["tv#3"]
    assert bootstrap["roots"]["track_visual"]["imx_resource_ids"] == ["tv#4"]
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
