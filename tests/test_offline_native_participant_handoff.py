from __future__ import annotations

import hashlib
import json
from pathlib import Path

from offline_native_participant_handoff import (
    ARTIFACT_NAME,
    attach_participant_runtime_evidence_files,
)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _handoff() -> dict:
    return {
        "format": "SHIFT.OfflineNativeResourceHandoff/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "resource_inputs_ready": True,
        "blocking_reasons": [],
        "artifacts": {
            "native_physics_manifest": {
                "path": "native_physics_manifest.json",
                "sha256": "a" * 64,
            }
        },
        "boundary": {
            "native_resource_inputs_joined": True,
            "participant_runtime_identity_evaluated": False,
            "runtime_execution_claimed": False,
        },
    }


def _participant(*, ready: bool = True) -> dict:
    return {
        "format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": [] if ready else ["fixture-blocked"],
        "registry_selector_identity_join_proven": ready,
        "participant_instance_ready": ready,
        "participant_pointer_token": "0x12345678",
    }


def test_ready_participant_evidence_is_copied_byte_exact_without_changing_resource_ready(
    tmp_path: Path,
):
    handoff = tmp_path / "native-handoff" / "native_resource_handoff.json"
    evidence = tmp_path / "evidence" / "participant.json"
    _write(handoff, _handoff())
    _write(evidence, _participant())
    source_bytes = evidence.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()

    report = attach_participant_runtime_evidence_files(
        handoff,
        evidence,
        handoff.parent,
    )

    copied = handoff.parent / ARTIFACT_NAME
    assert copied.read_bytes() == source_bytes
    assert report["ready"] is True
    assert report["resource_inputs_ready"] is True
    assert report["participant_runtime_identity_evaluated"] is True
    assert report["participant_runtime_identity_ready"] is True
    assert report["participant_runtime_identity_blocking_reasons"] == []
    artifact = report["artifacts"]["participant_runtime_evidence"]
    assert artifact["sha256"] == source_sha
    assert artifact["source_sha256"] == source_sha
    assert artifact["bytes_preserved"] is True
    assert report["boundary"]["participant_runtime_evidence_created"] is False
    assert (
        report["boundary"]["participant_runtime_identity_changes_resource_readiness"]
        is False
    )
    assert report["boundary"]["runtime_execution_claimed"] is False


def test_blocked_participant_evidence_is_diagnostic_only(tmp_path: Path):
    handoff = tmp_path / "native-handoff" / "native_resource_handoff.json"
    evidence = tmp_path / "participant.json"
    _write(handoff, _handoff())
    _write(evidence, _participant(ready=False))

    report = attach_participant_runtime_evidence_files(
        handoff,
        evidence,
        handoff.parent,
    )

    assert report["ready"] is True
    assert report["resource_inputs_ready"] is True
    assert report["participant_runtime_identity_ready"] is False
    assert "participant-runtime-evidence:not-ready" in report[
        "participant_runtime_identity_blocking_reasons"
    ]
    assert "participant_runtime_evidence" not in report["artifacts"]
    assert not (handoff.parent / ARTIFACT_NAME).exists()


def test_invalid_retry_removes_stale_participant_artifact(tmp_path: Path):
    handoff = tmp_path / "native-handoff" / "native_resource_handoff.json"
    valid = tmp_path / "valid.json"
    invalid = tmp_path / "invalid.json"
    _write(handoff, _handoff())
    _write(valid, _participant())
    _write(invalid, {"format": "wrong", "version": 1, "ready": True})

    first = attach_participant_runtime_evidence_files(handoff, valid, handoff.parent)
    assert first["participant_runtime_identity_ready"] is True
    copied = handoff.parent / ARTIFACT_NAME
    assert copied.is_file()

    second = attach_participant_runtime_evidence_files(handoff, invalid, handoff.parent)
    assert second["ready"] is True
    assert second["resource_inputs_ready"] is True
    assert second["participant_runtime_identity_ready"] is False
    assert "participant_runtime_evidence" not in second["artifacts"]
    assert not copied.exists()


def test_missing_evidence_is_runtime_diagnostic_only(tmp_path: Path):
    handoff = tmp_path / "native-handoff" / "native_resource_handoff.json"
    _write(handoff, _handoff())

    report = attach_participant_runtime_evidence_files(
        handoff,
        tmp_path / "missing.json",
        handoff.parent,
    )

    assert report["ready"] is True
    assert report["resource_inputs_ready"] is True
    assert report["participant_runtime_identity_ready"] is False
    assert any(
        reason.startswith("participant-runtime-evidence:file-error:FileNotFoundError:")
        for reason in report["participant_runtime_identity_blocking_reasons"]
    )
