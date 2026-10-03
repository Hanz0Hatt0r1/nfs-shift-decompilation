"""Attach existing participant runtime evidence to an offline native handoff.

This module transports already-proven runtime identity evidence. It does not
create participant observations, infer an identity, or alter scene/physics
resource admission. The original evidence bytes are copied unchanged and bound
into the handoff with SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

HANDOFF_FORMAT = "SHIFT.OfflineNativeResourceHandoff/1"
PARTICIPANT_FORMAT = "SHIFT.NativePhysicsParticipantRuntimeEvidence/1"
ARTIFACT_NAME = "native_physics_participant_runtime_evidence.json"


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_participant(value: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if value.get("format") != PARTICIPANT_FORMAT:
        blockers.append("participant-runtime-evidence:invalid-format")
    if value.get("ready") is not True:
        blockers.append("participant-runtime-evidence:not-ready")
    if value.get("registry_selector_identity_join_proven") is not True:
        blockers.append("participant-runtime-evidence:identity-join-not-proven")
    if value.get("participant_instance_ready") is not True:
        blockers.append("participant-runtime-evidence:instance-not-ready")
    return blockers


def attach_participant_runtime_evidence_files(
    handoff_path: str | Path,
    participant_evidence_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Copy exact participant evidence into handoff layout and record its digest."""
    handoff_file = Path(handoff_path)
    handoff = _load(handoff_file)
    if handoff.get("format") != HANDOFF_FORMAT:
        raise ValueError(f"handoff must be {HANDOFF_FORMAT}")

    source = Path(participant_evidence_path)
    blockers: list[str] = []
    participant: dict[str, Any] | None = None
    try:
        participant = _load(source)
    except (OSError, ValueError) as exc:
        blockers.append(
            f"participant-runtime-evidence:file-error:{type(exc).__name__}:{exc}"
        )
    if participant is not None:
        blockers.extend(_validate_participant(participant))

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    destination = out / ARTIFACT_NAME
    artifacts = dict(handoff.get("artifacts") or {})
    artifacts.pop("participant_runtime_evidence", None)
    if destination.is_file() and source.resolve() != destination.resolve():
        destination.unlink()

    if not blockers and participant is not None:
        if source.resolve() != destination.resolve():
            shutil.copyfile(source, destination)
        elif not destination.is_file():
            blockers.append("participant-runtime-evidence:file-missing-after-copy")
        if not blockers:
            digest = _sha256(destination)
            source_digest = _sha256(source)
            if digest != source_digest:
                blockers.append("participant-runtime-evidence:copy-sha256-mismatch")
            else:
                artifacts["participant_runtime_evidence"] = {
                    "path": str(destination),
                    "sha256": digest,
                    "source_sha256": source_digest,
                }

    updated = dict(handoff)
    updated["artifacts"] = artifacts
    updated["participant_runtime_identity_evaluated"] = True
    updated["participant_runtime_identity_ready"] = not blockers
    updated["participant_runtime_identity_blocking_reasons"] = list(
        dict.fromkeys(blockers)
    )
    boundary = dict(handoff.get("boundary") or {})
    boundary["participant_runtime_identity_evaluated"] = True
    boundary["participant_runtime_identity_ready"] = not blockers
    boundary["participant_runtime_evidence_transported"] = not blockers
    boundary["participant_runtime_evidence_created"] = False
    boundary["participant_runtime_evidence_bytes_preserved"] = not blockers
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
