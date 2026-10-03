from __future__ import annotations

import importlib.util
from pathlib import Path

import offline_native_vehicle as vehicle


def test_blocked_participant_boundary_blocks_offline_vehicle_build(monkeypatch):
    monkeypatch.setattr(
        vehicle,
        "build_vehicle_physics_resource_manifest",
        lambda *args, **kwargs: {
            "format": "SHIFT.VehiclePhysicsResourceManifest/1",
            "ready": True,
            "blocking_reasons": [],
            "source_archive": "Car.bff",
        },
    )
    monkeypatch.setattr(
        vehicle,
        "build_bmw_m3_runtime_compat_manifest",
        lambda manifest: {
            "format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        vehicle,
        "build_native_physics_participant_boundary",
        lambda: {
            "format": "SHIFT.NativePhysicsParticipantBoundary/1",
            "ready": False,
            "status": "blocked",
            "blocking_reasons": ["registry:not-ready"],
            "participant_instance_ready": False,
        },
    )

    report = vehicle.build_native_vehicle({}, {"vehicle": "Car"}, {})

    assert report["resource_ready"] is True
    assert report["participant_structural_ready"] is False
    assert report["runtime_physics_contract_ready"] is True
    assert report["native_vehicle_runtime_ready"] is False
    assert report["status"] == "participant-structural-blocked"
    assert "participant-boundary:registry:not-ready" in report["blocking_reasons"]
    assert report["boundary"]["participant_instance_invented"] is False


def test_vehicle_cli_returns_nonzero_when_participant_structure_is_blocked(
    monkeypatch,
    tmp_path,
):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "build_native_vehicle_cli",
        root / "tools" / "build_native_vehicle.py",
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    monkeypatch.setattr(
        cli,
        "build_native_vehicle_files",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "status": "participant-structural-blocked",
            "resource_ready": True,
            "participant_structural_ready": False,
            "runtime_physics_contract_ready": True,
            "native_vehicle_runtime_ready": False,
            "blocking_reasons": ["participant-boundary:registry:not-ready"],
            "artifacts": {},
        },
    )

    rc = cli.main([
        "catalog.json",
        "bootstrap.json",
        "physics.json",
        "-o",
        str(tmp_path / "out"),
    ])
    assert rc == 2
