from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import offline_native_vehicle as vehicle


def _observation() -> dict:
    return {
        "format": "SHIFT.NativePhysicsParticipantObservation/1",
        "version": 1,
        "ready": True,
        "verification_scope": "synthetic-regression-fixture",
        "manager_registry": {
            "global_instance": "DAT_00c109e0",
            "participant_pointer_token": "0x12345678",
            "registry_index": 7,
            "registry_index_source": "PhysicsParticipant+0x3c",
            "registry_index_source_offset": 0x3C,
            "participant_descriptor_type": 3,
        },
        "selector": {
            "global_instance": "DAT_00bbc600",
            "candidate_ready_offset": 0x74,
            "candidate_ready_value": 0,
        },
        "igphasevehicle_selection": {
            "participant_pointer_token": "0x12345678",
            "selector_ordinal": 2,
            "process_state": 1,
            "pointer_slot": "IGPhaseVehicle+0x450",
            "ordinal_slot": "IGPhaseVehicle+0x454",
            "state_slot": "IGPhaseVehicle+0x45c",
        },
        "join": {
            "same_participant_pointer_proven": True,
            "manager_registry_identity_observed": True,
            "igphasevehicle_selection_observed": True,
        },
    }


def _install_ready_resource_stages(monkeypatch) -> None:
    monkeypatch.setattr(
        vehicle,
        "build_vehicle_physics_resource_manifest",
        lambda *args, **kwargs: {
            "format": "SHIFT.VehiclePhysicsResourceManifest/1",
            "ready": True,
            "blocking_reasons": [],
            "source_archive": "BMW_M3_E36.bff",
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


def _write_minimal_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    catalog = tmp_path / "catalog.json"
    bootstrap = tmp_path / "bootstrap.json"
    physics = tmp_path / "physics.json"
    for path, value in (
        (catalog, {}),
        (bootstrap, {"vehicle": "BMW_M3_E36"}),
        (physics, {}),
    ):
        path.write_text(json.dumps(value), encoding="utf-8")
    return catalog, bootstrap, physics


def test_exact_runtime_observation_closes_only_participant_identity_gate(monkeypatch):
    _install_ready_resource_stages(monkeypatch)

    report = vehicle.build_native_vehicle(
        {},
        {"vehicle": "BMW_M3_E36"},
        {},
        participant_observation=_observation(),
    )

    assert report["resource_ready"] is True
    assert report["participant_structural_ready"] is True
    assert report["participant_runtime_identity_evaluated"] is True
    assert report["participant_runtime_identity_ready"] is True
    assert report["runtime_physics_contract_ready"] is True
    assert report["native_vehicle_runtime_ready"] is False
    assert report["participant_runtime_evidence"]["participant_registry_index"] == 7
    assert report["participant_runtime_evidence"]["selector_ordinal"] == 2
    assert report["runtime_gate_blocking_reasons"] == [
        "input-binding-runtime-evidence-required",
        "fixed-step-runtime-evidence-required",
    ]
    assert report["boundary"]["participant_instance_invented"] is False
    assert report["boundary"]["runtime_execution_claimed"] is False


def test_invalid_runtime_observation_is_a_runtime_gate_not_offline_resource_failure(
    monkeypatch,
):
    _install_ready_resource_stages(monkeypatch)
    observation = _observation()
    observation["igphasevehicle_selection"]["participant_pointer_token"] = "0x87654321"

    report = vehicle.build_native_vehicle(
        {},
        {"vehicle": "BMW_M3_E36"},
        {},
        participant_observation=observation,
    )

    assert report["resource_ready"] is True
    assert report["participant_structural_ready"] is True
    assert report["participant_runtime_identity_evaluated"] is True
    assert report["participant_runtime_identity_ready"] is False
    assert report["blocking_reasons"] == []
    assert report["participant_runtime_evidence"]["ready"] is False
    assert any(
        reason.startswith("participant-runtime-identity:runtime-evidence-join-error:")
        for reason in report["runtime_gate_blocking_reasons"]
    )
    assert "input-binding-runtime-evidence-required" in report[
        "runtime_gate_blocking_reasons"
    ]
    assert "fixed-step-runtime-evidence-required" in report[
        "runtime_gate_blocking_reasons"
    ]


def test_file_builder_persists_runtime_identity_artifact_with_input_hashes(
    monkeypatch,
    tmp_path,
):
    _install_ready_resource_stages(monkeypatch)
    catalog, bootstrap, physics = _write_minimal_inputs(tmp_path)
    observation = tmp_path / "participant-observation.json"
    observation.write_text(json.dumps(_observation()), encoding="utf-8")

    out = tmp_path / "out"
    report = vehicle.build_native_vehicle_files(
        catalog,
        bootstrap,
        physics,
        out,
        participant_observation_path=observation,
    )

    artifact = out / "native_physics_participant_runtime_evidence.json"
    assert artifact.is_file()
    assert report["participant_runtime_identity_ready"] is True
    assert "participant_runtime_evidence" in report["artifacts"]
    persisted = json.loads(artifact.read_text(encoding="utf-8"))
    assert len(persisted["provenance"]["structural_boundary_sha256"]) == 64
    assert len(persisted["provenance"]["runtime_observation_sha256"]) == 64


def test_missing_observation_path_is_runtime_only_blocker(monkeypatch, tmp_path):
    _install_ready_resource_stages(monkeypatch)
    catalog, bootstrap, physics = _write_minimal_inputs(tmp_path)
    missing = tmp_path / "missing-participant-observation.json"

    out = tmp_path / "out"
    report = vehicle.build_native_vehicle_files(
        catalog,
        bootstrap,
        physics,
        out,
        participant_observation_path=missing,
    )

    assert report["resource_ready"] is True
    assert report["participant_structural_ready"] is True
    assert report["participant_runtime_identity_evaluated"] is True
    assert report["participant_runtime_identity_ready"] is False
    assert report["blocking_reasons"] == []
    assert any(
        reason.startswith(
            "participant-runtime-identity:runtime-observation-load-error:FileNotFoundError:"
        )
        for reason in report["runtime_gate_blocking_reasons"]
    )
    artifact = out / "native_physics_participant_runtime_evidence.json"
    assert artifact.is_file()
    persisted = json.loads(artifact.read_text(encoding="utf-8"))
    assert persisted["ready"] is False
    assert len(persisted["provenance"]["structural_boundary_sha256"]) == 64
    assert "runtime_observation_sha256" not in persisted["provenance"]


def test_vehicle_cli_can_require_participant_runtime_identity(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "build_native_vehicle_runtime_identity_cli",
        root / "tools" / "build_native_vehicle.py",
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    calls = {}

    def fake_builder(*args, **kwargs):
        calls["participant_observation_path"] = kwargs.get(
            "participant_observation_path"
        )
        return {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "status": "runtime-physics-contract-ready",
            "resource_ready": True,
            "participant_structural_ready": True,
            "participant_runtime_identity_evaluated": True,
            "participant_runtime_identity_ready": False,
            "runtime_physics_contract_ready": True,
            "native_vehicle_runtime_ready": False,
            "blocking_reasons": [],
            "runtime_gate_blocking_reasons": [
                "participant-runtime-identity:not-ready"
            ],
            "artifacts": {},
        }

    monkeypatch.setattr(cli, "build_native_vehicle_files", fake_builder)
    observation = tmp_path / "participant.json"
    rc = cli.main([
        "catalog.json",
        "bootstrap.json",
        "physics.json",
        "-o",
        str(tmp_path / "out"),
        "--participant-observation",
        str(observation),
        "--require-participant-runtime-identity",
    ])

    assert rc == 2
    assert calls["participant_observation_path"] == str(observation)
