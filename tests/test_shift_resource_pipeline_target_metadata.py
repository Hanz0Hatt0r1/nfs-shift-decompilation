from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "shift_resource_pipeline_target_metadata",
    ROOT / "tools" / "shift_resource_pipeline.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

TRACK = "Silverstone_Era3_GrandPrix"
VEHICLE = "BMW_M3_E36"


def _base_report() -> dict:
    return {
        "format": "SHIFT.OfflineResourcePipelineRun/1",
        "version": 1,
        "resource_bootstrap_ready": True,
        "native_runtime_ready": False,
        "artifacts": {},
        "boundary": {
            "resource_semantics_only": True,
        },
    }


def test_selected_target_is_recorded_without_becoming_identity_proof():
    report = MODULE._record_selected_target(
        _base_report(),
        track=TRACK,
        vehicle=VEHICLE,
    )

    assert report["track"] == TRACK
    assert report["vehicle"] == VEHICLE
    assert report["boundary"]["selected_target_labels_recorded"] is True
    assert (
        report["boundary"]["selected_target_labels_are_retail_identity_proof"]
        is False
    )
    assert report["boundary"]["resource_semantics_only"] is True


def test_selected_target_survives_all_report_augmentation(tmp_path: Path):
    report = MODULE._record_selected_target(
        _base_report(),
        track=TRACK,
        vehicle=VEHICLE,
    )
    validation = {
        "status": "ready",
        "ready": True,
        "summary": {"targets": 1, "ready": 1, "blocked": 0},
        "blocking_reasons": [],
    }
    report = MODULE._augment_all_report_with_corpus_validation(
        report,
        validation,
        tmp_path,
    )
    handoff = {
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "participant_runtime_identity_evaluated": False,
        "participant_runtime_identity_ready": False,
        "participant_runtime_identity_blocking_reasons": [],
        "artifacts": {},
    }
    report = MODULE._augment_all_report_with_native_handoff(
        report,
        handoff,
        tmp_path,
        scene_set_dir=None,
        participant_runtime_evidence=None,
    )

    persisted = json.loads(
        (tmp_path / "pipeline_run.json").read_text(encoding="utf-8")
    )
    assert report["track"] == TRACK
    assert report["vehicle"] == VEHICLE
    assert persisted["track"] == TRACK
    assert persisted["vehicle"] == VEHICLE
    assert persisted["boundary"]["selected_target_labels_recorded"] is True
    assert (
        persisted["boundary"]["selected_target_labels_are_retail_identity_proof"]
        is False
    )
    assert persisted["native_resource_handoff_ready"] is True
