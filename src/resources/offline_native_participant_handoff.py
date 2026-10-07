"""Transport existing participant runtime evidence through the offline native handoff.

This module never creates participant observations or promotes resource readiness.
It copies already-ready runtime identity evidence byte-for-byte, binds the copied
artifact by SHA-256, and records participant readiness as a separate runtime axis.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

HANDOFF_FORMAT = "SHIFT.OfflineNativeResourceHandoff/1"
PARTICIPANT_FORMAT = "SHIFT.NativePhysicsParticipantRuntimeEvidence/1"
ARTIFACT_NAME = "native_physics_participant_runtime_evidence.json"


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _validate_participant(value: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if value.get("format") != PARTICIPANT_FORMAT:
        blockers.append("participant-runtime-evidence:invalid-format")
    if value.get("version") != 1:
        blockers.append("participant-runtime-evidence:invalid-version")
    if value.get("ready") is not True:
        blockers.append("participant-runtime-evidence:not-ready")
    if value.get("registry_selector_identity_join_proven") is not True:
        blockers.append("participant-runtime-evidence:identity-join-not-proven")
    if value.get("participant_instance_ready") is not True:
        blockers.append("participant-runtime-evidence:instance-not-ready")
    if value.get("blocking_reasons") not in (None, []):
        blockers.append("participant-runtime-evidence:blocking-reasons-present")
    return blockers


def attach_participant_runtime_evidence_files(
    handoff_path: str | Path,
    participant_evidence_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Attach exact ready participant evidence without changing resource readiness."""
    handoff_file = Path(handoff_path)
    handoff = _load_object(handoff_file)
    if handoff.get("format") != HANDOFF_FORMAT:
        raise ValueError(f"handoff must be {HANDOFF_FORMAT}")

    source = Path(participant_evidence_path)
    destination = Path(output_dir) / ARTIFACT_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)

    blockers: list[str] = []
    participant: dict[str, Any] | None = None
    source_bytes: bytes | None = None
    try:
        source_bytes = source.read_bytes()
        decoded = json.loads(source_bytes.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("participant evidence must be a JSON object")
        participant = decoded
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        blockers.append(
            f"participant-runtime-evidence:file-error:{type(exc).__name__}:{exc}"
        )

    if participant is not None:
        blockers.extend(_validate_participant(participant))

    artifacts = dict(handoff.get("artifacts") or {})
    artifacts.pop("participant_runtime_evidence", None)

    if blockers:
        try:
            destination.unlink(missing_ok=True)
        except OSError as exc:
            blockers.append(
                f"participant-runtime-evidence:stale-artifact-remove-error:{type(exc).__name__}:{exc}"
            )
    elif source_bytes is not None:
        try:
            destination.write_bytes(source_bytes)
            copied_bytes = destination.read_bytes()
        except OSError as exc:
            blockers.append(
                f"participant-runtime-evidence:copy-error:{type(exc).__name__}:{exc}"
            )
        else:
            source_sha = _sha256_bytes(source_bytes)
            copied_sha = _sha256_bytes(copied_bytes)
            if copied_bytes != source_bytes or copied_sha != source_sha:
                blockers.append("participant-runtime-evidence:copy-sha256-mismatch")
                try:
                    destination.unlink(missing_ok=True)
                except OSError:
                    pass
            else:
                artifacts["participant_runtime_evidence"] = {
                    "path": str(destination),
                    "sha256": copied_sha,
                    "source_sha256": source_sha,
                    "bytes_preserved": True,
                }

    blockers = list(dict.fromkeys(blockers))
    participant_ready = not blockers and "participant_runtime_evidence" in artifacts

    updated = dict(handoff)
    updated["artifacts"] = artifacts
    updated["participant_runtime_identity_evaluated"] = True
    updated["participant_runtime_identity_ready"] = participant_ready
    updated["participant_runtime_identity_blocking_reasons"] = blockers

    boundary = dict(handoff.get("boundary") or {})
    boundary["participant_runtime_identity_evaluated"] = True
    boundary["participant_runtime_identity_ready"] = participant_ready
    boundary["participant_runtime_evidence_transported"] = participant_ready
    boundary["participant_runtime_evidence_created"] = False
    boundary["participant_runtime_evidence_bytes_preserved"] = participant_ready
    boundary["participant_runtime_identity_changes_resource_readiness"] = False
    boundary["runtime_execution_claimed"] = False
    updated["boundary"] = boundary

    handoff_file.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return updated


__all__ = [
    "ARTIFACT_NAME",
    "HANDOFF_FORMAT",
    "PARTICIPANT_FORMAT",
    "attach_participant_runtime_evidence_files",
]
