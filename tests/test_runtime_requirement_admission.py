from __future__ import annotations

from offline_runtime_requirements import (
    AMBIGUOUS,
    READY,
    RUNTIME_EVIDENCE_REQUIRED,
    VALIDATED_INPUT_FORMAT,
    build_runtime_requirements,
)


def _bootstrap() -> dict:
    return {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "offline_build_ready": True,
        "runtime_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "readiness": {
            "vehicle_runtime_physics_contract_ready": True,
            "vehicle_participant_runtime_identity_ready": True,
            "runtime_scene_ready": False,
        },
        "artifacts": {
            "participant_runtime_evidence": "out/participant.json",
        },
        "stages": {
            "native_vehicle": {
                "artifacts": {
                    "native_physics_manifest": {
                        "path": "out/physics.json",
                    }
                }
            }
        },
    }


def _validated(name: str, artifact: str | None = None, *, ready: bool = True) -> dict:
    return {
        "format": VALIDATED_INPUT_FORMAT,
        "version": 1,
        "name": name,
        "ready": ready,
        "artifact": artifact,
        "source": "validated explicit runtime input",
        "validation": {"ready": ready},
        "blocking_reasons": [] if ready else ["invalid-contract"],
    }


def test_validated_explicit_runtime_evidence_becomes_ready_without_relabeling_origin():
    report = build_runtime_requirements(
        _bootstrap(),
        validated_runtime_inputs={
            "camera_state": _validated("camera_state", "/workspace/camera.json"),
            "solver_frame": _validated("solver_frame", "/workspace/solver.sbfr"),
            "input_binding": _validated("input_binding", None),
        },
    )
    rows = {row["name"]: row for row in report["requirements"]}

    assert rows["camera_state"]["classification"] == READY
    assert rows["camera_state"]["satisfied"] is True
    assert rows["camera_state"]["artifact_origin"] == "explicit-validated"
    assert rows["solver_frame"]["classification"] == READY
    assert rows["input_binding"]["classification"] == READY
    assert "camera_state" not in report["summary"]["blocking"]
    assert report["boundary"]["unvalidated_explicit_path_is_ready"] is False


def test_missing_runtime_evidence_is_classified_as_runtime_evidence_required():
    report = build_runtime_requirements(_bootstrap())
    rows = {row["name"]: row for row in report["requirements"]}

    assert rows["camera_state"]["classification"] == RUNTIME_EVIDENCE_REQUIRED
    assert rows["solver_frame"]["classification"] == RUNTIME_EVIDENCE_REQUIRED
    assert rows["scene_set"]["classification"] != RUNTIME_EVIDENCE_REQUIRED
    assert "runtime-evidence-required:camera_state" in report["blocking_reasons"]
    assert any(row["name"] == "camera_state" for row in report["RUNTIME-EVIDENCE REQUIRED"])


def test_conflicting_validated_explicit_artifact_stays_ambiguous_and_cannot_override_proof():
    bootstrap = _bootstrap()
    bootstrap["readiness"]["runtime_scene_ready"] = True
    handoff = {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "ready": True,
        "scene_set_ready": True,
        "artifacts": {"scene_set_dir": "/workspace/proven-scene"},
    }
    report = build_runtime_requirements(
        bootstrap,
        runtime_scene_handoff=handoff,
        validated_runtime_inputs={
            "scene_set": _validated("scene_set", "/workspace/other-scene"),
        },
    )
    row = next(row for row in report["requirements"] if row["name"] == "scene_set")

    assert row["satisfied"] is True
    assert row["artifact"] == "/workspace/proven-scene"
    assert row["classification"] == AMBIGUOUS
    assert row["ambiguity_reasons"] == [
        "validated-explicit-conflicts-with-proven-artifact"
    ]
    assert report["ready"] is False
    assert "runtime-requirement-ambiguous:scene_set" in report["blocking_reasons"]


def test_invalid_explicit_runtime_input_does_not_turn_missing_evidence_ready():
    report = build_runtime_requirements(
        _bootstrap(),
        validated_runtime_inputs={
            "camera_state": _validated("camera_state", "/workspace/bad.json", ready=False),
        },
    )
    row = next(row for row in report["requirements"] if row["name"] == "camera_state")

    assert row["satisfied"] is False
    assert row["classification"] == RUNTIME_EVIDENCE_REQUIRED
    assert row["explicit_input_supplied"] is True
    assert row["explicit_input_validated"] is False
    assert row["explicit_validation_blocking_reasons"] == ["invalid-contract"]
