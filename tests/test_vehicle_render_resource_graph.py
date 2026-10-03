from __future__ import annotations

from vehicle_render_resource_graph import (
    FORMAT,
    build_vehicle_render_resource_graph,
)


def _resource(resource_id, path, ext, *, archive="vehicle", status="parsed"):
    return {
        "id": resource_id,
        "archive_id": archive,
        "archive_name": "BMW_M3_E36.bff" if archive == "vehicle" else "RENDER.bff",
        "path": path,
        "extension": ext,
        "category": {
            ".vhf": "SCENE",
            ".meb": "MESH",
            ".bmt": "MATERIAL",
            ".dds": "TEXTURE",
            ".fx": "SHADER",
        }.get(ext, "UNKNOWN"),
        "decode_status": status,
        "decoded_sha256": (resource_id[-1] * 64)[:64],
        "raw_sha256": None,
        "neutral_ir": {"format": "fixture"},
    }


def _catalog():
    return {
        "format": "SHIFT.OfflineResourceCatalog/1",
        "resources": [
            _resource("v1", "vehicles/bmw/car.vhf", ".vhf"),
            _resource("m2", "vehicles/bmw/body.meb", ".meb"),
            _resource("b3", "vehicles/bmw/body.bmt", ".bmt"),
            _resource("d4", "vehicles/bmw/body.dds", ".dds"),
            _resource("f5", "shaders/car.fx", ".fx", archive="render"),
        ],
    }


def _bootstrap():
    return {
        "format": "SHIFT.SceneVehicleBootstrap/1",
        "vehicle": "BMW_M3_E36",
        "selected_archives": {
            "vehicle": {
                "id": "vehicle",
                "archive_name": "BMW_M3_E36.bff",
            }
        },
        "roots": {"vehicle": {".vhf": "v1"}},
    }


def _edge(source, path, ref, kind, target, *, status="resolved", admissible=True):
    return {
        "source_id": source,
        "source_path": path,
        "ref": ref,
        "kind": kind,
        "scope": "same-archive-exact" if kind != "shader-source" else "global-exact",
        "parser": "fixture-parser",
        "evidence": "semantic-parser",
        "admissible": admissible,
        "status": status,
        "targets": [target] if target else [],
    }


def _graph():
    return {
        "format": "SHIFT.OfflineResourceDependencyGraph/1",
        "edges": [
            _edge("v1", "vehicles/bmw/car.vhf", "vehicles/bmw/body.meb", "geometry", "m2"),
            _edge("m2", "vehicles/bmw/body.meb", "vehicles/bmw/body.bmt", "material", "b3"),
            _edge("b3", "vehicles/bmw/body.bmt", "vehicles/bmw/body.dds", "texture", "d4"),
            _edge("b3", "vehicles/bmw/body.bmt", "shaders/car.fx", "shader-source", "f5"),
            _edge(
                "v1",
                "vehicles/bmw/car.vhf",
                "diagnostic-only.dds",
                "texture",
                None,
                status="diagnostic",
                admissible=False,
            ),
        ],
    }


def test_vehicle_render_graph_builds_exact_semantic_closure():
    report = build_vehicle_render_resource_graph(_catalog(), _graph(), _bootstrap())

    assert report["format"] == FORMAT
    assert report["resource_closure_ready"] is True
    assert report["native_render_ready"] is False
    assert report["status"] == "resource-ready-native-blocked"
    assert {row["resource_id"] for row in report["resources"]} == {
        "v1", "m2", "b3", "d4", "f5"
    }
    assert len(report["edges"]) == 4
    assert report["unresolved_dependencies"] == []
    assert report["boundary"]["diagnostic_edges_traversed"] is False
    assert report["boundary"]["lod_or_damage_selection_invented"] is False
    assert report["native_blocking_reasons"] == [
        "runtime-draw-shader-permutation-provenance-required"
    ]


def test_vehicle_render_graph_preserves_missing_dependency_blocker():
    graph = _graph()
    graph["edges"][3] = _edge(
        "b3",
        "vehicles/bmw/body.bmt",
        "shaders/missing.fx",
        "shader-source",
        None,
        status="missing",
    )
    report = build_vehicle_render_resource_graph(_catalog(), graph, _bootstrap())

    assert report["resource_closure_ready"] is False
    assert report["native_render_ready"] is False
    assert len(report["unresolved_dependencies"]) == 1
    assert any(reason.startswith("dependency-missing:") for reason in report["blocking_reasons"])


def test_vehicle_render_graph_rejects_unparsed_semantic_source():
    catalog = _catalog()
    for row in catalog["resources"]:
        if row["id"] == "m2":
            row["decode_status"] = "blocked"
    report = build_vehicle_render_resource_graph(catalog, _graph(), _bootstrap())

    assert report["resource_closure_ready"] is False
    assert "dependency-source-not-parsed:m2:.meb" in report["blocking_reasons"]


def test_vehicle_render_graph_requires_exact_vehicle_vhf_root():
    bootstrap = _bootstrap()
    bootstrap["roots"]["vehicle"][".vhf"] = None
    report = build_vehicle_render_resource_graph(_catalog(), _graph(), bootstrap)

    assert report["resource_closure_ready"] is False
    assert "vehicle-vhf-root:missing" in report["blocking_reasons"]
