from pathlib import Path

import vehicle_physics_handoff_runtime as runtime


def _bundle(profile):
    return {
        "format": "SHIFT.VehiclePhysicsBundleExtractor/1",
        "ready": True,
        "physics_profile": "out/vehicle_physics_asset_graph.json",
        "profile": profile,
    }


def test_build_vehicle_physics_handoff_composes_sdf_profile(monkeypatch, tmp_path: Path):
    sdf = {"records": []}
    profile = {
        "details": {"sdf": sdf},
        "summary": {"sdf_bodies": 2},
        "blockers": [],
    }

    def fake_extract(bff, output, *, strict=False):
        return _bundle(profile)

    monkeypatch.setattr(runtime, "extract_bundle", fake_extract)
    monkeypatch.setattr(
        runtime,
        "build_prephysx_provider_handoff_contract",
        lambda report: {
            "format": "SHIFT.PrePhysXProviderHandoffRuntime/1",
            "ready": True,
            "errors": [],
            "selection": {
                "solver_scalar_count": 40,
                "same_dimension_candidates": [0],
                "generic_fallback_available": True,
            },
            "construction": {
                "counts": {
                    "bodies": 2,
                    "runtime_constraints": 28,
                }
            },
        },
    )

    bff = tmp_path / "BMW_M3_E36.bff"
    bff.write_bytes(b"fixture")
    out = tmp_path / "out"
    result = runtime.build_vehicle_physics_handoff(bff, out)

    assert result["ready"] is True
    assert result["summary"]["solver_scalar_count"] == 40
    assert result["summary"]["same_dimension_provider_candidates"] == [0]
    assert result["summary"]["sdf_body_count"] == 2
    assert result["summary"]["participant_gate_ready"] is True
    assert result["participant_gate"]["selection"]["callee"] == "FUN_00410ef0"
    assert result["summary"]["participant_registry_update_ready"] is True
    assert result["participant_registry_update"]["registration"]["function"] == "FUN_00713f40"
    assert result["summary"]["participant_process_reselect_ready"] is True
    assert result["participant_process_reselect"]["selection_step"]["selector_global"] == "DAT_00bbc600"
    assert result["summary"]["selector_candidate_lifecycle_ready"] is True
    assert result["summary"]["igphasevehicle_finalization_ready"] is True
    assert result["summary"]["selector_descriptor_population_ready"] is True
    assert result["igphasevehicle_finalization"]["owner"]["finalizer"] == "FUN_004d5930"
    assert result["selector_candidate_lifecycle"]["selection_scan"]["function"] == "FUN_0043af50"
    assert (out / "prephysx_provider_handoff.json").is_file()
    assert (out / "participant_process_reselect.json").is_file()
    assert (out / "selector_candidate_lifecycle.json").is_file()
    assert (out / "igphasevehicle_finalization.json").is_file()
    assert (out / "selector_descriptor_population.json").is_file()


def test_build_vehicle_physics_handoff_blocks_missing_sdf(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        runtime,
        "extract_bundle",
        lambda *args, **kwargs: {
            "ready": True,
            "profile": {"details": {}},
        },
    )

    bff = tmp_path / "vehicle.bff"
    bff.write_bytes(b"fixture")
    result = runtime.build_vehicle_physics_handoff(bff, tmp_path / "out")

    assert result["ready"] is False
    assert result["errors"] == ["sdf-report-missing-from-vehicle-profile"]
    assert result["participant_registry_update"]["ready"] is True
    assert result["participant_process_reselect"]["ready"] is True
    assert result["participant_gate"]["ready"] is True
    assert result["selector_candidate_lifecycle"]["ready"] is True
    assert result["summary"]["selector_candidate_lifecycle_ready"] is True
    assert result["summary"]["igphasevehicle_finalization_ready"] is True
    assert result["summary"]["selector_descriptor_population_ready"] is True
    assert result["summary"]["solver_scalar_count"] == 0


def test_build_vehicle_physics_handoff_blocks_missing_profile_details(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        runtime,
        "extract_bundle",
        lambda *args, **kwargs: {
            "ready": True,
            "profile": {},
        },
    )

    bff = tmp_path / "vehicle.bff"
    bff.write_bytes(b"fixture")
    result = runtime.build_vehicle_physics_handoff(bff, tmp_path / "out")

    assert result["ready"] is False
    assert result["errors"] == ["vehicle-physics-profile-details-missing"]
    assert result["summary"]["participant_gate_ready"] is True
    assert result["summary"]["participant_registry_update_ready"] is True
    assert result["summary"]["participant_process_reselect_ready"] is True
    assert result["summary"]["selector_candidate_lifecycle_ready"] is True
    assert result["summary"]["selector_descriptor_population_ready"] is True


def test_build_vehicle_physics_handoff_propagates_bundle_blockers(monkeypatch, tmp_path: Path):
    profile = {
        "details": {"sdf": {"records": []}},
        "summary": {"sdf_bodies": 0},
        "blockers": ["sdf:parse-not-ready"],
    }
    monkeypatch.setattr(
        runtime,
        "extract_bundle",
        lambda *args, **kwargs: {
            "ready": False,
            "profile": profile,
            "physics_profile": "out/vehicle_physics_asset_graph.json",
        },
    )
    monkeypatch.setattr(
        runtime,
        "build_prephysx_provider_handoff_contract",
        lambda report: {
            "ready": True,
            "errors": [],
            "selection": {
                "solver_scalar_count": 0,
                "same_dimension_candidates": [],
                "generic_fallback_available": True,
            },
            "construction": {"counts": {}},
        },
    )

    bff = tmp_path / "vehicle.bff"
    bff.write_bytes(b"fixture")
    result = runtime.build_vehicle_physics_handoff(bff, tmp_path / "out")

    assert result["ready"] is False
    assert "sdf:parse-not-ready" in result["errors"]
    assert result["summary"]["selector_candidate_lifecycle_ready"] is True
    assert result["summary"]["igphasevehicle_finalization_ready"] is True
