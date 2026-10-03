from __future__ import annotations

from pathlib import Path

import offline_resource_pipeline as pipeline


def _resource(archive_id: str, index: int, path: str, *, status: str = "parsed"):
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


def _catalog(*, sgb_status: str):
    return {
        "format": pipeline.CATALOG_FORMAT,
        "archives": [
            {"id": "tv", "archive_name": "Track.bff"},
            {"id": "tp", "archive_name": "Track_Physics.bff"},
            {"id": "veh", "archive_name": "Car.bff"},
        ],
        "resources": [
            {
                **_resource("tv", 0, "tracks/test/scene.sgb", status=sgb_status),
                "analysis_error": (
                    "source-backed-sgb-runtime-not-ready:FLAT:decode:fixture"
                    if sgb_status == "blocked"
                    else None
                ),
            },
            _resource("tv", 1, "tracks/test/data.trd"),
            _resource("tv", 2, "tracks/test/scene.lsd"),
            _resource("tp", 0, "tracks/_data/aiw/test.aiw"),
            _resource("tp", 1, "tracks/test/physics/test.csm"),
            *[
                _resource("veh", i, "vehicles/test/x" + ext)
                for i, ext in enumerate(
                    pipeline.VEHICLE_PHYSICS_EXTENSIONS
                    + pipeline.VEHICLE_RENDER_ROOT_EXTENSIONS
                )
            ],
        ],
    }


def test_bootstrap_blocks_explicitly_failed_required_root_validation():
    bootstrap, admission = pipeline.build_bootstrap_manifest(
        _catalog(sgb_status="blocked"),
        {"format": pipeline.GRAPH_FORMAT, "edges": []},
        track="Track",
        vehicle="Car",
    )

    assert bootstrap["ready"] is False
    assert bootstrap["status"] == "blocked"
    assert bootstrap["blocked_required_roots"] == [
        {
            "group": "track_visual",
            "extension": ".sgb",
            "resource_id": "tv#0",
            "path": "tracks/test/scene.sgb",
            "decode_status": "blocked",
            "analysis_error": "source-backed-sgb-runtime-not-ready:FLAT:decode:fixture",
            "error_kind": None,
            "error": None,
        }
    ]
    assert (
        "root-validation-blocked:track_visual:.sgb:tracks/test/scene.sgb"
        in bootstrap["blocking_reasons"]
    )
    assert bootstrap["boundary"]["blocked_required_root_closes_gate"] is True
    assert admission["resource_bootstrap_ready"] is False
    assert admission["status"] == "resource-blocked"


def test_bootstrap_does_not_reclassify_unsupported_required_root_as_parser_failure():
    catalog = _catalog(sgb_status="parsed")
    trd = next(row for row in catalog["resources"] if row["extension"] == ".trd")
    trd["decode_status"] = "unsupported"

    bootstrap, admission = pipeline.build_bootstrap_manifest(
        catalog,
        {"format": pipeline.GRAPH_FORMAT, "edges": []},
        track="Track",
        vehicle="Car",
    )

    assert bootstrap["ready"] is True
    assert bootstrap["blocked_required_roots"] == []
    assert not any(
        reason.startswith("root-validation-blocked:")
        for reason in bootstrap["blocking_reasons"]
    )
    assert admission["resource_bootstrap_ready"] is True
