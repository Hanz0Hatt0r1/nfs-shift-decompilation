"""Deterministic portable bundle for full-mode SDF runtime probe evidence."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Mapping

from sdf_runtime_probe_capture_session import validate_capture_session_id

FORMAT = "SHIFT.SDFRuntimeProbeEvidenceBundle/1"
TIMELINE_FORMAT = "SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1"
DEFAULT_ARCHIVE_NAME = "sdf_capture_evidence.zip"
MANIFEST_NAME = "evidence_manifest.json"

_CAPTURE_PATTERNS = (
    ("relation-state-mutation", "relation_state_mutation_events.jsonl"),
    ("relation-state-timeline", "relation_state_mutation_timeline.json"),
    ("frame-entry", "frame_entry_*.json"),
    ("builtin-solver-entry", "pre_solve_*.json"),
    ("provider-solver-entry", "provider_pre_*_*.json"),
    ("provider-solver-return", "provider_post_*_*.json"),
    ("scalar-reset", "scalar_reset_events.jsonl"),
    ("provider-reset-effects", "provider_reset_effects.jsonl"),
    ("post-solve", "post_solve_*.json"),
)

_REQUIRED_CAPTURE_FILES = (
    "relation_state_mutation_events.jsonl",
    "relation_state_mutation_timeline.json",
)

_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON value must be an object")
    return payload


def _read_capture_records(
    path: Path,
) -> tuple[list[tuple[str, Mapping[str, Any]]], list[str]]:
    records: list[tuple[str, Mapping[str, Any]]] = []
    errors: list[str] = []
    if path.suffix.lower() == ".jsonl":
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            1,
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"capture-session-json-invalid:{path.name}:{line_number}:"
                    f"{type(exc).__name__}:{exc}"
                )
                continue
            if not isinstance(payload, Mapping):
                errors.append(
                    f"capture-session-json-object-required:"
                    f"{path.name}:{line_number}"
                )
                continue
            records.append((f"{path.name}:{line_number}", payload))
        return records, errors

    try:
        payload = _read_json_object(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(
            f"capture-session-json-invalid:{path.name}:"
            f"{type(exc).__name__}:{exc}"
        )
        return records, errors
    records.append((path.name, payload))
    return records, errors


def _probe_manifest_capture_session(
    root: Path,
) -> tuple[bool, str | None, list[str]]:
    path = root / "probe_manifest.json"
    if not path.is_file():
        return False, None, []

    try:
        payload = _read_json_object(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False, None, []
    if payload.get("format") != "SHIFT.SDFRuntimeProbeLauncher/1":
        return False, None, []

    candidates: list[Any] = []
    capture_session = payload.get("capture_session")
    if isinstance(capture_session, Mapping) and "id" in capture_session:
        candidates.append(capture_session.get("id"))
    probe = payload.get("probe")
    if isinstance(probe, Mapping) and "capture_session_id" in probe:
        candidates.append(probe.get("capture_session_id"))
    if not candidates:
        return False, None, []

    errors: list[str] = []
    normalized: list[str] = []
    for value in candidates:
        try:
            normalized.append(validate_capture_session_id(value))
        except (TypeError, ValueError):
            errors.append("probe-manifest-capture-session-id-invalid")

    session_id = normalized[0] if normalized else None
    if any(value != session_id for value in normalized[1:]):
        errors.append("probe-manifest-capture-session-id-mismatch")
    return True, session_id, errors


def _classify_capture_files(
    capture_directory: Path,
) -> list[tuple[str, Path]]:
    matched: dict[str, tuple[str, Path]] = {}
    for kind, pattern in _CAPTURE_PATTERNS:
        for path in sorted(capture_directory.glob(pattern)):
            if not path.is_file():
                continue
            matched[path.name] = (kind, path)
    return [matched[name] for name in sorted(matched)]


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=_FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def build_sdf_runtime_probe_evidence_bundle(
    capture_directory: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Package capture evidence without executable or host-local launcher files.

    The ZIP uses sorted entries, fixed timestamps, fixed permissions and stored
    payloads so identical capture bytes produce an identical archive.
    """
    root = Path(capture_directory).resolve()
    archive = (
        root / DEFAULT_ARCHIVE_NAME
        if output_path is None
        else Path(output_path).resolve()
    )

    errors: list[str] = []
    if not root.is_dir():
        errors.append(f"capture-directory-missing:{root}")

    rows: list[dict[str, Any]] = []
    payloads: list[tuple[str, bytes]] = []
    kind_counts: dict[str, int] = {}
    capture_records: list[tuple[str, Mapping[str, Any]]] = []
    capture_record_errors: list[str] = []
    declared_session = False
    capture_session_id = None

    if root.is_dir():
        (
            declared_session,
            capture_session_id,
            probe_session_errors,
        ) = _probe_manifest_capture_session(root)
        errors.extend(probe_session_errors)

        classified = _classify_capture_files(root)
        for kind, path in classified:
            data = path.read_bytes()
            payloads.append((path.name, data))
            rows.append(
                {
                    "path": path.name,
                    "kind": kind,
                    "size": len(data),
                    "sha256": _sha256(data),
                }
            )
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            records, record_errors = _read_capture_records(path)
            capture_records.extend(records)
            capture_record_errors.extend(record_errors)

        present = {row["path"] for row in rows}
        for required in _REQUIRED_CAPTURE_FILES:
            if required not in present:
                errors.append(f"missing-required-capture-file:{required}")

    evidence_session_present = any(
        record.get("capture_session_id") is not None
        for _, record in capture_records
    )
    capture_session_required = declared_session or evidence_session_present
    if capture_session_required:
        errors.extend(capture_record_errors)
        if not capture_records:
            errors.append("capture-session-records-missing")

        if capture_session_id is None:
            for _, record in capture_records:
                raw_session_id = record.get("capture_session_id")
                if raw_session_id is None:
                    continue
                try:
                    capture_session_id = validate_capture_session_id(
                        raw_session_id
                    )
                except (TypeError, ValueError):
                    continue
                break

        for label, record in capture_records:
            raw_session_id = record.get("capture_session_id")
            if raw_session_id is None:
                errors.append(f"capture-session-id-missing:{label}")
                continue
            try:
                normalized_session_id = validate_capture_session_id(
                    raw_session_id
                )
            except (TypeError, ValueError):
                errors.append(f"capture-session-id-invalid:{label}")
                continue
            if (
                capture_session_id is not None
                and normalized_session_id != capture_session_id
            ):
                errors.append(f"capture-session-id-mismatch:{label}")

        if capture_session_id is None:
            errors.append("capture-session-id-unresolved")

    timeline_path = root / "relation_state_mutation_timeline.json"
    timeline_ready = False
    timeline_status = None
    timeline_error_count = None
    if timeline_path.is_file():
        try:
            timeline = _read_json_object(timeline_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(
                f"timeline-json-invalid:{type(exc).__name__}:{exc}"
            )
        else:
            timeline_format_ready = (
                timeline.get("format") == TIMELINE_FORMAT
            )
            if not timeline_format_ready:
                errors.append("timeline-format-mismatch")
            timeline_ready = (
                timeline_format_ready
                and timeline.get("ready") is True
            )
            timeline_status = timeline.get("status")
            timeline_errors = timeline.get("errors")
            if isinstance(timeline_errors, list):
                timeline_error_count = len(timeline_errors)

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "capture_ready": timeline_ready,
        "capture_status": timeline_status,
        "capture_error_count": timeline_error_count,
        "file_count": len(rows),
        "files": rows,
        "kind_counts": {
            key: kind_counts[key]
            for key in sorted(kind_counts)
        },
        "archive_policy": {
            "entry_order": "lexicographic-path",
            "compression": "stored",
            "fixed_timestamp": "1980-01-01T00:00:00",
            "fixed_mode": "0644",
            "includes_executable": False,
            "includes_attach_script": False,
            "includes_probe_manifest": False,
            "includes_preflight_manifest": False,
        },
        "errors": errors,
    }
    if capture_session_required:
        manifest["capture_session_required"] = True
        manifest["capture_session_id"] = capture_session_id

    manifest_bytes = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, mode="w") as bundle:
        bundle.writestr(_zip_info(MANIFEST_NAME), manifest_bytes)
        for name, data in payloads:
            bundle.writestr(_zip_info(name), data)

    archive_bytes = archive.read_bytes()
    return {
        **manifest,
        "archive": {
            "path": str(archive),
            "size": len(archive_bytes),
            "sha256": _sha256(archive_bytes),
            "manifest_path": MANIFEST_NAME,
        },
    }


__all__ = [
    "FORMAT",
    "TIMELINE_FORMAT",
    "DEFAULT_ARCHIVE_NAME",
    "MANIFEST_NAME",
    "build_sdf_runtime_probe_evidence_bundle",
]
