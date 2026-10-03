from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from offline_native_vehicle import FORMAT, build_native_vehicle, build_native_vehicle_files


KINDS = ("cdf", "edf", "gdf", "sdf", "tbf", "bbf")
RUNTIME_KINDS = {"cdf", "edf", "gdf", "sdf"}


def _inputs(vehicle: str = "BMW_M3_E36"):
    archive_id = "vehicle-archive"
    resources = []
    roots = {}
    entries = {}
    profile_resources = {}
    for index, kind in enumerate(KINDS, 10):
        resource_id = f"{archive_id}#{index}"
        path = f"vehicles/physics/{kind}/fixture.{kind}"
        decoded_sha = (f"{index:02x}" * 32)[:64]
        raw_sha = (f"{index + 32:02x}" * 32)[:64]
        resources.append({
            "id": resource_id,
            "archive_id": archive_id,
            "archive_name": f"{vehicle}.bff",
            "index": index,
            "path": path,
            "normalized_path": path.lower(),
            "extension": f".{kind}",
            "compression_type": 2,
            "compressed_size": 100 + index,
            "uncompressed_size": 200 + index,
        })
        roots[f".{kind}"] = resource_id
        entries[kind] = {
            "archive_path": path,
            "index": index,
            "type": 2,
            "compressed_size": 100 + index,
            "uncompressed_size": 200 + index,
            "decoded_sha256": decoded_sha,
            "raw_sha256": raw_sha,
        }
        if kind in RUNTIME_KINDS:
            profile_resources[kind] = {"sha256": decoded_sha}

    catalog = {
        "format": "SHIFT.OfflineResourceCatalog/1",
        "resources": resources,
    }
    bootstrap = {
        "format": "SHIFT.SceneVehicleBootstrap/1",
        "ready": True,
        "vehicle": vehicle,
        "selected_archives": {
            "vehicle": {
                "id": archive_id,
                "archive_name": f"{vehicle}.bff",
            }
        },
        "roots": {"vehicle": roots},
    }
    physics = {
        "format": "SHIFT.VehiclePhysicsBundleExtractor/1",
        "ready": True,
        "source": {"bff": f"/retail/{vehicle}.bff"},
        "entries": entries,
        "profile": {
            "format": "SHIFT.VehiclePhysicsAssetGraph/1",
            "ready": True,
            "resources": profile_resources,
            "summary": {
                "sdf_bodies": 11,
                "sdf_joint_hinge_count": 4,
                "sdf_bar_count": 20,
            },
        },
    }
    return catalog, bootstrap, physics


def test_bmw_build_emits_current_runtime_physics_contract():
    report = build_native_vehicle(*_inputs())

    assert report["format"] == FORMAT
    assert report["status"] == "runtime-physics-contract-ready"
    assert report["resource_ready"] is True
    assert report["participant_structural_ready"] is True
    assert report["runtime_physics_contract_ready"] is True
    assert report["native_vehicle_runtime_ready"] is False
    assert report["vehicle_physics_manifest"]["ready"] is True
    assert report["participant_boundary"]["ready"] is True
    assert report["participant_boundary"]["participant_instance_ready"] is False
    assert report["native_physics_compatibility"]["ready"] is True
    assert report["boundary"]["participant_structural_boundary_evaluated"] is True
    assert report["boundary"]["participant_runtime_identity_evaluated"] is False
    assert report["boundary"]["participant_instance_invented"] is False
    assert report["boundary"]["runtime_execution_claimed"] is False


def test_non_bmw_build_keeps_generic_resource_ready_but_runtime_blocked():
    report = build_native_vehicle(*_inputs("Ford_Mustang_2010"))

    assert report["status"] == "resource-ready-runtime-physics-blocked"
    assert report["resource_ready"] is True
    assert report["participant_structural_ready"] is True
    assert report["runtime_physics_contract_ready"] is False
    assert report["native_vehicle_runtime_ready"] is False
    assert (
        "runtime-physics:native-runtime-currently-accepts-bmw-m3-e36-only"
        in report["blocking_reasons"]
    )
    assert report["boundary"]["non_bmw_runtime_compatibility_invented"] is False


def test_file_builder_writes_native_manifest_only_when_exact_runtime_contract_ready(tmp_path):
    for vehicle, expect_native in (("BMW_M3_E36", True), ("Ford_Mustang_2010", False)):
        catalog_value, bootstrap_value, physics_value = _inputs(vehicle)
        root = tmp_path / vehicle
        root.mkdir()
        catalog = root / "catalog.json"
        bootstrap = root / "bootstrap.json"
        physics = root / "physics.json"
        for path, value in (
            (catalog, catalog_value),
            (bootstrap, bootstrap_value),
            (physics, physics_value),
        ):
            path.write_text(json.dumps(value), encoding="utf-8")

        out = root / "out"
        report = build_native_vehicle_files(catalog, bootstrap, physics, out)
        assert (out / "vehicle_physics_resource_manifest.json").is_file()
        assert (out / "native_physics_participant_boundary.json").is_file()
        assert (out / "native_vehicle_build.json").is_file()
        assert (out / "native_physics_manifest.json").is_file() is expect_native
        assert "participant_boundary" in report["artifacts"]
        assert ("native_physics_manifest" in report["artifacts"]) is expect_native


def test_cli_can_require_current_runtime_physics_contract(tmp_path):
    catalog_value, bootstrap_value, physics_value = _inputs("Ford_Mustang_2010")
    catalog = tmp_path / "catalog.json"
    bootstrap = tmp_path / "bootstrap.json"
    physics = tmp_path / "physics.json"
    for path, value in (
        (catalog, catalog_value),
        (bootstrap, bootstrap_value),
        (physics, physics_value),
    ):
        path.write_text(json.dumps(value), encoding="utf-8")

    command = [
        sys.executable,
        "tools/build_native_vehicle.py",
        str(catalog),
        str(bootstrap),
        str(physics),
        "-o",
        str(tmp_path / "out"),
        "--require-runtime-physics-contract",
    ]
    completed = subprocess.run(command, cwd=Path(__file__).resolve().parents[1], check=False)
    assert completed.returncode == 2
    report = json.loads((tmp_path / "out" / "native_vehicle_build.json").read_text())
    assert report["resource_ready"] is True
    assert report["participant_structural_ready"] is True
    assert report["runtime_physics_contract_ready"] is False
