"""Capture-session identity and stale-artifact hygiene for the retail SDF probe."""
from __future__ import annotations

import uuid
from pathlib import Path

FORMAT = "SHIFT.SDFRuntimeProbeCaptureSession/1"

_CAPTURE_ARTIFACT_PATTERNS = (
    "relation_state_mutation_events.jsonl",
    "relation_state_mutation_timeline.json",
    "frame_entry_*.json",
    "pre_solve_*.json",
    "post_solve_*.json",
    "provider_pre_*_*.json",
    "provider_post_*_*.json",
    "scalar_reset_events.jsonl",
    "provider_reset_effects.jsonl",
    "sdf_capture_evidence.zip",
)


def new_capture_session_id() -> str:
    """Return one opaque 128-bit capture-session identifier."""
    return uuid.uuid4().hex


def validate_capture_session_id(value: str) -> str:
    """Normalize and validate a capture-session identifier."""
    text = str(value).strip().lower()
    if len(text) != 32:
        raise ValueError("capture session id must be 32 hexadecimal characters")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(
            "capture session id must be 32 hexadecimal characters"
        ) from exc
    return text


def capture_artifact_paths(output_dir: str | Path) -> list[Path]:
    """List generated evidence artifacts that would contaminate a new session."""
    root = Path(output_dir).resolve()
    if not root.is_dir():
        return []

    matched: dict[str, Path] = {}
    for pattern in _CAPTURE_ARTIFACT_PATTERNS:
        for path in root.glob(pattern):
            if path.is_file():
                matched[path.name] = path
    return [matched[name] for name in sorted(matched)]


def clear_capture_artifacts(output_dir: str | Path) -> list[str]:
    """Remove only known generated evidence artifacts and return their names."""
    removed: list[str] = []
    for path in capture_artifact_paths(output_dir):
        path.unlink()
        removed.append(path.name)
    return removed


def describe_capture_session(
    session_id: str,
    *,
    stale_artifacts_removed: list[str] | tuple[str, ...] = (),
) -> dict:
    """Build the launcher manifest fragment for one isolated capture session."""
    normalized = validate_capture_session_id(session_id)
    removed = sorted(str(name) for name in stale_artifacts_removed)
    return {
        "format": FORMAT,
        "version": 1,
        "id": normalized,
        "single_session_output": True,
        "stale_artifact_count": len(removed),
        "stale_artifacts_removed": removed,
    }


__all__ = [
    "FORMAT",
    "new_capture_session_id",
    "validate_capture_session_id",
    "capture_artifact_paths",
    "clear_capture_artifacts",
    "describe_capture_session",
]
