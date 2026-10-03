from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "shift_resource_pipeline_loader_cli",
    ROOT / "tools" / "shift_resource_pipeline.py",
)
assert SPEC is not None and SPEC.loader is not None
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def _write_contracts(tmp_path: Path) -> tuple[Path, Path]:
    catalog = tmp_path / "resource_catalog.json"
    graph = tmp_path / "dependency_graph.json"
    catalog.write_text(json.dumps({"format": "SHIFT.OfflineResourceCatalog/1"}) + "\n")
    graph.write_text(json.dumps({"format": "SHIFT.OfflineResourceDependencyGraph/1"}) + "\n")
    return catalog, graph


def test_load_track_command_writes_high_level_contract(monkeypatch, tmp_path):
    catalog, graph = _write_contracts(tmp_path)
    output = tmp_path / "track_load.json"
    calls = {}

    def fake_load(catalog_value, graph_value, *, track):
        calls["catalog"] = catalog_value
        calls["graph"] = graph_value
        calls["track"] = track
        return {
            "format": "SHIFT.OfflineTrackLoad/1",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(cli, "load_track", fake_load)
    args = cli.build_parser().parse_args([
        "load-track",
        str(catalog),
        str(graph),
        "--track",
        "Silverstone_Era3_GrandPrix",
        "-o",
        str(output),
    ])

    assert args.fn(args) == 0
    assert calls["track"] == "Silverstone_Era3_GrandPrix"
    assert calls["catalog"]["format"] == "SHIFT.OfflineResourceCatalog/1"
    assert calls["graph"]["format"] == "SHIFT.OfflineResourceDependencyGraph/1"
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["format"] == "SHIFT.OfflineTrackLoad/1"
    assert persisted["ready"] is True


def test_load_vehicle_command_returns_two_when_blocked(monkeypatch, tmp_path):
    catalog, graph = _write_contracts(tmp_path)
    output = tmp_path / "vehicle_load.json"

    monkeypatch.setattr(
        cli,
        "load_vehicle",
        lambda catalog_value, graph_value, *, vehicle: {
            "format": "SHIFT.OfflineVehicleLoad/1",
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["vehicle.cdf-missing"],
        },
    )
    args = cli.build_parser().parse_args([
        "load-vehicle",
        str(catalog),
        str(graph),
        "--vehicle",
        "BMW_M3_E36",
        "-o",
        str(output),
    ])

    assert args.fn(args) == 2
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["format"] == "SHIFT.OfflineVehicleLoad/1"
    assert persisted["ready"] is False
    assert persisted["blocking_reasons"] == ["vehicle.cdf-missing"]


def test_parser_exposes_load_track_and_load_vehicle_commands():
    parser = cli.build_parser()

    track = parser.parse_args([
        "load-track",
        "catalog.json",
        "graph.json",
        "--track",
        "Silverstone_Era3_GrandPrix",
        "-o",
        "track.json",
    ])
    assert track.fn is cli.cmd_load_track
    assert track.track == "Silverstone_Era3_GrandPrix"

    vehicle = parser.parse_args([
        "load-vehicle",
        "catalog.json",
        "graph.json",
        "--vehicle",
        "BMW_M3_E36",
        "-o",
        "vehicle.json",
    ])
    assert vehicle.fn is cli.cmd_load_vehicle
    assert vehicle.vehicle == "BMW_M3_E36"
