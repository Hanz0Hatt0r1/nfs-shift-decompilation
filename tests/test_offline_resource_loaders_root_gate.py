from __future__ import annotations

from pathlib import Path

import offline_resource_loaders as loaders
import offline_resource_pipeline as pipeline


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
            {"id": "tv", "archive_name": "Track.bff"},
            {"id": "tp", "archive_name": "Track_Physics.bff"},
            {"id": "veh", "archive_name": "Car.bff"},
        ],
        "resources": [
            _resource("tv", 0, "tracks/test/scene.sgb"),
            _resource("tv", 1, "tracks/test/data.trd"),
            _resource("tv", 2, "tracks/test/scene.lsd"),
            _resource("tp", 0, "tracks/_data/aiw/test.aiw"),
            _resource("tp", 1, "tracks/test/physics/test.csm"),
            *[
                _resource("veh", index, "vehicles/test/car" + ext)
                for index, ext in enumerate(
                    pipeline.VEHICLE_PHYSICS_EXTENSIONS
                    + pipeline.VEHICLE_RENDER_ROOT_EXTENSIONS
                )
            ],
        ],
    }


def _graph() -> dict:
    return {"format": pipeline.GRAPH_FORMAT, "edges": []}


def test_track_loader_blocks_explicitly_failed_required_root():
    catalog = _catalog()
    sgb = next(row for row in catalog["resources"] if row["extension"] == ".sgb")
    sgb.update({
        "decode_status": "blocked",
        "analysis_error": "source-backed-sgb-runtime-not-ready:fixture",
    })

    result = loaders.load_track(catalog, _graph(), track="Track")

    assert result["ready"] is False
    assert result["status"] == "blocked"
    assert result["blocked_required_roots"] == [
        {
            "group": "track_visual",
            "extension": ".sgb",
            "resource_id": "tv#0",
            "path": "tracks/test/scene.sgb",
            "decode_status": "blocked",
            "analysis_error": "source-backed-sgb-runtime-not-ready:fixture",
            "error_kind": None,
            "error": None,
        }
    ]
    assert (
        "root-validation-blocked:track_visual:.sgb:tracks/test/scene.sgb"
        in result["blocking_reasons"]
    )
    assert result["boundary"]["blocked_required_root_closes_gate"] is True


def test_vehicle_loader_blocks_explicitly_failed_required_root():
    catalog = _catalog()
    cdf = next(row for row in catalog["resources"] if row["extension"] == ".cdf")
    cdf.update({
        "decode_status": "blocked",
        "error_kind": "ValueError",
        "error": "fixture parser failure",
    })

    result = loaders.load_vehicle(catalog, _graph(), vehicle="Car")

    assert result["ready"] is False
    assert result["blocked_required_roots"][0]["group"] == "vehicle"
    assert result["blocked_required_roots"][0]["extension"] == ".cdf"
    assert result["blocked_required_roots"][0]["resource_id"] == "veh#0"
    assert (
        "root-validation-blocked:vehicle:.cdf:vehicles/test/car.cdf"
        in result["blocking_reasons"]
    )


def test_loader_does_not_reclassify_unsupported_root_as_parser_failure():
    catalog = _catalog()
    trd = next(row for row in catalog["resources"] if row["extension"] == ".trd")
    trd["decode_status"] = "unsupported"

    result = loaders.load_track(catalog, _graph(), track="Track")

    assert result["ready"] is True
    assert result["blocked_required_roots"] == []
    assert not any(
        reason.startswith("root-validation-blocked:")
        for reason in result["blocking_reasons"]
    )
    assert result["boundary"]["unsupported_or_deferred_root_reclassified_as_parser_failure"] is False
