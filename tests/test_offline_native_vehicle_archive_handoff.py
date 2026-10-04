from __future__ import annotations

import hashlib
import json
from pathlib import Path

import offline_native_vehicle as vehicle


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _inputs(tmp_path: Path, data: bytes):
    bff = tmp_path / "BMW_M3_E36.bff"
    bff.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    catalog = _write(
        tmp_path / "catalog.json",
        {
            "format": "SHIFT.OfflineResourceCatalog/1",
            "archives": [{
                "id": "vehicle-archive",
                "source": str(bff),
                "source_member": None,
                "source_kind": "bff",
                "archive_name": bff.name,
                "sha256": digest,
                "bytes": len(data),
            }],
        },
    )
    bootstrap = _write(
        tmp_path / "bootstrap.json",
        {
            "format": "SHIFT.SceneVehicleBootstrap/1",
            "selected_archives": {
                "vehicle": {
                    "id": "vehicle-archive",
                    "archive_name": bff.name,
                    "sha256": digest,
                },
            },
        },
    )
    physics = _write(tmp_path / "physics.json", {"format": "fixture"})
    return bff, catalog, bootstrap, physics


def _ready_vehicle_report():
    return {
        "format": "SHIFT.OfflineNativeVehicleBuild/1",
        "status": "runtime-physics-contract-ready",
        "resource_ready": True,
        "participant_structural_ready": True,
        "participant_runtime_identity_evaluated": False,
        "participant_runtime_identity_ready": False,
        "runtime_physics_contract_ready": True,
        "native_vehicle_runtime_ready": False,
        "blocking_reasons": [],
        "runtime_gate_blocking_reasons": [
            "participant-runtime-observation-required",
            "input-binding-runtime-evidence-required",
            "fixed-step-runtime-evidence-required",
        ],
        "vehicle_physics_manifest": {
            "format": "SHIFT.VehiclePhysicsResourceManifest/1",
            "ready": True,
            "blocking_reasons": [],
            "entries": {},
        },
        "materialized_physics_resources": {},
        "participant_boundary": {
            "format": "SHIFT.NativePhysicsParticipantBoundary/1",
            "ready": True,
            "blocking_reasons": [],
        },
        "participant_runtime_evidence": None,
        "native_physics_compatibility": {
            "format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "ready": True,
            "blocking_reasons": [],
        },
        "boundary": {},
    }


def test_native_vehicle_files_persist_exact_selected_vehicle_archive(monkeypatch, tmp_path):
    original = b"exact selected BMW BFF bytes"
    _bff, catalog, bootstrap, physics = _inputs(tmp_path, original)
    monkeypatch.setattr(vehicle, "build_native_vehicle", lambda *args, **kwargs: _ready_vehicle_report())

    report = vehicle.build_native_vehicle_files(
        catalog,
        bootstrap,
        physics,
        tmp_path / "out",
    )

    materialization = report["vehicle_archive_materialization"]
    assert materialization["ready"] is True
    assert materialization["sha256"] == hashlib.sha256(original).hexdigest()
    artifact = report["artifacts"]["vehicle_archive"]
    archive_path = Path(artifact["path"])
    assert archive_path.is_file()
    assert archive_path.read_bytes() == original
    assert artifact["sha256"] == hashlib.sha256(original).hexdigest()
    assert report["resource_ready"] is True
    assert report["boundary"]["vehicle_archive_materialization_evaluated"] is True
    assert report["boundary"]["vehicle_archive_materialization_ready"] is True
    assert report["boundary"]["vehicle_archive_materialization_claims_body_semantics"] is False


def test_native_vehicle_files_block_when_selected_source_hash_drifts(monkeypatch, tmp_path):
    original = b"catalog-time BMW bytes"
    bff, catalog, bootstrap, physics = _inputs(tmp_path, original)
    bff.write_bytes(b"changed after catalog")
    monkeypatch.setattr(vehicle, "build_native_vehicle", lambda *args, **kwargs: _ready_vehicle_report())

    report = vehicle.build_native_vehicle_files(
        catalog,
        bootstrap,
        physics,
        tmp_path / "out",
    )

    assert report["resource_ready"] is False
    assert report["status"] == "resource-blocked"
    assert report["vehicle_archive_materialization"]["ready"] is False
    assert "vehicle_archive" not in report["artifacts"]
    assert any(
        reason.startswith("vehicle-archive-materialization:")
        for reason in report["blocking_reasons"]
    )
