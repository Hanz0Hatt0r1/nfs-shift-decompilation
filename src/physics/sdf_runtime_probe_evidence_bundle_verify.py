"""Strict verifier for portable SDF runtime probe evidence bundles."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import stat
import zipfile
from pathlib import Path
from typing import Any, Mapping

from sdf_runtime_probe_capture_session import validate_capture_session_id
from sdf_runtime_probe_evidence_bundle import (
    FORMAT as BUNDLE_FORMAT,
    MANIFEST_NAME,
    TIMELINE_FORMAT,
)

FORMAT = "SHIFT.SDFRuntimeProbeEvidenceBundleVerification/1"

_ALLOWED_PATTERNS = (
    "relation_state_mutation_events.jsonl",
    "relation_state_mutation_timeline.json",
    "frame_entry_*.json",
    "pre_solve_*.json",
    "provider_pre_*_*.json",
    "provider_post_*_*.json",
    "scalar_reset_events.jsonl",
    "provider_reset_effects.jsonl",
    "post_solve_*.json",
)

_REQUIRED_CAPTURE_FILES = (
    "relation_state_mutation_events.jsonl",
    "relation_state_mutation_timeline.json",
)

_FORBIDDEN_NAMES = {
    "shift.exe",
    "attach.gdb",
    "probe_manifest.json",
    "provider_capture_preflight.json",
}

_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_EXPECTED_MODE = stat.S_IFREG | 0o644


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_root_name(name: str) -> bool:
    if not name or name.startswith(("/", "\\")):
        return False
    if "/" in name or "\\" in name:
        return False
    if name in (".", ".."):
        return False
    return Path(name).name == name


def _allowed_evidence_name(name: str) -> bool:
    if not _safe_root_name(name):
        return False
    if name.lower() in _FORBIDDEN_NAMES:
        return False
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in _ALLOWED_PATTERNS)


def _manifest_object(raw: bytes) -> dict[str, Any]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest top-level JSON value must be an object")
    return payload


def _timeline_object(raw: bytes) -> dict[str, Any]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("timeline top-level JSON value must be an object")
    return payload


def _evidence_records(
    name: str,
    raw: bytes,
) -> tuple[list[tuple[str, Mapping[str, Any]]], list[str]]:
    records: list[tuple[str, Mapping[str, Any]]] = []
    errors: list[str] = []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [], [
            f"capture-session-json-invalid:{name}:"
            f"{type(exc).__name__}:{exc}"
        ]

    if name.endswith(".jsonl"):
        for line_number, raw_line in enumerate(text.splitlines(), 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"capture-session-json-invalid:{name}:{line_number}:"
                    f"{type(exc).__name__}:{exc}"
                )
                continue
            if not isinstance(payload, Mapping):
                errors.append(
                    f"capture-session-json-object-required:"
                    f"{name}:{line_number}"
                )
                continue
            records.append((f"{name}:{line_number}", payload))
        return records, errors

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [], [
            f"capture-session-json-invalid:{name}:"
            f"{type(exc).__name__}:{exc}"
        ]
    if not isinstance(payload, Mapping):
        return [], [f"capture-session-json-object-required:{name}"]
    return [(name, payload)], []


def verify_sdf_runtime_probe_evidence_bundle(
    archive_path: str | Path,
) -> dict[str, Any]:
    archive = Path(archive_path).resolve()
    errors: list[str] = []
    archive_size = None
    archive_sha256 = None
    manifest: dict[str, Any] | None = None
    file_rows: list[Mapping[str, Any]] = []
    package_ready = False
    capture_ready = False
    capture_status = None
    capture_session_required = False
    capture_session_id = None
    evidence_payloads: dict[str, bytes] = {}

    if not archive.is_file():
        errors.append(f"archive-missing:{archive}")
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "package_ready": False,
            "capture_ready": False,
            "evidence_ready": False,
            "archive": {
                "path": str(archive),
                "size": None,
                "sha256": None,
            },
            "file_count": 0,
            "errors": errors,
        }

    archive_bytes = archive.read_bytes()
    archive_size = len(archive_bytes)
    archive_sha256 = _sha256(archive_bytes)

    try:
        bundle = zipfile.ZipFile(archive, mode="r")
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"archive-invalid:{type(exc).__name__}:{exc}")
    else:
        with bundle:
            infos = bundle.infolist()
            names = [info.filename for info in infos]
            seen: set[str] = set()
            for name in names:
                if name in seen:
                    errors.append(f"duplicate-zip-entry:{name}")
                seen.add(name)
                if not _safe_root_name(name):
                    errors.append(f"unsafe-zip-entry:{name}")

            if names.count(MANIFEST_NAME) != 1:
                errors.append(
                    f"manifest-entry-count:{names.count(MANIFEST_NAME)}"
                )
            else:
                try:
                    manifest = _manifest_object(bundle.read(MANIFEST_NAME))
                except (
                    KeyError,
                    UnicodeDecodeError,
                    ValueError,
                    json.JSONDecodeError,
                ) as exc:
                    errors.append(
                        f"manifest-invalid:{type(exc).__name__}:{exc}"
                    )

            for info in infos:
                if info.date_time != _FIXED_ZIP_TIMESTAMP:
                    errors.append(
                        f"entry-timestamp-mismatch:{info.filename}"
                    )
                if info.compress_type != zipfile.ZIP_STORED:
                    errors.append(
                        f"entry-compression-mismatch:{info.filename}"
                    )
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode != _EXPECTED_MODE:
                    errors.append(f"entry-mode-mismatch:{info.filename}")

            if manifest is not None:
                if manifest.get("format") != BUNDLE_FORMAT:
                    errors.append("bundle-format-mismatch")
                if manifest.get("version") != 1:
                    errors.append("bundle-version-mismatch")

                files = manifest.get("files")
                if not isinstance(files, list):
                    errors.append("manifest-files-invalid")
                    files = []
                file_rows = [
                    row
                    for row in files
                    if isinstance(row, Mapping)
                ]
                if len(file_rows) != len(files):
                    errors.append("manifest-file-row-invalid")

                declared_count = manifest.get("file_count")
                if declared_count != len(file_rows):
                    errors.append("manifest-file-count-mismatch")

                declared_paths: list[str] = []
                declared_seen: set[str] = set()
                for index, row in enumerate(file_rows):
                    path = row.get("path")
                    if not isinstance(path, str):
                        errors.append(
                            f"manifest-file-path-invalid:{index}"
                        )
                        continue
                    declared_paths.append(path)
                    if path in declared_seen:
                        errors.append(
                            f"duplicate-manifest-file:{path}"
                        )
                    declared_seen.add(path)

                    if not _allowed_evidence_name(path):
                        errors.append(
                            f"manifest-file-not-allowed:{path}"
                        )
                        continue
                    if path not in seen:
                        errors.append(
                            f"manifest-file-missing-from-archive:{path}"
                        )
                        continue

                    data = bundle.read(path)
                    evidence_payloads[path] = data
                    if row.get("size") != len(data):
                        errors.append(f"file-size-mismatch:{path}")
                    if row.get("sha256") != _sha256(data):
                        errors.append(f"file-sha256-mismatch:{path}")

                expected_entries = set(declared_paths) | {MANIFEST_NAME}
                for name in seen - expected_entries:
                    errors.append(f"archive-extra-entry:{name}")
                for name in expected_entries - seen:
                    errors.append(f"archive-missing-entry:{name}")

                for required in _REQUIRED_CAPTURE_FILES:
                    if required not in declared_seen:
                        errors.append(
                            f"required-capture-file-missing:{required}"
                        )

                policy = manifest.get("archive_policy")
                expected_policy = {
                    "entry_order": "lexicographic-path",
                    "compression": "stored",
                    "fixed_timestamp": "1980-01-01T00:00:00",
                    "fixed_mode": "0644",
                    "includes_executable": False,
                    "includes_attach_script": False,
                    "includes_probe_manifest": False,
                    "includes_preflight_manifest": False,
                }
                if policy != expected_policy:
                    errors.append("archive-policy-mismatch")

                expected_order = [
                    MANIFEST_NAME,
                    *sorted(declared_paths),
                ]
                if names != expected_order:
                    errors.append("archive-entry-order-mismatch")

                package_ready = manifest.get("ready") is True
                capture_ready = manifest.get("capture_ready") is True
                capture_status = manifest.get("capture_status")

                if "relation_state_mutation_timeline.json" in seen:
                    try:
                        timeline = _timeline_object(
                            bundle.read(
                                "relation_state_mutation_timeline.json"
                            )
                        )
                    except (
                        KeyError,
                        UnicodeDecodeError,
                        ValueError,
                        json.JSONDecodeError,
                    ) as exc:
                        errors.append(
                            f"timeline-invalid:{type(exc).__name__}:{exc}"
                        )
                    else:
                        if timeline.get("format") != TIMELINE_FORMAT:
                            errors.append("timeline-format-mismatch")
                        timeline_ready = (
                            timeline.get("format") == TIMELINE_FORMAT
                            and timeline.get("ready") is True
                        )
                        if capture_ready != timeline_ready:
                            errors.append(
                                "manifest-timeline-readiness-mismatch"
                            )
                        if capture_status != timeline.get("status"):
                            errors.append(
                                "manifest-timeline-status-mismatch"
                            )

                manifest_session_flag_present = (
                    "capture_session_required" in manifest
                )
                manifest_session_id_present = (
                    "capture_session_id" in manifest
                )

                session_records: list[
                    tuple[str, Mapping[str, Any]]
                ] = []
                session_parse_errors: list[str] = []
                for path in declared_paths:
                    raw = evidence_payloads.get(path)
                    if raw is None:
                        continue
                    records, record_errors = _evidence_records(
                        path,
                        raw,
                    )
                    session_records.extend(records)
                    session_parse_errors.extend(record_errors)

                evidence_session_present = any(
                    record.get("capture_session_id") is not None
                    for _, record in session_records
                )
                session_aware = (
                    manifest_session_flag_present
                    or manifest_session_id_present
                    or evidence_session_present
                )
                if session_aware:
                    capture_session_required = True
                    errors.extend(session_parse_errors)

                    if manifest.get("capture_session_required") is not True:
                        errors.append(
                            "manifest-capture-session-required-invalid"
                        )

                    raw_manifest_session_id = manifest.get(
                        "capture_session_id"
                    )
                    if raw_manifest_session_id is None:
                        errors.append(
                            "manifest-capture-session-id-missing"
                        )
                    else:
                        try:
                            capture_session_id = (
                                validate_capture_session_id(
                                    raw_manifest_session_id
                                )
                            )
                        except (TypeError, ValueError):
                            errors.append(
                                "manifest-capture-session-id-invalid"
                            )

                    if capture_session_id is None:
                        for _, record in session_records:
                            raw_session_id = record.get(
                                "capture_session_id"
                            )
                            if raw_session_id is None:
                                continue
                            try:
                                capture_session_id = (
                                    validate_capture_session_id(
                                        raw_session_id
                                    )
                                )
                            except (TypeError, ValueError):
                                continue
                            break

                    if not session_records:
                        errors.append("capture-session-records-missing")

                    for label, record in session_records:
                        raw_session_id = record.get(
                            "capture_session_id"
                        )
                        if raw_session_id is None:
                            errors.append(
                                f"capture-session-id-missing:{label}"
                            )
                            continue
                        try:
                            normalized_session_id = (
                                validate_capture_session_id(
                                    raw_session_id
                                )
                            )
                        except (TypeError, ValueError):
                            errors.append(
                                f"capture-session-id-invalid:{label}"
                            )
                            continue
                        if (
                            capture_session_id is not None
                            and normalized_session_id
                            != capture_session_id
                        ):
                            errors.append(
                                f"capture-session-id-mismatch:{label}"
                            )

                    if capture_session_id is None:
                        errors.append("capture-session-id-unresolved")

    ready = not errors
    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "package_ready": package_ready,
        "capture_ready": capture_ready,
        "evidence_ready": (
            ready and package_ready and capture_ready
        ),
        "archive": {
            "path": str(archive),
            "size": archive_size,
            "sha256": archive_sha256,
        },
        "file_count": len(file_rows),
        "errors": errors,
    }
    if capture_session_required:
        report["capture_session_required"] = True
        report["capture_session_id"] = capture_session_id
    return report


__all__ = [
    "FORMAT",
    "verify_sdf_runtime_probe_evidence_bundle",
]
