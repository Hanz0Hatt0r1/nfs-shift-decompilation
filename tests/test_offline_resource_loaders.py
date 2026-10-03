from __future__ import annotations

from pathlib import Path

import offline_resource_loaders as loaders
import offline_resource_pipeline as pipeline


def _archive(archive_id: str, name: str) -> dict:
    return {"id": archive_id, "archive_name": name}


def _resource(archive_id: str, index: int, path: str, *, status: str = "parsed") -> dict:
    return {
        "id": f"{archive_id}#{index}",
        "archive_id": archive_id,
        "archive_name": archive_id + ".bff",
        "index": index,
        "path": path,
        "normalized_path": path.lower(),
        "extension": Path(path).suffix.lower(),
        "decode_status": status,
    }


def _catalog() -> dict:
    return {
        "format": pipeline.CATALOG_FORMAT,
        "archives": [
            _archive("tv", "Silverstone_Era3_GrandPrix.bff"),
            _archive("tp", "Silverstone_Era3_GrandPrix_Physics.bff"),
            _archive("veh", "BMW_M3_E36.bff"),
        ],
        "resources": [
            _resource("tv", 0, "tracks/test/scene.sgb"),
            _resource("tv", 1, "tracks/test/data.trd"),
            _resource("tv", 2, "tracks/test/scene.lsd"),
            _resource("tv", 3, "tracks/test/a.imb"),
            _resource("tv", 4, "tracks/test/b.imx"),
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


def _graph(edges=None) -> dict:
    return {
        "format": pipeline.GRAPH_FORMAT,
        "edges": list(edges or []),
    }


def test_load_track_selects_exact_archives_and_roots():
    result = loaders.load_track(
        _catalog(),
        _graph(),
        track="Silverstone_Era3_GrandPrix",
    )

    assert result["format"] == loaders.TRACK_LOAD_FORMAT
    assert result["ready"] is True
    assert result["selected_archives"]["track_visual"]["id"] == "tv"
    assert result["selected_archives"]["track_physics"]["id"] == "tp"
    assert result["roots"]["track_visual"][".sgb"] == "tv#0"
    assert result["roots"]["track_visual"]["imb_resource_ids"] == ["tv#3"]
    assert result["roots"]["track_visual"]["imx_resource_ids"] == ["tv#4"]
    assert result["roots"]["track_physics"][".aiw"] == "tp#0"
    assert result["boundary"]["archive_selection"] == "exact-filename"
    assert result["boundary"]["basename_fallback"] is False


def test_load_vehicle_allows_missing_optional_cockpit_and_selects_physics_roots():
    result = loaders.load_vehicle(_catalog(), _graph(), vehicle="BMW_M3_E36")

    assert result["format"] == loaders.VEHICLE_LOAD_FORMAT
    assert result["ready"] is True
    assert set(result["selected_archives"]) == {"vehicle"}
    assert result["roots"]["vehicle"][".cdf"] == "veh#0"
    assert result["roots"]["vehicle"][".bbf"] == "veh#5"
    assert result["roots"]["vehicle"][".vhf"] == "veh#6"
    assert result["blocking_reasons"] == []


def test_load_track_fails_closed_on_unresolved_semantic_dependency():
    edge = {
        "source_id": "tv#3",
        "source_archive_id": "tv",
        "source_path": "tracks/test/a.imb",
        "ref": "tracks/test/missing.bmt",
        "admissible": True,
        "status": "missing",
        "targets": [],
    }
    result = loaders.load_track(
        _catalog(),
        _graph([edge]),
        track="Silverstone_Era3_GrandPrix",
    )

    assert result["ready"] is False
    assert result["unresolved_dependencies"] == [edge]
    assert result["blocking_reasons"] == [
        "dependency-missing:tracks/test/a.imb->tracks/test/missing.bmt"
    ]


def test_load_vehicle_requires_known_format_validation_to_have_run():
    catalog = _catalog()
    for row in catalog["resources"]:
        if row["archive_id"] == "veh":
            row["decode_status"] = "deferred"

    result = loaders.load_vehicle(catalog, _graph(), vehicle="BMW_M3_E36")

    assert result["ready"] is False
    assert "dependency-validation-not-run:use --decode-known" in result["blocking_reasons"]


def test_load_track_fails_closed_on_ambiguous_required_root():
    catalog = _catalog()
    catalog["resources"].append(_resource("tv", 99, "tracks/test/other.sgb"))

    result = loaders.load_track(
        catalog,
        _graph(),
        track="Silverstone_Era3_GrandPrix",
    )

    assert result["ready"] is False
    assert "track-visual.sgb-ambiguous:2" in result["blocking_reasons"]
